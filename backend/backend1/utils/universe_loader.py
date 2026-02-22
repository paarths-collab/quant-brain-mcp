import json
import os
import pandas as pd

def get_global_universe(region="US"):
    """
    Loads stock universe from local JSON data files.
    """
    
    # Resolving path relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up 2 levels to access backend/data (utils -> backend1 -> backend -> data)
    # File is at: backend/backend1/utils/universe_loader.py
    # Data is at: backend/data/
    data_dir = os.path.join(base_dir, "..", "..", "data")
    
    universe = []

    try:
        if region == "India":
            file_path = os.path.join(data_dir, "nifty500.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
                    # Data is list of dicts with "Symbol"
                    universe = [item["Symbol"] + ".NS" for item in data if "Symbol" in item]
            else:
                print(f"Data file not found: {file_path}")
                # Fallback
                return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

        elif region == "US":
            file_path = os.path.join(data_dir, "us_stocks.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
                    # Data is list of dicts with "Symbol"
                    universe = [item["Symbol"] for item in data if "Symbol" in item]
            else:
                 print(f"Data file not found: {file_path}")
                 # Fallback
                 return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
        
        # Remove duplicates
        return list(set(universe))

    except Exception as e:
        print(f"Error loading universe: {e}")
        return []

def get_sector_universe(sector, region="US"):
     # Placeholder if needed later
     pass
