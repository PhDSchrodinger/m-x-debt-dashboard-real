# Dashboard macroeconómico: deuda total de México

## Qué incluye esta versión

- Gráficas sin líneas de ejes; conserva grid y valores/ticks.
- Gráfica principal con dos variables comparadas:
  - eje Y izquierdo: variable izquierda.
  - eje Y derecho: variable derecha.
  - eje X: años.
- Comparativa internacional abajo a la derecha:
  - México + País 1 + País 2.
  - Usa `data/wdi_country_indicators.csv`.
- Trazabilidad en el expander inferior.

## Ejecutar en Visual Studio Code

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app_streamlit_dashboard.py
```

## Archivos clave

- `app_streamlit_dashboard.py`: app principal.
- `data/mexico_economic_master.csv`: CSV maestro del ETL.
- `data/wdi_country_indicators.csv`: indicadores internacionales WDI para comparativa.
- `variable_map.csv`: mapa de variables.

## Nota metodológica

La comparativa internacional usa indicadores WDI comparables. Para `DEUDA TOTAL`, el archivo WDI disponible contiene `Central government debt, total (% of GDP)`, por eso la comparación internacional se grafica como porcentaje del PIB y no como monto nominal.
