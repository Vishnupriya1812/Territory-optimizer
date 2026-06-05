import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import geopandas as gpd
import pandas as pd
import config

def load_geo_data(shapefile_path=None):
    """
    Loads US state shapes and maps state names to 2-letter postal codes.
    
    Args:
        shapefile_path (str, optional): Custom path to shapefile.
        
    Returns:
        gpd.GeoDataFrame: Geopandas dataframe of US state geometries.
    """
    if shapefile_path is None:
        shapefile_path = config.SHAPEFILE_PATH
        
    print(f"Loading shapefiles from {shapefile_path}...")
    gdf = gpd.read_file(shapefile_path)
    
    # Map full state name (e.g. 'California') to 'CA'
    gdf['state'] = gdf['name'].map(config.STATE_MAP)
    
    # Drop rows that don't map to standard abbreviations
    gdf = gdf.dropna(subset=['state'])
    return gdf

def get_merged_geo_data(scored_df_path=None, shapefile_path=None):
    """
    Loads shapefiles, merges them with scored territory data, and projects to EPSG:4326.
    
    Args:
        scored_df_path (str, optional): Custom path to territory_scored.csv.
        shapefile_path (str, optional): Custom path to shapefiles.
        
    Returns:
        gpd.GeoDataFrame: Merged spatial dataframe.
    """
    if scored_df_path is None:
        scored_df_path = config.TERRITORY_SCORED_PATH
        
    df = pd.read_csv(scored_df_path)
    gdf = load_geo_data(shapefile_path)
    
    # Merge on state code
    print("Merging shapefiles with ML scored results...")
    merged = gdf.merge(df, on='state', how='left')
    
    # Fill remaining NaNs for states that might be missing in census or scoring
    merged['total_revenue'] = merged['total_revenue'].fillna(0.0)
    merged['market_potential'] = merged['market_potential'].fillna(0.0)
    merged['penetration_index'] = merged['penetration_index'].fillna(0.0)
    merged['penetration_index_norm'] = merged['penetration_index_norm'].fillna(0.0)
    merged['territory_label'] = merged['territory_label'].fillna('whitespace')
    merged['rep_count'] = merged['rep_count'].fillna(0).astype(int)
    merged['recommended_investment'] = merged['recommended_investment'].fillna(0.0)
    
    # Reproject to WGS84 for Folium
    print("Projecting geometry to EPSG:4326...")
    merged = merged.to_crs(epsg=4326)
    
    return merged

if __name__ == "__main__":
    merged_gdf = get_merged_geo_data()
    print(f"Geo merge successful. Columns: {list(merged_gdf.columns)}")
    print(f"Total polygons merged: {len(merged_gdf)}")
