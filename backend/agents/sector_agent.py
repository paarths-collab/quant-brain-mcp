# File: agents/sector_agent.py

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from typing import Dict, Any, List, Optional


class SectorAgent:
    """
    Sector Analysis Agent

    Responsibilities:
    - Compute sector-wise performance for US and Indian markets
    - Use stock universes to derive sectors dynamically
    - Fetch lightweight sentiment score from news (optional)

    Non-responsibilities:
    - NO Streamlit / UI
    - NO plotting
    - NO LLM-based sentiment
    """

    def __init__(
        self,
        news_api_key: Optional[str],
        us_universe: pd.DataFrame,
        indian_universe: pd.DataFrame,
    ):
        self.news_api_key = news_api_key
        self.universes = {
            "US": us_universe,
            "INDIA": indian_universe,
        }

    # ---------- Internal helpers ----------

    def _fetch_performance(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> float:
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
            )
            if df.empty or "Close" not in df.columns or len(df) < 2:
                return 0.0

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)

            start_price = float(df["Close"].iloc[0])
            end_price = float(df["Close"].iloc[-1])

            if start_price <= 0:
                return 0.0

            return ((end_price / start_price) - 1) * 100

        except Exception:
            return 0.0

    def _fetch_sentiment(self, sector: str, market: str) -> float:
        if not self.news_api_key:
            return 0.0

        query = f"{sector} sector {market}"
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "pageSize": 5,
            "apiKey": self.news_api_key,
        }

        try:
            articles = requests.get(url, params=params, timeout=10).json().get(
                "articles", []
            )
            if not articles:
                return 0.0

            # Simple proxy sentiment: volume-based signal
            return min(len(articles) / 5.0, 1.0)

        except Exception:
            return 0.0

    # ---------- Public API ----------

    def analyze_sectors(
        self,
        start_date: str,
        end_date: str,
        sample_size: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Analyze sector-wise performance for both US and Indian markets.
        """

        results: List[Dict[str, Any]] = []

        for market, universe in self.universes.items():
            if universe is None or universe.empty:
                continue

            if "Sector" not in universe.columns or "YF_TICKER" not in universe.columns:
                continue

            sectors = [
                s for s in universe["Sector"].unique() if s and s != "Unknown"
            ]

            for sector in sectors:
                sector_stocks = universe[universe["Sector"] == sector]
                if sector_stocks.empty:
                    continue

                tickers = (
                    sector_stocks.sample(
                        n=min(sample_size, len(sector_stocks)),
                        random_state=42,
                    )["YF_TICKER"]
                    .dropna()
                    .tolist()
                )

                performances = [
                    self._fetch_performance(t, start_date, end_date)
                    for t in tickers
                ]

                avg_performance = (
                    float(np.mean(performances)) if performances else 0.0
                )

                sentiment_score = self._fetch_sentiment(sector, market)

                booming_score = (0.7 * avg_performance) + (0.3 * sentiment_score * 100)

                results.append(
                    {
                        "market": market,
                        "sector": sector,
                        "average_performance_pct": round(avg_performance, 2),
                        "sentiment_score": round(sentiment_score, 3),
                        "booming_score": round(booming_score, 2),
                        "sampled_stocks": tickers,
                    }
                )

        return sorted(
            results,
            key=lambda x: x["booming_score"],
            reverse=True,
        )


# import yfinance as yf
# import pandas as pd
# import numpy as np
# import requests
# import streamlit as st
# import plotly.express as px
# import os

# # --- Try to import transformers, but don't fail if it's not there ---
# try:
#     from transformers import pipeline
#     _HAS_TRANSFORMERS = True
# except ImportError:
#     pipeline = None
#     _HAS_TRANSFORMERS = False

# class SectorAgent:
#     def __init__(self, news_api_key: str, us_universe: pd.DataFrame, indian_universe: pd.DataFrame):
#         self.news_api_key = news_api_key
        
#         # --- THIS IS THE UPGRADE: Store the full stock universes ---
#         self.us_universe = us_universe
#         self.indian_universe = indian_universe
#         self.universes = {"USA": self.us_universe, "India": self.indian_universe}
#         # --- END OF UPGRADE ---
        
#         if _HAS_TRANSFORMERS:
#             self.sentiment_model = pipeline("sentiment-analysis", model="ProsusAI/finbert")
#             print("[SUCCESS] SectorAgent: FinBERT sentiment model loaded.")
#         else:
#             self.sentiment_model = None
#             print("[WARNING] SectorAgent: 'transformers' not installed. Sentiment analysis is disabled.")

#     def _fetch_performance(self, ticker, start, end):
#         """
#         Fetches historical data and calculates the percentage change.
#         """
#         try:
#             df = yf.download(ticker, start=start, end=end, progress=False)
            
#             # Check if data is available and 'Close' column exists
#             if df.empty or 'Close' not in df.columns or len(df) < 2:
#                 print(f"No data or 'Close' column for {ticker}. Skipping.")
#                 return 0.0
            
#             if isinstance(df.columns, pd.MultiIndex):
#                 df.columns = df.columns.droplevel(0)

#             end_price = float(df["Close"].iloc[-1])
#             start_price = float(df["Close"].iloc[0])
            
#             if start_price == 0:
#                 return 0.0

#             return ((end_price / start_price) - 1) * 100
#         except Exception as e:
#             print(f"Could not fetch performance for {ticker}: {e}")
#             return 0.0

#     def _get_sentiment_score(self, sector, market):
#         if not self.sentiment_model or not self.news_api_key: return 0.0
#         query = f"{sector} sector {market}"
#         url = f"https://newsapi.org/v2/everything?q={query}&language=en&apiKey={self.news_api_key}"
#         try:
#             articles = requests.get(url, timeout=10).json().get("articles", [])
#             if not articles: return 0.0
            
#             texts = [f"{a.get('title', '')}. {a.get('description', '')}" for a in articles[:5]]
#             sentiments = self.sentiment_model(texts)
            
#             score = 0
#             for sent in sentiments:
#                 if sent['label'] == 'positive': score += sent['score']
#                 elif sent['label'] == 'negative': score -= sent['score']
#             return score / len(sentiments) if sentiments else 0.0
#         except Exception:
#             return 0.0

#     def analyze(self, start_date: str, end_date: str) -> pd.DataFrame:
#         """Analyzes all defined sectors dynamically from the provided universes."""
#         print(f"SectorAgent: Analyzing sector performance from {start_date} to {end_date}...")
#         data = []
        
#         # --- DYNAMICALLY ANALYZE SECTORS FROM THE UNIVERSE FILES ---
#         for market, universe_df in self.universes.items():
#             if universe_df.empty:
#                 print(f"WARNING: Stock universe for {market} is empty. Skipping.")
#                 continue
            
#             # Get a list of unique, valid sectors
#             unique_sectors = [s for s in universe_df['Sector'].unique() if s and s != 'Unknown']
            
#             for sector in unique_sectors:
#                 # Get all stocks for the current sector
#                 sector_stocks = universe_df[universe_df['Sector'] == sector]
                
#                 # Take a sample of up to 5 stocks to represent the sector
#                 sample_size = min(len(sector_stocks), 5)
#                 ticker_sample = sector_stocks.sample(n=sample_size, random_state=42)['YF_TICKER'].tolist()
                
#                 # Calculate the average performance of the sample
#                 performances = [self._fetch_performance(ticker, start_date, end_date) for ticker in ticker_sample]
#                 avg_perf = np.mean([p for p in performances if p is not None]) if performances else 0.0
                
#                 sentiment = self._get_sentiment_score(sector, market)
#                 score = 0.7 * avg_perf + 0.3 * sentiment * 100
#                 data.append((market, sector, f"{avg_perf:.2f}%", f"{sentiment:.2f}", f"{score:.2f}"))
#         # --- END OF DYNAMIC ANALYSIS LOGIC ---
                
#         df = pd.DataFrame(data, columns=["Market", "Sector", "Performance", "Sentiment", "Booming Score"])
#         df['Booming Score'] = pd.to_numeric(df['Booming Score'])
#         return df.sort_values("Booming Score", ascending=False).reset_index(drop=True)

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Sector Analysis Agent", layout="wide")
#     st.title("🌍 Sector Analysis Agent Showcase")

#     NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", os.getenv("NEWS_API_KEY"))
#     if not NEWS_API_KEY:
#         st.error("NEWS_API_KEY not found! Please set it in your Streamlit secrets.")
#     else:
#         # For standalone testing, we need to load the universes manually
#         from agents.stock_picker_agent import StockPickerAgent
#         picker = StockPickerAgent()
        
#         agent = SectorAgent(
#             news_api_key=NEWS_API_KEY,
#             us_universe=picker.us_stock_universe,
#             indian_universe=picker.indian_stock_universe
#         )

#         with st.sidebar:
#             st.header("⚙️ Configuration")
#             start_date = st.date_input("Start Date", pd.to_datetime("today") - pd.DateOffset(months=3))
#             end_date = st.date_input("End Date", pd.to_datetime("today"))
#             run_button = st.button("🔬 Analyze Sectors", use_container_width=True)

#         if run_button:
#             st.header("Sector Performance Rankings")
#             with st.spinner("Fetching performance and analyzing news sentiment for all sectors..."):
#                 results_df = agent.analyze(str(start_date.date()), str(end_date.date()))
#                 st.dataframe(results_df)
                
#                 st.subheader("Booming Score Comparison")
#                 fig = px.bar(results_df, x="Sector", y="Booming Score", color="Market",
#                              title="Sector 'Booming' Score (Performance + Sentiment)")
#                 st.plotly_chart(fig, use_container_width=True)

