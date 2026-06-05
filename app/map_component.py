import sys
from pathlib import Path
# Insert parent directory to allow relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from src.geo import get_merged_geo_data

def render_map(selected_labels, min_potential_m):
    """
    Renders an interactive Folium choropleth map in Streamlit.
    Colors states by territory_label and shows detailed popup metrics on click.
    
    Args:
        selected_labels (list): List of selected territory labels (e.g. ['whitespace'])
        min_potential_m (float): Minimum market potential in Millions of USD.
    """
    st.subheader("🗺️ Sales Territory Segment Mapping")
    st.write(
        "Hover over a state to see its name and classification. Click on a state "
        "to view detailed CRM sales metrics, market potential, and investment recommendations."
    )
    
    # Load merged GeoDataFrame
    try:
        gdf = get_merged_geo_data()
    except Exception as e:
        st.error(f"Error loading spatial data: {e}")
        return
        
    # Scale market potential to Millions for comparison
    gdf['market_potential_m'] = gdf['market_potential'] / 1000.0
    
    # Filter by selected labels and minimum potential (in Millions)
    filtered_gdf = gdf[
        gdf['territory_label'].isin(selected_labels) & 
        (gdf['market_potential_m'] >= min_potential_m)
    ]
    
    if filtered_gdf.empty:
        st.warning("No states match the selected filters. Try adjusting the sidebar options.")
        return
        
    # Initialize Folium Map centered on US
    m = folium.Map(location=[39.5, -98.35], zoom_start=4, tiles="cartodbpositron")
    
    # Color mapping for labels
    color_map = {
        'whitespace': '#ea4335',  # Red
        'balanced': '#fbbc05',    # Yellow
        'saturated': '#34a853'    # Green
    }
    
    # Style function for GeoJSON polygons
    def style_function(feature):
        state_id = feature['properties']['state']
        # Look up state in filtered geo dataframe
        state_row = filtered_gdf[filtered_gdf['state'] == state_id]
        if not state_row.empty:
            label = state_row.iloc[0]['territory_label']
            fill_color = color_map.get(label, '#cccccc')
            fill_opacity = 0.75
        else:
            # Not matching the filter
            fill_color = '#e0e0e0'
            fill_opacity = 0.15
            
        return {
            'fillColor': fill_color,
            'color': '#ffffff',
            'weight': 1.5,
            'fillOpacity': fill_opacity
        }
        
    # Highlight function on hover
    def highlight_function(feature):
        return {
            'fillColor': '#1a73e8',
            'color': '#1a73e8',
            'weight': 2.0,
            'fillOpacity': 0.9
        }
        
    # Add GeoJSON layer to map
    for _, row in gdf.iterrows():
        state_code = row['state']
        is_filtered = state_code in filtered_gdf['state'].values
        
        # Define style for this specific feature
        state_label = row['territory_label']
        col = color_map.get(state_label, '#cccccc') if is_filtered else '#e0e0e0'
        op = 0.75 if is_filtered else 0.15
        
        # HTML Popup content with beautiful styling
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 200px; padding: 5px;">
            <h4 style="margin: 0 0 8px 0; color: #333; border-bottom: 2px solid {col}; padding-bottom: 4px;">
                {row['name']} ({row['state']})
            </h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="font-weight: bold; padding: 3px 0;">Segment:</td>
                    <td style="text-align: right; color: {col}; font-weight: bold;">{state_label.upper()}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 3px 0;">Reps Active:</td>
                    <td style="text-align: right;">{int(row['rep_count'])}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 3px 0;">Total Revenue:</td>
                    <td style="text-align: right; color: #34a853; font-weight: bold;">${row['total_revenue']:,.2f}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 3px 0;">Market Potential:</td>
                    <td style="text-align: right;">${row['market_potential_m']:,.2f}M</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 3px 0;">Penetration Index:</td>
                    <td style="text-align: right;">{row['penetration_index_norm']:.3f} (norm)</td>
                </tr>
                <tr style="border-top: 1px solid #ddd;">
                    <td style="font-weight: bold; padding: 6px 0 3px 0; color: #d93025;">Revenue Gap:</td>
                    <td style="text-align: right; padding: 6px 0 3px 0; color: #d93025; font-weight: bold;">
                        ${(row['revenue_gap'] / 1000.0):,.2f}M
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 3px 0; color: #1a73e8;">Rec. Investment:</td>
                    <td style="text-align: right; color: #1a73e8; font-weight: bold;">
                        ${row['recommended_investment']:,.2f}
                    </td>
                </tr>
            </table>
            <div style="font-size: 10px; color: #888; margin-top: 10px; font-style: italic;">
                *Recommended investment assumes 5% conversion rate on the revenue gap.
            </div>
        </div>
        """
        
        # GeoJSON single feature
        geojson_feature = {
            "type": "Feature",
            "geometry": row['geometry'].__geo_interface__,
            "properties": {
                "name": row['name'],
                "state": row['state'],
                "label": state_label
            }
        }
        
        # Create Folium GeoJson layer for this state
        folium_style = lambda x, col=col, op=op: {
            'fillColor': col,
            'color': '#ffffff',
            'weight': 1.5,
            'fillOpacity': op
        }
        
        folium_geo = folium.GeoJson(
            geojson_feature,
            style_function=folium_style,
            highlight_function=highlight_function,
            tooltip=folium.Tooltip(f"<b>{row['name']}</b> ({state_code}): {state_label.title()}")
        )
        
        # Attach popup
        folium.Popup(popup_html, max_width=280).add_to(folium_geo)
        folium_geo.add_to(m)
        
    # Render map in streamlit iframe
    components.html(m._repr_html_(), height=600)
