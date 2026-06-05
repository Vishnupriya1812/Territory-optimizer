import sys
import hashlib
import requests
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import config

# Fallback Census CBP Data for 2022
# Units: ESTAB (count), EMP (count of employees), PAYANN (annual payroll in $1,000s)
FALLBACK_CENSUS = {
    'AL': (114000, 1700000, 85000000),
    'AK': (21000, 260000, 16000000),
    'AZ': (163000, 2600000, 142000000),
    'AR': (68000, 1000000, 46000000),
    'CA': (1050000, 15300000, 1150000000),
    'CO': (187000, 2500000, 161000000),
    'CT': (90000, 1500000, 104000000),
    'DE': (29000, 410000, 26000000),
    'DC': (24000, 520000, 51000000),
    'FL': (635000, 8300000, 465000000),
    'GA': (252000, 4000000, 235000000),
    'HI': (34000, 520000, 27000000),
    'ID': (56000, 700000, 32000000),
    'IL': (326000, 5400000, 348000000),
    'IN': (153000, 2700000, 131000000),
    'IA': (83000, 1300000, 62000000),
    'KS': (76000, 1200000, 59000000),
    'KY': (92000, 1600000, 78000000),
    'LA': (106000, 1600000, 81000000),
    'ME': (42000, 530000, 25000000),
    'MD': (142000, 2200000, 138000000),
    'MA': (185000, 3200000, 252000000),
    'MI': (224000, 3700000, 208000000),
    'MN': (154000, 2600000, 162000000),
    'MS': (59000, 940000, 39000000),
    'MO': (149000, 2400000, 121000000),
    'MT': (41000, 410000, 19000000),
    'NE': (56000, 870000, 43000000),
    'NV': (74000, 1200000, 64000000),
    'NH': (40000, 590000, 34000000),
    'NJ': (242000, 3600000, 251000000),
    'NM': (45000, 640000, 29000000),
    'NY': (552000, 7800000, 640000000),
    'NC': (251000, 3900000, 211000000),
    'ND': (25000, 340000, 18000000),
    'OH': (258000, 4800000, 252000000),
    'OK': (96000, 1300000, 61000000),
    'OR': (121000, 1700000, 96000000),
    'PA': (308000, 5200000, 301000000),
    'RI': (29000, 430000, 24000000),
    'SC': (116000, 1800000, 84000000),
    'SD': (29000, 380000, 18000000),
    'TN': (157000, 2700000, 142000000),
    'TX': (654000, 10800000, 651000000),
    'UT': (92000, 1400000, 74000000),
    'VT': (22000, 260000, 12000000),
    'VA': (206000, 3300000, 198000000),
    'WA': (212000, 2900000, 212000000),
    'WV': (38000, 570000, 25000000),
    'WI': (144000, 2500000, 126000000),
    'WY': (22000, 220000, 11000000)
}

def setup_directories():
    """Ensure data processed and shapefiles directories exist."""
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.SHAPEFILES_DIR.mkdir(parents=True, exist_ok=True)

def ingest_crm_data():
    """
    Ingests and cleans CRM data, assigning deterministic states and zip codes.
    
    Returns:
        pd.DataFrame: Cleaned CRM sales pipeline dataframe.
    """
    print("Ingesting B2B CRM Sales Pipeline...")
    pipeline = pd.read_csv(config.CRM_SALES_PATH)
    teams = pd.read_csv(config.CRM_TEAMS_PATH)
    
    # Merge pipeline with teams to get regional office (region)
    merged = pd.merge(pipeline, teams, on='sales_agent', how='left')
    
    # Determine the primary region for each account based on mode
    account_regions = merged.groupby('account')['regional_office'].agg(
        lambda x: x.mode().iloc[0] if not x.mode().empty else 'Central'
    ).to_dict()
    
    # Deterministic mapping of account name to state and zip code within their region
    account_geo = {}
    for acc, reg in account_regions.items():
        if not isinstance(acc, str) or pd.isna(acc):
            continue
        state_list = config.REGION_TO_STATES.get(reg, config.REGION_TO_STATES['Central'])
        # Use md5 hash for deterministic but distributed state mapping
        hasher = hashlib.md5(acc.encode('utf-8'))
        hash_val = int(hasher.hexdigest(), 16)
        state = state_list[hash_val % len(state_list)]
        zip_code = config.STATE_ZIP_BASES.get(state, '10001')
        account_geo[acc] = (state, zip_code)
    
    # Assign state and zip code back to pipeline
    pipeline['state'] = pipeline['account'].map(lambda x: account_geo.get(x, ('TX', '75001'))[0])
    pipeline['zip_code'] = pipeline['account'].map(lambda x: account_geo.get(x, ('TX', '75001'))[1])
    
    # Add region column from team assignment
    pipeline = pd.merge(pipeline, teams[['sales_agent', 'regional_office']], on='sales_agent', how='left')
    pipeline = pipeline.rename(columns={'regional_office': 'region'})
    pipeline['region'] = pipeline['region'].fillna('Central')
    
    # Standardize column names as expected by Stage 2 & 3
    pipeline = pipeline.rename(columns={
        'account': 'account_name',
        'sales_agent': 'sales_rep',
        'close_value': 'revenue'
    })
    
    # Standardize data types
    pipeline['revenue'] = pd.to_numeric(pipeline['revenue']).fillna(0.0)
    pipeline.loc[pipeline['revenue'] < 0, 'revenue'] = 0.0
    pipeline['zip_code'] = pipeline['zip_code'].astype(str)
    
    # Apply assert validations
    assert pipeline['zip_code'].str.len().eq(5).all(), "ZIP codes must be 5 digits"
    assert pipeline['revenue'].ge(0).all(), "Revenue cannot be negative"
    assert pipeline['state'].isin(config.US_STATE_ABBREVS).all(), "Invalid state codes"
    
    print(f"CRM Ingestion complete. Row count: {len(pipeline)}")
    return pipeline

def ingest_census_data():
    """
    Ingests US Census County Business Patterns data for 2022.
    Attempts the API first, falling back to static data if unavailable.
    
    Returns:
        pd.DataFrame: Processed Census business density dataframe.
    """
    url = "https://api.census.gov/data/2022/cbp?get=ESTAB,EMP,PAYANN,NAME&for=state:*&NAICS2017=00"
    df_census = None
    
    try:
        print(f"Querying US Census CBP API: {url}")
        response = requests.get(url, timeout=10)
        
        # Check if the API was successful and returned JSON (not "Missing Key" HTML)
        if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            header = data[0]
            rows = data[1:]
            df_api = pd.DataFrame(rows, columns=header)
            
            # Map state names to abbreviations
            df_api['state'] = df_api['NAME'].map(config.STATE_MAP)
            # Drop rows with unmapped state abbreviations (e.g. Puerto Rico/Islands if not in map)
            df_api = df_api.dropna(subset=['state'])
            
            # Reorganize and cast columns
            df_census = pd.DataFrame({
                'state': df_api['state'],
                'total_establishments': pd.to_numeric(df_api['ESTAB']),
                'employees': pd.to_numeric(df_api['EMP']),
                'annual_payroll': pd.to_numeric(df_api['PAYANN']),
                'state_name': df_api['NAME']
            })
            print("Census data successfully fetched via API.")
        else:
            print(f"Census API response check failed (Status {response.status_code}).")
            raise Exception("API returned error page or unexpected content type")
            
    except Exception as e:
        print(f"Census API request failed: {e}. Falling back to pre-defined static 2022 Census data.")
        
        records = []
        for state_abbr, (estab, emp, payann) in FALLBACK_CENSUS.items():
            # Find the state name
            state_name = next((name for name, abbr in config.STATE_MAP.items() if abbr == state_abbr), state_abbr)
            records.append({
                'state': state_abbr,
                'total_establishments': estab,
                'employees': emp,
                'annual_payroll': payann,
                'state_name': state_name
            })
        df_census = pd.DataFrame(records)
        
    # Enrich with GDP Proxy and average payroll
    # avg_payroll_per_employee = annual_payroll / employees (handle division by zero)
    df_census['avg_payroll_per_employee'] = np.where(
        df_census['employees'] > 0,
        df_census['annual_payroll'] / df_census['employees'],
        0.0
    )
    # gdp_proxy = total_establishments * avg_payroll_per_employee * 1000 (convert to actual USD since payroll is in thousands of dollars)
    df_census['gdp_proxy'] = df_census['total_establishments'] * df_census['avg_payroll_per_employee'] * 1000.0
    
    # Add state_fips/market_potential aliases for dashboard consistency
    df_census['market_potential'] = df_census['gdp_proxy']
    
    print(f"Census Ingestion complete. Row count: {len(df_census)}")
    return df_census

def main():
    setup_directories()
    
    # Process CRM Data
    df_crm = ingest_crm_data()
    crm_out_path = config.PROCESSED_DATA_DIR / "crm_cleaned.csv"
    df_crm.to_csv(crm_out_path, index=False)
    print(f"Saved cleaned CRM data to {crm_out_path}")
    
    # Process Census Data
    df_census = ingest_census_data()
    census_out_path = config.PROCESSED_DATA_DIR / "census_business_density.csv"
    df_census.to_csv(census_out_path, index=False)
    print(f"Saved cleaned Census density data to {census_out_path}")
    print("Ingestion pipeline executed successfully.")

if __name__ == "__main__":
    main()
