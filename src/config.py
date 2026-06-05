from pathlib import Path

# Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SHAPEFILES_DIR = DATA_DIR / "shapefiles"
SQL_DIR = PROJECT_ROOT / "sql"

# Raw file paths
CRM_SALES_PATH = RAW_DATA_DIR / "sales_pipeline.csv"
CRM_ACCOUNTS_PATH = RAW_DATA_DIR / "accounts.csv"
CRM_TEAMS_PATH = RAW_DATA_DIR / "sales_teams.csv"
CRM_PRODUCTS_PATH = RAW_DATA_DIR / "products.csv"
SHAPEFILE_PATH = SHAPEFILES_DIR / "us_states.geojson"

# Processed file paths
TERRITORY_MASTER_PATH = PROCESSED_DATA_DIR / "territory_master.csv"
TERRITORY_SCORED_PATH = PROCESSED_DATA_DIR / "territory_scored.csv"
SQLITE_DB_PATH = PROCESSED_DATA_DIR / "territory.db"

# State data mappings
US_STATE_ABBREVS = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
    'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}

STATE_MAP = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
    "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI",
    "Wyoming": "WY"
}

STATE_ZIP_BASES = {
    'AL': '35201', 'AK': '99501', 'AZ': '85001', 'AR': '72201', 'CA': '90001',
    'CO': '80201', 'CT': '06101', 'DE': '19801', 'DC': '20001', 'FL': '33101',
    'GA': '30301', 'HI': '96801', 'ID': '83701', 'IL': '60601', 'IN': '46201',
    'IA': '50301', 'KS': '66601', 'KY': '40201', 'LA': '70101', 'ME': '04101',
    'MD': '21201', 'MA': '02101', 'MI': '48201', 'MN': '55401', 'MS': '39201',
    'MO': '63101', 'MT': '59601', 'NE': '68101', 'NV': '89101', 'NH': '03101',
    'NJ': '07101', 'NM': '87101', 'NY': '10001', 'NC': '28201', 'ND': '58501',
    'OH': '43201', 'OK': '73101', 'OR': '97201', 'PA': '19101', 'RI': '02901',
    'SC': '29201', 'SD': '57101', 'TN': '37201', 'TX': '75001', 'UT': '84101',
    'VT': '05601', 'VA': '23201', 'WA': '98101', 'WV': '25301', 'WI': '53201',
    'WY': '82001'
}

STATE_TO_REGION = {
    'CA': 'West', 'WA': 'West', 'OR': 'West', 'AZ': 'West', 'CO': 'West',
    'UT': 'West', 'NV': 'West', 'NM': 'West', 'ID': 'West', 'MT': 'West',
    'WY': 'West', 'AK': 'West', 'HI': 'West',
    'NY': 'East', 'MA': 'East', 'PA': 'East', 'NJ': 'East', 'VA': 'East',
    'NC': 'East', 'GA': 'East', 'FL': 'East', 'MD': 'East', 'DE': 'East',
    'CT': 'East', 'RI': 'East', 'VT': 'East', 'NH': 'East', 'ME': 'East',
    'DC': 'East', 'SC': 'East', 'WV': 'East',
    'TX': 'Central', 'IL': 'Central', 'OH': 'Central', 'MI': 'Central', 'IN': 'Central',
    'WI': 'Central', 'MN': 'Central', 'MO': 'Central', 'AL': 'Central', 'MS': 'Central',
    'TN': 'Central', 'KY': 'Central', 'LA': 'Central', 'AR': 'Central', 'OK': 'Central',
    'KS': 'Central', 'NE': 'Central', 'SD': 'Central', 'ND': 'Central', 'IA': 'Central'
}

REGION_TO_STATES = {
    'West': ['CA', 'WA', 'OR', 'AZ', 'CO', 'UT', 'NV', 'NM', 'ID', 'MT', 'WY', 'AK', 'HI'],
    'East': ['NY', 'MA', 'PA', 'NJ', 'VA', 'NC', 'GA', 'FL', 'MD', 'DE', 'CT', 'RI', 'VT', 'NH', 'ME', 'DC', 'SC', 'WV'],
    'Central': ['TX', 'IL', 'OH', 'MI', 'IN', 'WI', 'MN', 'MO', 'AL', 'MS', 'TN', 'KY', 'LA', 'AR', 'OK', 'KS', 'NE', 'SD', 'ND', 'IA']
}

# ML Settings
N_CLUSTERS = 3
KMEANS_RANDOM_STATE = 42
FEATURES = ['penetration_index_norm', 'revenue_per_rep', 'market_potential_norm']
