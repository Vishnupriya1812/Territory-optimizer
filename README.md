# Sales Territory Optimiser & Whitespace Analyser

An B2B Sales geo-analytics application built with Python, SQLite, Scikit-Learn, and Streamlit. The system segments geographic markets into Saturated, Balanced, and Whitespace opportunities by comparing actual sales performance against US Census business density.

---

## 🏗️ Project Architecture

```
Stage 1: Data Ingestion (src/ingest.py)
  ├── Load raw Kaggle CRM B2B Sales & Team structure
  ├── Deterministically map B2B accounts to US states aligning with agent territories
  └── Ingest 2022 US Census County Business Patterns (CBP) data (API with local fallback)
         ↓
Stage 2: SQLite database rollups (src/transform.py)
  ├── sql/01_territory_rollup.sql -> Roll up won revenue & active reps by state
  ├── sql/02_rep_coverage.sql    -> Compute representative density & efficiency metrics
  └── sql/03_whitespace_view.sql  -> Join rollup with Census market potential proxy (GDP Proxy)
         ↓
Stage 3: ML Modelling (src/model.py)
  ├── Calculate Penetration Index = total_revenue / market_potential
  ├── Standardize features and run K-Means Clustering (3 clusters)
  └── Sort and classify dynamically into: Saturated, Balanced, and Whitespace
         ↓
Stage 4: Geo Integration & Visualization (src/geo.py & app/map_component.py)
  ├── Load state boundaries from us-states.json and join with scored ML metrics
  └── Build Folium interactive map showing segment codes and hover tooltips
         ↓
Stage 5: Streamlit Web Dashboard (app/streamlit_app.py)
  ├── Sidebar filters (Classification, minimum potential)
  ├── Tab 1: Interactive Leaflet Map showing state hover cards and popups
  ├── Tab 2: Custom CSV Upload Scorer (runs calculations on uploaded CSVs dynamically)
  └── Tab 3: Glossary and business presentation helper
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.9+ and `pip` installed.

### 2. Local Setup
Recreate the virtual environment and install the required libraries:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Data Pipeline
Execute the pipeline in sequence to clean data, perform SQL transforms, and run the ML segmentation models:
```bash
# Stage 1: Ingest and map raw CRM data and Census metrics
python src/ingest.py

# Stage 2: Load SQLite database and run SQL queries
python src/transform.py

# Stage 3: Perform ML segmentation and dynamic scoring
python src/model.py
```
This generates `data/processed/territory_scored.csv` which is read by the dashboard.

### 4. Start the Streamlit App
Run the local development server:
```bash
streamlit run app/streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🐳 Running with Docker

To containerize and run the app locally:
```bash
# Build the image
docker build -t territory-optimiser .

# Run the container
docker run -p 8501:8501 territory-optimiser
```
The app will be accessible at [http://localhost:8501](http://localhost:8501).

---

## 📈 Key Business Definitions

| Metric | Calculation | Definition / Interpretation |
|---|---|---|
| **Penetration Index** | `total_revenue / market_potential` | High index (>0.7) means saturated; Low index (<0.3) means whitespace opportunity. |
| **Market Potential** | `total_establishments * avg_payroll_per_employee` | GDP-based proxy for the total addressable market (TAM) in a state. |
| **Revenue Gap** | `market_potential - total_revenue` | Total dollar volume of unpenetrated market demand. |
| **Recommended Investment** | `revenue_gap * 0.05` | Budget recommendation based on a 5% target conversion rate of the gap. |
