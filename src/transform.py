import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import sqlite3
import pandas as pd
import config

def run_transformations():
    print("Initiating SQL Transformations via SQLite...")
    
    # Read processed CSV files
    crm_cleaned_path = config.PROCESSED_DATA_DIR / "crm_cleaned.csv"
    census_cleaned_path = config.PROCESSED_DATA_DIR / "census_business_density.csv"
    
    if not crm_cleaned_path.exists() or not census_cleaned_path.exists():
        raise FileNotFoundError("Cleaned ingestion datasets not found. Please run ingest.py first.")
        
    df_crm = pd.read_csv(crm_cleaned_path)
    df_census = pd.read_csv(census_cleaned_path)
    
    # Establish SQLite connection (in-memory or file-based)
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    
    try:
        # Load dataframes into SQLite tables
        df_crm.to_sql("crm_sales", conn, if_exists="replace", index=False)
        df_census.to_sql("census_enriched", conn, if_exists="replace", index=False)
        
        # Read and run the SQL transformation scripts in order
        sql_files = ["01_territory_rollup.sql", "02_rep_coverage.sql", "03_whitespace_view.sql"]
        for sql_file in sql_files:
            file_path = config.SQL_DIR / sql_file
            print(f"Executing SQL script: {sql_file}")
            with open(file_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
                
            # SQLite execute script
            conn.executescript(sql_script)
            
        # Extract the final view output into a pandas DataFrame
        df_master = pd.read_sql_query("SELECT * FROM whitespace_view", conn)
        
        # Save results
        config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_master.to_csv(config.TERRITORY_MASTER_PATH, index=False)
        print(f"SQL transformations complete. Output saved to {config.TERRITORY_MASTER_PATH}")
        print(f"Territory master row count: {len(df_master)}")
        
    except Exception as e:
        print(f"Error during SQLite transformations: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_transformations()
