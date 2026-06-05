import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import config

def compute_penetration_index(df):
    """
    Computes raw and normalized penetration index.
    Penetration Index = total_revenue / market_potential.
    Normalized to 0-1 scale using min-max normalization.
    
    Args:
        df (pd.DataFrame): Input dataframe containing total_revenue and market_potential.
        
    Returns:
        pd.DataFrame: Dataframe with penetration_index and penetration_index_norm columns.
    """
    # Prevent division by zero
    df['penetration_index'] = np.where(
        df['market_potential'] > 0,
        df['total_revenue'] / df['market_potential'],
        0.0
    )
    
    min_pi = df['penetration_index'].min()
    max_pi = df['penetration_index'].max()
    
    # Avoid division by zero if all values are identical
    if max_pi > min_pi:
        df['penetration_index_norm'] = (df['penetration_index'] - min_pi) / (max_pi - min_pi)
    else:
        df['penetration_index_norm'] = 0.0
        
    return df

def cluster_territories(df):
    """
    Groups states into saturated, balanced, and whitespace territories using K-Means.
    Standardizes features before clustering.
    Sorts and labels clusters dynamically based on mean penetration.
    
    Args:
        df (pd.DataFrame): Dataframe with features.
        
    Returns:
        pd.DataFrame: Dataframe with cluster and territory_label columns.
    """
    # Log-transform market_potential to mitigate skew
    df['market_potential_log'] = np.log1p(df['market_potential'])
    min_mp = df['market_potential_log'].min()
    max_mp = df['market_potential_log'].max()
    if max_mp > min_mp:
        df['market_potential_norm'] = (df['market_potential_log'] - min_mp) / (max_mp - min_mp)
    else:
        df['market_potential_norm'] = 0.0
        
    # Scale and cluster
    scaler = StandardScaler()
    X = scaler.fit_transform(df[config.FEATURES])
    
    km = KMeans(n_clusters=config.N_CLUSTERS, random_state=config.KMEANS_RANDOM_STATE, n_init=10)
    df['cluster'] = km.fit_predict(X)
    
    # Sort cluster numbers by mean penetration index (lowest mean = whitespace, highest = saturated)
    cluster_means = df.groupby('cluster')['penetration_index_norm'].mean().sort_values()
    
    label_map = {
        cluster_means.index[0]: 'whitespace',
        cluster_means.index[1]: 'balanced',
        cluster_means.index[2]: 'saturated'
    }
    df['territory_label'] = df['cluster'].map(label_map)
    return df

def run_modelling():
    print("Running ML Segmentation Pipeline...")
    master_path = config.TERRITORY_MASTER_PATH
    if not master_path.exists():
        raise FileNotFoundError("Master territory rollup data not found. Please run transform.py first.")
        
    df = pd.read_csv(master_path)
    
    # Compute metrics
    df = compute_penetration_index(df)
    df = cluster_territories(df)
    
    # Calculate Business Metrics (for Power BI and Streamlit dashboard)
    # Revenue Gap = market_potential - total_revenue
    df['revenue_gap'] = np.clip(df['market_potential'] - df['total_revenue'], 0.0, None)
    
    # Recommended Investment Level (Assumption: 5% conversion rate on the revenue gap)
    # Recommended Investment = revenue_gap * 0.05
    CONVERSION_RATE_ASSUMPTION = 0.05
    df['recommended_investment'] = df['revenue_gap'] * CONVERSION_RATE_ASSUMPTION
    
    # Save scored dataset
    df.to_csv(config.TERRITORY_SCORED_PATH, index=False)
    print(f"ML modelling complete. Scored output saved to {config.TERRITORY_SCORED_PATH}")
    print(df[['state', 'penetration_index_norm', 'territory_label']].head())

if __name__ == "__main__":
    run_modelling()
