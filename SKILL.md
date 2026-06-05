# SKILL: Sales Territory Optimiser & Whitespace Analyser
**Grundfos BA Interview Portfolio Project**

You are helping build a geo-analytics Python project that identifies underpenetrated sales territories ("whitespace") by combining CRM sales data with US Census business density data. The end goal is a deployed Streamlit app with Power BI dashboards that a business analyst can demo in an interview context.

---

## Project Architecture (5-Stage Pipeline)

```
Stage 1: Data Ingestion
  ├── Kaggle CRM Sales Opportunities dataset
  ├── US Census business density data (zip/state)
  └── Synthetic enrichment (rep headcount, GDP proxy)
        ↓
Stage 2: SQL Transforms (DuckDB or SQLite)
  ├── Revenue rollup by zip / state / region
  ├── Deal count and rep coverage aggregations
  └── Territory-level summary tables
        ↓
Stage 3: ML Modelling (Python)
  ├── Penetration Index = actual_revenue ÷ market_potential
  ├── K-Means clustering → saturated / balanced / whitespace
  └── Geo join (GeoPandas) — attach scores to shapefiles
        ↓
Stage 4: Power BI Dashboard
  ├── Choropleth map of penetration index by state/zip
  ├── Top-10 whitespace opportunities table
  └── KPI cards: coverage %, revenue gap
        ↓
Stage 5: Streamlit Web App (deployed on Render)
  ├── Interactive Folium map — click region → scores
  ├── Territory scorer — upload CSV → instant output
  └── Public URL via Docker + Render
```

---

## Directory Structure to Maintain

```
grundfos_territory_optimiser/
│
├── data/
│   ├── raw/                    # downloaded CSVs, never edited
│   │   ├── kaggle_crm_sales.csv
│   │   └── census_business_density.csv
│   ├── processed/              # cleaned, joined outputs
│   │   ├── territory_master.csv
│   │   └── territory_scored.csv
│   └── shapefiles/             # US state/zip GeoJSON files
│       └── us_states.geojson
│
├── sql/
│   ├── 01_territory_rollup.sql
│   ├── 02_rep_coverage.sql
│   └── 03_whitespace_view.sql
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_penetration_index.ipynb
│   └── 03_kmeans_clustering.ipynb
│
├── src/
│   ├── ingest.py               # download + validate raw data
│   ├── transform.py            # SQL execution wrapper
│   ├── model.py                # penetration index + K-Means
│   ├── geo.py                  # GeoPandas spatial joins
│   └── utils.py                # shared helpers
│
├── app/
│   ├── streamlit_app.py        # main Streamlit entry point
│   ├── map_component.py        # Folium map builder
│   └── scorer_component.py     # CSV upload scorer
│
├── powerbi/
│   └── territory_dashboard.pbix
│
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Stage 1 — Data Ingestion

### Kaggle Dataset
- **Source:** "CRM Sales Opportunities" on Kaggle (B2B sales pipeline)
- **Key columns to preserve:** `account_name`, `close_date`, `revenue`, `region`, `state`, `zip_code`, `sales_rep`, `deal_stage`
- **Download method:** Use `kaggle` CLI or direct CSV drop into `data/raw/`

### US Census Data
- **Source:** Census Bureau County Business Patterns (CBP) API or pre-downloaded CSV
- **Key columns:** `zip_code` or `state_fips`, `total_establishments`, `naics_sector`, `annual_payroll`
- **Use as market potential proxy** — more establishments = larger addressable market

### Synthetic Enrichment
- If real rep headcount data is unavailable, generate synthetic `rep_count` per state using a seeded random distribution that roughly correlates with population
- Add a `gdp_proxy` column = `total_establishments × avg_payroll_per_employee`
- Document all synthetic assumptions clearly in code comments for interview transparency

### Validation Rules
```python
# Always enforce these after ingestion
assert df['zip_code'].str.len().eq(5).all(), "ZIP codes must be 5 digits"
assert df['revenue'].ge(0).all(), "Revenue cannot be negative"
assert df['state'].isin(US_STATE_ABBREVS).all(), "Invalid state codes"
```

---

## Stage 2 — SQL Transforms

Use **DuckDB** (preferred — runs in-process, no server needed) or SQLite.

### Key Queries to Build

**01_territory_rollup.sql**
```sql
-- Roll up revenue, deal count, rep coverage by state
SELECT
    state,
    COUNT(DISTINCT sales_rep)        AS rep_count,
    COUNT(*)                         AS deal_count,
    SUM(revenue)                     AS total_revenue,
    AVG(revenue)                     AS avg_deal_size
FROM crm_sales
WHERE deal_stage = 'Won'
GROUP BY state;
```

**02_rep_coverage.sql**
```sql
-- Revenue per rep (efficiency metric)
SELECT
    state,
    total_revenue / NULLIF(rep_count, 0) AS revenue_per_rep,
    deal_count    / NULLIF(rep_count, 0) AS deals_per_rep
FROM territory_rollup;
```

**03_whitespace_view.sql**
```sql
-- Join CRM rollup with Census market potential
SELECT
    t.state,
    t.total_revenue,
    t.rep_count,
    c.gdp_proxy                             AS market_potential,
    t.total_revenue / NULLIF(c.gdp_proxy, 0) AS penetration_index_raw
FROM territory_rollup t
LEFT JOIN census_enriched c ON t.state = c.state;
```

### DuckDB Usage Pattern
```python
import duckdb
con = duckdb.connect("data/processed/territory.duckdb")
con.execute("CREATE TABLE crm_sales AS SELECT * FROM read_csv_auto('data/raw/kaggle_crm_sales.csv')")
df = con.execute("SELECT * FROM territory_rollup").df()
```

---

## Stage 3 — ML Modelling

### Penetration Index (Custom Metric)
```python
def compute_penetration_index(df):
    """
    Penetration Index = actual revenue / estimated market potential
    Normalised to 0–1 scale for comparability across territories.
    Low score + high market potential = whitespace opportunity.
    """
    df['penetration_index'] = df['total_revenue'] / df['market_potential']
    # Normalise using min-max so index is always 0–1
    min_pi = df['penetration_index'].min()
    max_pi = df['penetration_index'].max()
    df['penetration_index_norm'] = (df['penetration_index'] - min_pi) / (max_pi - min_pi)
    return df
```

### K-Means Clustering (Territory Segmentation)
```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

FEATURES = ['penetration_index_norm', 'revenue_per_rep', 'market_potential_norm']
N_CLUSTERS = 3  # saturated, balanced, whitespace

def cluster_territories(df):
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURES])
    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df['cluster'] = km.fit_predict(X)
    # Label clusters by penetration index mean (lowest = whitespace)
    cluster_means = df.groupby('cluster')['penetration_index_norm'].mean().sort_values()
    label_map = {
        cluster_means.index[0]: 'whitespace',
        cluster_means.index[1]: 'balanced',
        cluster_means.index[2]: 'saturated'
    }
    df['territory_label'] = df['cluster'].map(label_map)
    return df
```

### GeoPandas Spatial Join
```python
import geopandas as gpd

def attach_geo(df, shapefile_path='data/shapefiles/us_states.geojson'):
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.rename(columns={'STUSPS': 'state'})  # adjust column name to match
    merged = gdf.merge(df, on='state', how='left')
    return merged  # GeoDataFrame with geometry + scores
```

---

## Stage 4 — Power BI Dashboard

### Expected .pbix Contents
1. **Choropleth Map** — US states coloured by `penetration_index_norm` (red = whitespace, green = saturated)
2. **Top-10 Whitespace Table** — sorted by `market_potential DESC` where `territory_label = 'whitespace'`
3. **KPI Cards:**
   - `Coverage %` = states with at least 1 rep / total states × 100
   - `Revenue Gap` = SUM(market_potential) - SUM(total_revenue) for whitespace territories
   - `Avg Penetration Index` = mean of `penetration_index_norm`

### Data Connection
- Export `data/processed/territory_scored.csv` → import into Power BI Desktop
- Refresh strategy: manual for portfolio; can add scheduled refresh if hosted

---

## Stage 5 — Streamlit App

### Entry Point Structure (`app/streamlit_app.py`)
```python
import streamlit as st
st.set_page_config(page_title="Territory Optimiser", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Filters")
    selected_label = st.multiselect("Territory type", ['whitespace', 'balanced', 'saturated'], default=['whitespace'])
    min_potential = st.slider("Min market potential ($M)", 0, 500, 50)

# Main tabs
tab1, tab2 = st.tabs(["🗺️ Interactive Map", "📊 Territory Scorer"])
with tab1:
    from map_component import render_map
    render_map(selected_label, min_potential)
with tab2:
    from scorer_component import render_scorer
    render_scorer()
```

### Folium Map Component (`app/map_component.py`)
```python
import folium
import streamlit.components.v1 as components

def render_map(labels, min_potential):
    # Load scored GeoDataFrame
    # Filter by selected labels and minimum potential
    # Colour-code by territory_label: red=whitespace, yellow=balanced, green=saturated
    # On click: popup showing state, revenue, market_potential, penetration_index, recommended_investment
    m = folium.Map(location=[39.5, -98.35], zoom_start=4)
    # ... choropleth + popup logic
    components.html(m._repr_html_(), height=600)
```

### Territory Scorer (`app/scorer_component.py`)
```python
def render_scorer():
    uploaded = st.file_uploader("Upload territory CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        df = compute_penetration_index(df)
        df = cluster_territories(df)
        st.dataframe(df[['state', 'penetration_index_norm', 'territory_label']])
        st.download_button("Download scored CSV", df.to_csv(index=False), "scored.csv")
```

### Deployment (Render + Docker)

**Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**render.yaml**
```yaml
services:
  - type: web
    name: territory-optimiser
    runtime: docker
    plan: free
    envVars:
      - key: STREAMLIT_SERVER_HEADLESS
        value: "true"
```

---

## Requirements (`requirements.txt`)

```
pandas>=2.0
geopandas>=0.14
folium>=0.15
streamlit>=1.33
duckdb>=0.10
scikit-learn>=1.4
matplotlib>=3.8
plotly>=5.20
kaggle>=1.6
requests>=2.31
python-dotenv>=1.0
openpyxl>=3.1          # Power BI CSV export compatibility
```

---

## Key Business Metrics & Interview-Ready Definitions

| Metric | Formula | Interpretation |
|---|---|---|
| **Penetration Index** | `actual_revenue / market_potential` | < 0.3 = whitespace; > 0.7 = saturated |
| **Revenue per Rep** | `total_revenue / rep_count` | Efficiency; low in underserved territories |
| **Revenue Gap** | `market_potential - actual_revenue` | Dollar opportunity if fully penetrated |
| **Coverage %** | `states_with_reps / total_states × 100` | Sales force reach |
| **Deals per Rep** | `deal_count / rep_count` | Workload proxy |

**Interview narrative:** *"The Midwest generated 60% of coastal revenue with only 20% of rep headcount — but three states had near-zero penetration despite strong business density. Classic whitespace worth prioritising for Grundfos pump and water solution sales."*

---

## Coding Conventions

- All functions must have docstrings with `Args:` and `Returns:` sections
- Use `pathlib.Path` for all file paths, never string concatenation
- Load config (paths, cluster count, thresholds) from `config.py` or `.env`, never hardcode
- Separate data loading, transformation, and visualisation into distinct functions — never mix in a single block
- Write one pytest test per SQL query verifying row counts and null checks
- Every notebook must have a markdown cell at the top explaining its purpose and expected inputs/outputs

---

## Common Pitfalls to Avoid

- **ZIP code type:** always store as string with leading zeros (`'01001'` not `1001`)
- **Projection:** use `EPSG:4326` for Folium; reproject with `gdf.to_crs(epsg=4326)` if needed
- **K-Means instability:** always set `random_state=42` and `n_init=10`; re-label clusters by penetration mean, not by cluster number (cluster numbers are arbitrary)
- **Division by zero:** use `NULLIF` in SQL and `np.where(denominator > 0, num/denom, 0)` in Python
- **Market potential skew:** log-transform `market_potential` before clustering if distribution is heavily right-skewed
- **Streamlit reruns:** cache expensive operations with `@st.cache_data`

---

## Grundfos Context (for Interview Framing)

Grundfos sells pumps and water solutions B2B across industrial, commercial, and municipal segments. When referencing the project in interviews:

- Map "customer segments" to NAICS codes in Census data (e.g., 22 = Utilities, 23 = Construction — both Grundfos targets)
- "Market potential" can be framed as number of relevant establishments × average spend per pump system
- Whitespace territories are states/regions with high relevant business density but low Grundfos rep presence or revenue
- Recommended investment level = `revenue_gap × conversion_rate_assumption` (document assumption explicitly)
