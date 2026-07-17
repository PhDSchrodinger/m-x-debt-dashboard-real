"""
Dashboard Streamlit: deuda total de México y variables macroeconómicas.

Versión afinada:
- Sin bordes en paneles.
- Gráficas sin líneas de ejes, pero con grid y valores/ticks visibles.
- Gráfica principal con doble eje Y: variable izquierda vs variable derecha.
- Comparativa internacional abajo a la derecha: México + país 1 + país 2.

Ejecución local:
    streamlit run app_streamlit_dashboard.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =============================================================================
# 1) CONFIGURACIÓN GENERAL
# =============================================================================

st.set_page_config(
    page_title="Dashboard Deuda México",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Paleta inspirada en tu boceto.
BG = "#124F63"
PANEL = "#124F63"
TEXT = "#F1F4F5"
GRID = "rgba(255,255,255,0.18)"
LINE_MAIN = "#FFFFFF"
LINE_2 = "#FFD166"
LINE_3 = "#06D6A0"
LINE_4 = "#EF476F"
MUTED = "rgba(255,255,255,0.72)"

ROOT = Path(__file__).parent
DATA_PATHS = [
    ROOT / "data" / "mexico_economic_master.csv",
    ROOT / "mexico_economic_master.csv",
    Path("/mnt/data/mexico_economic_master.csv"),
]
WDI_PATHS = [
    ROOT / "data" / "wdi_country_indicators.csv",
    ROOT / "wdi_country_indicators.csv",
    Path("/mnt/data/6ebee357-cfc1-4762-b809-d3578759235b_Data.csv"),
]


# =============================================================================
# 2) VARIABLES DISPONIBLES EN EL DASHBOARD
#    label_usuario -> columna_csv + unidad + descripción
# =============================================================================

VARIABLES: Dict[str, Dict[str, str]] = {
    "PIB": {
        "column": "gdp_nominal_mxn",
        "unit": "MXN corrientes",
        "description": "Producto Interno Bruto nominal en pesos corrientes.",
    },
    "DEUDA TOTAL": {
        "column": "public_debt_total_mxn",
        "unit": "MXN corrientes",
        "description": "Deuda pública total en pesos corrientes.",
    },
    "DEUDA INTERNA": {
        "column": "public_debt_internal_mxn",
        "unit": "MXN corrientes",
        "description": "Componente interno de la deuda pública.",
    },
    "DEUDA EXTERNA": {
        "column": "public_debt_external_mxn",
        "unit": "MXN corrientes",
        "description": "Componente externo de la deuda pública convertido a pesos.",
    },
    "INFLACIÓN": {
        "column": "inflation_annual_pct",
        "unit": "% anual",
        "description": "Inflación anual calculada a partir del INPC.",
    },
    "POBLACIÓN": {
        "column": "population",
        "unit": "personas",
        "description": "Población total.",
    },
    "EXPORTACIONES": {
        "column": "exports_usd",
        "unit": "USD",
        "description": "Exportaciones de bienes y servicios.",
    },
    "IMPORTACIONES": {
        "column": "imports_usd",
        "unit": "USD",
        "description": "Importaciones de bienes y servicios.",
    },
    "REMESAS": {
        "column": "remittances_usd",
        "unit": "USD",
        "description": "Remesas recibidas.",
    },
    "TIPO DE CAMBIO": {
        "column": "exchange_rate_fix_mxn_usd_avg",
        "unit": "MXN/USD",
        "description": "Tipo de cambio promedio anual MXN por USD.",
    },
    "INVERSIÓN EXTRANJERA": {
        "column": "fdi_usd",
        "unit": "USD",
        "description": "Inversión extranjera directa.",
    },
    "INVERSIÓN INTERNA": {
        "column": "domestic_investment_mxn",
        "unit": "MXN corrientes",
        "description": "Inversión doméstica / formación bruta de capital en pesos.",
    },
    "INVERSIÓN TOTAL": {
        "column": "investment_total_mxn",
        "unit": "MXN corrientes",
        "description": "Inversión interna + IED convertida a pesos. Cálculo derivado.",
    },
    "INFLACIÓN ACUMULADA": {
        "column": "inflation_accumulated_since_1990_pct",
        "unit": "% acumulado desde 1990",
        "description": "Inflación acumulada usando 1990 como base.",
    },
    "DEFLACTOR DEL PIB": {
        "column": "gdp_deflator_index",
        "unit": "índice",
        "description": "Deflactor implícito del PIB.",
    },
    "PIB PERCÁPITA REAL": {
        "column": "gdp_real_per_capita_2018_mxn",
        "unit": "MXN de 2018 por persona",
        "description": "PIB real per cápita a precios de 2018.",
    },
    "POBRES": {
        "column": "poverty_pct",
        "unit": "% de población",
        "description": "Porcentaje de población en pobreza.",
    },
    "POBREZA EXTREMA": {
        "column": "extreme_poverty_pct",
        "unit": "% de población",
        "description": "Porcentaje de población en pobreza extrema.",
    },
    "DESIGUALDAD": {
        "column": "gini_index",
        "unit": "índice / sin fuente cargada",
        "description": "Reservado para Gini u otro indicador de desigualdad. Actualmente no hay fuente cargada.",
    },
    "CLASE MEDIA": {
        "column": "middle_class_pct",
        "unit": "% de población / sin fuente completa",
        "description": "Porcentaje de clase media si existe en fuentes cargadas.",
    },
    "RICOS / CLASE ALTA": {
        "column": "rich_or_high_class_pct",
        "unit": "% de población / sin fuente completa",
        "description": "Porcentaje de clase alta o población rica si existe en fuentes cargadas.",
    },
    "CLASE MEDIA + RICOS": {
        "column": "middle_and_rich_pct",
        "unit": "% de población / derivado",
        "description": "Suma de clase media + clase alta cuando ambas columnas existan.",
    },
    "DEUDA / PIB": {
        "column": "debt_to_gdp_pct",
        "unit": "% del PIB",
        "description": "Deuda pública total como porcentaje del PIB.",
    },
}

# Mapeo de variables del dashboard a indicadores World Bank para comparar países.
# Nota: si una variable no tiene indicador comparable en el archivo WDI cargado, se muestra aviso.
WDI_SERIES_BY_VARIABLE = {
    "PIB": "NY.GDP.MKTP.CD",                         # GDP current US$
    "DEUDA TOTAL": "GC.DOD.TOTL.GD.ZS",              # Central government debt, % GDP
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
    "PIB PERCÁPITA REAL": "NY.GDP.PCAP.KD",
}


# =============================================================================
# 3) CARGA Y PREPARACIÓN DE DATOS
# =============================================================================

def first_existing_path(paths: Iterable[Path]) -> Path:
    """Regresa la primera ruta existente. Lanza error claro si no encuentra archivo."""
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("No se encontró el archivo requerido en las rutas configuradas.")


@st.cache_data(show_spinner=False)
def load_master_csv() -> pd.DataFrame:
    """Carga el CSV maestro y crea columnas derivadas usadas por el dashboard."""
    path = first_existing_path(DATA_PATHS)
    df = pd.read_csv(path)

    if "year" not in df.columns:
        raise ValueError("El CSV maestro debe contener una columna 'year'.")

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    # Convertir a numérico todas las columnas que no son descriptivas.
    string_cols = {"president", "party", "sexenio", "crisis_event", "source_flags", "validation_notes"}
    for col in df.columns:
        if col not in string_cols and col != "year":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # IED en MXN e inversión total. No se inventa información; sólo se calcula si existen las bases.
    if {"fdi_usd", "exchange_rate_fix_mxn_usd_avg"}.issubset(df.columns):
        df["investment_foreign_mxn"] = df["fdi_usd"] * df["exchange_rate_fix_mxn_usd_avg"]
    else:
        df["investment_foreign_mxn"] = np.nan

    if "domestic_investment_mxn" in df.columns:
        df["investment_total_mxn"] = df["domestic_investment_mxn"] + df["investment_foreign_mxn"]
    else:
        df["investment_total_mxn"] = np.nan

    # Columnas reservadas para no romper selectores si todavía no hay fuente.
    for missing_col in ["gini_index", "middle_class_pct", "rich_or_high_class_pct"]:
        if missing_col not in df.columns:
            df[missing_col] = np.nan

    df["middle_and_rich_pct"] = df["middle_class_pct"] + df["rich_or_high_class_pct"]

    # Composición de deuda.
    if {"public_debt_total_mxn", "public_debt_internal_mxn"}.issubset(df.columns):
        df["debt_internal_share_pct"] = df["public_debt_internal_mxn"] / df["public_debt_total_mxn"] * 100
    else:
        df["debt_internal_share_pct"] = np.nan

    if {"public_debt_total_mxn", "public_debt_external_mxn"}.issubset(df.columns):
        df["debt_external_share_pct"] = df["public_debt_external_mxn"] / df["public_debt_total_mxn"] * 100
    else:
        df["debt_external_share_pct"] = np.nan

    return df.dropna(subset=["year"]).sort_values("year").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_wdi_long() -> pd.DataFrame:
    """Carga el archivo WDI de países y lo transforma de formato ancho a largo.

    Entrada esperada: columnas tipo '1990 [YR1990]', '1991 [YR1991]', etc.
    Salida: series_code, series_name, country_name, country_code, year, value.
    """
    try:
        path = first_existing_path(WDI_PATHS)
    except FileNotFoundError:
        return pd.DataFrame()

    raw = pd.read_csv(path)
    raw = raw.dropna(subset=["Series Code", "Country Name"], how="any")

    year_cols = [c for c in raw.columns if re.match(r"^\d{4} \[YR\d{4}\]$", str(c))]
    if not year_cols:
        return pd.DataFrame()

    long = raw.melt(
        id_vars=["Series Name", "Series Code", "Country Name", "Country Code"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name="value",
    )
    long["year"] = long["year_raw"].str.extract(r"(\d{4})").astype(int)
    long["value"] = pd.to_numeric(long["value"].replace("..", np.nan), errors="coerce")
    long = long.rename(
        columns={
            "Series Name": "series_name",
            "Series Code": "series_code",
            "Country Name": "country_name",
            "Country Code": "country_code",
        }
    )
    return long[["series_name", "series_code", "country_name", "country_code", "year", "value"]].dropna(subset=["value"])


# =============================================================================
# 4) FUNCIONES DE FORMATO
# =============================================================================

def variable_column(label: str) -> str:
    """Obtiene la columna asociada a una etiqueta del selector."""
    return VARIABLES[label]["column"]


def display_scale(series: pd.Series, unit: str, column: str) -> Tuple[pd.Series, str, float]:
    """Escala una serie para que el eje Y sea legible."""
    s = pd.to_numeric(series, errors="coerce")
    max_abs = float(s.abs().max()) if s.notna().any() else np.nan

    if np.isnan(max_abs):
        return s, unit, 1.0
    if unit.startswith("%") or "%" in unit:
        return s, unit, 1.0
    if "MXN/USD" in unit:
        return s, unit, 1.0
    if "índice" in unit:
        return s, unit, 1.0
    if column == "population":
        return s / 1_000_000, "millones de personas", 1_000_000
    if "USD" in unit:
        if max_abs >= 1_000_000_000_000:
            return s / 1_000_000_000_000, "billones USD", 1_000_000_000_000
        if max_abs >= 1_000_000_000:
            return s / 1_000_000_000, "miles de millones USD", 1_000_000_000
        if max_abs >= 1_000_000:
            return s / 1_000_000, "millones USD", 1_000_000
    if "MXN" in unit:
        if max_abs >= 1_000_000_000_000:
            return s / 1_000_000_000_000, "billones MXN", 1_000_000_000_000
        if max_abs >= 1_000_000_000:
            return s / 1_000_000_000, "miles de millones MXN", 1_000_000_000
        if max_abs >= 1_000_000:
            return s / 1_000_000, "millones MXN", 1_000_000
    return s, unit, 1.0


def nice_number(value: float, unit: str) -> str:
    """Formato compacto para KPIs."""
    if pd.isna(value):
        return "Sin dato"
    if "%" in unit:
        return f"{value:,.2f}%"
    if "MXN/USD" in unit:
        return f"{value:,.2f} MXN/USD"
    if "índice" in unit:
        return f"{value:,.2f}"
    abs_v = abs(value)
    if abs_v >= 1_000_000_000_000:
        return f"{value/1_000_000_000_000:,.2f} billones"
    if abs_v >= 1_000_000_000:
        return f"{value/1_000_000_000:,.2f} mil millones"
    if abs_v >= 1_000_000:
        return f"{value/1_000_000:,.2f} millones"
    return f"{value:,.2f}"


def axis_clean(title: str, show_grid: bool = True, side: str | None = None) -> dict:
    """Configuración común de ejes: sin línea del eje, con grid y etiquetas visibles."""
    cfg = dict(
        title=dict(text=title, font=dict(color=TEXT, size=15)),
        showgrid=show_grid,
        gridcolor=GRID,
        zeroline=False,
        showline=False,
        ticks="",
        tickfont=dict(color=TEXT, size=11),
        automargin=True,
    )
    if side:
        cfg["side"] = side
    return cfg


def add_event_lines(fig: go.Figure, data: pd.DataFrame) -> go.Figure:
    """Agrega líneas verticales para años con crisis_event, ignorando valores vacíos."""
    if "crisis_event" not in data.columns or "year" not in data.columns:
        return fig

    events = data[["year", "crisis_event"]].dropna(subset=["crisis_event"]).copy()
    events = events[events["crisis_event"].astype(str).str.strip() != ""]
    for _, row in events.iterrows():
        year = pd.to_numeric(row["year"], errors="coerce")
        if pd.isna(year):
            continue
        fig.add_vline(
            x=int(year),
            line_width=1,
            line_dash="dot",
            line_color="rgba(255,255,255,0.28)",
        )
    return fig


def empty_chart(message: str, height: int = 260) -> None:
    """Muestra un panel cuando no hay datos suficientes para graficar."""
    st.markdown(
        f"""
        <div class="empty-chart" style="height:{height}px;">
            <div>{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 5) GRÁFICAS
# =============================================================================

def line_chart(
    data: pd.DataFrame,
    variable_label: str,
    title: str | None = None,
    height: int = 280,
    color: str = LINE_MAIN,
    show_events: bool = True,
) -> None:
    """Dibuja una serie anual simple."""
    col = variable_column(variable_label)
    meta = VARIABLES[variable_label]

    if col not in data.columns:
        empty_chart(f"{variable_label}: columna no encontrada ({col}).", height)
        return

    plot_df = data[["year", col]].dropna()
    if len(plot_df) < 2:
        empty_chart(f"{variable_label}: no hay datos suficientes para graficar.", height)
        return

    y_scaled, y_label, _ = display_scale(plot_df[col], meta["unit"], col)
    plot_df = plot_df.assign(y_scaled=y_scaled)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_df["year"],
            y=plot_df["y_scaled"],
            mode="lines+markers",
            line=dict(color=color, width=3),
            marker=dict(size=5, color=color),
            name=variable_label,
            customdata=np.stack([plot_df[col]], axis=-1),
            hovertemplate="Año: %{x}<br>" + variable_label + ": %{customdata[0]:,.2f}<extra></extra>",
        )
    )

    if show_events:
        fig = add_event_lines(fig, data)

    fig.update_layout(
        title=dict(text=title or variable_label, font=dict(color=TEXT, size=18)),
        height=height,
        margin=dict(l=18, r=18, t=50, b=35),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Arial"),
        xaxis=axis_clean("Años", show_grid=True),
        yaxis=axis_clean(y_label, show_grid=True),
        hovermode="x unified",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def dual_axis_chart(
    data: pd.DataFrame,
    left_label: str,
    right_label: str,
    height: int = 430,
    show_events: bool = True,
) -> None:
    """Gráfica principal con dos variables y dos ejes Y.

    En X siempre van los años. La variable izquierda se mide con el eje Y izquierdo;
    la variable derecha se mide con el eje Y derecho. Ambas se dibujan de izquierda a derecha.
    """
    left_col = variable_column(left_label)
    right_col = variable_column(right_label)

    missing = [c for c in [left_col, right_col] if c not in data.columns]
    if missing:
        empty_chart(f"Faltan columnas para graficar: {missing}", height)
        return

    left_df = data[["year", left_col]].dropna()
    right_df = data[["year", right_col]].dropna()
    if len(left_df) < 2 or len(right_df) < 2:
        empty_chart("No hay datos suficientes para comparar ambas variables.", height)
        return

    left_scaled, left_axis_label, _ = display_scale(left_df[left_col], VARIABLES[left_label]["unit"], left_col)
    right_scaled, right_axis_label, _ = display_scale(right_df[right_col], VARIABLES[right_label]["unit"], right_col)
    left_df = left_df.assign(y_scaled=left_scaled)
    right_df = right_df.assign(y_scaled=right_scaled)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=left_df["year"],
            y=left_df["y_scaled"],
            mode="lines+markers",
            name=left_label,
            line=dict(color=LINE_MAIN, width=3),
            marker=dict(size=6, color=LINE_MAIN),
            customdata=np.stack([left_df[left_col]], axis=-1),
            hovertemplate="%{fullData.name}<br>Año: %{x}<br>Valor original: %{customdata[0]:,.2f}<extra></extra>",
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=right_df["year"],
            y=right_df["y_scaled"],
            mode="lines+markers",
            name=right_label,
            line=dict(color=LINE_2, width=3),
            marker=dict(size=6, color=LINE_2),
            customdata=np.stack([right_df[right_col]], axis=-1),
            hovertemplate="%{fullData.name}<br>Año: %{x}<br>Valor original: %{customdata[0]:,.2f}<extra></extra>",
            yaxis="y2",
        )
    )

    if show_events:
        fig = add_event_lines(fig, data)

    fig.update_layout(
        title=dict(
            text=f"{left_label} vs {right_label}",
            font=dict(color=TEXT, size=20),
        ),
        height=height,
        margin=dict(l=28, r=28, t=58, b=40),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Arial"),
        xaxis=axis_clean("Años", show_grid=True),
        yaxis=axis_clean(f"{left_label} · {left_axis_label}", show_grid=True, side="left"),
        yaxis2=dict(
            **axis_clean(f"{right_label} · {right_axis_label}", show_grid=False, side="right"),
            overlaying="y",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def normalized_comparison_chart(data: pd.DataFrame, labels: list[str], height: int = 360) -> None:
    """Compara variables con base 100 en el primer año disponible."""
    colors = [LINE_MAIN, LINE_2, LINE_3, LINE_4]
    fig = go.Figure()
    added = 0

    for i, label in enumerate(labels):
        col = variable_column(label)
        if col not in data.columns:
            continue
        temp = data[["year", col]].dropna()
        if len(temp) < 2:
            continue
        base = temp[col].iloc[0]
        if pd.isna(base) or base == 0:
            continue
        temp = temp.assign(index_100=temp[col] / base * 100)
        fig.add_trace(
            go.Scatter(
                x=temp["year"],
                y=temp["index_100"],
                mode="lines+markers",
                name=label,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=5),
                hovertemplate="%{fullData.name}<br>Año: %{x}<br>Índice: %{y:,.2f}<extra></extra>",
            )
        )
        added += 1

    if added == 0:
        empty_chart("No hay datos suficientes para el comparativo normalizado.", height)
        return

    fig.update_layout(
        title=dict(text="Variables de México normalizadas, base 100", font=dict(color=TEXT, size=18)),
        height=height,
        margin=dict(l=18, r=18, t=55, b=35),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Arial"),
        xaxis=axis_clean("Años", show_grid=True),
        yaxis=axis_clean("Índice base 100", show_grid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def debt_stack_chart(data: pd.DataFrame, height: int = 340) -> None:
    """Gráfica de composición de deuda interna vs externa."""
    needed = ["year", "debt_internal_share_pct", "debt_external_share_pct"]
    if not set(needed).issubset(data.columns):
        empty_chart("No hay columnas de composición de deuda.", height)
        return

    temp = data[needed].dropna()
    if len(temp) < 2:
        empty_chart("No hay datos suficientes para composición de deuda.", height)
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=temp["year"],
            y=temp["debt_internal_share_pct"],
            mode="lines",
            stackgroup="one",
            name="Interna",
            line=dict(color=LINE_3, width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=temp["year"],
            y=temp["debt_external_share_pct"],
            mode="lines",
            stackgroup="one",
            name="Externa",
            line=dict(color=LINE_2, width=2),
        )
    )

    fig.update_layout(
        title=dict(text="Deuda interna vs externa", font=dict(color=TEXT, size=18)),
        height=height,
        margin=dict(l=18, r=18, t=55, b=35),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Arial"),
        xaxis=axis_clean("Años", show_grid=True),
        yaxis=axis_clean("% de deuda total", show_grid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def country_comparison_chart(
    wdi: pd.DataFrame,
    variable_label: str,
    country_1: str,
    country_2: str,
    year_range: tuple[int, int],
    height: int = 380,
) -> None:
    """Comparativa internacional: México + dos países seleccionados.

    Usa World Development Indicators cargado en data/wdi_country_indicators.csv.
    Para DEUDA TOTAL se usa deuda del gobierno central como % del PIB porque es la
    serie comparable disponible en el archivo WDI cargado.
    """
    if wdi.empty:
        empty_chart("No se encontró archivo WDI para comparar países.", height)
        return

    series_code = WDI_SERIES_BY_VARIABLE.get(variable_label)
    if series_code is None:
        empty_chart(f"{variable_label}: no hay indicador internacional comparable cargado.", height)
        return

    countries = ["Mexico", country_1, country_2]
    colors = [LINE_MAIN, LINE_2, LINE_3]
    temp = wdi[
        (wdi["series_code"] == series_code)
        & (wdi["country_name"].isin(countries))
        & (wdi["year"].between(year_range[0], year_range[1]))
    ].copy()

    if temp.empty or temp["country_name"].nunique() < 1:
        empty_chart("No hay datos suficientes para la comparativa internacional.", height)
        return

    series_name = temp["series_name"].dropna().iloc[0]

    # Escala común para todos los países.
    # Definimos la unidad según el indicador WDI para mantener ejes legibles.
    if series_code == "SP.POP.TOTL":
        wdi_unit, wdi_column_hint = "personas", "population"
    elif "US$" in series_name or "current US" in series_name:
        wdi_unit, wdi_column_hint = "USD", ""
    elif "%" in series_name or "annual %" in series_name:
        wdi_unit, wdi_column_hint = "%", ""
    elif series_code == "PA.NUS.FCRF":
        wdi_unit, wdi_column_hint = "LCU/USD", ""
    else:
        wdi_unit, wdi_column_hint = "índice", ""

    y_scaled, y_label, _ = display_scale(temp["value"], wdi_unit, wdi_column_hint)
    temp = temp.assign(y_scaled=y_scaled)

    fig = go.Figure()
    for i, country in enumerate(countries):
        cdf = temp[temp["country_name"] == country].sort_values("year")
        if len(cdf) < 2:
            continue
        fig.add_trace(
            go.Scatter(
                x=cdf["year"],
                y=cdf["y_scaled"],
                mode="lines+markers",
                name="México" if country == "Mexico" else country,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=5),
                customdata=np.stack([cdf["value"]], axis=-1),
                hovertemplate="%{fullData.name}<br>Año: %{x}<br>Valor original: %{customdata[0]:,.2f}<extra></extra>",
            )
        )

    if not fig.data:
        empty_chart("No hay suficientes años para comparar los países elegidos.", height)
        return

    fig.update_layout(
        title=dict(text=f"México, {country_1} y {country_2}", font=dict(color=TEXT, size=17)),
        height=height,
        margin=dict(l=18, r=18, t=55, b=35),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Arial"),
        xaxis=axis_clean("Años", show_grid=True),
        yaxis=axis_clean(f"{variable_label} · {y_label}", show_grid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def correlation_table(data: pd.DataFrame, target_label: str, candidate_labels: list[str]) -> pd.DataFrame:
    """Calcula correlación simple Pearson entre una variable objetivo y otras variables."""
    target_col = variable_column(target_label)
    rows = []
    for label in candidate_labels:
        col = variable_column(label)
        if col == target_col or col not in data.columns or target_col not in data.columns:
            continue
        pair = data[[target_col, col]].dropna()
        if len(pair) < 4:
            continue
        rows.append({"Variable": label, "Correlación Pearson": pair[target_col].corr(pair[col]), "Años usados": len(pair)})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Correlación Pearson", key=lambda s: s.abs(), ascending=False)


# =============================================================================
# 6) CSS SIN BORDES
# =============================================================================

st.markdown(
    f"""
    <style>
    .stApp {{
        background: {BG};
        color: {TEXT};
    }}
    h1, h2, h3, h4, h5, h6, p, label, span {{
        color: {TEXT} !important;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stMetric"] {{
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }}
    .dash-title {{
        font-size: 22px;
        font-weight: 800;
        line-height: 1.15;
        text-align: center;
        margin-bottom: 10px;
        letter-spacing: .5px;
    }}
    .dash-subtitle {{
        font-size: 13px;
        color: {MUTED} !important;
        text-align: center;
        margin-bottom: 12px;
    }}
    .empty-chart {{
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: {TEXT};
        font-weight: 700;
        padding: 18px;
        background: rgba(255,255,255,0.03);
        border: none;
    }}
    .source-note {{
        padding-left: 0px;
        margin-top: 6px;
        font-size: 12px;
        color: {MUTED} !important;
    }}
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div,
    .stSlider,
    .stCheckbox {{
        color: {TEXT};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# 7) INTERFAZ DEL DASHBOARD
# =============================================================================

df_original = load_master_csv()
wdi_long = load_wdi_long()
variable_options = list(VARIABLES.keys())

st.markdown("# 📊 Dashboard macroeconómico: deuda total de México")
st.markdown("Selecciona variables y filtros. Todas las gráficas usan años en X y se actualizan automáticamente.")

# Defaults para análisis de deuda.
default_left = "DEUDA TOTAL"
default_right = "PIB"
default_v3 = "DEUDA / PIB"
default_v4 = "INFLACIÓN"
default_v5 = "TIPO DE CAMBIO"
default_country_metric = "DEUDA / PIB"

# Países disponibles para comparativa internacional.
wdi_countries = sorted([c for c in wdi_long.get("country_name", pd.Series(dtype=str)).dropna().unique() if c != "Mexico"])
default_country_1 = "United States" if "United States" in wdi_countries else (wdi_countries[0] if wdi_countries else "")
default_country_2 = "Brazil" if "Brazil" in wdi_countries else (wdi_countries[1] if len(wdi_countries) > 1 else default_country_1)

left_col, main_col, right_col = st.columns([1.15, 3.25, 1.35], gap="medium")

with left_col:
    st.markdown('<div class="dash-title">Elección De<br>Variables</div>', unsafe_allow_html=True)

    selected_left = st.selectbox(
        "Variable izquierda / gráfica principal",
        variable_options,
        index=variable_options.index(default_left),
    )
    selected_right = st.selectbox(
        "Variable derecha / gráfica principal",
        variable_options,
        index=variable_options.index(default_right),
    )
    selected_3 = st.selectbox("Variable 3", variable_options, index=variable_options.index(default_v3))
    selected_4 = st.selectbox("Variable 4", variable_options, index=variable_options.index(default_v4))
    selected_5 = st.selectbox("Variable 5", variable_options, index=variable_options.index(default_v5))

    st.markdown("---")
    st.markdown('<div class="dash-title">Países</div>', unsafe_allow_html=True)
    country_metric_options = [v for v in variable_options if v in WDI_SERIES_BY_VARIABLE]
    selected_country_metric = st.selectbox(
        "Variable para comparar países",
        country_metric_options,
        index=country_metric_options.index(default_country_metric) if default_country_metric in country_metric_options else 0,
    )
    country_1 = st.selectbox("PAÍS 1", wdi_countries, index=wdi_countries.index(default_country_1) if default_country_1 in wdi_countries else 0)
    country_2 = st.selectbox("PAÍS 2", wdi_countries, index=wdi_countries.index(default_country_2) if default_country_2 in wdi_countries else 0)

    st.markdown("---")
    st.markdown('<div class="dash-title">Presidentes<br>Hitos<br>Años</div>', unsafe_allow_html=True)
    min_year = int(df_original["year"].min())
    max_year = int(df_original["year"].max())
    year_range = st.slider("Rango de años", min_year, max_year, (min_year, max_year))

    presidents = sorted([p for p in df_original.get("president", pd.Series(dtype=str)).dropna().unique()])
    selected_presidents = st.multiselect("Presidentes", presidents, default=presidents)
    show_events = st.checkbox("Mostrar hitos/crisis", value=True)
    show_validation_notes = st.checkbox("Mostrar notas de validación", value=False)

# Filtro global para México.
df = df_original[(df_original["year"] >= year_range[0]) & (df_original["year"] <= year_range[1])].copy()
if selected_presidents and "president" in df.columns:
    df = df[df["president"].isin(selected_presidents)]

with main_col:
    st.markdown(
        f'<div class="dash-title">{selected_left} &nbsp; vs &nbsp; {selected_right}</div>'
        f'<div class="dash-subtitle">Izquierda: {VARIABLES[selected_left]["description"]}<br>Derecha: {VARIABLES[selected_right]["description"]}</div>',
        unsafe_allow_html=True,
    )
    dual_axis_chart(df, selected_left, selected_right, height=430, show_events=show_events)

    small_1, small_2 = st.columns(2, gap="medium")
    with small_1:
        line_chart(df, selected_3, title=selected_3, height=250, color=LINE_3, show_events=show_events)
        line_chart(df, selected_5, title=selected_5, height=250, color=LINE_MAIN, show_events=show_events)
    with small_2:
        line_chart(df, selected_4, title=selected_4, height=250, color=LINE_4, show_events=show_events)
        normalized_comparison_chart(df, [selected_left, selected_right, selected_3, selected_4], height=250)

with right_col:
    st.markdown('<div class="dash-title">Deuda</div>', unsafe_allow_html=True)
    debt_stack_chart(df, height=330)

    st.markdown('<div class="dash-title">KPIs</div>', unsafe_allow_html=True)
    main_col_name = variable_column(selected_left)
    if main_col_name in df.columns and df[main_col_name].notna().any():
        valid = df.dropna(subset=[main_col_name])
        latest_row = valid.iloc[-1]
        first_row = valid.iloc[0]
        latest_val = latest_row[main_col_name]
        first_val = first_row[main_col_name]
        delta_pct = (latest_val / first_val - 1) * 100 if pd.notna(first_val) and first_val != 0 else np.nan
        st.metric(
            label=f"{selected_left} · último dato {int(latest_row['year'])}",
            value=nice_number(latest_val, VARIABLES[selected_left]["unit"]),
            delta=f"{delta_pct:,.1f}% vs {int(first_row['year'])}" if pd.notna(delta_pct) else None,
        )
    else:
        st.warning("Variable sin datos suficientes.")

# Fila inferior: izquierda análisis México, derecha países.
bottom_left, bottom_right = st.columns([2.1, 1.45], gap="medium")

with bottom_left:
    st.markdown('<div class="dash-title">México: variables normalizadas</div>', unsafe_allow_html=True)
    normalized_comparison_chart(df, [selected_left, selected_right, selected_3, selected_4, selected_5], height=380)
    st.markdown(
        '<div class="source-note">Nota: base 100 permite ver trayectorias relativas entre variables con unidades distintas. No implica causalidad.</div>',
        unsafe_allow_html=True,
    )

with bottom_right:
    st.markdown('<div class="dash-title">Comparativa internacional</div>', unsafe_allow_html=True)
    country_comparison_chart(wdi_long, selected_country_metric, country_1, country_2, year_range, height=380)
    st.markdown(
        '<div class="source-note">Para DEUDA TOTAL se usa la serie comparable disponible: deuda del gobierno central como % del PIB.</div>',
        unsafe_allow_html=True,
    )

# Trazabilidad y validación.
with st.expander("🔎 Trazabilidad, validación, correlaciones y datos faltantes"):
    selected_labels = [selected_left, selected_right, selected_3, selected_4, selected_5]
    trace_rows = []
    for label in selected_labels:
        col = variable_column(label)
        available_years = df_original.loc[df_original[col].notna(), "year"].tolist() if col in df_original.columns else []
        trace_rows.append(
            {
                "Variable": label,
                "Columna CSV": col,
                "Unidad": VARIABLES[label]["unit"],
                "Años con dato": len(available_years),
                "Primer año": min(available_years) if available_years else None,
                "Último año": max(available_years) if available_years else None,
                "Descripción": VARIABLES[label]["description"],
            }
        )
    st.markdown("### Trazabilidad de variables seleccionadas")
    st.dataframe(pd.DataFrame(trace_rows), use_container_width=True, hide_index=True)

    st.markdown("### Correlación exploratoria contra la variable izquierda")
    corr = correlation_table(df, selected_left, variable_options)
    if corr.empty:
        st.info("No hay suficientes datos para calcular correlaciones con la variable seleccionada.")
    else:
        st.dataframe(
            corr.head(12),
            use_container_width=True,
            hide_index=True,
            column_config={"Correlación Pearson": st.column_config.NumberColumn(format="%.3f")},
        )
        st.caption("Correlación ≠ causalidad. Para causalidad se requieren rezagos, controles y pruebas estadísticas.")

    if show_validation_notes and "validation_notes" in df.columns:
        notes = df[["year", "validation_notes"]].dropna()
        notes = notes[notes["validation_notes"].astype(str).str.strip() != ""]
        st.markdown("### Notas de validación por año")
        st.dataframe(notes, use_container_width=True, hide_index=True)

    if show_events and "crisis_event" in df.columns:
        events = df[["year", "crisis_event"]].dropna()
        events = events[events["crisis_event"].astype(str).str.strip() != ""]
        st.markdown("### Hitos / crisis cargados")
        st.dataframe(events, use_container_width=True, hide_index=True)

st.caption(
    "Dashboard creado sobre mexico_economic_master.csv y archivo WDI para países. "
    "Variables sin fuente cargada se conservan vacías para no inventar datos."
)
