

# core/strategies/pairs_trading.py

import pandas as pd
import numpy as np
from .base import Strategy


class PairsTradingStrategy(Strategy):
    """
    Pairs Trading Strategy (Statistical Arbitrage)

    Long spread  → Z-score < -entry_z
    Short spread → Z-score > +entry_z
    """

    name = "Pairs Trading"

    def __init__(self, lookback: int = 30, entry_z: float = 2.0):
        self.lookback = lookback
        self.entry_z = entry_z

    def parameters(self) -> dict:
        return {
            "lookback": self.lookback,
            "entry_z": self.entry_z
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected input:
        - DataFrame with exactly TWO columns
        - Each column = adjusted close of an asset
        """

        if data.shape[1] != 2:
            raise ValueError("PairsTradingStrategy requires exactly two price series")

        df = data.copy()
        asset_x, asset_y = df.columns

        # --- Hedge ratio (beta) ---
        beta = np.polyfit(df[asset_y], df[asset_x], 1)[0]

        # --- Spread ---
        df["spread"] = df[asset_x] - beta * df[asset_y]

        # --- Rolling statistics ---
        df["spread_mean"] = df["spread"].rolling(self.lookback).mean()
        df["spread_std"] = df["spread"].rolling(self.lookback).std()

        df["zscore"] = (df["spread"] - df["spread_mean"]) / df["spread_std"]

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None     # Long the spread
        df["entry_short"] = None    # Short the spread

        # --- Trading logic ---
        long_spread = df["zscore"] < -self.entry_z
        short_spread = df["zscore"] > self.entry_z

        df.loc[long_spread, "signal"] = 1
        df.loc[short_spread, "signal"] = -1

        df.loc[long_spread, "entry_long"] = df["spread"]
        df.loc[short_spread, "entry_short"] = df["spread"]

        # --- Store beta for downstream use (portfolio sizing) ---
        df.attrs["beta"] = beta
        df.attrs["pair"] = f"{asset_x}/{asset_y}"

        return df

# import yfinance as yf
# import pandas as pd
# import numpy as np
# import streamlit as st
# import plotly.express as px
# import plotly.graph_objects as go
# from typing import List

# # --- Core Backtesting Logic ---
# @st.cache_data 
# def run_backtest(ticker1, ticker2, start_date, end_date, lookback=30, entry_z=2.0, initial_capital=100000):
#     """Runs a vectorized backtest for a pairs trading strategy."""
#     data = yf.download([ticker1, ticker2], start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
#     if data.empty or data.isnull().values.any() or len(data) < lookback:
#         return pd.DataFrame()
    
#     # Calculate spread and z-score
#     data.dropna(inplace=True)
#     beta = np.polyfit(data[ticker2], data[ticker1], 1)[0]
#     data['Spread'] = data[ticker1] - beta * data[ticker2]
#     data['Mean'] = data['Spread'].rolling(lookback).mean()
#     data['STD'] = data['Spread'].rolling(lookback).std()
#     data['Zscore'] = (data['Spread'] - data['Mean']) / data['STD']
    
#     # Generate signals
#     data['Signal'] = 0
#     data.loc[data['Zscore'] > entry_z, 'Signal'] = -1  # Short the spread
#     data.loc[data['Zscore'] < -entry_z, 'Signal'] = 1   # Long the spread
#     data['Position'] = data['Signal'].shift(1).ffill().fillna(0)
    
#     # Calculate returns and equity curve
#     data['Strategy_Returns'] = data['Spread'].pct_change() * data['Position']
#     data['Equity_Curve'] = (1 + data['Strategy_Returns']).cumprod() * initial_capital
    
#     # Add beta to the final dataframe for reference
#     data.attrs['beta'] = beta
#     return data

# def calculate_performance_metrics(backtest_df, initial_capital):
#     """Calculates summary statistics for the backtest and formats them."""
#     if backtest_df.empty: return {}
    
#     final_equity = backtest_df['Equity_Curve'].iloc[-1]
#     total_return_pct = (final_equity / initial_capital - 1) * 100
#     daily_returns = backtest_df['Strategy_Returns'].dropna()
#     sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
#     peak = backtest_df['Equity_Curve'].cummax()
#     drawdown = (backtest_df['Equity_Curve'] - peak) / peak
#     max_drawdown_pct = drawdown.min() * 100
#     trades = backtest_df[backtest_df['Signal'] != backtest_df['Signal'].shift(1)]
    
#     return {
#         "Total Return %": f"{total_return_pct:.2f}",
#         "Sharpe Ratio": f"{sharpe_ratio:.2f}",
#         "Max Drawdown %": f"{max_drawdown_pct:.2f}",
#         "Number of Trades": len(trades),
#         "Hedge Ratio (Beta)": f"{backtest_df.attrs.get('beta', 0.0):.2f}"
#     }

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(tickers: List[str], start_date: str, end_date: str, initial_capital=100000, **kwargs) -> dict:
#     """Main entry point for the Pairs Trading strategy."""
#     if not isinstance(tickers, list) or len(tickers) != 2:
#         return {"summary": {"Error": "Pairs Trading requires exactly two tickers."}, "data": pd.DataFrame()}
    
#     try:
#         df_backtest = run_backtest(
#             tickers[0], 
#             tickers[1], 
#             start_date, 
#             end_date,
#             initial_capital=initial_capital,
#             **kwargs
#         )
#         if df_backtest.empty:
#             return {"summary": {"Error": "Could not fetch sufficient data for the pair."}, "data": pd.DataFrame()}
        
#         summary_metrics = calculate_performance_metrics(df_backtest, initial_capital)
        
#         # Rename the single ticker column to 'ticker' for portfolio builder consistency if needed
#         summary_metrics['ticker'] = f"{tickers[0]}/{tickers[1]}"
        
#         return {"summary": summary_metrics, "data": df_backtest}
#     except Exception as e:
#         return {"summary": {"Error": str(e)}, "data": pd.DataFrame()}

# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Pairs Trading Strategy", layout="wide")
#     st.title("📈 Pairs Trading Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         tickers_input = st.text_input("Enter Ticker Pair (comma-separated)", "PEP,KO")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
#         initial_capital = st.number_input("Initial Capital", 1000, 1000000, 100000)
        
#         st.header("Strategy Parameters")
#         lookback = st.slider("Lookback Period (days)", 10, 100, 30)
#         entry_z = st.slider("Entry Z-Score Threshold", 1.0, 3.0, 2.0, 0.1)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         tickers = [t.strip().upper() for t in tickers_input.split(",")]
#         if len(tickers) != 2:
#             st.error("Please enter exactly two tickers separated by a comma.")
#         else:
#             st.header(f"Results for {tickers[0]} / {tickers[1]}")
#             with st.spinner("Running backtest..."):
#                 results = run(
#                     tickers=tickers, 
#                     start_date=start_date, 
#                     end_date=end_date, 
#                     initial_capital=initial_capital,
#                     lookback=lookback, 
#                     entry_z=entry_z
#                 )
#                 summary = results.get("summary", {})
#                 backtest_df = results.get("data", pd.DataFrame())

#             if "Error" in summary:
#                 st.error(summary["Error"])
#             elif not backtest_df.empty:
#                 st.subheader("Performance Summary")
#                 cols = st.columns(5)
#                 cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#                 cols[3].metric("Trades", summary.get('Number of Trades', 0))
#                 cols[4].metric("Hedge Ratio (Beta)", summary.get('Hedge Ratio (Beta)', '0.00'))

#                 st.subheader("Visual Analysis")
                
#                 # Chart 1: Z-Score
#                 fig_z = px.line(backtest_df, x=backtest_df.index, y='Zscore', title='Spread Z-Score with Entry/Exit Thresholds')
#                 fig_z.add_hline(y=entry_z, line_dash="dash", line_color="red", annotation_text="Short Spread Entry")
#                 fig_z.add_hline(y=-entry_z, line_dash="dash", line_color="green", annotation_text="Long Spread Entry")
#                 fig_z.add_hline(y=0, line_dash="dot", line_color="grey", annotation_text="Mean")
#                 st.plotly_chart(fig_z, use_container_width=True)
                
#                 # Chart 2: Equity Curve
#                 fig_eq = px.line(backtest_df, x=backtest_df.index, y='Equity_Curve', title='Strategy Equity Curve')
#                 st.plotly_chart(fig_eq, use_container_width=True)
                
#             else:
#                 st.warning("Backtest ran but did not produce any data.")
