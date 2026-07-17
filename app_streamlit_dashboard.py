"""Dashboard Streamlit v4.1: deuda, economía y mundiales de México.

Funciones principales
---------------------
- Selección de hasta cuatro variables en la gráfica principal.
- Ocho transformaciones: original, real, base 100, log10, log10(base100),
  variación anual, variación acumulada y Z-score.
- Hitos económicos y puntos de Copas del Mundo con fase, goles a favor y contra.
- Pestaña Análisis: tendencias, cambios, elasticidades, correlaciones, rezagos y modelos.
- Comparativa internacional mediante World Development Indicators.

Ejecución:
    streamlit run app_streamlit_dashboard.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable
import math
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.modeling import MODEL_OPTIONS, TARGET_MODES, fit_predict_model

# =============================================================================
# 1) CONFIGURACIÓN
# =============================================================================

st.set_page_config(
    page_title="Deuda, economía y mundiales de México",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BG = "#124F63"
PANEL = "#124F63"
TEXT = "#F1F4F5"
MUTED = "rgba(255,255,255,0.72)"
GRID = "rgba(255,255,255,0.18)"
COLORS = ["#FFFFFF", "#FFD166", "#06D6A0", "#EF476F"]
WORLD_CUP_COLOR = "#F7B801"
ROOT = Path(__file__).resolve().parent

MASTER_PATHS = [
    ROOT / "data" / "mexico_dashboard_master.csv",
    ROOT / "mexico_dashboard_master.csv",
    Path("/mnt/data/mexico_dashboard_master.csv"),
]
FOOTBALL_PATHS = [
    ROOT / "data" / "mexico_futbol_economia_1930_2026.csv",
    ROOT / "mexico_futbol_economia_1930_2026.csv",
    Path("/mnt/data/mexico_master_streamlit_futbol_economia_1930_2026.csv"),
]
WDI_PATHS = [
    ROOT / "data" / "wdi_country_indicators.csv",
    ROOT / "wdi_country_indicators.csv",
    Path("/mnt/data/6ebee357-cfc1-4762-b809-d3578759235b_Data.csv"),
]
EVENT_PATHS = [
    ROOT / "data" / "hitos_mexico_1990_2026.csv",
    ROOT / "hitos_mexico_1990_2026.csv",
]

# Cada variable tiene una columna original y, cuando procede, su equivalente real.
VARIABLES: dict[str, dict[str, str | None]] = {
    "PIB": {
        "column": "gdp_nominal_mxn",
        "real_column": "gdp_real_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Producto Interno Bruto.",
    },
    "DEUDA TOTAL": {
        "column": "public_debt_total_mxn",
        "real_column": "real_public_debt_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Deuda pública total.",
    },
    "DEUDA INTERNA": {
        "column": "public_debt_internal_mxn",
        "real_column": "real_public_debt_internal_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Componente interno de la deuda pública.",
    },
    "DEUDA EXTERNA": {
        "column": "public_debt_external_mxn",
        "real_column": "real_public_debt_external_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Componente externo de la deuda pública convertido a pesos.",
    },
    "DEUDA / PIB": {
        "column": "debt_to_gdp_pct",
        "real_column": None,
        "unit": "% del PIB",
        "real_unit": "% del PIB",
        "description": "Deuda pública total como porcentaje del PIB.",
    },
    "DEUDA PER CÁPITA": {
        "column": "debt_per_capita_mxn",
        "real_column": "debt_per_capita_real_2018_mxn",
        "unit": "MXN corrientes por persona",
        "real_unit": "MXN de 2018 por persona",
        "description": "Deuda pública por habitante.",
    },
    "INFLACIÓN": {
        "column": "inflation_annual_pct",
        "real_column": None,
        "unit": "% promedio anual",
        "real_unit": "% promedio anual",
        "description": "Variación promedio anual del INPC.",
    },
    "INFLACIÓN DIC-DIC": {
        "column": "inflacion_dic_dic_pct",
        "real_column": None,
        "unit": "% diciembre-diciembre",
        "real_unit": "% diciembre-diciembre",
        "description": "Inflación de cierre anual, diciembre contra diciembre.",
    },
    "INFLACIÓN ACUMULADA": {
        "column": "inflation_accumulated_since_1990_pct",
        "real_column": None,
        "unit": "% acumulado desde 1990",
        "real_unit": "% acumulado desde 1990",
        "description": "Inflación acumulada desde 1990.",
    },
    "POBLACIÓN": {
        "column": "population",
        "real_column": None,
        "unit": "personas",
        "real_unit": "personas",
        "description": "Población total.",
    },
    "PIB PER CÁPITA REAL": {
        "column": "gdp_real_per_capita_2018_mxn",
        "real_column": "gdp_real_per_capita_2018_mxn",
        "unit": "MXN de 2018 por persona",
        "real_unit": "MXN de 2018 por persona",
        "description": "PIB real por habitante.",
    },
    "TIPO DE CAMBIO": {
        "column": "exchange_rate_fix_mxn_usd_avg",
        "real_column": None,
        "unit": "MXN/USD",
        "real_unit": "MXN/USD",
        "description": "Tipo de cambio promedio anual.",
    },
    "EXPORTACIONES": {
        "column": "exports_usd",
        "real_column": "exports_real_2018_mxn",
        "unit": "USD corrientes",
        "real_unit": "MXN de 2018",
        "description": "Exportaciones de bienes y servicios.",
    },
    "IMPORTACIONES": {
        "column": "imports_usd",
        "real_column": "imports_real_2018_mxn",
        "unit": "USD corrientes",
        "real_unit": "MXN de 2018",
        "description": "Importaciones de bienes y servicios.",
    },
    "REMESAS": {
        "column": "remittances_usd",
        "real_column": "remittances_real_2018_mxn",
        "unit": "USD corrientes",
        "real_unit": "MXN de 2018",
        "description": "Remesas recibidas.",
    },
    "INVERSIÓN EXTRANJERA": {
        "column": "fdi_usd",
        "real_column": "fdi_real_2018_mxn",
        "unit": "USD corrientes",
        "real_unit": "MXN de 2018",
        "description": "Inversión extranjera directa.",
    },
    "INVERSIÓN INTERNA": {
        "column": "domestic_investment_mxn",
        "real_column": "domestic_investment_real_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Formación bruta de capital / inversión doméstica.",
    },
    "INVERSIÓN TOTAL": {
        "column": "investment_total_mxn",
        "real_column": "investment_total_real_2018_mxn",
        "unit": "MXN corrientes",
        "real_unit": "MXN de 2018",
        "description": "Inversión interna más IED convertida a pesos.",
    },
    "DEFLACTOR DEL PIB": {
        "column": "gdp_deflator_index",
        "real_column": None,
        "unit": "índice, 2018=100",
        "real_unit": "índice, 2018=100",
        "description": "Deflactor implícito del PIB.",
    },
    "DESEMPLEO": {
        "column": "unemployment_pct",
        "real_column": None,
        "unit": "% de la población económicamente activa",
        "real_unit": "% de la población económicamente activa",
        "description": "Tasa de desempleo anual; prioriza la nueva serie mensual desestacionalizada.",
    },
    "POBRES": {
        "column": "poverty_pct",
        "real_column": None,
        "unit": "% de población",
        "real_unit": "% de población",
        "description": "Población en pobreza.",
    },
    "POBREZA EXTREMA": {
        "column": "extreme_poverty_pct",
        "real_column": None,
        "unit": "% de población",
        "real_unit": "% de población",
        "description": "Población en pobreza extrema.",
    },
    "DESIGUALDAD": {
        "column": "gini_index",
        "real_column": None,
        "unit": "índice",
        "real_unit": "índice",
        "description": "Índice de desigualdad; se muestra sólo si la fuente aporta datos.",
    },
    "CLASE MEDIA": {
        "column": "middle_class_pct",
        "real_column": None,
        "unit": "% de población",
        "real_unit": "% de población",
        "description": "Porcentaje de clase media cuando exista fuente.",
    },
    "RICOS / CLASE ALTA": {
        "column": "rich_or_high_class_pct",
        "real_column": None,
        "unit": "% de población",
        "real_unit": "% de población",
        "description": "Porcentaje de clase alta cuando exista fuente.",
    },
}

TRANSFORMATIONS = [
    "Valores originales",
    "Valores reales (pesos constantes)",
    "Índice Base 100",
    "Escala logarítmica (Log10)",
    "Log10(Base100)",
    "Variación anual %",
    "Variación acumulada %",
    "Z-score",
]

WDI_SERIES_BY_VARIABLE = {
    "PIB": "NY.GDP.MKTP.CD",
    "DEUDA TOTAL": "GC.DOD.TOTL.GD.ZS",
    "DEUDA / PIB": "GC.DOD.TOTL.GD.ZS",
    "INFLACIÓN": "FP.CPI.TOTL.ZG",
    "POBLACIÓN": "SP.POP.TOTL",
    "EXPORTACIONES": "NE.EXP.GNFS.CD",
    "IMPORTACIONES": "NE.IMP.GNFS.CD",
    "REMESAS": "BX.TRF.PWKR.CD.DT",
    "TIPO DE CAMBIO": "PA.NUS.FCRF",
    "INVERSIÓN EXTRANJERA": "BX.KLT.DINV.CD.WD",
    "INVERSIÓN INTERNA": "NE.GDI.TOTL.CD",
    "INVERSIÓN TOTAL": "NE.GDI.TOTL.CD",
    "DEFLACTOR DEL PIB": "NY.GDP.DEFL.ZS",
    "PIB PER CÁPITA REAL": "NY.GDP.PCAP.KD",
}

# =============================================================================
# 2) CARGA DE DATOS
# =============================================================================

def first_existing_path(paths: Iterable[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("No se encontró el archivo requerido.")


@st.cache_data(show_spinner=False)
def load_master() -> pd.DataFrame:
    df = pd.read_csv(first_existing_path(MASTER_PATHS))
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    text_columns = {
        "president", "party", "sexenio", "crisis_event", "source_flags",
        "validation_notes", "hitos_anio", "mundial_sede", "mundial_estatus_mexico",
        "mundial_fase_alcanzada", "mundial_resultado_resumen", "mundial_detalle",
        "notas_calidad_datos", "fuentes_disponibles_anio",
    }
    for col in df.columns:
        if col != "year" and col not in text_columns and df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
    # Columnas reservadas para que el selector no se rompa si aún no hay fuente.
    for col in ["gini_index", "middle_class_pct", "rich_or_high_class_pct"]:
        if col not in df.columns:
            df[col] = np.nan
    return df.dropna(subset=["year"]).sort_values("year").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_football_history() -> pd.DataFrame:
    df = pd.read_csv(first_existing_path(FOOTBALL_PATHS))
    if "anio" in df.columns:
        df["year"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    elif "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    else:
        return pd.DataFrame()
    for col in [
        "es_anio_mundial", "mundial_participo", "mundial_goles_favor",
        "mundial_goles_contra", "mundial_fase_orden", "mundial_posicion_final",
        "mundial_partidos", "mundial_ganados", "mundial_empatados", "mundial_perdidos",
        "mundial_datos_provisionales",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("year").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_wdi_long() -> pd.DataFrame:
    try:
        path = first_existing_path(WDI_PATHS)
    except FileNotFoundError:
        return pd.DataFrame()
    raw = pd.read_csv(path)
    required = {"Series Name", "Series Code", "Country Name", "Country Code"}
    if not required.issubset(raw.columns):
        return pd.DataFrame()
    year_cols = [c for c in raw.columns if re.search(r"\d{4}", str(c))]
    long = raw.melt(
        id_vars=["Series Name", "Series Code", "Country Name", "Country Code"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name="value",
    )
    long["year"] = long["year_raw"].astype(str).str.extract(r"(\d{4})")[0]
    long["year"] = pd.to_numeric(long["year"], errors="coerce").astype("Int64")
    long["value"] = pd.to_numeric(long["value"].replace("..", np.nan), errors="coerce")
    return long.rename(columns={
        "Series Name": "series_name", "Series Code": "series_code",
        "Country Name": "country_name", "Country Code": "country_code",
    })[["series_name", "series_code", "country_name", "country_code", "year", "value"]].dropna(subset=["year", "value"])

@st.cache_data(show_spinner=False)
def load_events() -> pd.DataFrame:
    try:
        path = first_existing_path(EVENT_PATHS)
    except FileNotFoundError:
        return pd.DataFrame()
    events = pd.read_csv(path)
    for col in ["anio_inicio", "anio_fin", "severidad"]:
        if col in events.columns:
            events[col] = pd.to_numeric(events[col], errors="coerce")
    return events.dropna(subset=["anio_inicio"]).sort_values(["anio_inicio", "severidad"], ascending=[True, False]).reset_index(drop=True)

# =============================================================================
# 3) PREPARACIÓN Y TRANSFORMACIONES
# =============================================================================

def variable_column(label: str, use_real: bool = False) -> tuple[str, str, bool]:
    meta = VARIABLES[label]
    original = str(meta["column"])
    real = meta.get("real_column")
    if use_real and real:
        return str(real), str(meta.get("real_unit") or meta["unit"]), True
    return original, str(meta["unit"]), False


def display_scale(series: pd.Series, unit: str, column: str) -> tuple[pd.Series, str, float]:
    s = pd.to_numeric(series, errors="coerce")
    max_abs = float(s.abs().max()) if s.notna().any() else np.nan
    if np.isnan(max_abs):
        return s, unit, 1.0
    if "%" in unit or "MXN/USD" in unit or "índice" in unit:
        return s, unit, 1.0
    if column == "population":
        return s / 1_000_000, "millones de personas", 1_000_000
    if "USD" in unit:
        if max_abs >= 1e12:
            return s / 1e12, "billones USD", 1e12
        if max_abs >= 1e9:
            return s / 1e9, "miles de millones USD", 1e9
        if max_abs >= 1e6:
            return s / 1e6, "millones USD", 1e6
    if "MXN" in unit:
        if max_abs >= 1e12:
            return s / 1e12, "billones MXN", 1e12
        if max_abs >= 1e9:
            return s / 1e9, "miles de millones MXN", 1e9
        if max_abs >= 1e6:
            return s / 1e6, "millones MXN", 1e6
    return s, unit, 1.0


def base_value(series: pd.Series, years: pd.Series, requested_year: int) -> tuple[float | None, int | None]:
    valid = pd.DataFrame({"year": years, "value": pd.to_numeric(series, errors="coerce")}).dropna()
    if valid.empty:
        return None, None
    exact = valid[valid["year"] == requested_year]
    if not exact.empty and exact.iloc[0]["value"] != 0:
        return float(exact.iloc[0]["value"]), int(exact.iloc[0]["year"])
    after = valid[(valid["year"] >= requested_year) & (valid["value"] != 0)]
    nonzero = valid[valid["value"] != 0]
    if nonzero.empty:
        return None, None
    chosen = after.iloc[0] if not after.empty else nonzero.iloc[0]
    return float(chosen["value"]), int(chosen["year"])


def transform_variable(
    data: pd.DataFrame,
    label: str,
    transformation: str,
    base_year_requested: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    use_real = transformation == "Valores reales (pesos constantes)"
    col, unit, used_real = variable_column(label, use_real=use_real)
    if col not in data.columns:
        return pd.DataFrame(), {"warning": f"{label}: falta la columna {col}."}

    temp = data[["year", col]].copy()
    temp["original"] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.drop(columns=[col]).dropna(subset=["year", "original"]).sort_values("year")
    if len(temp) < 2:
        return pd.DataFrame(), {"warning": f"{label}: no hay datos suficientes."}

    actual_base, actual_base_year = base_value(temp["original"], temp["year"], base_year_requested)
    transformed = temp["original"].copy()
    axis_label = unit
    warning = ""

    if transformation in {"Valores originales", "Valores reales (pesos constantes)"}:
        transformed, scaled_unit, scale = display_scale(temp["original"], unit, col)
        axis_label = scaled_unit
        if transformation == "Valores reales (pesos constantes)" and not used_real:
            warning = f"{label}: no tiene versión real; se conservó el indicador original."
    elif transformation == "Índice Base 100":
        if actual_base is None or actual_base == 0:
            return pd.DataFrame(), {"warning": f"{label}: no se pudo calcular base 100."}
        transformed = temp["original"] / actual_base * 100
        axis_label = "Índice base 100"
    elif transformation == "Escala logarítmica (Log10)":
        transformed = np.log10(temp["original"].where(temp["original"] > 0))
        axis_label = "Log10(valor)"
        if (temp["original"] <= 0).any():
            warning = f"{label}: valores ≤0 fueron omitidos en Log10."
    elif transformation == "Log10(Base100)":
        if actual_base is None or actual_base == 0:
            return pd.DataFrame(), {"warning": f"{label}: no se pudo calcular Log10(Base100)."}
        index_100 = temp["original"] / actual_base * 100
        transformed = np.log10(index_100.where(index_100 > 0))
        axis_label = "Log10(índice base 100)"
    elif transformation == "Variación anual %":
        transformed = temp["original"].pct_change(fill_method=None) * 100
        axis_label = "Variación anual (%)"
    elif transformation == "Variación acumulada %":
        if actual_base is None or actual_base == 0:
            return pd.DataFrame(), {"warning": f"{label}: no se pudo calcular variación acumulada."}
        transformed = (temp["original"] / actual_base - 1) * 100
        axis_label = "Variación acumulada (%)"
    elif transformation == "Z-score":
        std = temp["original"].std(ddof=0)
        if pd.isna(std) or std == 0:
            return pd.DataFrame(), {"warning": f"{label}: desviación estándar igual a cero."}
        transformed = (temp["original"] - temp["original"].mean()) / std
        axis_label = "Z-score"

    temp["transformed"] = pd.to_numeric(transformed, errors="coerce").replace([np.inf, -np.inf], np.nan)
    temp = temp.dropna(subset=["transformed"])
    info = {
        "column": col,
        "unit": unit,
        "axis_label": axis_label,
        "base_year": actual_base_year,
        "warning": warning,
        "used_real": used_real,
    }
    return temp, info


def axis_clean(title: str, show_grid: bool = True) -> dict:
    return {
        "title": {"text": title, "font": {"color": TEXT, "size": 14}},
        "showgrid": show_grid,
        "gridcolor": GRID,
        "zeroline": False,
        "showline": False,
        "ticks": "",
        "tickfont": {"color": TEXT, "size": 11},
        "automargin": True,
    }


def empty_chart(message: str, height: int = 260) -> None:
    st.markdown(
        f'<div class="empty-chart" style="height:{height}px"><div>{message}</div></div>',
        unsafe_allow_html=True,
    )


def add_event_lines(fig: go.Figure, data: pd.DataFrame) -> None:
    if "crisis_event" not in data.columns:
        return
    events = data[["year", "crisis_event"]].dropna()
    events = events[events["crisis_event"].astype(str).str.strip() != ""]
    for _, row in events.iterrows():
        year = pd.to_numeric(row["year"], errors="coerce")
        if pd.isna(year):
            continue
        fig.add_vline(x=int(year), line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.28)")


def add_world_cup_markers(
    fig: go.Figure,
    football: pd.DataFrame,
    y_values: list[float],
    year_range: tuple[int, int],
) -> None:
    if football.empty or "es_anio_mundial" not in football.columns:
        return
    cups = football[
        (football["es_anio_mundial"] == 1)
        & football["year"].between(year_range[0], year_range[1])
    ].copy()
    if cups.empty or not y_values:
        return
    finite = np.asarray([v for v in y_values if pd.notna(v) and np.isfinite(v)], dtype=float)
    if finite.size == 0:
        return
    ymin, ymax = float(finite.min()), float(finite.max())
    span = ymax - ymin
    marker_y = ymin + (span * 0.07 if span > 0 else 0.0)

    def safe(row: pd.Series, col: str, default: str = "Sin dato") -> str:
        value = row.get(col, default)
        if pd.isna(value) or str(value).strip() == "":
            return default
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    hover = []
    colors = []
    for _, row in cups.iterrows():
        provisional = " · PROVISIONAL" if safe(row, "mundial_datos_provisionales", "0") == "1" else ""
        hover.append(
            "<b>México en el Mundial " + safe(row, "year") + provisional + "</b><br>"
            + "Sede: " + safe(row, "mundial_sede") + "<br>"
            + "Estatus: " + safe(row, "mundial_estatus_mexico") + "<br>"
            + "Fase: " + safe(row, "mundial_fase_alcanzada") + "<br>"
            + "Goles a favor: " + safe(row, "mundial_goles_favor", "—") + "<br>"
            + "Goles en contra: " + safe(row, "mundial_goles_contra", "—") + "<br>"
            + safe(row, "mundial_resultado_resumen", "")
        )
        colors.append(WORLD_CUP_COLOR if safe(row, "mundial_participo", "0") == "1" else "rgba(255,255,255,0.45)")

    fig.add_trace(go.Scatter(
        x=cups["year"],
        y=[marker_y] * len(cups),
        mode="markers+text",
        text=["⚽"] * len(cups),
        textposition="top center",
        textfont={"size": 13},
        marker={"size": 9, "color": colors, "line": {"width": 1, "color": TEXT}},
        name="Mundiales de México",
        customdata=np.asarray(hover, dtype=object).reshape(-1, 1),
        hovertemplate="%{customdata[0]}<extra></extra>",
    ))


EVENT_COLORS = {
    "Devaluación / crisis": "#EF476F",
    "Crisis financiera": "#EF476F",
    "Crisis externa": "#FF8C42",
    "Pandemia": "#A78BFA",
    "Pandemia / crisis": "#A78BFA",
    "Choque petrolero / depreciación": "#F59E0B",
    "Inflación": "#FFD166",
    "Inflación / choque externo": "#FFD166",
    "Comercio": "#06D6A0",
    "Política": "#94A3B8",
}


def add_event_overlays(
    fig: go.Figure,
    events: pd.DataFrame,
    categories: list[str],
    severity_range: tuple[int, int],
    year_range: tuple[int, int],
    y_values: list[float],
    shade_periods: bool,
) -> None:
    if events.empty or not y_values:
        return
    selected = events[
        events["categoria"].isin(categories)
        & events["severidad"].between(severity_range[0], severity_range[1])
        & (events["anio_fin"] >= year_range[0])
        & (events["anio_inicio"] <= year_range[1])
    ].copy()
    if selected.empty:
        return
    finite = np.asarray([v for v in y_values if pd.notna(v) and np.isfinite(v)], dtype=float)
    if finite.size == 0:
        return
    ymax = float(finite.max())
    ymin = float(finite.min())
    span = ymax - ymin
    marker_y = ymax - (0.03 * span if span else 0)
    xs, ys, colors, hovers = [], [], [], []
    for _, row in selected.iterrows():
        start, end = int(row["anio_inicio"]), int(row["anio_fin"])
        color = EVENT_COLORS.get(str(row["categoria"]), "#FFFFFF")
        if shade_periods:
            fig.add_vrect(
                x0=start - 0.35,
                x1=end + 0.35,
                fillcolor=color,
                opacity=0.055 + 0.018 * int(row["severidad"]),
                line_width=0,
                layer="below",
            )
        fig.add_vline(x=start, line_width=1, line_dash="dot", line_color=color, opacity=0.55)
        xs.append((start + end) / 2)
        ys.append(marker_y)
        colors.append(color)
        hovers.append(
            f"<b>{row['hito']}</b><br>Periodo: {start}" + (f"–{end}" if end != start else "")
            + f"<br>Categoría: {row['categoria']}<br>Severidad: {int(row['severidad'])}/5"
            + f"<br>{row['descripcion']}<br>Fuente: {row['fuente']}"
        )
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers", name="Hitos históricos",
        marker={"symbol": "diamond", "size": 11, "color": colors, "line": {"color": TEXT, "width": 0.8}},
        customdata=np.asarray(hovers, dtype=object).reshape(-1, 1),
        hovertemplate="%{customdata[0]}<extra></extra>",
    ), secondary_y=False)


def add_football_score_trace(
    fig: go.Figure,
    football: pd.DataFrame,
    score_column: str,
    score_label: str,
    year_range: tuple[int, int],
) -> None:
    if football.empty or score_column not in football.columns:
        return
    cups = football[
        (football.get("es_anio_mundial", pd.Series(index=football.index, dtype=float)) == 1)
        & football["year"].between(*year_range)
        & pd.to_numeric(football[score_column], errors="coerce").notna()
    ].copy()
    if cups.empty:
        return
    provisional = pd.to_numeric(cups.get("mundial_datos_provisionales", 0), errors="coerce").fillna(0).astype(int)
    custom_cols = [
        "mundial_fase_alcanzada", "mundial_goles_favor", "mundial_goles_contra",
        "mundial_ganados", "mundial_puntos_goles", "mundial_puntos_victorias",
        "mundial_puntos_fases", "mundial_puntos_eliminacion",
        "mundial_bonus_rival_fuerte", "mundial_penalizacion_rival_debil",
    ]
    for col in custom_cols:
        if col not in cups.columns:
            cups[col] = np.nan
    fig.add_trace(go.Scatter(
        x=cups["year"],
        y=pd.to_numeric(cups[score_column], errors="coerce"),
        mode="lines+markers",
        name=f"México · {score_label}",
        line={"color": WORLD_CUP_COLOR, "width": 3, "dash": "dot"},
        marker={
            "size": np.where(provisional.eq(1), 14, 10),
            "symbol": np.where(provisional.eq(1), "diamond-open", "circle"),
            "color": WORLD_CUP_COLOR,
            "line": {"color": TEXT, "width": 1},
        },
        customdata=cups[custom_cols].fillna("—").to_numpy(),
        hovertemplate=(
            "<b>México %{x}</b><br>Calificación: %{y:.3f}<br>"
            "Fase: %{customdata[0]}<br>GF / GC: %{customdata[1]} / %{customdata[2]}<br>"
            "Victorias: %{customdata[3]}<br>Puntos goles: %{customdata[4]}<br>"
            "Puntos victorias: %{customdata[5]}<br>Puntos fases: %{customdata[6]}<br>"
            "Puntos eliminación: %{customdata[7]}<br>Bonus rival fuerte: %{customdata[8]}<br>"
            "Penalización rival débil: %{customdata[9]}<extra></extra>"
        ),
    ), secondary_y=True)

# =============================================================================
# 4) GRÁFICAS PRINCIPALES
# =============================================================================

def multi_variable_chart(
    data: pd.DataFrame,
    football: pd.DataFrame,
    events: pd.DataFrame,
    labels: list[str],
    transformation: str,
    base_year: int,
    year_range: tuple[int, int],
    show_events: bool,
    event_categories: list[str],
    event_severity: tuple[int, int],
    shade_event_periods: bool,
    show_world_cups: bool,
    show_football_score: bool,
    football_score_column: str,
    football_score_label: str,
    height: int = 500,
) -> list[str]:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    warnings: list[str] = []
    all_y: list[float] = []
    axis_labels: set[str] = set()
    actual_bases: dict[str, int] = {}

    for index, label in enumerate(labels):
        temp, info = transform_variable(data, label, transformation, base_year)
        if temp.empty:
            warnings.append(str(info.get("warning", f"{label}: sin datos.")))
            continue
        if info.get("warning"):
            warnings.append(str(info["warning"]))
        axis_labels.add(str(info["axis_label"]))
        if info.get("base_year") is not None:
            actual_bases[label] = int(info["base_year"])
        all_y.extend(temp["transformed"].tolist())
        fig.add_trace(go.Scatter(
            x=temp["year"],
            y=temp["transformed"],
            mode="lines+markers",
            name=label,
            line={"color": COLORS[index % len(COLORS)], "width": 3},
            marker={"size": 5, "color": COLORS[index % len(COLORS)]},
            customdata=np.column_stack([temp["original"], temp["transformed"]]),
            hovertemplate=(
                "<b>%{fullData.name}</b><br>Año: %{x}<br>"
                "Valor original: %{customdata[0]:,.4g}<br>"
                "Valor mostrado: %{customdata[1]:,.4g}<extra></extra>"
            ),
        ), secondary_y=False)

    if not fig.data:
        empty_chart("No hay datos suficientes para las variables seleccionadas.", height)
        return warnings

    if show_events:
        add_event_overlays(
            fig, events, event_categories, event_severity, year_range, all_y,
            shade_periods=shade_event_periods,
        )
    if show_world_cups:
        add_world_cup_markers(fig, football, all_y, year_range)
    if show_football_score:
        add_football_score_trace(fig, football, football_score_column, football_score_label, year_range)

    if transformation in {"Valores originales", "Valores reales (pesos constantes)"} and len(axis_labels) > 1:
        y_title = "Escalas mixtas · consulta unidades en tooltip"
        warnings.append(
            "Las variables originales/reales tienen unidades diferentes. Para comparar magnitudes relativas usa Base 100, Log10(Base100), variación o Z-score."
        )
    else:
        y_title = next(iter(axis_labels)) if axis_labels else transformation

    base_note = ""
    if transformation in {"Índice Base 100", "Log10(Base100)", "Variación acumulada %"} and actual_bases:
        base_note = " · Bases usadas: " + ", ".join(f"{k}={v}" for k, v in actual_bases.items())

    # El encabezado se dibuja fuera de Plotly para evitar que el título, la leyenda
    # y las etiquetas de eventos se encimen en pantallas pequeñas o con zoom.
    st.markdown(f"<div class='chart-heading'>{transformation}</div>", unsafe_allow_html=True)
    if base_note:
        st.caption(base_note.replace(" · ", ""))

    fig.update_layout(
        height=height,
        margin={"l": 28, "r": 34, "t": 72, "b": 48},
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font={"color": TEXT, "family": "Arial"},
        xaxis=axis_clean("Años", show_grid=False),
        yaxis=axis_clean(y_title, show_grid=True),
        yaxis2={
            "title": {
                "text": "Calificación futbolística",
                "font": {"color": WORLD_CUP_COLOR, "size": 13},
                "standoff": 10,
            },
            "tickfont": {"color": WORLD_CUP_COLOR, "size": 10},
            "showgrid": False,
            "zeroline": False,
            "automargin": True,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.035,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11},
            "traceorder": "normal",
        },
        hovermode="closest",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    return warnings


def simple_line_chart(data: pd.DataFrame, label: str, height: int = 240, color: str = COLORS[0]) -> None:
    col, unit, _ = variable_column(label, use_real=False)
    if col not in data.columns:
        empty_chart(f"{label}: columna no encontrada.", height)
        return
    temp = data[["year", col]].copy()
    temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.dropna()
    if len(temp) < 2:
        empty_chart(f"{label}: datos insuficientes.", height)
        return
    scaled, y_label, _ = display_scale(temp[col], unit, col)
    fig = go.Figure(go.Scatter(
        x=temp["year"], y=scaled, mode="lines+markers", name=label,
        line={"color": color, "width": 2.5}, marker={"size": 4},
        customdata=np.column_stack([temp[col]]),
        hovertemplate="Año: %{x}<br>Valor: %{customdata[0]:,.4g}<extra></extra>",
    ))
    fig.update_layout(
        title={"text": label, "font": {"color": TEXT, "size": 16}},
        height=height, margin={"l": 14, "r": 14, "t": 45, "b": 30},
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT},
        xaxis=axis_clean("Años", True), yaxis=axis_clean(y_label, True), showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})



def football_score_small_chart(
    football: pd.DataFrame,
    score_column: str,
    score_label: str,
    year_range: tuple[int, int],
    height: int = 235,
) -> None:
    """Cuarta gráfica compacta cuando se eligen menos de cuatro variables económicas."""
    if football.empty or score_column not in football.columns:
        empty_chart("Calificación de México: datos no disponibles.", height)
        return
    cups = football[
        (pd.to_numeric(football.get("es_anio_mundial"), errors="coerce") == 1)
        & football["year"].between(*year_range)
    ].copy()
    cups[score_column] = pd.to_numeric(cups[score_column], errors="coerce")
    cups = cups.dropna(subset=[score_column])
    if len(cups) < 2:
        empty_chart("Calificación de México: datos insuficientes en el rango.", height)
        return

    fig = go.Figure(go.Scatter(
        x=cups["year"],
        y=cups[score_column],
        mode="lines+markers",
        name=score_label,
        line={"color": WORLD_CUP_COLOR, "width": 2.8},
        marker={"size": 7, "color": WORLD_CUP_COLOR, "line": {"color": TEXT, "width": 0.8}},
        customdata=cups[[
            "mundial_fase_alcanzada", "mundial_goles_favor", "mundial_goles_contra"
        ]].fillna("—").to_numpy(),
        hovertemplate=(
            "Año: %{x}<br>Calificación: %{y:.3f}<br>"
            "Fase: %{customdata[0]}<br>GF / GC: %{customdata[1]} / %{customdata[2]}"
            "<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=GRID, line_width=1)
    fig.update_layout(
        title={"text": "CALIFICACIÓN DE MÉXICO", "font": {"color": TEXT, "size": 16}},
        height=height,
        margin={"l": 14, "r": 14, "t": 45, "b": 30},
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font={"color": TEXT},
        xaxis=axis_clean("Año del Mundial", True),
        yaxis=axis_clean(score_label, True),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_original_small_multiples(
    data: pd.DataFrame,
    football: pd.DataFrame,
    labels: list[str],
    score_column: str,
    score_label: str,
    year_range: tuple[int, int],
) -> None:
    """Renderiza siempre una cuadrícula 2×2 estable.

    Si hay sólo tres variables económicas, la cuarta posición muestra la
    calificación futbolística, que es útil para la comparación economía-fútbol.
    """
    items: list[tuple[str, str]] = [("economic", label) for label in labels[:4]]
    if len(items) < 4:
        items.append(("football", "CALIFICACIÓN DE MÉXICO"))
    while len(items) < 4:
        items.append(("empty", "Selecciona otra variable"))

    for row_start in (0, 2):
        cols = st.columns(2, gap="large")
        for offset, container in enumerate(cols):
            kind, label = items[row_start + offset]
            with container:
                if kind == "economic":
                    color_index = labels.index(label) if label in labels else row_start + offset
                    simple_line_chart(
                        data,
                        label,
                        height=245,
                        color=COLORS[color_index % len(COLORS)],
                    )
                elif kind == "football":
                    football_score_small_chart(
                        football,
                        score_column,
                        score_label,
                        year_range,
                        height=245,
                    )
                else:
                    empty_chart("Selecciona una cuarta variable para completar la cuadrícula.", 245)


def debt_stack_chart(data: pd.DataFrame, height: int = 300) -> None:
    needed = ["year", "public_debt_total_mxn", "public_debt_internal_mxn", "public_debt_external_mxn"]
    if not set(needed).issubset(data.columns):
        empty_chart("No hay composición de deuda.", height)
        return
    temp = data[needed].copy()
    for col in needed[1:]:
        temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.dropna()
    if len(temp) < 2:
        empty_chart("No hay composición de deuda suficiente.", height)
        return
    temp["interna_pct"] = temp["public_debt_internal_mxn"] / temp["public_debt_total_mxn"] * 100
    temp["externa_pct"] = temp["public_debt_external_mxn"] / temp["public_debt_total_mxn"] * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=temp["year"], y=temp["interna_pct"], mode="lines", stackgroup="one", name="Interna", line={"color": COLORS[2], "width": 2}))
    fig.add_trace(go.Scatter(x=temp["year"], y=temp["externa_pct"], mode="lines", stackgroup="one", name="Externa", line={"color": COLORS[1], "width": 2}))
    fig.update_layout(
        title={"text": "Deuda interna vs externa", "font": {"color": TEXT, "size": 17}},
        height=height, margin={"l": 15, "r": 15, "t": 50, "b": 30},
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT},
        xaxis=axis_clean("Años", True), yaxis=axis_clean("% de la deuda total", True),
        legend={"orientation": "h", "y": 1.02, "x": 0, "bgcolor": "rgba(0,0,0,0)"},
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def world_cup_performance_chart(
    football: pd.DataFrame,
    year_range: tuple[int, int],
    score_column: str = "mundial_score_por_partido",
    score_label: str = "Puntaje por partido",
    height: int = 390,
) -> None:
    if football.empty:
        empty_chart("No se encontró la fuente de mundiales.", height)
        return
    cups = football[
        (pd.to_numeric(football.get("es_anio_mundial"), errors="coerce") == 1)
        & football["year"].between(year_range[0], year_range[1])
        & (pd.to_numeric(football.get("mundial_participo"), errors="coerce") == 1)
    ].copy()
    if cups.empty:
        empty_chart("No hay participaciones de México en el rango seleccionado.", height)
        return

    gf = pd.to_numeric(cups["mundial_goles_favor"], errors="coerce")
    gc = pd.to_numeric(cups["mundial_goles_contra"], errors="coerce")
    score = pd.to_numeric(cups.get(score_column), errors="coerce")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    custom = cups[["mundial_fase_alcanzada", "mundial_sede"]].fillna("Sin dato").to_numpy()
    fig.add_trace(go.Bar(
        x=cups["year"], y=gf, name="Goles a favor",
        marker={"color": COLORS[2]}, customdata=custom,
        hovertemplate=(
            "Año %{x}<br>GF %{y}<br>Fase: %{customdata[0]}<br>"
            "Sede: %{customdata[1]}<extra></extra>"
        ),
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=cups["year"], y=gc, name="Goles en contra",
        marker={"color": COLORS[3]}, customdata=custom,
        hovertemplate=(
            "Año %{x}<br>GC %{y}<br>Fase: %{customdata[0]}<br>"
            "Sede: %{customdata[1]}<extra></extra>"
        ),
    ), secondary_y=False)
    if score.notna().sum() >= 2:
        fig.add_trace(go.Scatter(
            x=cups["year"], y=score, name=score_label,
            mode="lines+markers",
            line={"color": WORLD_CUP_COLOR, "width": 2.6, "dash": "dot"},
            marker={"size": 7, "color": WORLD_CUP_COLOR, "line": {"color": TEXT, "width": 0.8}},
            hovertemplate="Año %{x}<br>Calificación %{y:.3f}<extra></extra>",
        ), secondary_y=True)

    fig.update_layout(
        title={
            "text": "Selección mexicana en Copas del Mundo",
            "font": {"color": TEXT, "size": 17},
            "x": 0.02,
            "xanchor": "left",
        },
        barmode="group",
        height=height,
        margin={"l": 24, "r": 24, "t": 88, "b": 44},
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font={"color": TEXT},
        xaxis=axis_clean("Año del Mundial", True),
        yaxis=axis_clean("Goles", True),
        yaxis2={
            "title": {"text": "Calificación", "font": {"color": WORLD_CUP_COLOR, "size": 12}},
            "tickfont": {"color": WORLD_CUP_COLOR, "size": 10},
            "showgrid": False,
            "zeroline": False,
            "automargin": True,
        },
        legend={
            "orientation": "h", "y": 1.08, "x": 0.02,
            "xanchor": "left", "yanchor": "bottom",
            "bgcolor": "rgba(0,0,0,0)", "font": {"size": 10},
        },
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})



def country_comparison_chart(
    wdi: pd.DataFrame,
    variable_label: str,
    country_1: str,
    country_2: str,
    year_range: tuple[int, int],
    height: int = 390,
) -> None:
    if wdi.empty:
        empty_chart("No se encontró el archivo WDI.", height)
        return
    code = WDI_SERIES_BY_VARIABLE.get(variable_label)
    if not code:
        empty_chart(f"{variable_label}: no hay indicador internacional comparable.", height)
        return
    countries = ["Mexico", country_1, country_2]
    temp = wdi[
        (wdi["series_code"] == code)
        & wdi["country_name"].isin(countries)
        & wdi["year"].between(*year_range)
    ].copy()
    if temp.empty:
        empty_chart("No hay datos internacionales en el rango.", height)
        return

    fig = go.Figure()
    for i, country in enumerate(countries):
        cdf = temp[temp["country_name"] == country].sort_values("year")
        if len(cdf) < 2:
            continue
        fig.add_trace(go.Scatter(
            x=cdf["year"], y=cdf["value"], mode="lines+markers",
            name="México" if country == "Mexico" else country,
            line={"color": COLORS[i % len(COLORS)], "width": 2.5},
            marker={"size": 4},
            hovertemplate="%{fullData.name}<br>Año: %{x}<br>Valor: %{y:,.4g}<extra></extra>",
        ))
    if not fig.data:
        empty_chart("Países sin series suficientes.", height)
        return

    fig.update_layout(
        title={
            "text": f"{variable_label}: México, {country_1} y {country_2}",
            "font": {"color": TEXT, "size": 17},
            "x": 0.02,
            "xanchor": "left",
        },
        height=height,
        margin={"l": 24, "r": 18, "t": 88, "b": 44},
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font={"color": TEXT},
        xaxis=axis_clean("Años", True),
        yaxis=axis_clean(variable_label, True),
        legend={
            "orientation": "h", "y": 1.08, "x": 0.02,
            "xanchor": "left", "yanchor": "bottom",
            "bgcolor": "rgba(0,0,0,0)", "font": {"size": 10},
        },
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# =============================================================================
# 5) ANÁLISIS
# =============================================================================

def trend_summary(data: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    rows = []
    for label in labels:
        col, unit, _ = variable_column(label, False)
        if col not in data.columns:
            continue
        temp = data[["year", col]].copy()
        temp[col] = pd.to_numeric(temp[col], errors="coerce")
        temp = temp.dropna()
        if len(temp) < 2:
            continue
        first, last = temp.iloc[0], temp.iloc[-1]
        years = int(last["year"] - first["year"])
        cagr = np.nan
        if years > 0 and first[col] > 0 and last[col] > 0:
            cagr = ((last[col] / first[col]) ** (1 / years) - 1) * 100
        rows.append({
            "Variable": label, "Unidad": unit,
            "Primer año": int(first["year"]), "Primer valor": first[col],
            "Último año": int(last["year"]), "Último valor": last[col],
            "Cambio total %": (last[col] / first[col] - 1) * 100 if first[col] != 0 else np.nan,
            "CAGR %": cagr, "Mínimo": temp[col].min(), "Máximo": temp[col].max(),
        })
    return pd.DataFrame(rows)


def changes_chart(data: pd.DataFrame, labels: list[str], height: int = 360) -> None:
    fig = go.Figure()
    added = 0
    for i, label in enumerate(labels):
        temp, _ = transform_variable(data, label, "Variación anual %", int(data["year"].min()))
        if temp.empty:
            continue
        fig.add_trace(go.Scatter(x=temp["year"], y=temp["transformed"], mode="lines+markers", name=label, line={"color": COLORS[i % len(COLORS)], "width": 2.5}, marker={"size": 4}))
        added += 1
    if added == 0:
        empty_chart("No hay cambios porcentuales suficientes.", height)
        return
    fig.update_layout(
        title={"text": "Cambios porcentuales anuales", "font": {"color": TEXT, "size": 18}},
        height=height, margin={"l": 15, "r": 15, "t": 55, "b": 35},
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT},
        xaxis=axis_clean("Años", True), yaxis=axis_clean("Variación anual (%)", True),
        legend={"orientation": "h", "y": 1.02, "x": 0, "bgcolor": "rgba(0,0,0,0)"},
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def elasticity_series(data: pd.DataFrame, target: str, driver: str) -> pd.DataFrame:
    tcol, _, _ = variable_column(target, False)
    dcol, _, _ = variable_column(driver, False)
    if tcol not in data.columns or dcol not in data.columns:
        return pd.DataFrame()
    temp = data[["year", tcol, dcol]].copy()
    temp[tcol] = pd.to_numeric(temp[tcol], errors="coerce")
    temp[dcol] = pd.to_numeric(temp[dcol], errors="coerce")
    temp = temp.dropna().sort_values("year")
    temp["target_pct"] = temp[tcol].pct_change(fill_method=None) * 100
    temp["driver_pct"] = temp[dcol].pct_change(fill_method=None) * 100
    temp["elasticity"] = temp["target_pct"] / temp["driver_pct"].where(temp["driver_pct"].abs() >= 0.1)
    return temp.replace([np.inf, -np.inf], np.nan).dropna(subset=["elasticity"])


def correlation_matrix(data: pd.DataFrame, labels: list[str], use_changes: bool, method: str) -> pd.DataFrame:
    frame: dict[str, pd.Series] = {}
    for label in labels:
        col, _, _ = variable_column(label, False)
        if col not in data.columns:
            continue
        series = pd.to_numeric(data[col], errors="coerce")
        frame[label] = series.pct_change(fill_method=None) * 100 if use_changes else series
    if len(frame) < 2:
        return pd.DataFrame()
    return pd.DataFrame(frame, index=data["year"]).corr(method=method)


def lag_analysis(data: pd.DataFrame, target: str, driver: str, use_changes: bool, selected_lag: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    tcol, _, _ = variable_column(target, False)
    dcol, _, _ = variable_column(driver, False)
    temp = data[["year", tcol, dcol]].copy()
    temp[tcol] = pd.to_numeric(temp[tcol], errors="coerce")
    temp[dcol] = pd.to_numeric(temp[dcol], errors="coerce")
    temp = temp.sort_values("year")
    if use_changes:
        temp["target"] = temp[tcol].pct_change(fill_method=None) * 100
        temp["driver"] = temp[dcol].pct_change(fill_method=None) * 100
    else:
        temp["target"] = temp[tcol]
        temp["driver"] = temp[dcol]
    temp["driver_lagged"] = temp["driver"].shift(selected_lag)
    selected = temp[["year", "target", "driver_lagged"]].dropna()

    rows = []
    for lag in range(-5, 6):
        pair = pd.DataFrame({"target": temp["target"], "driver": temp["driver"].shift(lag)}).dropna()
        rows.append({"Rezago": lag, "Correlación": pair["target"].corr(pair["driver"]) if len(pair) >= 4 else np.nan, "Años": len(pair)})
    return selected, pd.DataFrame(rows)


def fit_regression_model(
    data: pd.DataFrame,
    target: str,
    predictors: list[str],
    lag: int,
    horizon: int,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    tcol, _, _ = variable_column(target, False)
    predictor_cols = [(label, variable_column(label, False)[0]) for label in predictors]
    columns = ["year", tcol] + [c for _, c in predictor_cols]
    if any(c not in data.columns for c in columns):
        return pd.DataFrame(), {"error": "Faltan columnas para el modelo."}

    model = data[columns].copy().sort_values("year")
    for col in columns[1:]:
        model[col] = pd.to_numeric(model[col], errors="coerce")
    for _, col in predictor_cols:
        model[col] = model[col].shift(lag)
    model = model.dropna()
    if len(model) < max(8, len(predictors) + 4):
        return pd.DataFrame(), {"error": "Hay muy pocos años completos para ajustar el modelo."}

    y = model[tcol].to_numpy(dtype=float)
    year_center = model["year"].to_numpy(dtype=float) - float(model["year"].min())
    X_parts = [np.ones(len(model)), year_center]
    for _, col in predictor_cols:
        X_parts.append(model[col].to_numpy(dtype=float))
    X = np.column_stack(X_parts)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ beta
    residual = y - fitted
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    rmse = float(np.sqrt(np.mean(residual ** 2)))

    output = pd.DataFrame({"year": model["year"].astype(int), "actual": y, "predicted": fitted, "type": "Histórico"})
    last_year = int(model["year"].max())
    future_years = np.arange(last_year + 1, last_year + horizon + 1)
    future_parts = [np.ones(horizon), future_years - float(model["year"].min())]

    # Cada predictor futuro se extrapola con una tendencia lineal simple.
    for _, col in predictor_cols:
        valid = data[["year", col]].copy()
        valid[col] = pd.to_numeric(valid[col], errors="coerce")
        valid = valid.dropna()
        if len(valid) < 2:
            return pd.DataFrame(), {"error": f"No se puede proyectar el predictor {col}."}
        slope, intercept = np.polyfit(valid["year"].to_numpy(dtype=float), valid[col].to_numpy(dtype=float), 1)
        predicted_driver = slope * (future_years - lag) + intercept
        future_parts.append(predicted_driver)
    future_X = np.column_stack(future_parts)
    future_y = future_X @ beta
    future = pd.DataFrame({"year": future_years, "actual": np.nan, "predicted": future_y, "type": "Proyección"})
    output = pd.concat([output, future], ignore_index=True)
    return output, {"r2": r2, "rmse": rmse, "n": len(model), "equation_terms": len(beta)}

# =============================================================================
# 6) ESTILO
# =============================================================================

st.markdown(f"""
<style>
.stApp {{ background: {BG}; color: {TEXT}; }}
.block-container {{ max-width: 100%; padding-top: 0.8rem; padding-bottom: 1rem; }}
h1,h2,h3,h4,h5,h6,p,label,span {{ color: {TEXT} !important; }}
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stMetric"] {{
  border: none !important; box-shadow: none !important; background: transparent !important;
}}
.dash-title {{ font-size: 21px; font-weight: 800; text-align: center; line-height: 1.15; margin: 5px 0 10px; }}
.dash-subtitle {{ font-size: 12px; color: {MUTED} !important; text-align: center; margin-bottom: 8px; }}
.chart-heading {{ font-size: 18px; font-weight: 800; text-align: center; margin: 2px 0 0; }}
.empty-chart {{ display:flex; align-items:center; justify-content:center; text-align:center; color:{TEXT}; font-weight:700; background:rgba(255,255,255,0.025); }}
.source-note {{ font-size: 12px; color: {MUTED} !important; }}
div[data-testid="stTabs"] button p {{ font-size: 15px; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 7) INTERFAZ
# =============================================================================

master = load_master()
football = load_football_history()
wdi = load_wdi_long()
events = load_events()
options = list(VARIABLES)

st.markdown("# 📊 Deuda, economía y mundiales de México")
st.markdown("Compara hasta cuatro variables, aplica transformaciones y explora tendencias, correlaciones, rezagos y modelos.")

countries = sorted(c for c in wdi.get("country_name", pd.Series(dtype=str)).dropna().unique() if c != "Mexico")
default_c1 = "United States" if "United States" in countries else (countries[0] if countries else "")
default_c2 = "Brazil" if "Brazil" in countries else (countries[1] if len(countries) > 1 else default_c1)

left_col, main_col, right_col = st.columns([1.15, 3.45, 1.3], gap="medium")

with left_col:
    st.markdown('<div class="dash-title">Elección de variables</div>', unsafe_allow_html=True)
    selected_variables = st.multiselect(
        "Variables de la gráfica principal",
        options,
        default=["DEUDA TOTAL", "PIB", "POBLACIÓN", "TIPO DE CAMBIO"],
        max_selections=4,
    )
    if not selected_variables:
        selected_variables = ["DEUDA TOTAL"]
    transformation = st.selectbox("Transformación", TRANSFORMATIONS, index=2)

    min_year = int(master["year"].min())
    max_year = int(master["year"].max())
    year_range = st.slider("Rango de años", min_year, max_year, (min_year, max_year))
    base_year = st.selectbox(
        "Año base",
        list(range(year_range[0], year_range[1] + 1)),
        index=0,
        help="Si una variable no tiene dato exactamente en ese año, se usa el primer dato posterior disponible.",
    )

    presidents = sorted(str(p) for p in master.get("president", pd.Series(dtype=str)).dropna().unique())
    selected_presidents = st.multiselect("Presidentes", presidents, default=presidents)
    show_events = st.checkbox("Mostrar hitos económicos", value=True)
    all_event_categories = sorted(events["categoria"].dropna().astype(str).unique()) if not events.empty else []
    event_categories = st.multiselect(
        "Tipos de hitos",
        all_event_categories,
        default=all_event_categories,
        disabled=not show_events,
    )
    event_severity = st.slider("Severidad de hitos", 1, 5, (1, 5), disabled=not show_events)
    shade_event_periods = st.checkbox(
        "Sombrear periodos de hitos",
        value=True,
        disabled=not show_events,
        help="Desactívalo para conservar sólo las líneas y diamantes de los hitos.",
    )
    show_world_cups = st.checkbox("Mostrar marcas ⚽ de Mundiales", value=True)
    show_football_score = st.checkbox("Mostrar calificación de México", value=True)
    football_score_label = st.radio(
        "Calificación futbolística",
        ["Puntaje por partido", "Puntaje total"],
        horizontal=True,
        disabled=not show_football_score,
        help="Por partido es la comparación recomendada porque los formatos de los Mundiales tuvieron distinto número de encuentros.",
    )
    football_score_column = "mundial_score_por_partido" if football_score_label == "Puntaje por partido" else "mundial_score_total"


filtered = master[master["year"].between(*year_range)].copy()
if selected_presidents and "president" in filtered.columns:
    filtered = filtered[filtered["president"].astype(str).isin(selected_presidents)]

with main_col:
    st.markdown('<div class="dash-title">Gráfica principal</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-subtitle">Eje izquierdo: economía. Eje derecho: calificación de México. Los diamantes muestran crisis, devaluaciones, pandemias y otros hitos.</div>', unsafe_allow_html=True)
    chart_warnings = multi_variable_chart(
        filtered, football, events, selected_variables, transformation, base_year,
        year_range, show_events, event_categories, event_severity,
        shade_event_periods, show_world_cups, show_football_score, football_score_column,
        football_score_label, height=520,
    )
    for warning in dict.fromkeys(w for w in chart_warnings if w):
        st.caption("⚠️ " + warning)

    st.markdown('<div class="dash-title">Valores originales y desempeño futbolístico</div>', unsafe_allow_html=True)
    st.caption("La cuadrícula conserva cuatro espacios. Si eliges tres variables, el cuarto muestra la calificación de México.")
    render_original_small_multiples(
        filtered,
        football,
        selected_variables,
        football_score_column,
        football_score_label,
        year_range,
    )

with right_col:
    debt_stack_chart(filtered, height=300)
    st.markdown('<div class="dash-title">KPIs</div>', unsafe_allow_html=True)
    for label in selected_variables[:3]:
        col, unit, _ = variable_column(label, False)
        if col not in filtered.columns:
            continue
        temp = filtered[["year", col]].copy()
        temp[col] = pd.to_numeric(temp[col], errors="coerce")
        temp = temp.dropna()
        if temp.empty:
            continue
        first, last = temp.iloc[0], temp.iloc[-1]
        delta = (last[col] / first[col] - 1) * 100 if first[col] != 0 else np.nan
        value = last[col]
        if "%" in unit:
            value_text = f"{value:,.2f}%"
        elif abs(value) >= 1e12:
            value_text = f"{value/1e12:,.2f} billones"
        elif abs(value) >= 1e9:
            value_text = f"{value/1e9:,.2f} mil millones"
        elif abs(value) >= 1e6:
            value_text = f"{value/1e6:,.2f} millones"
        else:
            value_text = f"{value:,.2f}"
        st.metric(label=f"{label} · {int(last['year'])}", value=value_text, delta=f"{delta:,.1f}% vs {int(first['year'])}" if pd.notna(delta) else None)

st.markdown("## ⚽ México y comparativa internacional")
country_metrics = [v for v in options if v in WDI_SERIES_BY_VARIABLE]
control_1, control_2, control_3 = st.columns(3, gap="medium")
with control_1:
    country_metric = st.selectbox(
        "Indicador internacional",
        country_metrics,
        index=country_metrics.index("DEUDA / PIB") if "DEUDA / PIB" in country_metrics else 0,
    )
with control_2:
    country_1 = st.selectbox(
        "País 1",
        countries,
        index=countries.index(default_c1) if default_c1 in countries else 0,
    )
with control_3:
    country_2 = st.selectbox(
        "País 2",
        countries,
        index=countries.index(default_c2) if default_c2 in countries else 0,
    )

bottom_left, bottom_right = st.columns(2, gap="large")
with bottom_left:
    world_cup_performance_chart(
        football,
        year_range,
        score_column=football_score_column,
        score_label=football_score_label,
        height=400,
    )
with bottom_right:
    country_comparison_chart(wdi, country_metric, country_1, country_2, year_range, height=400)
    st.caption("Para deuda se usa el indicador WDI comparable de deuda del gobierno central como % del PIB.")

st.markdown("## 🔬 Análisis")
tab_trends, tab_changes, tab_elast, tab_corr, tab_lags, tab_hitos, tab_models = st.tabs([
    "Tendencias", "Cambios porcentuales", "Elasticidades", "Correlaciones", "Rezagos", "Hitos", "Modelos"
])

with tab_trends:
    summary = trend_summary(filtered, selected_variables)
    if summary.empty:
        st.info("No hay suficientes datos para resumir tendencias.")
    else:
        st.dataframe(summary, width="stretch", hide_index=True, column_config={
            "Primer valor": st.column_config.NumberColumn(format="%.4g"),
            "Último valor": st.column_config.NumberColumn(format="%.4g"),
            "Cambio total %": st.column_config.NumberColumn(format="%.2f%%"),
            "CAGR %": st.column_config.NumberColumn(format="%.2f%%"),
            "Mínimo": st.column_config.NumberColumn(format="%.4g"),
            "Máximo": st.column_config.NumberColumn(format="%.4g"),
        })
    cups_table = football[(football.get("es_anio_mundial", pd.Series(dtype=float)) == 1) & football["year"].between(*year_range)].copy()
    if not cups_table.empty:
        st.markdown("### Mundial y resultado de México")
        show_cols = [c for c in ["year", "mundial_sede", "mundial_estatus_mexico", "mundial_fase_alcanzada", "mundial_goles_favor", "mundial_goles_contra", "mundial_resultado_resumen", "mundial_datos_provisionales"] if c in cups_table.columns]
        st.dataframe(cups_table[show_cols], width="stretch", hide_index=True)

with tab_changes:
    changes_chart(filtered, selected_variables, height=380)
    shocks = []
    for label in selected_variables:
        temp, _ = transform_variable(filtered, label, "Variación anual %", base_year)
        if temp.empty:
            continue
        top = temp.assign(abs_change=temp["transformed"].abs()).nlargest(3, "abs_change")
        for _, row in top.iterrows():
            shocks.append({"Variable": label, "Año": int(row["year"]), "Variación anual %": row["transformed"]})
    if shocks:
        st.markdown("### Años con los tres cambios absolutos más grandes por variable")
        st.dataframe(pd.DataFrame(shocks).sort_values("Variación anual %", key=lambda s: s.abs(), ascending=False), width="stretch", hide_index=True)

with tab_elast:
    c1, c2 = st.columns(2)
    target_elastic = c1.selectbox("Variable respuesta", options, index=options.index("DEUDA TOTAL"), key="elastic_target")
    driver_elastic = c2.selectbox("Variable explicativa", options, index=options.index("PIB"), key="elastic_driver")
    elastic = elasticity_series(filtered, target_elastic, driver_elastic)
    if elastic.empty:
        st.info("No hay suficientes tasas de variación para calcular elasticidades.")
    else:
        fig = go.Figure(go.Scatter(x=elastic["year"], y=elastic["elasticity"], mode="lines+markers", line={"color": COLORS[1], "width": 2.5}, marker={"size": 5}, hovertemplate="Año %{x}<br>Elasticidad %{y:.3f}<extra></extra>"))
        fig.add_hline(y=0, line_dash="dot", line_color=GRID)
        fig.update_layout(title={"text": f"Elasticidad de {target_elastic} respecto a {driver_elastic}", "font": {"color": TEXT, "size": 18}}, height=380, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT}, xaxis=axis_clean("Años", True), yaxis=axis_clean("Elasticidad = %Δ respuesta / %Δ explicativa", True), showlegend=False)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        k1, k2, k3 = st.columns(3)
        k1.metric("Elasticidad media", f"{elastic['elasticity'].mean():.3f}")
        k2.metric("Elasticidad mediana", f"{elastic['elasticity'].median():.3f}")
        k3.metric("Años usados", f"{len(elastic)}")
        st.caption("Elasticidad exploratoria: valores extremos pueden surgir cuando la variación de la variable explicativa es cercana a cero.")

with tab_corr:
    c1, c2 = st.columns(2)
    corr_mode = c1.radio("Datos para correlacionar", ["Niveles", "Variaciones anuales"], horizontal=True)
    corr_method = c2.radio("Método", ["pearson", "spearman"], horizontal=True)
    corr_labels = st.multiselect("Variables de la matriz", options, default=selected_variables, max_selections=10, key="corr_vars")
    corr = correlation_matrix(filtered, corr_labels, corr_mode == "Variaciones anuales", corr_method)
    if corr.empty:
        st.info("Selecciona al menos dos variables con datos suficientes.")
    else:
        fig = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, zmin=-1, zmax=1, colorscale="RdBu", reversescale=True, text=np.round(corr.values, 2), texttemplate="%{text}", hovertemplate="%{y} vs %{x}<br>r=%{z:.3f}<extra></extra>"))
        fig.update_layout(title={"text": f"Correlaciones {corr_method.title()} · {corr_mode}", "font": {"color": TEXT, "size": 18}}, height=520, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT}, margin={"l": 120, "r": 20, "t": 60, "b": 120})
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("Las correlaciones entre niveles con tendencia pueden ser espurias. Para investigar relaciones dinámicas usa variaciones y rezagos.")

with tab_lags:
    c1, c2, c3 = st.columns(3)
    lag_target = c1.selectbox("Variable objetivo", options, index=options.index("DEUDA TOTAL"), key="lag_target")
    lag_driver = c2.selectbox("Variable que antecede", options, index=options.index("TIPO DE CAMBIO"), key="lag_driver")
    selected_lag = c3.slider("Rezago (años)", 0, 10, 1, help="Lag 2 compara objetivo(t) contra variable explicativa(t-2).")
    lag_changes = st.checkbox("Analizar variaciones anuales en lugar de niveles", value=True)
    selected_pair, lag_corr = lag_analysis(filtered, lag_target, lag_driver, lag_changes, selected_lag)
    if selected_pair.empty:
        st.info("No hay suficientes datos para el rezago seleccionado.")
    else:
        # Normalización Z para ver ambas series juntas sin mezclar unidades.
        for col in ["target", "driver_lagged"]:
            std = selected_pair[col].std(ddof=0)
            selected_pair[col + "_z"] = (selected_pair[col] - selected_pair[col].mean()) / std if std else 0
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=selected_pair["year"], y=selected_pair["target_z"], mode="lines+markers", name=lag_target, line={"color": COLORS[0], "width": 2.5}))
        fig.add_trace(go.Scatter(x=selected_pair["year"], y=selected_pair["driver_lagged_z"], mode="lines+markers", name=f"{lag_driver} rezagada {selected_lag} años", line={"color": COLORS[1], "width": 2.5}))
        fig.update_layout(title={"text": "Comparación con rezago, estandarizada", "font": {"color": TEXT, "size": 18}}, height=370, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT}, xaxis=axis_clean("Años", True), yaxis=axis_clean("Z-score", True), legend={"orientation": "h", "y": 1.02, "x": 0}, hovermode="x unified")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.metric("Correlación del rezago seleccionado", f"{selected_pair['target'].corr(selected_pair['driver_lagged']):.3f}")
    lag_corr = lag_corr.dropna(subset=["Correlación"])
    if not lag_corr.empty:
        fig2 = go.Figure(go.Bar(x=lag_corr["Rezago"], y=lag_corr["Correlación"], marker={"color": COLORS[2]}, customdata=lag_corr[["Años"]], hovertemplate="Lag %{x}<br>Correlación %{y:.3f}<br>Años %{customdata[0]}<extra></extra>"))
        fig2.update_layout(title={"text": "Correlación cruzada por rezago", "font": {"color": TEXT, "size": 18}}, height=330, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT}, xaxis=axis_clean("Rezago aplicado a la variable explicativa", True), yaxis=axis_clean("Correlación", True), showlegend=False)
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
        st.caption("Un pico en un rezago sugiere una relación temporal para investigar; no demuestra causalidad.")


with tab_hitos:
    if events.empty:
        st.info("No se encontró el catálogo de hitos.")
    else:
        selected_events = events[
            events["categoria"].isin(event_categories)
            & events["severidad"].between(event_severity[0], event_severity[1])
            & (events["anio_fin"] >= year_range[0])
            & (events["anio_inicio"] <= year_range[1])
        ].copy()
        if selected_events.empty:
            st.info("No hay hitos que coincidan con los filtros.")
        else:
            timeline = go.Figure(go.Scatter(
                x=selected_events["anio_inicio"],
                y=selected_events["categoria"],
                mode="markers",
                marker={
                    "size": 8 + selected_events["severidad"] * 3,
                    "color": [EVENT_COLORS.get(c, "#FFFFFF") for c in selected_events["categoria"]],
                    "line": {"color": TEXT, "width": 1},
                },
                customdata=selected_events[["hito", "anio_fin", "severidad", "descripcion", "fuente"]].to_numpy(),
                hovertemplate=("<b>%{customdata[0]}</b><br>Inicio %{x} · Fin %{customdata[1]}<br>"
                               "Severidad %{customdata[2]}/5<br>%{customdata[3]}<br>Fuente: %{customdata[4]}<extra></extra>"),
            ))
            timeline.update_layout(
                title={"text": "Línea de tiempo de hitos", "font": {"color": TEXT, "size": 18}},
                height=350, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT},
                xaxis=axis_clean("Año", True), yaxis=axis_clean("Categoría", False), showlegend=False,
            )
            st.plotly_chart(timeline, width="stretch", config={"displayModeBar": False})
            st.dataframe(selected_events[["anio_inicio", "anio_fin", "categoria", "severidad", "hito", "descripcion", "fuente"]], width="stretch", hide_index=True)

            st.markdown("### Antes, durante y después del hito")
            impact_variable = st.selectbox("Variable para evaluar alrededor del evento", options, index=options.index("PIB") if "PIB" in options else 0, key="impact_variable")
            impact_col, impact_unit, _ = variable_column(impact_variable, False)
            impact_rows = []
            if impact_col in master.columns:
                values = master.set_index("year")[impact_col].apply(pd.to_numeric, errors="coerce")
                for _, ev in selected_events.iterrows():
                    start, end = int(ev["anio_inicio"]), int(ev["anio_fin"])
                    before, during, after = values.get(start - 1, np.nan), values.get(end, np.nan), values.get(end + 1, np.nan)
                    impact_rows.append({
                        "Hito": ev["hito"], "Antes": before, "Durante/final": during, "Después": after,
                        "Cambio antes→durante %": ((during / before - 1) * 100) if pd.notna(before) and before != 0 and pd.notna(during) else np.nan,
                        "Cambio durante→después %": ((after / during - 1) * 100) if pd.notna(during) and during != 0 and pd.notna(after) else np.nan,
                    })
            if impact_rows:
                st.dataframe(pd.DataFrame(impact_rows), width="stretch", hide_index=True)
            st.caption("La coincidencia temporal ayuda a formular hipótesis, pero no prueba que el hito haya causado el cambio económico.")

with tab_models:
    c1, c2, c3, c4 = st.columns(4)
    model_target = c1.selectbox("Objetivo del modelo", options, index=options.index("DEUDA TOTAL"), key="model_target")
    model_predictor_options = [v for v in options if v != model_target]
    preferred_predictors = ["PIB", "INFLACIÓN", "TIPO DE CAMBIO"]
    model_default_predictors = [v for v in preferred_predictors if v in model_predictor_options][:3]
    model_predictors = c2.multiselect("Predictores", model_predictor_options, default=model_default_predictors, max_selections=4)
    model_name = c3.selectbox("Modelo predictivo", MODEL_OPTIONS, index=0)
    target_mode = c4.selectbox("Qué proyectar", TARGET_MODES, index=0)

    c5, c6, c7 = st.columns(3)
    model_lag = c5.slider("Rezago de predictores", 0, 5, 1)
    horizon = c6.slider("Horizonte de proyección", 1, 10, 5)
    available_cutoffs = sorted(int(y) for y in filtered["year"].dropna().unique())
    default_cutoff = 2025 if 2025 in available_cutoffs else max(available_cutoffs)
    training_end_year = c7.selectbox(
        "Último año de entrenamiento",
        available_cutoffs,
        index=available_cutoffs.index(default_cutoff),
    )

    v1, v2 = st.columns(2)
    show_all_observed = v1.checkbox(
        "Mostrar observaciones posteriores al entrenamiento",
        value=True,
        help=(
            "Muestra la serie observada completa, aunque los años posteriores al corte no se usan en fit(). "
            "Esto permite comparar visualmente la proyección contra datos realmente observados."
        ),
    )
    mark_training_end = v2.checkbox(
        "Marcar fin del entrenamiento",
        value=True,
        help="Dibuja una línea vertical entre el periodo usado para entrenar y el periodo fuera de muestra.",
    )

    if training_end_year >= 2026:
        st.warning("2026 contiene datos parciales para varias variables. Entrenar hasta 2025 es la opción recomendada para un modelo anual.")
    if target_mode == "Nivel directo (exploratorio)":
        st.warning("El nivel directo puede generar saltos entre el último dato observado y la primera proyección. Crecimiento anual o variación absoluta conservan continuidad.")

    if not model_predictors:
        st.info("Selecciona al menos un predictor.")
    else:
        target_col = variable_column(model_target, False)[0]
        predictor_cols = [variable_column(v, False)[0] for v in model_predictors]
        model_output, metrics, importance = fit_predict_model(
            filtered, target_col, predictor_cols, model_name, model_lag,
            horizon, target_mode, training_end_year,
        )
        if model_output.empty:
            st.warning(str(metrics.get("error", "No se pudo ajustar el modelo.")))
        else:
            fig = go.Figure()
            hist = model_output[model_output["type"] == "Histórico"]
            future = model_output[model_output["type"] == "Proyección"]

            observed_full = filtered[["year", target_col]].copy()
            observed_full[target_col] = pd.to_numeric(observed_full[target_col], errors="coerce")
            observed_full = observed_full.dropna().sort_values("year")
            observed_train = observed_full[observed_full["year"] <= training_end_year]
            observed_after = observed_full[observed_full["year"] > training_end_year]

            fig.add_trace(go.Scatter(
                x=observed_train["year"], y=observed_train[target_col],
                mode="lines+markers", name="Observado · entrenamiento",
                line={"color": COLORS[0], "width": 3}, marker={"size": 6},
                hovertemplate="Año %{x}<br>Observado %{y:,.4g}<extra></extra>",
            ))

            if show_all_observed and not observed_after.empty:
                # Incluye el último punto de entrenamiento para que la línea posterior sea continua.
                bridge = pd.concat([observed_train.tail(1), observed_after], ignore_index=True)
                fig.add_trace(go.Scatter(
                    x=bridge["year"], y=bridge[target_col],
                    mode="lines+markers", name="Observado · fuera de entrenamiento",
                    line={"color": COLORS[0], "width": 2.5, "dash": "dashdot"},
                    marker={"size": 8, "symbol": "circle-open", "line": {"width": 2}},
                    hovertemplate="Año %{x}<br>Observado fuera de entrenamiento %{y:,.4g}<extra></extra>",
                ))

            fig.add_trace(go.Scatter(
                x=hist["year"], y=hist["predicted"], mode="lines",
                name="Ajuste histórico", line={"color": COLORS[2], "width": 2, "dash": "dash"},
                hovertemplate="Año %{x}<br>Ajuste %{y:,.4g}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=future["year"], y=future["predicted"], mode="lines+markers",
                name="Proyección", line={"color": COLORS[1], "width": 3, "dash": "dot"},
                marker={"size": 7},
                hovertemplate="Año %{x}<br>Proyección %{y:,.4g}<extra></extra>",
            ))

            if mark_training_end:
                fig.add_vline(
                    x=training_end_year + 0.5,
                    line_width=1.5,
                    line_dash="dot",
                    line_color="rgba(255,255,255,0.55)",
                )
                fig.add_annotation(
                    x=training_end_year + 0.5, y=1.02, xref="x", yref="paper",
                    text="Fin de entrenamiento", showarrow=False,
                    font={"color": MUTED, "size": 11}, xanchor="left",
                )

            fig.update_layout(
                title={"text": f"{model_name} · {model_target} · {target_mode}", "font": {"color": TEXT, "size": 18}},
                height=460, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TEXT},
                xaxis=axis_clean("Años", True), yaxis=axis_clean("Nivel del objetivo", True),
                legend={"orientation": "h", "y": 1.10, "x": 0}, hovermode="x unified",
                margin={"l": 20, "r": 20, "t": 95, "b": 40},
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            if target_mode == "Crecimiento anual % (recomendado)":
                rmse_label = "RMSE histórico (puntos porcentuales)"
            elif target_mode == "Variación absoluta":
                rmse_label = "RMSE histórico (variación absoluta)"
            else:
                rmse_label = "RMSE histórico (nivel)"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("R² histórico", f"{float(metrics['r2_historico']):.3f}")
            m2.metric(rmse_label, f"{float(metrics['rmse_historico']):,.4g}")
            r2_val = metrics.get("r2_validacion", np.nan)
            m3.metric("R² validación temporal", f"{float(r2_val):.3f}" if pd.notna(r2_val) else "N/D")
            m4.metric("Observaciones de entrenamiento", f"{int(metrics['n'])}")
            n_val = int(metrics.get("n_validacion", 0))
            st.caption(
                f"La validación temporal usa {n_val} observaciones recientes dentro del periodo que termina en {training_end_year}. "
                "Las observaciones posteriores visibles en la gráfica no participan en fit()."
            )

            if not importance.empty:
                metric_column = next((c for c in importance.columns if c != "Variable" and not c.startswith("Desv.")), None)
                if metric_column == "Importancia":
                    st.markdown("### Importancia relativa de variables")
                    st.dataframe(importance, width="stretch", hide_index=True)
                    st.caption(
                        "En Gradient Boosting las importancias suman aproximadamente 1. Indican cuánto ayudó cada variable "
                        "a reducir el error en los árboles; no muestran si el efecto es positivo o negativo."
                    )
                else:
                    st.markdown("### Coeficientes estandarizados del modelo")
                    st.dataframe(importance, width="stretch", hide_index=True)
                    st.caption(
                        "El signo indica la dirección de la asociación estimada y la magnitud permite comparar variables porque "
                        "los predictores fueron estandarizados. No implica causalidad."
                    )

            with st.expander("Detalles del modelo seleccionado"):
                if model_name == "ElasticNet":
                    st.write(
                        f"α seleccionado: {metrics.get('alpha_seleccionado', np.nan):.5g} · "
                        f"l1_ratio seleccionado: {metrics.get('l1_ratio_seleccionado', np.nan):.2f} · "
                        f"coeficientes llevados a cero: {int(metrics.get('variables_coeficiente_cero', 0))}."
                    )
                    st.caption("ElasticNet elige α y l1_ratio mediante validación temporal interna y penaliza coeficientes inestables o redundantes.")
                elif model_name == "Gradient Boosting":
                    st.write(
                        f"Árboles: {int(metrics.get('numero_arboles', 0))} · "
                        f"profundidad máxima: {int(metrics.get('profundidad_maxima', 0))} · "
                        f"learning rate: {metrics.get('tasa_aprendizaje', np.nan):.3f} · "
                        f"mínimo por hoja: {int(metrics.get('minimo_muestras_hoja', 0))} · "
                        f"pérdida: {metrics.get('funcion_perdida', '')}."
                    )
                    st.caption("Cada árbol agrega reglas de división que corrigen residuos del conjunto anterior; el dashboard resume esas reglas como importancia de variables.")
                elif model_name == "Regresión bayesiana":
                    st.write(
                        f"Precisión estimada del ruido (alpha): {metrics.get('precision_ruido_alpha', np.nan):.5g} · "
                        f"precisión previa/posterior de coeficientes (lambda): {metrics.get('precision_coeficientes_lambda', np.nan):.5g}."
                    )
                    st.caption("La tabla añade la desviación posterior: valores menores significan mayor certeza estadística sobre el coeficiente, bajo los supuestos del modelo.")
                else:
                    st.caption("OLS estima los coeficientes que minimizan la suma de errores cuadrados en el periodo de entrenamiento.")

            st.caption(
                "fit() ajusta los parámetros sólo con los años hasta el corte de entrenamiento. La validación temporal reserva "
                "los años más recientes de ese bloque. Los predictores futuros se extrapolan con tendencias locales; "
                "la proyección es exploratoria y no prueba causalidad."
            )

with st.expander("🔎 Trazabilidad, fuentes y calidad de datos"):

    trace = []
    for label in selected_variables:
        col, unit, _ = variable_column(label, False)
        years = master.loc[pd.to_numeric(master.get(col), errors="coerce").notna(), "year"].tolist() if col in master.columns else []
        trace.append({
            "Variable": label, "Columna": col, "Unidad": unit,
            "Años con dato": len(years), "Primer año": min(years) if years else None,
            "Último año": max(years) if years else None,
            "Descripción": VARIABLES[label]["description"],
        })
    st.dataframe(pd.DataFrame(trace), width="stretch", hide_index=True)

    if "validation_notes" in filtered.columns:
        notes = filtered[["year", "validation_notes"]].dropna()
        notes = notes[notes["validation_notes"].astype(str).str.strip() != ""]
        if not notes.empty:
            st.markdown("### Notas de validación macroeconómica")
            st.dataframe(notes, width="stretch", hide_index=True)

    source_columns = [c for c in master.columns if c.startswith("fuente_")]
    source_rows = []
    for col in source_columns:
        values = sorted({str(v).strip() for v in master[col].dropna() if str(v).strip()})
        for value in values:
            source_rows.append({"Campo fuente": col, "Fuente": value})
    if source_rows:
        st.markdown("### Fuentes registradas en el maestro consolidado")
        st.dataframe(pd.DataFrame(source_rows), width="stretch", hide_index=True)

st.caption(
    "Proyecto v4.1. Datos macroeconómicos 1990-2026, fuente consolidada de presidentes/INPC/desempleo/mundiales y WDI. "
    "La calificación futbolística usa GF-GC, victorias, fases superadas, victorias de eliminación directa y ajustes objetivos por historial del rival. El Mundial 2026 se mantiene provisional."
)
