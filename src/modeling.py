from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import BayesianRidge, ElasticNetCV, LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_OPTIONS = [
    "Regresión lineal (OLS)",
    "ElasticNet",
    "Gradient Boosting",
    "Regresión bayesiana",
]
TARGET_MODES = [
    "Crecimiento anual % (recomendado)",
    "Variación absoluta",
    "Nivel directo (exploratorio)",
]


def _make_model(name: str, n_samples: int):
    if name == "Regresión lineal (OLS)":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ])
    if name == "ElasticNet":
        splits = max(2, min(5, n_samples // 5))
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", ElasticNetCV(
                l1_ratio=[0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95],
                alphas=np.logspace(-5, 3, 120),
                cv=TimeSeriesSplit(n_splits=splits),
                max_iter=100_000,
            )),
        ])
    if name == "Gradient Boosting":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(
                n_estimators=300,
                learning_rate=0.03,
                max_depth=2,
                min_samples_leaf=2,
                loss="huber",
                random_state=42,
            )),
        ])
    if name == "Regresión bayesiana":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", BayesianRidge()),
        ])
    raise ValueError(f"Modelo no reconocido: {name}")


def _target_transform(series: pd.Series, mode: str) -> pd.Series:
    if mode == "Crecimiento anual % (recomendado)":
        return series.pct_change(fill_method=None) * 100
    if mode == "Variación absoluta":
        return series.diff()
    return series.copy()


def _to_level(previous: float, prediction: float, mode: str) -> float:
    if mode == "Crecimiento anual % (recomendado)":
        return previous * (1 + prediction / 100.0)
    if mode == "Variación absoluta":
        return previous + prediction
    return prediction


def _fitted_levels(actual: pd.Series, transformed_prediction: np.ndarray, mode: str) -> np.ndarray:
    if mode == "Nivel directo (exploratorio)":
        return transformed_prediction
    previous = actual.shift(1).to_numpy(dtype=float)
    if mode == "Crecimiento anual % (recomendado)":
        return previous * (1 + transformed_prediction / 100.0)
    return previous + transformed_prediction


def _future_driver(data: pd.DataFrame, col: str, requested_years: np.ndarray, cutoff: int) -> np.ndarray:
    valid = data[["year", col]].copy()
    valid[col] = pd.to_numeric(valid[col], errors="coerce")
    valid = valid.dropna().sort_values("year")
    valid = valid[valid["year"] <= cutoff]
    if len(valid) < 2:
        raise ValueError(f"No hay datos suficientes para proyectar {col}.")
    # Tendencia local: usa como máximo los últimos 10 datos para reducir distorsión de décadas lejanas.
    fit = valid.tail(min(10, len(valid)))
    slope, intercept = np.polyfit(fit["year"].to_numpy(dtype=float), fit[col].to_numpy(dtype=float), 1)
    known = dict(zip(valid["year"].astype(int), valid[col].astype(float)))
    return np.array([known.get(int(y), slope * float(y) + intercept) for y in requested_years], dtype=float)


def _importance(model, feature_names: Sequence[str]) -> pd.DataFrame:
    """Resume importancia o coeficientes del estimador final.

    Los modelos lineales se entrenan después de StandardScaler, por lo que sus
    coeficientes son comparables entre predictores. Gradient Boosting reporta
    importancia relativa (reducción acumulada de la pérdida), no dirección.
    BayesianRidge añade la desviación posterior de cada coeficiente.
    """
    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_, dtype=float)
        return (
            pd.DataFrame({"Variable": list(feature_names), "Importancia": values})
            .sort_values("Importancia", ascending=False)
            .reset_index(drop=True)
        )
    if hasattr(estimator, "coef_"):
        values = np.asarray(estimator.coef_, dtype=float).reshape(-1)
        result = pd.DataFrame({
            "Variable": list(feature_names),
            "Coeficiente estandarizado": values,
        })
        if isinstance(estimator, BayesianRidge) and hasattr(estimator, "sigma_"):
            posterior_std = np.sqrt(np.clip(np.diag(estimator.sigma_), 0, None))
            result["Desv. posterior del coeficiente"] = posterior_std
        return result.sort_values(
            "Coeficiente estandarizado", key=lambda col: col.abs(), ascending=False
        ).reset_index(drop=True)
    return pd.DataFrame()


def fit_predict_model(
    data: pd.DataFrame,
    target_col: str,
    predictor_cols: Sequence[str],
    model_name: str,
    lag: int,
    horizon: int,
    target_mode: str,
    training_end_year: int,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    columns = ["year", target_col] + list(predictor_cols)
    missing = [c for c in columns if c not in data.columns]
    if missing:
        return pd.DataFrame(), {"error": f"Faltan columnas: {', '.join(missing)}"}, pd.DataFrame()

    frame = data[columns].copy().sort_values("year")
    for col in columns[1:]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame[frame["year"] <= training_end_year].copy()
    frame["target_level"] = frame[target_col]
    frame["target_model"] = _target_transform(frame[target_col], target_mode)
    for col in predictor_cols:
        frame[f"{col}_lag{lag}"] = frame[col].shift(lag)
    frame["tendencia"] = frame["year"] - frame["year"].min()
    feature_names = ["tendencia"] + [f"{c}_lag{lag}" for c in predictor_cols]
    model_frame = frame[["year", "target_level", "target_model"] + feature_names].dropna().copy()

    minimum = max(10, len(feature_names) + 5)
    if len(model_frame) < minimum:
        return pd.DataFrame(), {"error": f"Hay {len(model_frame)} observaciones completas; se requieren al menos {minimum}."}, pd.DataFrame()

    X = model_frame[feature_names]
    y = model_frame["target_model"]

    # Evaluación temporal: últimos 20%, mínimo 3 años.
    test_n = max(3, int(round(len(model_frame) * 0.20)))
    test_n = min(test_n, len(model_frame) - max(6, len(feature_names) + 2))
    validation = {}
    if test_n >= 2:
        train_X, test_X = X.iloc[:-test_n], X.iloc[-test_n:]
        train_y, test_y = y.iloc[:-test_n], y.iloc[-test_n:]
        eval_model = _make_model(model_name, len(train_X))
        eval_model.fit(train_X, train_y)
        test_pred = eval_model.predict(test_X)
        validation = {
            "r2_validacion": float(r2_score(test_y, test_pred)) if len(test_y) >= 2 else np.nan,
            "rmse_validacion": float(mean_squared_error(test_y, test_pred) ** 0.5),
            "n_validacion": int(len(test_y)),
        }

    model = _make_model(model_name, len(X))
    model.fit(X, y)
    fitted_transformed = np.asarray(model.predict(X), dtype=float)
    fitted_level = _fitted_levels(model_frame["target_level"], fitted_transformed, target_mode)

    output = pd.DataFrame({
        "year": model_frame["year"].astype(int),
        "actual": model_frame["target_level"].astype(float),
        "predicted": fitted_level,
        "type": "Histórico",
    })

    last_year = int(training_end_year)
    future_years = np.arange(last_year + 1, last_year + horizon + 1, dtype=int)
    future_X = pd.DataFrame({"tendencia": future_years - int(frame["year"].min())})
    for col in predictor_cols:
        requested_predictor_years = future_years - lag
        future_X[f"{col}_lag{lag}"] = _future_driver(data, col, requested_predictor_years, training_end_year)
    future_X = future_X[feature_names]
    future_transformed = np.asarray(model.predict(future_X), dtype=float)

    last_actual_series = data.loc[(data["year"] <= training_end_year), ["year", target_col]].copy()
    last_actual_series[target_col] = pd.to_numeric(last_actual_series[target_col], errors="coerce")
    last_actual_series = last_actual_series.dropna().sort_values("year")
    if last_actual_series.empty:
        return pd.DataFrame(), {"error": "No existe un último valor observado para reconstruir la proyección."}, pd.DataFrame()
    previous = float(last_actual_series.iloc[-1][target_col])
    future_levels = []
    for pred in future_transformed:
        previous = _to_level(previous, float(pred), target_mode)
        future_levels.append(previous)

    future = pd.DataFrame({"year": future_years, "actual": np.nan, "predicted": future_levels, "type": "Proyección"})
    output = pd.concat([output, future], ignore_index=True)

    train_pred = fitted_transformed
    estimator = model.named_steps["model"]
    model_details: dict[str, float | int | str] = {}
    if isinstance(estimator, ElasticNetCV):
        model_details.update({
            "alpha_seleccionado": float(estimator.alpha_),
            "l1_ratio_seleccionado": float(estimator.l1_ratio_),
            "variables_coeficiente_cero": int(np.isclose(estimator.coef_, 0.0).sum()),
        })
    elif isinstance(estimator, GradientBoostingRegressor):
        model_details.update({
            "numero_arboles": int(estimator.n_estimators),
            "profundidad_maxima": int(estimator.max_depth),
            "tasa_aprendizaje": float(estimator.learning_rate),
            "minimo_muestras_hoja": int(estimator.min_samples_leaf),
            "funcion_perdida": str(estimator.loss),
        })
    elif isinstance(estimator, BayesianRidge):
        model_details.update({
            "precision_ruido_alpha": float(estimator.alpha_),
            "precision_coeficientes_lambda": float(estimator.lambda_),
        })

    metrics = {
        "r2_historico": float(r2_score(y, train_pred)),
        "rmse_historico": float(mean_squared_error(y, train_pred) ** 0.5),
        "n": int(len(model_frame)),
        "ultimo_anio_entrenamiento": int(training_end_year),
        "modo_objetivo": target_mode,
        "n_validacion": int(validation.get("n_validacion", 0)),
        **validation,
        **model_details,
    }
    return output, metrics, _importance(model, feature_names)
