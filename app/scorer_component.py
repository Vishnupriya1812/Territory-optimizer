import sys
from pathlib import Path
# Insert parent directory to allow relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st
from src.model import compute_penetration_index, cluster_territories

def render_scorer():
    """
    Renders the territory scorer component.
    Allows user to download a template CSV, upload data, and score territories dynamically.
    """
    st.subheader("📊 Live Territory Whitespace Scorer")
    st.write(
        "Upload a CSV of your raw sales territories containing state, revenue, "
        "rep headcount, and estimated market potential. Antigravity's built-in ML engine "
        "will instantly calculate penetration scores and segment them into Whitespace, Balanced, "
        "and Saturated categories."
    )
    
    # Template download
    st.markdown("### 1. Download Input Template")
    st.write("First, download this pre-formatted template to ensure your columns match our system:")
    
    template_data = pd.DataFrame([
        {"state": "NY", "total_revenue": 1250000.0, "market_potential": 18000000.0, "rep_count": 3},
        {"state": "TX", "total_revenue": 5500000.0, "market_potential": 22000000.0, "rep_count": 8},
        {"state": "CA", "total_revenue": 210000.0, "market_potential": 45000000.0, "rep_count": 1},
        {"state": "OH", "total_revenue": 850000.0, "market_potential": 9000000.0, "rep_count": 2},
        {"state": "WY", "total_revenue": 400000.0, "market_potential": 800000.0, "rep_count": 2}
    ])
    
    template_csv = template_data.to_csv(index=False)
    st.download_button(
        label="📥 Download Template CSV",
        data=template_csv,
        file_name="territory_template.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    # File upload
    st.markdown("### 2. Upload and Segment Your Data")
    uploaded_file = st.file_uploader("Upload territory CSV", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Verify required columns
            required_cols = ["state", "total_revenue", "market_potential", "rep_count"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}. Please check the template format.")
                return
                
            st.success("File uploaded successfully! Running ML scoring...")
            
            # Compute intermediate performance metrics needed for features
            # revenue_per_rep
            df['revenue_per_rep'] = np.where(
                df['rep_count'] > 0,
                df['total_revenue'] / df['rep_count'],
                0.0
            )
            
            # Compute penetration and cluster
            df = compute_penetration_index(df)
            df = cluster_territories(df)
            
            # Calculate gap and recommended investment
            df['revenue_gap'] = np.clip(df['market_potential'] - df['total_revenue'], 0.0, None)
            df['recommended_investment'] = df['revenue_gap'] * 0.05
            
            # Visualise summary metrics
            c1, c2, c3 = st.columns(3)
            with c1:
                whitespace_count = len(df[df['territory_label'] == 'whitespace'])
                st.metric("Whitespace Territories Found", f"{whitespace_count} states")
            with c2:
                total_gap = df['revenue_gap'].sum()
                st.metric("Total Revenue Gap", f"${total_gap:,.2f}")
            with c3:
                avg_pi = df['penetration_index_norm'].mean()
                st.metric("Avg Penetration Index (Norm)", f"{avg_pi:.3f}")
                
            # Display results table
            st.markdown("### Segmented Results")
            st.write("Click column headers to sort the table. Labeled output is ready for download below.")
            
            # Style the dataframe output
            display_df = df[[
                'state', 'total_revenue', 'market_potential', 'rep_count', 
                'penetration_index_norm', 'revenue_gap', 'territory_label'
            ]].copy()
            
            display_df = display_df.rename(columns={
                'state': 'State',
                'total_revenue': 'Total Revenue ($)',
                'market_potential': 'Market Potential ($)',
                'rep_count': 'Sales Reps',
                'penetration_index_norm': 'Penetration Index (Norm)',
                'revenue_gap': 'Revenue Gap ($)',
                'territory_label': 'Classification'
            })
            
            st.dataframe(display_df.style.format({
                'Total Revenue ($)': '{:,.2f}',
                'Market Potential ($)': '{:,.2f}',
                'Penetration Index (Norm)': '{:.3f}',
                'Revenue Gap ($)': '{:,.2f}'
            }), use_container_width=True)
            
            # Download scored results
            scored_csv = df.to_csv(index=False)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.write("")
                st.write("")
                st.download_button(
                    label="📥 Download Scored Results CSV",
                    data=scored_csv,
                    file_name="territory_segmented_results.csv",
                    mime="text/csv"
                )
                
            # Add dynamic clustering visualization for uploaded data
            st.markdown("---")
            st.markdown("### 📈 Segment Clustering Visualizer (Custom Upload)")
            import plotly.express as px
            fig_upload = px.scatter(
                df,
                x="market_potential",
                y="total_revenue",
                color="territory_label",
                hover_name="state",
                hover_data=["rep_count", "penetration_index_norm"],
                labels={
                    "market_potential": "Market Potential ($)",
                    "total_revenue": "Total Revenue ($)",
                    "territory_label": "Classification"
                },
                title="Custom Territories Segment Distribution (K-Means Clustering)",
                color_discrete_map={
                    'whitespace': '#ea4335',
                    'balanced': '#fbbc05',
                    'saturated': '#34a853'
                }
            )
            fig_upload.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)',
                font_color='#f8fafc',
                title_font_family='Outfit',
                font_family='Inter',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_upload.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            fig_upload.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_upload, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error processing CSV: {e}")
