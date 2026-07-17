"""Actualiza el CSV maestro del dashboard.

Fuentes de entrada:
- data/mexico_economic_master_base.csv: maestro macroeconómico anual 1990-2026.
- data/mexico_futbol_economia_1930_2026.csv: presidentes, hitos, INPC,
  desempleo y desempeño de México en Copas del Mundo.

Salida:
- data/mexico_dashboard_master.csv

El script conserva las columnas originales, agrega trazabilidad y calcula versiones
reales en pesos constantes de 2018 para variables monetarias cuando es posible.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MACRO_PATH = DATA / "mexico_economic_master_base.csv"
FUTBOL_PATH = DATA / "mexico_futbol_economia_1930_2026.csv"
OUTPUT_PATH = DATA / "mexico_dashboard_master.csv"


def numeric(df: pd.DataFrame, columns: list[str]) -> None:
    """Convierte columnas existentes a números; valores inválidos pasan a NaN."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def deflate(nominal: pd.Series, deflator: pd.Series) -> pd.Series:
    """Convierte valores nominales a pesos de 2018 usando deflactor base 2018=100."""
    factor = pd.to_numeric(deflator, errors="coerce") / 100.0
    result = pd.to_numeric(nominal, errors="coerce") / factor
    return result.replace([np.inf, -np.inf], np.nan)


def combine_text(left: object, right: object) -> str:
    """Une textos sin duplicar valores vacíos o idénticos."""
    values: list[str] = []
    for value in (left, right):
        text = "" if pd.isna(value) else str(value).strip()
        if text and text.lower() != "nan" and text not in values:
            values.append(text)
    return " | ".join(values)


def build_master() -> pd.DataFrame:
    macro = pd.read_csv(MACRO_PATH)
    futbol = pd.read_csv(FUTBOL_PATH)

    macro["year"] = pd.to_numeric(macro["year"], errors="coerce").astype("Int64")
    futbol["anio"] = pd.to_numeric(futbol["anio"], errors="coerce").astype("Int64")

    # Selección explícita para mantener el maestro manejable y rastreable.
    football_columns = [
        "anio", "dataset_version", "fecha_corte_dataset",
        "presidente_principal_anio", "partido_principal_anio",
        "periodo_presidencial_principal", "presidente_fin_anio",
        "partido_fin_anio", "cambio_presidencial_en_anio",
        "hitos_anio", "numero_hitos", "hay_hitos",
        "inpc_promedio_anual", "inpc_cierre_anual",
        "inflacion_dic_dic_pct", "inflacion_promedio_anual_pct",
        "desempleo_sa_promedio_anual_pct", "desempleo_sa_cierre_anual_pct",
        "desempleo_sa_ultimo_valor_disponible_pct",
        "desempleo_trimestral_promedio_total_pct",
        "es_anio_mundial", "mundial_edicion_numero", "mundial_continente_sede",
        "mundial_sede", "mundial_estatus_mexico", "mundial_participo",
        "mundial_anfitrion", "mundial_fase_alcanzada", "mundial_fase_orden",
        "mundial_posicion_final", "mundial_partidos", "mundial_ganados",
        "mundial_empatados", "mundial_perdidos", "mundial_goles_favor",
        "mundial_goles_contra", "mundial_diferencia_goles",
        "mundial_rendimiento_puntos_pct", "mundial_porcentaje_victorias",
        "mundial_resultado_resumen", "mundial_eliminado_por",
        "mundial_siguiente_rival", "mundial_detalle",
        "mundial_datos_provisionales", "mundial_fecha_actualizacion",
        "mundial_fases_superadas", "mundial_puntos_goles",
        "mundial_puntos_victorias", "mundial_puntos_fases",
        "mundial_puntos_eliminacion", "mundial_bonus_rival_fuerte",
        "mundial_penalizacion_rival_debil", "mundial_score_total",
        "mundial_score_por_partido", "mundial_metodologia_score",
        "fuente_inpc", "fuente_desempleo_mensual",
        "fuente_desempleo_trimestral", "fuente_presidentes_hitos",
        "fuente_presidentes_enriquecida", "fuente_mundiales_historico",
        "fuente_mundial_2026", "fuentes_disponibles_anio",
        "notas_calidad_datos",
    ]
    football_columns = [c for c in football_columns if c in futbol.columns]
    futbol = futbol[football_columns].rename(columns={"anio": "year"})

    merged = macro.merge(futbol, on="year", how="left", validate="one_to_one")

    numeric_columns = [
        "gdp_nominal_mxn", "gdp_real_2018_mxn", "gdp_deflator_index",
        "population", "public_debt_total_mxn", "public_debt_internal_mxn",
        "public_debt_external_mxn", "exchange_rate_fix_mxn_usd_avg",
        "exports_usd", "imports_usd", "remittances_usd", "fdi_usd",
        "domestic_investment_mxn", "unemployment_pct",
        "desempleo_sa_promedio_anual_pct", "desempleo_sa_cierre_anual_pct",
        "inflacion_dic_dic_pct", "inflacion_promedio_anual_pct",
    ]
    numeric(merged, numeric_columns)

    # Presiente/partido/hitos: prioriza la fuente enriquecida nueva cuando existe.
    if "presidente_principal_anio" in merged.columns:
        merged["president_original"] = merged.get("president")
        merged["president"] = merged["presidente_principal_anio"].combine_first(merged.get("president"))
    if "partido_principal_anio" in merged.columns:
        merged["party_original"] = merged.get("party")
        merged["party"] = merged["partido_principal_anio"].combine_first(merged.get("party"))
    if "periodo_presidencial_principal" in merged.columns:
        merged["sexenio_original"] = merged.get("sexenio")
        merged["sexenio"] = merged["periodo_presidencial_principal"].combine_first(merged.get("sexenio"))

    if "hitos_anio" in merged.columns:
        merged["crisis_event_original"] = merged.get("crisis_event")
        merged["crisis_event"] = [
            combine_text(a, b)
            for a, b in zip(merged.get("crisis_event"), merged["hitos_anio"])
        ]

    # Desempleo: la serie mensual desestacionalizada nueva tiene prioridad.
    if "desempleo_sa_promedio_anual_pct" in merged.columns:
        merged["unemployment_pct_original"] = merged.get("unemployment_pct")
        merged["unemployment_pct"] = merged["desempleo_sa_promedio_anual_pct"].combine_first(
            merged.get("unemployment_pct")
        )

    # Columnas monetarias convertidas a MXN y a pesos constantes de 2018.
    fx = merged.get("exchange_rate_fix_mxn_usd_avg")
    deflator = merged.get("gdp_deflator_index")
    if fx is not None:
        for usd_col, mxn_col in [
            ("fdi_usd", "fdi_mxn"),
            ("exports_usd", "exports_mxn"),
            ("imports_usd", "imports_mxn"),
            ("remittances_usd", "remittances_mxn"),
        ]:
            if usd_col in merged.columns:
                merged[mxn_col] = merged[usd_col] * fx

    if deflator is not None:
        real_pairs = [
            ("public_debt_total_mxn", "real_public_debt_2018_mxn"),
            ("public_debt_internal_mxn", "real_public_debt_internal_2018_mxn"),
            ("public_debt_external_mxn", "real_public_debt_external_2018_mxn"),
            ("domestic_investment_mxn", "domestic_investment_real_2018_mxn"),
            ("fdi_mxn", "fdi_real_2018_mxn"),
            ("exports_mxn", "exports_real_2018_mxn"),
            ("imports_mxn", "imports_real_2018_mxn"),
            ("remittances_mxn", "remittances_real_2018_mxn"),
        ]
        for nominal_col, real_col in real_pairs:
            if nominal_col in merged.columns:
                # Conserva la columna real ya auditada si existe; completa faltantes por deflación.
                calculated = deflate(merged[nominal_col], deflator)
                if real_col in merged.columns:
                    merged[real_col] = merged[real_col].combine_first(calculated)
                else:
                    merged[real_col] = calculated

    if {"domestic_investment_mxn", "fdi_mxn"}.issubset(merged.columns):
        merged["investment_total_mxn"] = merged["domestic_investment_mxn"] + merged["fdi_mxn"]
    if {"domestic_investment_real_2018_mxn", "fdi_real_2018_mxn"}.issubset(merged.columns):
        merged["investment_total_real_2018_mxn"] = (
            merged["domestic_investment_real_2018_mxn"] + merged["fdi_real_2018_mxn"]
        )

    if {"real_public_debt_2018_mxn", "population"}.issubset(merged.columns):
        merged["debt_per_capita_real_2018_mxn"] = (
            merged["real_public_debt_2018_mxn"] / merged["population"]
        )

    merged["dashboard_master_version"] = "2026-07-03_v4"
    merged["dashboard_merge_note"] = (
        "Macro 1990-2026 + fuente consolidada fútbol/economía 1930-2026; "
        "mundial 2026 provisional y calificación futbolística integrada."
    )

    return merged.sort_values("year").reset_index(drop=True)


def main() -> None:
    output = build_master()
    output.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Creado: {OUTPUT_PATH}")
    print(f"Filas: {len(output):,} | Columnas: {len(output.columns):,}")
    print(f"Años: {int(output['year'].min())}-{int(output['year'].max())}")


if __name__ == "__main__":
    main()
