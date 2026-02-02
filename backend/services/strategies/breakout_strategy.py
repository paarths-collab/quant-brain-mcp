# # File: strategies/breakout_strategy.py


# core/strategies/breakout.py

import pandas as pd
from .base import Strategy


class BreakoutStrategy(Strategy):
    name = "Donchian Breakout"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def parameters(self):
        return {"lookback": self.lookback}

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        df["donchian_high"] = df["High"].rolling(self.lookback).max().shift(1)
        df["donchian_low"] = df["Low"].rolling(self.lookback).min().shift(1)

        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        long_cond = df["Close"] > df["donchian_high"]
        short_cond = df["Close"] < df["donchian_low"]

        df.loc[long_cond, "signal"] = 1
        df.loc[long_cond, "entry_long"] = df["Close"]

        df.loc[short_cond, "signal"] = -1
        df.loc[short_cond, "entry_short"] = df["Close"]

        return df

# import pandas as pd
# import streamlit as st
# import plotly.graph_objects as go
# from backtesting import Backtest, Strategy

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data
# from backend.services.market_utils import get_market_config


# class Breakout(Strategy):
#     """
#     Breakout Strategy implementation for backtesting.py library.
    
#     This strategy identifies breakouts above resistance levels or below support levels 
#     to enter trades. It uses rolling maximum and minimum values over a lookback period
#     to determine breakout points.
#     """
    
#     def init(self):
#         """
#         Initialize the strategy by defining indicators used for trading signals.
#         """
#         # Calculate rolling max of the high and min of the low over the lookback period
#         self.highs = self.I(lambda x: pd.Series(x).rolling(self.lookback).max(), self.data.High)
#         self.lows = self.I(lambda x: pd.Series(x).rolling(self.lookback).min(), self.data.Low)

#     def next(self):
#         """
#         Define the trading logic for each time step in the backtest.
#         """
#         # A breakout occurs if the closing price exceeds the highest high of the *previous* N bars
#         if self.data.Close[-1] > self.highs[-2]:
#             self.position.close()  # Close any short position
#             self.buy()
#         # A breakdown occurs if the closing price falls below the lowest low of the *previous* N bars
#         elif self.data.Close[-1] < self.lows[-2]:
#             self.position.close()  # Close any long position
#             self.sell()


# def run(ticker: str, start_date: str, end_date: str, market: str = "US", initial_capital=100000, **kwargs) -> dict:
#     """
#     Main orchestrator function for the Breakout strategy.
    
#     Args:
#         ticker (str): The stock ticker symbol to analyze
#         start_date (str): Start date in 'YYYY-MM-DD' format
#         end_date (str): End date in 'YYYY-MM-DD' format
#         market (str): Market identifier for currency and data formatting (default: "US")
#         initial_capital (float): Initial capital for the backtest (default: 100,000)
#         **kwargs: Additional keyword arguments (e.g., 'lookback' for lookback period)
        
#     Returns:
#         dict: Dictionary containing backtest summary, data, and trades
#     """
    
#     lookback_period = kwargs.get('lookback', 20)

#     # Set the lookback period for the strategy class
#     Breakout.lookback = lookback_period

#     # --- CORRECT: Call the centralized get_data function with the market ---
#     hist_df = get_data(ticker, start_date, end_date, market=market)
#     if hist_df.empty:
#         return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

#     # CORRECT CODE:
#     bt = Backtest(hist_df, Breakout, cash=initial_capital, commission=.002, finalize_trades=True)  # <-- CORRECT PLACE
#     stats = bt.run()

#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     # --- Prepare detailed data for professional plotting ---
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
#     plot_df['Breakout_High'] = plot_df['High'].rolling(lookback_period).max().shift(1)  # Shift for correct plotting
#     plot_df['Breakout_Low'] = plot_df['Low'].rolling(lookback_period).min().shift(1)   # Shift for correct plotting
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}


# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Breakout Strategy", layout="wide")
#     st.title("📈 Breakout Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "NVDA")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
#         market = st.selectbox("Market", ["US", "INDIA", "EUROPE", "UK", "JAPAN"], index=0)
        
#         st.header("Strategy Parameters")
#         lookback = st.slider("Lookback Period (days)", 10, 100, 20)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker,
#                 start_date=start_date,
#                 end_date=end_date,
#                 market=market,
#                 lookback=lookback
#             )
#             summary = results.get("summary", {})
#             backtest_df = results.get("data", pd.DataFrame())
#             trades_df = results.get("trades", pd.DataFrame())

#         if "Error" in summary:
#             st.error(summary["Error"])
#         elif not backtest_df.empty:
#             st.subheader("Performance Summary")
#             cols = st.columns(4)
#             cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#             cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#             cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#             cols[3].metric("Trades", summary.get('Number of Trades', 0))

#             # --- Professional Charting ---
#             st.subheader("Price Chart with Breakout Levels, Trades & Equity")
#             fig = go.Figure()

#             # Price, Breakout Levels, and Equity Curve
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Breakout_High'], name='Breakout High', line=dict(color='lightcoral', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Breakout_Low'], name='Breakout Low', line=dict(color='lightgreen', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
            
#             # Trade Markers
#             if not trades_df.empty:
#                 buy_signals = trades_df[trades_df['Size'] > 0]
#                 sell_signals = trades_df[trades_df['Size'] < 0]
#                 fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')))
#                 fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

#             fig.update_layout(
#                 title_text=f"{ticker} Breakout Strategy Backtest",
#                 xaxis_rangeslider_visible=False,
#                 yaxis=dict(title=f"Price ({get_market_config(market)['currency_symbol']})"),
#                 yaxis2=dict(title=f"Equity ({get_market_config(market)['currency_symbol']})", overlaying='y', side='right', showgrid=False)
#             )
#             st.plotly_chart(fig, use_container_width=True)