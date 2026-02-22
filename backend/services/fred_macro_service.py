from fredapi import Fred
import os
import pandas as pd

class FREDMacroService:

    def __init__(self):
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("Warning: FRED_API_KEY not found. Macro data will be empty.")
            self.fred = None
        else:
            self.fred = Fred(api_key=api_key)

    def get_macro_snapshot(self):
        """
        Fetches key macro indicators: GDP, Inflation (CPI), Fed Funds Rate.
        """
        if not self.fred:
             return {
                "gdp_latest": None,
                "inflation_latest": None,
                "fed_rate": None,
                "error": "FRED API Key missing"
            }

        try:
            # get_series_latest_release is sometimes unstable or returns object. 
            # safe approach: get_series().iloc[-1]
            gdp = self.fred.get_series("GDP")
            inflation = self.fred.get_series("CPIAUCSL") # Consumer Price Index for All Urban Consumers: All Items in U.S. City Average
            rates = self.fred.get_series("FEDFUNDS") # Federal Funds Effective Rate

            return {
                "gdp_latest": float(gdp.iloc[-1]) if not gdp.empty else None,
                "inflation_latest": float(inflation.iloc[-1]) if not inflation.empty else None,
                "fed_rate": float(rates.iloc[-1]) if not rates.empty else None
            }
        except Exception as e:
            print(f"Error fetching FRED data: {e}")
            return {
                "gdp_latest": None,
                "inflation_latest": None,
                "fed_rate": None,
                "error": str(e)
            }
