# 🇲🇽 Mexico Economic Dashboard (1990–2026)

An interactive **Streamlit** dashboard for exploring and analyzing Mexico's economy from **1990 to 2026**. The project combines official economic indicators, demographic information, historical events, predictive analytics, and FIFA World Cup performance into a single interactive application.

---

## 🚀 Features

- 📈 Interactive economic dashboard
- 💰 Public debt analysis
- 📊 GDP (Nominal & Real)
- 💵 Inflation (INPC)
- 💱 Exchange rate
- 📉 Unemployment
- 🌎 Foreign Direct Investment (FDI)
- 👥 Demographic indicators
- 🏛️ Presidents, political parties and historical events
- ⚽ Mexico's FIFA World Cup performance
- 🤖 Predictive models:
  - Elastic Net
  - Bayesian Regression
  - Gradient Boosting

---

## 📊 Visualizations

The dashboard includes:

- Multi-axis interactive charts
- International comparisons (World Bank WDI)
- Historical trends
- Time-series analysis
- Predictive projections
- Correlation analysis
- Variable normalization
- Data traceability

---

## 📁 Project Structure

```text
.
├── app_streamlit_dashboard.py   # Main Streamlit application
├── data/                        # Economic datasets
├── variable_map.csv             # Variable dictionary
├── requirements.txt             # Python dependencies
└── README.md
```

---

## ▶️ Installation

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the dashboard:

```powershell
streamlit run app_streamlit_dashboard.py
```

---

## 📂 Main Data Sources

- INEGI
- Banco de México
- Secretaría de Hacienda y Crédito Público (SHCP)
- World Bank (WDI)
- IMF
- FIFA

---

## 📝 Methodology

International comparisons are based on **World Bank WDI** indicators.

For public debt, the dashboard compares countries using **Central government debt (% of GDP)** because it is the most internationally comparable metric.

---

## 🛠️ Technologies

- Python
- Streamlit
- Plotly
- Pandas
- NumPy
- Scikit-learn

---

## 📄 License

No license for now


# 🇲🇽 Dashboard Interactivo de Economía de México (1990–2026)

> **Visualiza, analiza y proyecta la evolución económica de México mediante un dashboard interactivo desarrollado con Streamlit.**

Este proyecto integra indicadores económicos, demográficos e históricos provenientes de fuentes oficiales para facilitar el análisis de largo plazo de la economía mexicana. Además, incorpora modelos de aprendizaje automático para realizar proyecciones y relaciona los principales acontecimientos económicos y políticos con el desempeño de la Selección Mexicana en los Mundiales de la FIFA.

---

# 📸 Vista general

El dashboard permite explorar de forma interactiva más de **35 años de información económica**, comparar indicadores nacionales e internacionales y generar análisis visuales sin necesidad de programar.

---

# ✨ Características principales

## 📈 Indicadores económicos

- Producto Interno Bruto (PIB nominal y real)
- PIB per cápita
- Deuda pública
- Deuda como porcentaje del PIB
- Inflación (INPC)
- Tipo de cambio
- Inversión Extranjera Directa (IED)
- Desempleo
- Indicadores demográficos
- Comparativas internacionales (Banco Mundial)

---

## 📊 Visualizaciones

El proyecto incluye:

- Gráficas interactivas con Plotly
- Comparación de hasta dos variables simultáneamente
- Doble eje Y
- Transformaciones estadísticas
- Índice Base 100
- Variaciones porcentuales
- Escala logarítmica
- Z-Score
- Series históricas
- Comparaciones internacionales
- Trazabilidad de datos

---

## 🤖 Modelos predictivos

Se incluyen diferentes algoritmos para realizar proyecciones de indicadores económicos:

- Elastic Net
- Regresión Bayesiana
- Gradient Boosting

Cada modelo puede evaluarse mediante métricas como:

- R² histórico
- RMSE
- Validación temporal
- Error de predicción

---

## ⚽ Economía y Mundiales

Una característica distintiva del proyecto es la integración del desempeño de México en los Mundiales de la FIFA:

- Fase alcanzada
- Goles anotados
- Goles recibidos
- Comparación con indicadores económicos
- Contexto político e histórico

---

# 🗂️ Estructura del proyecto

```text
.
├── app_streamlit_dashboard.py      # Aplicación principal
├── data/                           # Bases de datos
├── variable_map.csv                # Diccionario de variables
├── requirements.txt                # Dependencias
└── README.md
```

---

# ▶️ Instalación

Crear un entorno virtual:

```powershell
python -m venv .venv
```

Activarlo:

```powershell
.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Ejecutar el dashboard:

```powershell
streamlit run app_streamlit_dashboard.py
```

---

# 🗃️ Principales fuentes de datos

Los datos provienen de organismos oficiales, entre ellos:

- 🇲🇽 INEGI
- 🇲🇽 Banco de México
- 🇲🇽 Secretaría de Hacienda y Crédito Público (SHCP)
- 🌎 Banco Mundial (World Development Indicators)
- 🌎 Fondo Monetario Internacional (FMI)
- ⚽ FIFA

---

# 🛠️ Tecnologías utilizadas

- Python
- Streamlit
- Plotly
- Pandas
- NumPy
- Scikit-learn

---

# 📚 Metodología

Las comparaciones internacionales utilizan indicadores homologados del **Banco Mundial (WDI)**.

Para la deuda pública se emplea el indicador **Central Government Debt (% of GDP)**, ya que permite realizar comparaciones consistentes entre distintos países.

---

# 🎯 Objetivos del proyecto

- Facilitar el análisis de la economía mexicana.
- Integrar múltiples fuentes oficiales en un solo dashboard.
- Aplicar Ciencia de Datos al análisis económico.
- Incorporar modelos predictivos para apoyar la toma de decisiones.
- Servir como proyecto demostrativo de Ingeniería de Datos, Ciencia de Datos y Visualización.

---

# 👨‍💻 Autor

**Alain Medel**

Ingeniero en Electrónica • Maestro en Física Aplicada • Ciencia de Datos • Inteligencia Artificial • Energías Renovables

---

# 📄 Licencia

No hay autorización de uso comercial. 
