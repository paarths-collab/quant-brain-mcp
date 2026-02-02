# File: agents/stock_picker_agent.py

import yfinance as yf
import pandas as pd
from typing import List, Dict, Any


class StockPickerAgent:
    """
    Direct Stock Picker Agent (NO CACHES, NO FILES)

    Responsibilities:
    - Rank a given list of tickers
    - Fetch data live via yfinance
    """

    def _calculate_scores(self, tickers: List[str]) -> pd.DataFrame:
        records = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="1y")

                if hist.empty or len(hist) < 2:
                    continue

                momentum = ((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100
                pe = info.get("trailingPE")
                roe = info.get("returnOnEquity")

                records.append(
                    {
                        "ticker": ticker,
                        "momentum": momentum,
                        "value": (1 / pe) * 100 if pe and pe > 0 else 0,
                        "quality": roe * 100 if roe else 0,
                    }
                )
            except Exception:
                continue

        return pd.DataFrame(records)

    def _rank(self, df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
        if df.empty:
            return df

        for col in ["momentum", "value", "quality"]:
            df[f"{col}_rank"] = df[col].rank(pct=True) * 100

        df["final_score"] = (
            df["momentum_rank"] * weights.get("momentum", 0)
            + df["value_rank"] * weights.get("value", 0)
            + df["quality_rank"] * weights.get("quality", 0)
        )

        return df.sort_values("final_score", ascending=False).reset_index(drop=True)

    # -------- PUBLIC API --------

    def pick(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rank provided tickers directly.
        """
        scores_df = self._calculate_scores(tickers)
        ranked_df = self._rank(scores_df, weights)
        return ranked_df.head(top_n).to_dict(orient="records")

# import yfinance as yf
# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from typing import List, Dict
# import os

# class StockPickerAgent:
#     def __init__(self, 
#                  data_path: str = "data",
#                  cache_path_india: str = "data/indian_stock_universe.parquet",
#                  cache_path_us: str = "data/us_stock_universe.parquet"):
#         """
#         Initializes the StockPickerAgent by loading dynamic, cached universes for both US and Indian stocks.
#         """
#         self.data_path = data_path
#         self.cache_path_india = cache_path_india
#         self.cache_path_us = cache_path_us
        
#         # Load both universes into memory upon initialization
#         self.indian_stock_universe = self._load_or_build_indian_universe_cache()
#         self.us_stock_universe = self._load_or_build_us_universe_cache()
        
#         print("StockPickerAgent: Initialization complete.")

#     def _build_indian_universe_cache(self) -> pd.DataFrame:
#         """Builds the cache for Indian stocks from nifty500.csv."""
#         print("StockPickerAgent: Building INDIAN stock universe cache... This may take time and only runs once.")
#         try:
#             india_path = os.path.join(self.data_path, "nifty500.csv")
#             universe_df = pd.read_csv(india_path)
#             universe_df.rename(columns={'Company Name': 'NAME_OF_COMPANY', 'Symbol': 'SYMBOL'}, inplace=True)
#             universe_df['YF_TICKER'] = universe_df['SYMBOL'] + '.NS'
#         except FileNotFoundError as e:
#             print(f"StockPickerAgent ERROR: Could not find Indian stock data file: {e}")
#             return pd.DataFrame()

#         sectors = []
#         total = len(universe_df)
#         for i, row in universe_df.iterrows():
#             print(f"  Fetching Indian sector for {row['YF_TICKER']} ({i+1}/{total})...")
#             try:
#                 sector = yf.Ticker(row['YF_TICKER']).info.get('sector', 'Unknown')
#                 sectors.append(sector)
#             except Exception:
#                 sectors.append('Unknown')
        
#         universe_df['Sector'] = sectors
#         universe_df.to_parquet(self.cache_path_india)
#         print(f"StockPickerAgent: Indian universe cache built and saved to {self.cache_path_india}")
#         return universe_df

#     def _load_or_build_indian_universe_cache(self) -> pd.DataFrame:
#         """Loads the Indian stock universe from cache or builds it."""
#         if os.path.exists(self.cache_path_india):
#             print(f"StockPickerAgent: Loading Indian stock universe from cache: {self.cache_path_india}")
#             return pd.read_parquet(self.cache_path_india)
#         return self._build_indian_universe_cache()

#     def _build_us_universe_cache(self) -> pd.DataFrame:
#         """Builds the cache for US stocks from us_stocks.csv."""
#         print("StockPickerAgent: Building US stock universe cache... This may take time and only runs once.")
#         try:
#             us_path = os.path.join(self.data_path, "us_stocks.csv")
#             universe_df = pd.read_csv(us_path)
#             universe_df.rename(columns={'Company Name': 'NAME_OF_COMPANY', 'Symbol': 'SYMBOL'}, inplace=True)
#             universe_df['YF_TICKER'] = universe_df['SYMBOL']
#         except FileNotFoundError as e:
#             print(f"❌ StockPickerAgent ERROR: Could not find US stock data file: {e}")
#             return pd.DataFrame()

#         sectors = []
#         total = len(universe_df)
#         for i, row in universe_df.iterrows():
#             print(f"  Fetching US sector for {row['YF_TICKER']} ({i+1}/{total})...")
#             try:
#                 sector = yf.Ticker(row['YF_TICKER']).info.get('sector', 'Unknown')
#                 sectors.append(sector)
#             except Exception:
#                 sectors.append('Unknown')
        
#         universe_df['Sector'] = sectors
#         universe_df.to_parquet(self.cache_path_us)
#         print(f"✅ StockPickerAgent: US universe cache built and saved to {self.cache_path_us}")
#         return universe_df

#     def _load_or_build_us_universe_cache(self) -> pd.DataFrame:
#         """Loads the US stock universe from cache or builds it."""
#         if os.path.exists(self.cache_path_us):
#             print(f"StockPickerAgent: Loading US stock universe from cache: {self.cache_path_us}")
#             return pd.read_parquet(self.cache_path_us)
#         return self._build_us_universe_cache()

#     def _get_stock_data(self, tickers: List[str]) -> Dict[str, yf.Ticker]:
#         """Fetches and caches yfinance Ticker objects."""
#         print(f"StockPickerAgent: Fetching detailed data for {len(tickers)} stocks...")
#         return {ticker: yf.Ticker(ticker) for ticker in tickers}

#     def calculate_scores(self, stock_data: Dict[str, yf.Ticker]) -> pd.DataFrame:
#         """Calculates momentum, value, and quality scores for each stock."""
#         all_metrics = []
#         for ticker, stock_obj in stock_data.items():
#             try:
#                 info = stock_obj.info
#                 hist = stock_obj.history(period="1y")
#                 if hist.empty or 'Close' not in hist.columns or len(hist) < 2: continue
                
#                 momentum_score = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
#                 pe = info.get('trailingPE')
#                 value_score = 1 / pe if pe and pe > 0 else 0
#                 roe = info.get('returnOnEquity')
#                 quality_score = roe * 100 if roe else 0

#                 all_metrics.append({
#                     "Ticker": ticker, "Momentum": momentum_score,
#                     "Value": value_score * 100, "Quality (ROE)": quality_score
#                 })
#             except Exception:
#                 continue
#         return pd.DataFrame(all_metrics).dropna()

#     def rank_stocks(self, scores_df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
#         """Ranks stocks based on a weighted average of their scores."""
#         if scores_df.empty: return pd.DataFrame()
#         for metric in ['Momentum', 'Value', 'Quality (ROE)']:
#             scores_df[f'{metric}_Rank'] = scores_df[metric].rank(pct=True) * 100
#         scores_df['Final Score'] = (
#             scores_df['Momentum_Rank'] * weights['momentum'] +
#             scores_df['Value_Rank'] * weights['value'] +
#             scores_df['Quality (ROE)_Rank'] * weights['quality']
#         )
#         return scores_df.sort_values('Final Score', ascending=False).reset_index(drop=True)

#     def run(self, market: str, sector: str, weights: Dict[str, float], top_n: int = 5) -> pd.DataFrame:
#         """
#         Runs the full stock picking pipeline for a given market and sector.
#         """
#         print(f"StockPickerAgent: Running discovery for '{sector}' sector in market '{market}'...")
        
#         universe_to_scan = self.indian_stock_universe if market.lower() == 'india' else self.us_stock_universe

#         if universe_to_scan.empty:
#             return pd.DataFrame([{"Error": f"Stock universe for market '{market}' is empty."}])
            
#         tickers_to_analyze = universe_to_scan[universe_to_scan['Sector'] == sector]['YF_TICKER'].tolist()
        
#         if not tickers_to_analyze:
#             return pd.DataFrame([{"Error": f"No stocks found for sector '{sector}' in the {market} universe."}])
                
#         stock_data = self._get_stock_data(tickers_to_analyze)
#         scores_df = self.calculate_scores(stock_data)
#         ranked_df = self.rank_stocks(scores_df, weights)
        
#         return ranked_df.head(top_n)

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Dynamic Stock Picker", layout="wide")
#     st.title("🎯 Dynamic Multi-Factor Stock Picker Agent")

#     agent = StockPickerAgent()
    
#     with st.sidebar:
#         st.header("⚙️ Configuration")
        
#         market = st.radio("Select Market", ["USA", "India"], horizontal=True)
        
#         universe = agent.us_stock_universe if market == "USA" else agent.indian_stock_universe
#         available_sectors = sorted(universe['Sector'].unique().tolist())
        
#         sector = st.selectbox("Select a Sector to Analyze", options=available_sectors)
        
#         st.subheader("Factor Weights")
#         w_momentum = st.slider("Momentum Weight", 0.0, 1.0, 0.4, 0.05)
#         w_value = st.slider("Value Weight", 0.0, 1.0, 0.3, 0.05)
#         w_quality = st.slider("Quality (ROE) Weight", 0.0, 1.0, 0.3, 0.05)

#         run_button = st.button("🔬 Find Top Stocks", use_container_width=True)

#     if run_button:
#         total_weight = w_momentum + w_value + w_quality
#         if total_weight == 0:
#             st.error("Total weight cannot be zero.")
#         else:
#             weights = {
#                 "momentum": w_momentum / total_weight, "value": w_value / total_weight, "quality": w_quality / total_weight,
#             }
#             st.header(f"Top Stock Picks for: *{sector}*")
#             with st.spinner(f"Fetching data and ranking stocks in the {sector} sector..."):
#                 ranked_df = agent.run(market, sector, weights, top_n=10)

#                 if ranked_df.empty or "Error" in ranked_df.iloc[0]:
#                     st.error("Could not generate rankings. The sector might be empty or data could not be fetched.")
#                 else:
#                     st.subheader("🏆 Final Rankings")
#                     st.dataframe(ranked_df[['Ticker', 'Final Score', 'Momentum', 'Value', 'Quality (ROE)']])

#                     st.subheader("Visual Factor Comparison")
#                     fig = px.bar(ranked_df, x='Ticker', y=['Momentum_Rank', 'Value_Rank', 'Quality (ROE)_Rank'],
#                                  title=f"Factor Ranks for Top 10 Stocks in {sector}",
#                                  labels={'value': 'Normalized Rank (0-100)', 'variable': 'Factor'})
#                     st.plotly_chart(fig, use_container_width=True)

