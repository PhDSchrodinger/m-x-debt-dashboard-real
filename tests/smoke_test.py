"""Validaciones rápidas del dashboard v4."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
master = pd.read_csv(ROOT / "data" / "mexico_dashboard_master.csv")
football = pd.read_csv(ROOT / "data" / "mexico_futbol_economia_1930_2026.csv")
matches = pd.read_csv(ROOT / "data" / "mexico_mundiales_partidos_puntaje.csv")
events = pd.read_csv(ROOT / "data" / "hitos_mexico_1990_2026.csv")
wdi = pd.read_csv(ROOT / "data" / "wdi_country_indicators.csv")

required_master = {
    "year", "gdp_nominal_mxn", "gdp_real_2018_mxn", "public_debt_total_mxn",
    "real_public_debt_2018_mxn", "population", "exchange_rate_fix_mxn_usd_avg",
    "president", "crisis_event", "es_anio_mundial", "mundial_fase_alcanzada",
    "mundial_goles_favor", "mundial_goles_contra", "mundial_score_total",
    "mundial_score_por_partido",
}
missing = sorted(required_master - set(master.columns))
assert not missing, f"Faltan columnas en maestro: {missing}"
assert master["year"].is_unique, "El maestro tiene años duplicados"
assert int(master["year"].min()) == 1990
assert int(master["year"].max()) == 2026
assert (master["public_debt_total_mxn"].dropna() >= 0).all()
assert {"anio", "rival", "resultado_mexico", "bonus_rival_fuerte", "penalizacion_rival_debil"}.issubset(matches.columns)
assert {"anio_inicio", "anio_fin", "categoria", "severidad", "hito"}.issubset(events.columns)
assert {"Series Name", "Series Code", "Country Name", "Country Code"}.issubset(wdi.columns)
score_2026 = football.loc[football["anio"].eq(2026), "mundial_score_total"].iloc[0]
assert score_2026 > 0
print("OK v4: estructura, hitos, calificación futbolística y fuentes válidas")
