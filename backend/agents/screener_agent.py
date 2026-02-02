# File: agents/screener_agent.py

import os
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

from backend.services.data_loader import get_company_snapshot


class ScreenerAgent:
    """
    Stock Screener Agent

    Responsibilities:
    - Screen stocks based on quantitative criteria
    - Support India (cached fundamentals) and US (API-based screener)
    - Return tickers only (NO formatting, NO UI)

    Non-responsibilities:
    - NO Streamlit / UI
    - NO plotting
    - NO analysis / opinions
    """

    def __init__(
        self,
        rapidapi_config: Dict[str, Any],
        data_path: str = "data",
        cache_path: str = "data/indian_fundamentals.parquet",
    ):
        self.rapidapi_key = rapidapi_config.get("key")
        self.investing_host = rapidapi_config.get("hosts", {}).get("investing")
        self.screener_url = (
            f"https://{self.investing_host}/screener/stocks"
            if self.investing_host
            else None
        )

        self.data_path = data_path
        self.cache_path = cache_path

        self.indian_fundamentals_df = self._load_or_build_indian_fundamentals_cache()

    # ------------------------------------------------------------------
    # Indian market (cached fundamentals)
    # ------------------------------------------------------------------

    def _load_indian_stock_universe(self) -> pd.DataFrame:
        equity_file = os.path.join(self.data_path, "EQUITY_L.csv")
        if not os.path.exists(equity_file):
            return pd.DataFrame()

        df = pd.read_csv(equity_file)
        df.rename(columns=lambda x: x.strip().upper(), inplace=True)

        if "SYMBOL" not in df.columns:
            return pd.DataFrame()

        df["YF_TICKER"] = df["SYMBOL"].astype(str) + ".NS"
        return df[["SYMBOL", "YF_TICKER"]]

    def _build_indian_fundamentals_cache(self) -> pd.DataFrame:
        stock_universe = self._load_indian_stock_universe()
        if stock_universe.empty:
            return pd.DataFrame()

        fundamentals: List[Dict[str, Any]] = []

        # NOTE: limit intentionally small to avoid long blocking runs
        for _, row in stock_universe.head(200).iterrows():
            ticker = row["YF_TICKER"]
            snapshot = get_company_snapshot(ticker, "india")

            if not isinstance(snapshot, dict):
                continue

            fundamentals.append(
                {
                    "YF_TICKER": ticker,
                    "marketCap": snapshot.get("marketCap"),
                    "trailingPE": snapshot.get("trailingPE"),
                    "priceToBook": snapshot.get("priceToBook"),
                    "dividendYield": snapshot.get("dividendYield"),
                    "returnOnEquity": snapshot.get("returnOnEquity"),
                }
            )

        df = pd.DataFrame(fundamentals).dropna(subset=["YF_TICKER"])

        if not df.empty:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            df.to_parquet(self.cache_path)

        return df

    def _load_or_build_indian_fundamentals_cache(self) -> pd.DataFrame:
        if os.path.exists(self.cache_path):
            return pd.read_parquet(self.cache_path)
        return self._build_indian_fundamentals_cache()

    def _run_indian_screen(
        self,
        criteria: Dict[str, Any],
        max_results: int,
    ) -> List[str]:
        if self.indian_fundamentals_df.empty:
            return []

        df = self.indian_fundamentals_df.copy().dropna()

        for key, value in criteria.items():
            try:
                threshold = float(value)
                if key.endswith("_Gt"):
                    col = key[:-3]
                    df = df[df[col] > threshold]
                elif key.endswith("_Lt"):
                    col = key[:-3]
                    df = df[df[col] < threshold]
            except Exception:
                continue

        if "marketCap" in df.columns:
            df = df.sort_values("marketCap", ascending=False)

        return df["YF_TICKER"].head(max_results).tolist()

    # ------------------------------------------------------------------
    # US / International market (API-based screener)
    # ------------------------------------------------------------------

    def _run_api_screen(
        self,
        criteria: Dict[str, Any],
        max_results: int,
    ) -> List[str]:
        if not self.rapidapi_key or not self.screener_url:
            return []

        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": self.investing_host,
        }

        try:
            resp = requests.get(
                self.screener_url,
                headers=headers,
                params=criteria,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                item.get("symbol")
                for item in data.get("data", [])
                if item.get("symbol")
            ][:max_results]

        except Exception:
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        market: str,
        criteria: Dict[str, Any],
        max_results: int = 10,
    ) -> List[str]:
        """
        Run stock screening for a given market.
        """
        market = market.lower()

        if market == "india":
            return self._run_indian_screen(criteria, max_results)

        # default: US / international
        criteria = dict(criteria)
        criteria["country"] = market
        return self._run_api_screen(criteria, max_results)

# import pandas as pd
# import os
# import requests
# import streamlit as st
# from typing import List, Dict, Any

# # Assuming data_loader is in a sibling 'utils' directory
# from utils.data_loader import get_company_snapshot

# class ScreenerAgent:
#     def __init__(self, rapidapi_config: dict, 
#                  data_path: str = "quant-company-insights-agent/data", 
#                  cache_path: str = "quant-company-insights-agent/data/indian_fundamentals.parquet"):
#         self.rapidapi_key = rapidapi_config.get("key")
#         self.investing_host = rapidapi_config.get("hosts", {}).get("investing")
#         self.screener_url = f"https://{self.investing_host}/screener/stocks"
#         self.data_path = data_path
#         self.cache_path = cache_path
#         self.indian_fundamentals_df = self._load_or_build_indian_fundamentals_cache()
#         print("[SUCCESS] ScreenerAgent: Initialization complete.")

#     def _load_indian_stock_universe(self) -> pd.DataFrame:
#         try:
#             main_path = os.path.join(self.data_path, "EQUITY_L.csv")
#             df_main = pd.read_csv(main_path)
#             df_main.rename(columns=lambda x: x.strip().upper().replace(" ", "_"), inplace=True)
#             df_main['YF_TICKER'] = df_main['SYMBOL'] + '.NS'
#             return df_main[['SYMBOL', 'YF_TICKER']]
#         except FileNotFoundError:
#             return pd.DataFrame()

#     def _build_indian_fundamentals_cache(self) -> pd.DataFrame:
#         print("ScreenerAgent: Building Indian fundamentals cache... This will take a long time and only runs once.")
#         stock_list_df = self._load_indian_stock_universe()
#         if stock_list_df.empty: return pd.DataFrame()
#         all_fundamentals = []
#         # Limit to first 200 for faster demo cache building
#         for i, row in stock_list_df.head(200).iterrows():
#             ticker = row['YF_TICKER']
#             print(f"  Fetching fundamentals for {ticker} ({i+1}/{len(stock_list_df.head(200))})...")
#             snapshot = get_company_snapshot(ticker, "India")
#             metrics = {
#                 "YF_TICKER": ticker, "marketCap": snapshot.get("marketCap"),
#                 "trailingPE": snapshot.get("trailingPE"), "priceToBook": snapshot.get("priceToBook"),
#                 "dividendYield": snapshot.get("dividendYield"), "returnOnEquity": snapshot.get("returnOnEquity")
#             }
#             all_fundamentals.append(metrics)
#         fundamentals_df = pd.DataFrame(all_fundamentals).dropna(subset=['YF_TICKER'])
#         fundamentals_df.to_parquet(self.cache_path)
#         print(f"✅ ScreenerAgent: Cache built and saved to {self.cache_path}")
#         return fundamentals_df

#     def _load_or_build_indian_fundamentals_cache(self) -> pd.DataFrame:
#         if os.path.exists(self.cache_path):
#             print(f"ScreenerAgent: Loading Indian fundamentals from cache: {self.cache_path}")
#             return pd.read_parquet(self.cache_path)
#         else:
#             return self._build_indian_fundamentals_cache()

#     def run_indian_screen(self, criteria: dict, max_results: int = 10) -> List[str]:
#         if self.indian_fundamentals_df.empty:
#             return ["ERROR: Indian fundamentals cache is empty."]
#         df = self.indian_fundamentals_df.copy().dropna() # Drop rows with missing data
#         for key, value in criteria.items():
#             try:
#                 numeric_value = float(value)
#                 if key.endswith("_Gt"):
#                     metric = key[:-3]
#                     df = df[df[metric] > numeric_value]
#                 elif key.endswith("_Lt"):
#                     metric = key[:-3]
#                     df = df[df[metric] < numeric_value]
#             except (ValueError, TypeError, KeyError):
#                 continue
#         df = df.sort_values(by="marketCap", ascending=False)
#         return df['YF_TICKER'].head(max_results).tolist()

#     def run_dynamic_api_screen(self, criteria: dict, max_results: int = 10) -> List[str]:
#         if not self.rapidapi_key or not self.investing_host:
#             return ["ERROR: Missing RapidAPI credentials."]
#         try:
#             response = requests.get(self.screener_url, headers={"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": self.investing_host}, params=criteria, timeout=15)
#             response.raise_for_status()
#             data = response.json()
#             tickers = [stock.get('symbol') for stock in data.get('data', []) if stock.get('symbol')]
#             return tickers[:max_results]
#         except Exception as e:
#             return [f"ERROR: RapidAPI request failed: {e}"]

#     def run(self, market: str, criteria: dict, max_results: int = 10) -> List[str]:
#         print(f"✅ ScreenerAgent: Running '{market}' screen with criteria: {criteria}")
#         if market.lower() == "india":
#             return self.run_indian_screen(criteria, max_results)
#         else:
#             criteria['country'] = market.lower()
#             return self.run_dynamic_api_screen(criteria, max_results)

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Dynamic Stock Screener", layout="wide")
#     st.title("🔬 Dynamic Stock Screener Agent")

#     # For standalone testing, load config manually
#     import yaml
#     try:
#         with open("quant-company-insights-agent/config.yaml", "r") as f:
#             config = yaml.safe_load(f)
#         RAPIDAPI_CONFIG = config.get("rapidapi", {})
#     except FileNotFoundError:
#         st.error("Config file not found. Make sure you are running from the project root.")
#         RAPIDAPI_CONFIG = {}

#     agent = ScreenerAgent(rapidapi_config=RAPIDAPI_CONFIG)

#     with st.sidebar:
#         st.header("⚙️ Screener Configuration")
#         market = st.selectbox("Select Market", ["usa", "india"])
        
#         st.subheader("Screening Criteria")
#         if market == 'usa':
#             mc_min = st.number_input("Min Market Cap ($M)", value=200000)
#             pe_min = st.number_input("Min P/E Ratio", value=10)
#             pe_max = st.number_input("Max P/E Ratio", value=50)
#             criteria = {"market_cap_Gt": mc_min, "pe_ratio_Gt": pe_min, "pe_ratio_Lt": pe_max}
#         else: # India
#             mc_min = st.number_input("Min Market Cap (INR Cr)", value=50000)
#             pe_max = st.number_input("Max P/E Ratio", value=40)
#             roe_min = st.number_input("Min Return on Equity (%)", value=15)
#             criteria = {"marketCap_Gt": mc_min * 10000000, "trailingPE_Lt": pe_max, "returnOnEquity_Gt": roe_min / 100}

#         run_button = st.button("▶️ Run Screen", use_container_width=True)

#     if run_button:
#         st.header("Screener Results")
#         with st.spinner(f"Screening {market.upper()} market..."):
#             results = agent.run(market=market, criteria=criteria, max_results=10)
#             if results and "ERROR" in results[0]:
#                 st.error(results[0])
#             elif not results:
#                 st.warning("No stocks found matching the criteria.")
#             else:
#                 st.success(f"Found {len(results)} stocks:")
#                 st.dataframe(pd.DataFrame(results, columns=["Ticker"]))