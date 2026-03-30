import requests
import pandas as pd
import streamlit as st
from typing import Dict, Any
from pathlib import Path
from functools import lru_cache

# --- Helper function to format tickers for API calls ---

@lru_cache(maxsize=1) # Cache the symbols so we only read the file once
def _get_indian_symbols_set():
    """Loads the set of Indian stock symbols from the EQUITY_L.csv file."""
    try:
        equity_file = Path("quant-company-insights-agent/data/EQUITY_L (1).csv")
        if equity_file.exists():
            df = pd.read_csv(equity_file)
            return set(df['SYMBOL'].str.upper())
        return set()
    except Exception:
        return set()

def _format_ticker_for_finnhub(ticker: str) -> str:
    """Appends .NS to Indian stock tickers for Finnhub API compatibility."""
    ticker_upper = ticker.upper().replace(".NS", "") # Use base ticker for lookup
    indian_symbols = _get_indian_symbols_set()
    if ticker_upper in indian_symbols:
        return f"{ticker_upper}.NS"
    return ticker_upper

# --- Insider Agent Class ---

class InsiderAgent:
    def __init__(self, finnhub_key: str, rapidapi_config: dict):
        self.finnhub_key = finnhub_key
        self.rapidapi_key = rapidapi_config.get("key")
        self.roster_host = rapidapi_config.get("hosts", {}).get("fmp")
        self.roster_url = f"https://{self.roster_host}/v4/insider-roaster"
        self.transactions_url = "https://finnhub.io/api/v1/stock/insider-transactions"

    def _safe_request(self, url, params=None, headers=None):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API Request Failed: {e}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}

    def analyze(self, ticker: str) -> dict:
        """
        Analyzes insider activity by combining transactions with the insider roster.
        """
        # --- 1. Get Insider Transactions from Finnhub ---
        finnhub_ticker = _format_ticker_for_finnhub(ticker)
        trans_params = {"symbol": finnhub_ticker, "token": self.finnhub_key}
        trans_response = self._safe_request(self.transactions_url, params=trans_params)
        
        buys = 0
        sells = 0
        net_sentiment = "Neutral"
        transaction_df = pd.DataFrame()
        if isinstance(trans_response, dict) and "data" in trans_response and trans_response["data"]:
            transaction_df = pd.DataFrame(trans_response["data"])
            buys = (transaction_df['change'] > 0).sum()
            sells = (transaction_df['change'] < 0).sum()
            if buys > sells: net_sentiment = "Bullish"
            elif sells > buys: net_sentiment = "Bearish"
            # Keep only relevant columns for display
            transaction_df = transaction_df[['name', 'change', 'transactionDate', 'transactionPrice']].head(10)
            transaction_df.columns = ['Insider Name', 'Shares Changed', 'Date', 'Avg Price']

        # --- 2. Get Insider Roster from Financial Modeling Prep ---
        # FMP API uses the base ticker without .NS
        base_ticker = ticker.upper().replace(".NS", "")
        roster_headers = {"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": self.roster_host}
        roster_response = self._safe_request(f"{self.roster_url}/{base_ticker}", headers=roster_headers)
        
        roster_df = pd.DataFrame()
        if isinstance(roster_response, list) and roster_response:
            roster_df = pd.DataFrame(roster_response)[['name', 'position', 'transactionDate']].head(10)
            roster_df.columns = ['Insider Name', 'Position', 'Last Activity Date']

        # --- 3. Combine and return the analysis ---
        return {
            "summary": {
                "Recent Buys (Count)": int(buys),
                "Recent Sells (Count)": int(sells),
                "Net Sentiment": net_sentiment,
            },
            "roster": roster_df,
            "transactions": transaction_df,
        }

# --- Streamlit Visualization (for standalone testing) ---
if __name__ == "__main__":
    st.set_page_config(page_title="Insider Activity Agent", layout="wide")
    st.title("📝 Insider Activity Analyzer")
    
    # This part would typically be handled by the Orchestrator loading config.yaml
    # For standalone testing, we get keys from Streamlit secrets.
    FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY")
    RAPIDAPI_CONFIG = {
        "key": st.secrets.get("RAPIDAPI_KEY"),
        "hosts": {"fmp": "financial-modeling-prep.p.rapidapi.com"}
    }

    if not FINNHUB_KEY or not RAPIDAPI_CONFIG["key"]:
        st.error("API keys not found! Please set FINNHUB_API_KEY and RAPIDAPI_KEY in your Streamlit secrets.")
    else:
        agent = InsiderAgent(finnhub_key=FINNHUB_KEY, rapidapi_config=RAPIDAPI_CONFIG)
        
        st.sidebar.header("⚙️ Configuration")
        ticker = st.sidebar.text_input("Ticker Symbol", "NVDA")
        run_button = st.sidebar.button("🔬 Analyze Insider Activity", use_container_width=True)

        if run_button:
            st.header(f"Results for {ticker}")
            with st.spinner(f"Fetching insider data for {ticker}..."):
                results = agent.analyze(ticker)
                
                summary = results.get("summary", {})
                roster = results.get("roster", pd.DataFrame())
                transactions = results.get("transactions", pd.DataFrame())

                st.subheader("Sentiment Summary")
                cols = st.columns(3)
                cols[0].metric("Recent Buys", summary.get("Recent Buys (Count)", 0))
                cols[1].metric("Recent Sells", summary.get("Recent Sells (Count)", 0))
                sentiment = summary.get("Net Sentiment", "Neutral")
                cols[2].markdown(f"**Net Sentiment:** {sentiment}")

                st.subheader("Key Insider Roster")
                if not roster.empty:
                    st.dataframe(roster.set_index("Insider Name"))
                else:
                    st.info("No insider roster data available.")
                
                st.subheader("Recent Transactions")
                if not transactions.empty:
                    st.dataframe(transactions.set_index("Insider Name"))
                else:
                    st.info("No recent transactions found.")


# import requests
# import pandas as pd
# import streamlit as st

# class InsiderAgent:
#     def __init__(self, finnhub_key: str, rapidapi_config: dict):
#         self.finnhub_key = finnhub_key
#         self.rapidapi_key = rapidapi_config.get("key")
#         self.roster_host = rapidapi_config.get("hosts", {}).get("fmp")
#         self.roster_url = f"https://{self.roster_host}/v4/insider-roaster"
#         self.transactions_url = "https://finnhub.io/api/v1/stock/insider-transactions"

#     def _safe_request(self, url, params=None, headers=None):
#         try:
#             resp = requests.get(url, params=params, headers=headers, timeout=15)
#             resp.raise_for_status()
#             return resp.json()
#         except requests.exceptions.RequestException as e:
#             return {"error": f"API Request Failed: {e}"}
#         except Exception as e:
#             return {"error": f"An unexpected error occurred: {e}"}

#     def analyze(self, ticker: str) -> dict:
#         """
#         Analyzes insider activity by combining transactions with the insider roster.
#         """
#         # --- 1. Get Insider Transactions from Finnhub ---
#         trans_params = {"symbol": ticker.upper(), "token": self.finnhub_key}
#         trans_response = self._safe_request(self.transactions_url, params=trans_params)
        
#         buys = 0
#         sells = 0
#         net_sentiment = "Neutral"
#         transaction_df = pd.DataFrame()
#         if isinstance(trans_response, dict) and "data" in trans_response and trans_response["data"]:
#             transaction_df = pd.DataFrame(trans_response["data"])
#             buys = (transaction_df['change'] > 0).sum()
#             sells = (transaction_df['change'] < 0).sum()
#             if buys > sells: net_sentiment = "Bullish"
#             elif sells > buys: net_sentiment = "Bearish"
#             # Keep only relevant columns for display
#             transaction_df = transaction_df[['name', 'change', 'transactionDate', 'transactionPrice']].head(10)
#             transaction_df.columns = ['Insider Name', 'Shares Changed', 'Date', 'Avg Price']

#         # --- 2. Get Insider Roster from Financial Modeling Prep ---
#         roster_headers = {"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": self.roster_host}
#         roster_response = self._safe_request(f"{self.roster_url}/{ticker.upper()}", headers=roster_headers)
        
#         roster_df = pd.DataFrame()
#         if isinstance(roster_response, list) and roster_response:
#              roster_df = pd.DataFrame(roster_response)[['name', 'position', 'transactionDate']].head(10)
#              roster_df.columns = ['Insider Name', 'Position', 'Last Activity Date']

#         # --- 3. Combine and return the analysis ---
#         return {
#             "summary": {
#                 "Recent Buys (Count)": int(buys),
#                 "Recent Sells (Count)": int(sells),
#                 "Net Sentiment": net_sentiment,
#             },
#             "roster": roster_df,
#             "transactions": transaction_df,
#         }

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Insider Activity Agent", layout="wide")
#     st.title("📝 Insider Activity Analyzer")
    
#     # This part would typically be handled by the Orchestrator loading config.yaml
#     # For standalone testing, we get keys from Streamlit secrets.
#     FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY")
#     RAPIDAPI_CONFIG = {
#         "key": st.secrets.get("RAPIDAPI_KEY"),
#         "hosts": {"fmp": "financial-modeling-prep.p.rapidapi.com"}
#     }

#     if not FINNHUB_KEY or not RAPIDAPI_CONFIG["key"]:
#         st.error("API keys not found! Please set FINNHUB_API_KEY and RAPIDAPI_KEY in your Streamlit secrets.")
#     else:
#         agent = InsiderAgent(finnhub_key=FINNHUB_KEY, rapidapi_config=RAPIDAPI_CONFIG)
        
#         st.sidebar.header("⚙️ Configuration")
#         ticker = st.sidebar.text_input("Ticker Symbol", "NVDA")
#         run_button = st.sidebar.button("🔬 Analyze Insider Activity", use_container_width=True)

#         if run_button:
#             st.header(f"Results for {ticker}")
#             with st.spinner(f"Fetching insider data for {ticker}..."):
#                 results = agent.analyze(ticker)
                
#                 summary = results.get("summary", {})
#                 roster = results.get("roster", pd.DataFrame())
#                 transactions = results.get("transactions", pd.DataFrame())

#                 st.subheader("Sentiment Summary")
#                 cols = st.columns(3)
#                 cols[0].metric("Recent Buys", summary.get("Recent Buys (Count)", 0))
#                 cols[1].metric("Recent Sells", summary.get("Recent Sells (Count)", 0))
#                 sentiment = summary.get("Net Sentiment", "Neutral")
#                 cols[2].markdown(f"**Net Sentiment:** {sentiment}")

#                 st.subheader("Key Insider Roster")
#                 if not roster.empty:
#                     st.dataframe(roster.set_index("Insider Name"))
#                 else:
#                     st.info("No insider roster data available.")
                
#                 st.subheader("Recent Transactions")
#                 if not transactions.empty:
#                     st.dataframe(transactions.set_index("Insider Name"))
#                 else:
#                     st.info("No recent transactions found.")