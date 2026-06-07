import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from src import config

# ==========================================
# FORMATTING UTILITIES FOR PREMIUM METRICS
# ==========================================
def format_compact_currency(val):
    if abs(val) >= 1e9:
        return f"${val / 1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"${val / 1e6:.1f}M"
    elif abs(val) >= 1e3:
        return f"${val / 1e3:.0f}K"
    else:
        return f"${val:.0f}"

def format_compact_percentage(val):
    if abs(val) >= 1e6:
        return f"{val / 1e6:.2f}M%"
    elif abs(val) >= 1e3:
        return f"{val:,.0f}%"
    else:
        return f"{val:.1f}%"

def format_delta_currency(val):
    sign = "+" if val >= 0 else "-"
    return f"{sign}{format_compact_currency(abs(val))}"

def format_delta_percentage(val):
    sign = "+" if val >= 0 else "-"
    return f"{sign}{format_compact_percentage(abs(val))}"

# ==========================================
# FEATURE 1: SCENARIO PLANNER & SIMULATOR
# ==========================================
def render_simulator_page(df_scored):
    st.subheader("🔮 Scenario Planner & Resource Simulator")
    st.write(
        "Simulate deploying new sales representatives to territories. Predict "
        "incremental revenue, sales reach expansion, and ROI based on historical "
        "penetration rates."
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Simulation Inputs")
        new_reps = st.slider("New Sales Reps to Deploy", 1, 20, 5)
        
        strategy = st.selectbox(
            "Deployment Strategy",
            options=[
                "Target Whitespaces (Highest TAM)",
                "Equal Distribution (Top Gap States)",
                "Target Lowest Penetration States"
            ]
        )
        
        rep_cost = st.number_input("Annual Cost per Rep ($)", min_value=30000, max_value=200000, value=100000, step=5000)
        conversion_rate = st.slider("Assumed Conversion Rate on Revenue Gap (%)", 1.0, 15.0, 5.0) / 100.0
        
        run_sim = st.button("🚀 Run Simulation")
        
    # Run the simulation logic
    if run_sim or 'sim_ran' not in st.session_state:
        st.session_state['sim_ran'] = True
        
        # Clone scored data for simulation
        sim_df = df_scored.copy()
        
        # Identify deployment states based on strategy
        if strategy == "Target Whitespaces (Highest TAM)":
            # Sort by whitespace segment first, then market potential desc
            sim_df['is_ws'] = (sim_df['territory_label'] == 'whitespace').astype(int)
            targets = sim_df.sort_values(by=['is_ws', 'market_potential'], ascending=[False, False])
        elif strategy == "Target Lowest Penetration States":
            # Sort by penetration index asc
            targets = sim_df.sort_values(by='penetration_index_norm', ascending=True)
        else: # Equal Distribution (Top Gap States)
            # Sort by revenue gap desc
            targets = sim_df.sort_values(by='revenue_gap', ascending=False)
            
        # Distribute reps
        assigned_reps = {state: 0 for state in sim_df['state']}
        target_states = targets['state'].tolist()
        
        for i in range(new_reps):
            state = target_states[i % len(target_states)]
            assigned_reps[state] += 1
            
        sim_df['new_reps_added'] = sim_df['state'].map(assigned_reps)
        sim_df['sim_rep_count'] = sim_df['rep_count'] + sim_df['new_reps_added']
        
        # Simulate revenue growth:
        # Each rep captures a percentage of the revenue gap (market_potential - total_revenue)
        # Dynamic return: Whitespace states give higher returns than saturated ones
        multiplier = {'whitespace': 1.2, 'balanced': 0.8, 'saturated': 0.3}
        
        def calculate_sim_rev(row):
            if row['new_reps_added'] == 0:
                return row['total_revenue']
            mult = multiplier.get(row['territory_label'], 0.8)
            captured = row['revenue_gap'] * conversion_rate * row['new_reps_added'] * mult
            # Bound simulated revenue to market potential
            return min(row['total_revenue'] + captured, row['market_potential'])
            
        sim_df['sim_revenue'] = sim_df.apply(calculate_sim_rev, axis=1)
        sim_df['sim_revenue_gap'] = np.clip(sim_df['market_potential'] - sim_df['sim_revenue'], 0.0, None)
        
        # Recalculate KPIs
        orig_rev = sim_df['total_revenue'].sum()
        sim_rev = sim_df['sim_revenue'].sum()
        incremental_rev = sim_rev - orig_rev
        
        orig_states_with_reps = len(sim_df[sim_df['rep_count'] > 0])
        sim_states_with_reps = len(sim_df[sim_df['sim_rep_count'] > 0])
        total_s = len(sim_df)
        orig_cov = (orig_states_with_reps / total_s) * 100 if total_s > 0 else 0.0
        sim_cov = (sim_states_with_reps / total_s) * 100 if total_s > 0 else 0.0
        
        total_investment = new_reps * rep_cost
        net_profit = incremental_rev - total_investment
        roi = (net_profit / total_investment) * 100 if total_investment > 0 else 0.0
        
        # Save simulation to session state
        st.session_state['sim_df'] = sim_df
        st.session_state['sim_kpis'] = (orig_rev, sim_rev, incremental_rev, orig_cov, sim_cov, total_investment, roi)

    # Render Simulation Outputs
    orig_rev, sim_rev, incremental_rev, orig_cov, sim_cov, total_investment, roi = st.session_state['sim_kpis']
    sim_df = st.session_state['sim_df']
    
    with col2:
        st.markdown("### Simulated Impact & ROI")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Investment", format_compact_currency(total_investment))
        with c2:
            st.metric("Incremental Revenue", format_compact_currency(incremental_rev), delta=format_delta_currency(incremental_rev))
        with c3:
            st.metric("Projected ROI", format_compact_percentage(roi), delta=format_delta_percentage(roi))
        with c4:
            st.metric("Coverage reach", format_compact_percentage(sim_cov), delta=format_delta_percentage(sim_cov - orig_cov))
            
        # Display chart comparing original vs simulated revenue for states receiving reps
        impacted_df = sim_df[sim_df['new_reps_added'] > 0].sort_values(by='new_reps_added', ascending=False)
        
        if not impacted_df.empty:
            chart_data = pd.melt(
                impacted_df, 
                id_vars=['state', 'new_reps_added'], 
                value_vars=['total_revenue', 'sim_revenue'],
                var_name='Scenario', 
                value_name='Revenue'
            )
            chart_data['Scenario'] = chart_data['Scenario'].map({'total_revenue': 'Current', 'sim_revenue': 'Simulated'})
            
            fig = px.bar(
                chart_data,
                x='state',
                y='Revenue',
                color='Scenario',
                barmode='group',
                title="Revenue Increase in Targeted States",
                labels={'state': 'State Code', 'Revenue': 'Revenue ($)'},
                color_discrete_map={'Current': '#94a3b8', 'Simulated': '#34a853'}
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.3)',
                font_color='#f8fafc',
                title_font_family='Outfit',
                font_family='Inter'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Assign representatives to view simulation results.")


# ==========================================
# FEATURE 2: INDUSTRY SECTOR ANALYSER
# ==========================================
def render_sector_page(df_crm, df_scored):
    st.subheader("🎯 Target Industry Sector Analyser")
    st.write(
        "Evaluate won revenue and market potential distributed across "
        "CRM industry sectors. Uncover which sectors are currently underserved."
    )
    
    # Load cleaned accounts to merge sector info
    try:
        accounts_path = getattr(config, 'CRM_ACCOUNTS_CLEAN_PATH', config.PROCESSED_DATA_DIR / "accounts_cleaned.csv")
        df_acc = pd.read_csv(accounts_path)
    except Exception as e:
        st.error(f"Error loading accounts database: {e}")
        return
        
    # Join CRM Won deals with Account sectors
    df_won = df_crm[df_crm['deal_stage'] == 'Won'].copy()
    df_joined = pd.merge(df_won, df_acc[['account', 'sector']], left_on='account_name', right_on='account', how='left')
    df_joined['sector'] = df_joined['sector'].fillna('Unknown').str.title()
    
    # Calculate revenue by sector
    sector_revenue = df_joined.groupby('sector')['revenue'].sum().reset_index()
    
    # Sector share based on account employees (TAM proxy)
    df_acc_clean = df_acc.copy()
    df_acc_clean['sector'] = df_acc_clean['sector'].fillna('Unknown').str.title()
    sector_emp = df_acc_clean.groupby('sector')['employees'].sum()
    sector_shares = (sector_emp / sector_emp.sum()).to_dict()
    
    # Distribute global market potential across sectors
    total_potential = df_scored['market_potential'].sum()
    sector_potential = []
    for sector, share in sector_shares.items():
        sector_potential.append({
            'sector': sector,
            'market_potential': total_potential * share
        })
    df_sec_pot = pd.DataFrame(sector_potential)
    
    # Merge revenue and potential
    df_sector = pd.merge(sector_revenue, df_sec_pot, on='sector', how='outer').fillna(0.0)
    df_sector['revenue_gap'] = np.clip(df_sector['market_potential'] - df_sector['revenue'], 0.0, None)
    df_sector['penetration_index'] = np.where(
        df_sector['market_potential'] > 0,
        df_sector['revenue'] / df_sector['market_potential'],
        0.0
    )
    
    # Render Plotly Charts
    c1, c2 = st.columns(2)
    
    with c1:
        # Grouped bar chart comparing revenue vs potential by sector
        chart_data = pd.melt(
            df_sector,
            id_vars=['sector'],
            value_vars=['revenue', 'market_potential'],
            var_name='Type',
            value_name='Value'
        )
        chart_data['Type'] = chart_data['Type'].map({'revenue': 'CRM Revenue', 'market_potential': 'Market Potential'})
        chart_data['Value_M'] = chart_data['Value'] / 1e6
        
        fig = px.bar(
            chart_data,
            x='sector',
            y='Value_M',
            color='Type',
            barmode='group',
            title="Revenue vs. Potential by Industry Sector ($M)",
            labels={'sector': 'Industry Sector', 'Value_M': 'Value ($M)'},
            color_discrete_map={'CRM Revenue': '#34a853', 'Market Potential': '#1a73e8'}
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)',
            font_color='#f8fafc',
            title_font_family='Outfit',
            font_family='Inter'
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        # Donut chart of revenue gap by sector (where growth potential is)
        df_gap_filtered = df_sector[df_sector['revenue_gap'] > 0]
        fig_pie = px.pie(
            df_gap_filtered,
            values='revenue_gap',
            names='sector',
            hole=0.4,
            title="Market Growth Opportunities (Revenue Gap Share)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f8fafc',
            title_font_family='Outfit',
            font_family='Inter'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    # Sector State Matrix
    st.markdown("### 🔎 Sector State-Level Drilling")
    selected_sector = st.selectbox("Select Sector to analyze State-Level Revenue", options=df_sector['sector'].tolist())
    
    # Calculate state-level revenue for selected sector
    sec_state_rev = df_joined[df_joined['sector'] == selected_sector].groupby('state')['revenue'].sum().reset_index()
    
    # Merge with states and score
    df_state_pot = df_scored[['state', 'market_potential']].copy()
    df_state_pot['sector_potential'] = df_state_pot['market_potential'] * sector_shares.get(selected_sector, 0.0)
    
    df_drill = pd.merge(df_state_pot, sec_state_rev, on='state', how='left').fillna(0.0)
    df_drill['sector_gap'] = np.clip(df_drill['sector_potential'] - df_drill['revenue'], 0.0, None)
    df_drill['sector_penetration'] = np.where(
        df_drill['sector_potential'] > 0,
        df_drill['revenue'] / df_drill['sector_potential'],
        0.0
    )
    
    df_drill_disp = df_drill.sort_values(by='sector_gap', ascending=False).head(10)
    df_drill_disp = df_drill_disp.rename(columns={
        'state': 'State',
        'sector_potential': 'Sector Potential ($)',
        'revenue': 'Sector CRM Revenue ($)',
        'sector_gap': 'Sector Revenue Gap ($)',
        'sector_penetration': 'Penetration Rate'
    })
    
    st.write(f"Top 10 States with largest growth opportunities for **{selected_sector}** sector:")
    st.dataframe(df_drill_disp[[
        'State', 'Sector Potential ($)', 'Sector CRM Revenue ($)', 'Sector Revenue Gap ($)', 'Penetration Rate'
    ]].style.format({
        'Sector Potential ($)': '{:,.2f}',
        'Sector CRM Revenue ($)': '{:,.2f}',
        'Sector Revenue Gap ($)': '{:,.2f}',
        'Penetration Rate': '{:.2%}'
    }), use_container_width=True)


# ==========================================
# FEATURE 3: REP PERFORMANCE & LEADERBOARD
# ==========================================
def render_rep_page(df_crm):
    st.subheader("🏆 Sales Representative Efficiency Leaderboard")
    st.write(
        "Analyse individual representative performance and segment agents based on won deal counts "
        "and average closed value."
    )
    
    # Filter Won deals
    df_won = df_crm[df_crm['deal_stage'] == 'Won'].copy()
    
    # Aggregate rep stats
    rep_stats = df_won.groupby(['sales_rep', 'region']).agg(
        total_revenue=('revenue', 'sum'),
        deal_count=('revenue', 'count'),
        avg_deal_size=('revenue', 'mean')
    ).reset_index()
    
    # Top Metrics Cards
    top_rep = rep_stats.sort_values(by='total_revenue', ascending=False).iloc[0]
    top_deal_hunter = rep_stats.sort_values(by='avg_deal_size', ascending=False).iloc[0]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Top Revenue Generator", f"{top_rep['sales_rep']}", format_compact_currency(top_rep['total_revenue']))
    with c2:
        st.metric("Highest Deal Velocity", f"{rep_stats.sort_values(by='deal_count', ascending=False).iloc[0]['sales_rep']}", f"{rep_stats.sort_values(by='deal_count', ascending=False).iloc[0]['deal_count']} deals")
    with c3:
        st.metric("Largest Average Deal Size", f"{top_deal_hunter['sales_rep']}", format_compact_currency(top_deal_hunter['avg_deal_size']))
        
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Plotly quadrant analysis scatter plot
        avg_deal_median = rep_stats['avg_deal_size'].median()
        deal_count_median = rep_stats['deal_count'].median()
        
        fig = px.scatter(
            rep_stats,
            x='deal_count',
            y='avg_deal_size',
            size='total_revenue',
            color='region',
            hover_name='sales_rep',
            title="Agent Performance Quadrants (Size = Total Revenue)",
            labels={'deal_count': 'Won Deals Count', 'avg_deal_size': 'Average Deal Size ($)'},
            color_discrete_map={'East': '#ea4335', 'Central': '#fbbc05', 'West': '#34a853'}
        )
        
        # Add quadrant lines
        fig.add_shape(type="line", x0=deal_count_median, y0=0, x1=deal_count_median, y1=rep_stats['avg_deal_size'].max()*1.1,
                      line=dict(color="rgba(255,255,255,0.2)", width=1.5, dash="dash"))
        fig.add_shape(type="line", x0=0, y0=avg_deal_median, x1=rep_stats['deal_count'].max()*1.1, y1=avg_deal_median,
                      line=dict(color="rgba(255,255,255,0.2)", width=1.5, dash="dash"))
                      
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)',
            font_color='#f8fafc',
            title_font_family='Outfit',
            font_family='Inter'
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        # Leaderboard table
        st.markdown("### Representative Leaderboard")
        leaderboard = rep_stats.sort_values(by='total_revenue', ascending=False).reset_index(drop=True)
        leaderboard.index = leaderboard.index + 1
        
        leaderboard_disp = leaderboard.rename(columns={
            'sales_rep': 'Representative',
            'region': 'Region',
            'total_revenue': 'Total Revenue ($)',
            'deal_count': 'Deals'
        })
        
        st.dataframe(leaderboard_disp[['Representative', 'Region', 'Total Revenue ($)', 'Deals']].style.format({
            'Total Revenue ($)': '{:,.2f}'
        }), height=340)


# ==========================================
# FEATURE 4: PIPELINE FORECASTING & VELOCITY
# ==========================================
def render_forecasting_page(df_crm):
    st.subheader("📅 Pipeline Forecasting & Deal Velocity")
    st.write(
        "Forecast sales revenue based on moving averages and calculate deal velocity "
        "(days from engage date to close date) by region."
    )
    
    # Parse dates
    df_dates = df_crm.copy()
    df_dates['close_date'] = pd.to_datetime(df_dates['close_date'])
    df_dates['engage_date'] = pd.to_datetime(df_dates['engage_date'])
    
    # Calculate Deal Velocity in days
    df_dates['deal_velocity'] = (df_dates['close_date'] - df_dates['engage_date']).dt.days
    
    # Render Pipeline velocity by region
    df_won = df_dates[df_dates['deal_stage'] == 'Won'].copy()
    avg_velocity = df_won.groupby('region')['deal_velocity'].mean().reset_index()
    
    c1, c2 = st.columns(2)
    
    with c1:
        # Historical revenue grouped by month
        df_won['month'] = df_won['close_date'].dt.to_period('M').astype(str)
        monthly_rev = df_won.groupby('month')['revenue'].sum().reset_index()
        
        # Calculate moving average forecast
        monthly_rev['Moving Average (3M)'] = monthly_rev['revenue'].rolling(window=3).mean()
        
        fig_trend = px.line(
            monthly_rev,
            x='month',
            y=['revenue', 'Moving Average (3M)'],
            title="Monthly Won Revenue & Trend Forecast ($)",
            labels={'month': 'Close Month', 'value': 'Revenue ($)', 'variable': 'Series'},
            color_discrete_map={'revenue': '#34a853', 'Moving Average (3M)': '#1a73e8'}
        )
        fig_trend.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)',
            font_color='#f8fafc',
            title_font_family='Outfit',
            font_family='Inter',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with c2:
        # Deal velocity bar chart
        fig_vel = px.bar(
            avg_velocity,
            x='region',
            y='deal_velocity',
            title="Average Sales Cycle Length (Velocity in Days)",
            labels={'region': 'Sales Region', 'deal_velocity': 'Avg Days to Close'},
            color='region',
            color_discrete_map={'East': '#ea4335', 'Central': '#fbbc05', 'West': '#34a853'}
        )
        fig_vel.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.3)',
            font_color='#f8fafc',
            title_font_family='Outfit',
            font_family='Inter',
            showlegend=False
        )
        st.plotly_chart(fig_vel, use_container_width=True)
