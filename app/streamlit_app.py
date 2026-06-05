import sys
from pathlib import Path
# Insert parent directory to allow relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from src import config

# Set page configuration with a wide layout and a custom title
st.set_page_config(
    page_title="Sales Territory Optimiser & Whitespace Analyser",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling using CSS
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap');
    
    /* Main Layout Styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        font-family: 'Inter', sans-serif;
    }
    
    /* Typography */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Banner Styling */
    .banner {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        text-align: left;
    }
    .banner h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 300;
        opacity: 0.9;
    }
    
    /* Metric Cards Styling */
    .card-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .kpi-card {
        flex: 1;
        min-width: 220px;
        background: rgba(30, 41, 59, 0.45); /* Theme-friendly translucent dark slate */
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.25rem;
    }
    
    /* Sidebar adjustments - remove white background for native theme adaptation */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        background-color: #0b1329 !important;
    }
    
    /* Premium styling for sidebar radio buttons */
    div[data-testid="stRadio"] > div {
        gap: 0.6rem;
    }
    div[data-testid="stRadio"] label {
        background-color: rgba(30, 41, 59, 0.45) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding: 0.65rem 1rem !important;
        border-radius: 10px !important;
        margin-bottom: 0px !important;
        transition: all 0.25s ease !important;
        cursor: pointer !important;
    }
    div[data-testid="stRadio"] label:hover {
        background-color: rgba(59, 130, 246, 0.15) !important;
        border-color: rgba(59, 130, 246, 0.35) !important;
        transform: translateX(4px);
    }
    /* Style checked menu tab item in sidebar */
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%) !important;
        border-color: #1a73e8 !important;
        box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
    }
    div[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] {
        font-weight: 600 !important;
        color: #f8fafc !important;
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Segment colors */
    .lbl-whitespace { color: #ea4335; font-weight: bold; }
    .lbl-balanced { color: #fbbc05; font-weight: bold; }
    .lbl-saturated { color: #34a853; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Load scored data for sidebar bounds & global KPI indicators
scored_data_path = config.TERRITORY_SCORED_PATH
if not scored_data_path.exists():
    st.error("No scored territory database found. Please run the data ingestion and SQL transforms first.")
    st.info("Run `python src/ingest.py` followed by `python src/transform.py` and `python src/model.py` to generate the workspace files.")
    st.stop()
    
df_scored = pd.read_csv(scored_data_path)

# Load cleaned CRM opportunities data for pipeline feature components
crm_data_path = config.PROCESSED_DATA_DIR / "crm_cleaned.csv"
if not crm_data_path.exists():
    st.error("No cleaned CRM database found. Please run the data ingestion and SQL transforms first.")
    st.info("Run `python src/ingest.py` followed by `python src/transform.py` and `python src/model.py` to generate the workspace files.")
    st.stop()

df_crm = pd.read_csv(crm_data_path)

# Sidebar Tabs Navigation & Filter Section
with st.sidebar:
    st.markdown("## 🧭 Dashboard Tabs")
    selected_tab = st.radio(
        "Select Tab View:",
        options=[
            "🗺️ Spatial Analytics Map",
            "🔮 Scenario Planner & Simulator",
            "🎯 Industry Sector Analyser",
            "🏆 Rep Performance & Leaderboard",
            "📅 Pipeline Forecast & Velocity",
            "📊 Custom CSV Upload Scorer",
            "📖 Glossary & Business Metrics"
        ]
    )
    st.markdown("---")
    
    # Render map filters only when the map page is active
    if selected_tab == "🗺️ Spatial Analytics Map":
        st.markdown("### 🔍 Map Filters & Settings")
        selected_labels = st.multiselect(
            "Territory Type Classification",
            options=['whitespace', 'balanced', 'saturated'],
            default=['whitespace', 'balanced', 'saturated']
        )
        
        max_pot_m = float(df_scored['market_potential'].max() / 1000.0)
        min_potential_m = st.slider(
            "Min Market Potential ($M)",
            min_value=0.0,
            max_value=max_pot_m,
            value=0.0,
            step=max_pot_m / 50.0 if max_pot_m > 0 else 1.0,
            format="$%.1fM"
        )
    else:
        # Default fallback values for other pages that might reference them
        selected_labels = ['whitespace', 'balanced', 'saturated']
        min_potential_m = 0.0
        
    st.markdown("### 💡 Business Narrative Context")
    st.info(
        "**B2B Territory Optimisation Framing:**\n"
        "Whitespace territories represent regions containing high business density (utilities, construction, "
        "industrial pumps/equipment customers) but low representative presence or sales. Saturated territories are fully staffed regions. "
        "Allocating new representatives to **high-potential whitespace** drives max marginal revenue."
    )

# Filter the data dynamically based on sidebar settings (mostly used by map view)
df_scored['market_potential_m'] = df_scored['market_potential'] / 1000.0
df_filtered = df_scored[
    df_scored['territory_label'].isin(selected_labels) & 
    (df_scored['market_potential_m'] >= min_potential_m)
]

# Header Banner
st.markdown("""
<div class="banner">
    <h1>Sales Territory Optimiser & Whitespace Analyser</h1>
    <p>B2B Sales Pipeline & US Census Market Potential Segmentation Dashboard</p>
</div>
""", unsafe_allow_html=True)

# Import rendering modules
from app.map_component import render_map
from app.scorer_component import render_scorer
from app.features_components import (
    render_simulator_page,
    render_sector_page,
    render_rep_page,
    render_forecasting_page
)

# Route content depending on active sidebar tab selection
if selected_tab == "🗺️ Spatial Analytics Map":
    # Calculate dynamic KPIs based on active filters
    if not df_filtered.empty:
        total_rev = df_filtered['total_revenue'].sum()
        total_potential = df_filtered['market_potential'].sum()
        total_gap = df_filtered['revenue_gap'].sum()
        
        states_with_reps = len(df_filtered[df_filtered['rep_count'] > 0])
        total_states = len(df_filtered)
        coverage_pct = (states_with_reps / total_states) * 100 if total_states > 0 else 0.0
    else:
        total_rev = 0.0
        total_potential = 0.0
        total_gap = 0.0
        coverage_pct = 0.0
        states_with_reps = 0
        total_states = 0

    # Render dynamic KPIs using customized CSS cards
    st.markdown(f"""
    <div class="card-container">
        <div class="kpi-card">
            <div class="kpi-title">Active CRM Revenue (Won)</div>
            <div class="kpi-value">${total_rev:,.0f}</div>
            <div class="kpi-sub">Sales volume in filtered territories</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Active Market Potential (TAM)</div>
            <div class="kpi-value">${total_potential / 1e9:,.2f}B</div>
            <div class="kpi-sub">Census business capacity proxy</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Active Coverage Reach</div>
            <div class="kpi-value">{coverage_pct:.1f}%</div>
            <div class="kpi-sub">{states_with_reps} of {total_states} filtered states staffed</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Active Revenue Gap</div>
            <div class="kpi-value" style="color: #ea4335;">${total_gap / 1e9:,.2f}B</div>
            <div class="kpi-sub">Unpenetrated market opportunity</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_map(selected_labels, min_potential_m)
    
    # Add Interactive Charts below the map
    st.markdown("---")
    st.markdown("### 📊 Advanced Segment Visualizations")
    
    if not df_filtered.empty:
        import plotly.express as px
        import numpy as np
        
        c1, c2 = st.columns(2)
        
        with c1:
            # 1. Market Potential vs Revenue Scatter Plot
            fig_scatter = px.scatter(
                df_filtered,
                x="market_potential_m",
                y="total_revenue",
                color="territory_label",
                size=np.clip(df_filtered["revenue_gap"] / 1000.0, 1.0, None), # size by gap in Millions, min size 1
                hover_name="state",
                hover_data=["rep_count", "penetration_index_norm"],
                labels={
                    "market_potential_m": "Market Potential ($M)",
                    "total_revenue": "Total Won Revenue ($)",
                    "territory_label": "Segment Class"
                },
                title="Market Potential vs. Won Revenue (Point Size = Revenue Gap)",
                color_discrete_map={
                    'whitespace': '#ea4335',
                    'balanced': '#fbbc05',
                    'saturated': '#34a853'
                }
            )
            fig_scatter.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)',
                font_color='#f8fafc',
                title_font_family='Outfit',
                font_family='Inter',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_scatter.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            fig_scatter.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with c2:
            # 2. Horizontal Bar Chart of Top Whitespace Opportunities
            df_ws = df_filtered[df_filtered['territory_label'] == 'whitespace'].sort_values(by='revenue_gap', ascending=True).tail(10)
            if not df_ws.empty:
                df_ws['revenue_gap_m'] = df_ws['revenue_gap'] / 1000000.0  # in Millions
                fig_bar = px.bar(
                    df_ws,
                    x="revenue_gap_m",
                    y="state",
                    orientation='h',
                    title="Top Growth Opportunities (Revenue Gap in $M)",
                    labels={
                        "revenue_gap_m": "Revenue Gap ($M)",
                        "state": "State"
                    },
                    color_discrete_sequence=['#ea4335']
                )
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,41,59,0.3)',
                    font_color='#f8fafc',
                    title_font_family='Outfit',
                    font_family='Inter'
                )
                fig_bar.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig_bar.update_yaxes(showgrid=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No active whitespace territories match the filter criteria. Select 'whitespace' to view opportunities.")
    else:
        st.warning("No data available to display charts. Try widening your filters.")

elif selected_tab == "🔮 Scenario Planner & Simulator":
    render_simulator_page(df_scored)
    
elif selected_tab == "🎯 Industry Sector Analyser":
    render_sector_page(df_crm, df_scored)
    
elif selected_tab == "🏆 Rep Performance & Leaderboard":
    render_rep_page(df_crm)
    
elif selected_tab == "📅 Pipeline Forecast & Velocity":
    render_forecasting_page(df_crm)

elif selected_tab == "📊 Custom CSV Upload Scorer":
    render_scorer()
    
elif selected_tab == "📖 Glossary & Business Metrics":
    st.subheader("📖 Business Metrics Glossary")
    st.write(
        "This glossary provides standard definitions used throughout the analysis "
        "pipeline to align sales teams and business analysts."
    )
    
    glossary_data = pd.DataFrame([
        {
            "Metric Name": "Penetration Index",
            "Formula": "actual_revenue / market_potential",
            "Target Threshold": "< 0.3 = Whitespace; > 0.7 = Saturated",
            "Interpretation": "Measures capture rate of addressable market. A low index in a large market indicates opportunity."
        },
        {
            "Metric Name": "Revenue per Rep",
            "Formula": "total_revenue / rep_count",
            "Target Threshold": "N/A (Efficiency ratio)",
            "Interpretation": "Measures active sales agent efficiency. Underserved territories often show artificially low values."
        },
        {
            "Metric Name": "Revenue Gap",
            "Formula": "market_potential - actual_revenue",
            "Target Threshold": "Higher is better for growth",
            "Interpretation": "Estimated dollar opportunity if territory was fully penetrated."
        },
        {
            "Metric Name": "Coverage %",
            "Formula": "(states_with_reps / total_states) * 100",
            "Target Threshold": "Target > 80%",
            "Interpretation": "Sales force geographic footprint reach."
        },
        {
            "Metric Name": "Deals per Rep",
            "Formula": "deal_count / rep_count",
            "Target Threshold": "N/A (Workload ratio)",
            "Interpretation": "Proxy for sales representative workload and deal velocity in a state."
        }
    ])
    
    st.table(glossary_data)
    
    st.markdown("### Executive Summary Guide")
    st.success(
        "**Narrative:** *'In building this model, we merged CRM sales records with US Census county business patterns "
        "to discover unserved demand. By clustering states using normalized penetration and rep density, we identified "
        "several key regions with high business density but zero representatives. For instance, the Midwest holds "
        "substantial utility density but represents a massive whitespace. Directing new headcounts to these specific regions "
        "unlocks the highest return on investment.'*"
    )
