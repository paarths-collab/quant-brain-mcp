# services/strategies/support_resistance.py

import pandas as pd
from .base import Strategy


class SupportResistanceStrategy(Strategy):
    """
    Support / Resistance Bounce Strategy

    Long Entry:
    - Price is within tolerance of rolling support

    Exit:
    - Price is within tolerance of rolling resistance
    """

    name = "Support / Resistance"

    def __init__(
        self,
        lookback: int = 30,
        tolerance_pct: float = 0.01,
    ):
        self.lookback = lookback
        self.tolerance_pct = tolerance_pct

    def parameters(self) -> dict:
        return {
            "lookback": self.lookback,
            "tolerance_pct": self.tolerance_pct,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- Support & Resistance levels ---
        df["support"] = df["Low"].rolling(self.lookback).min()
        df["resistance"] = df["High"].rolling(self.lookback).max()

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Entry: bounce from support ---
        near_support = (
            df["Close"] <= df["support"] * (1 + self.tolerance_pct)
        )

        # --- Exit: near resistance ---
        near_resistance = (
            df["Close"] >= df["resistance"] * (1 - self.tolerance_pct)
        )

        # Entry
        df.loc[near_support, "signal"] = 1
        df.loc[near_support, "entry_long"] = df["Close"]

        # Exit (flat)
        df.loc[near_resistance, "signal"] = 0

        return df


# import yfinance as yf
# import pandas as pd
# import streamlit as st
# import plotly.graph_objects as go
# from backtesting import Backtest, Strategy

# @st.cache_data 
# def get_data(ticker, start, end, market):
#     """ Standardized data fetching function. """
#     df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
#     if df.empty: return pd.DataFrame()
    
#     # Handle multi-level columns from yfinance
#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)
    
#     df.rename(columns={
#         "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
#     }, inplace=True, errors='ignore')
    
#     # Safely convert column names to title case, handling potential tuples
#     try:
#         df.columns = [col[0].title() if isinstance(col, tuple) else col.title() for col in df.columns]
#     except:
#         df.columns = [str(col).title() for col in df.columns]
        
#     # Ensure we have the required columns
#     required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
#     available_cols = [col for col in required_cols if col in df.columns]
#     if len(available_cols) >= len(required_cols) - 1:  # Allow for missing volume
#         return df[available_cols]
#     else:
#         return pd.DataFrame()  # Return empty if missing critical columns

# class SupportResistance(Strategy):
#     """
#     Support/Resistance Strategy implementation for backtesting.py library.
    
#     This strategy buys when the price is near support levels (within tolerance)
#     and sells when the price is near resistance levels (within tolerance).
#     """
#     finalize_trades = True
    
#     def init(self):
#         # Use rolling min/max of Low/High to define support/resistance bands
#         self.support = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low, self.lookback_period)
#         self.resistance = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).max(), self.data.High, self.lookback_period)

#     def next(self):
#         # Buy if price is near support (within tolerance)
#         if not self.position and self.data.Close[-1] <= self.support[-1] * (1 + self.tolerance_pct):
#             self.buy()
#         # Sell if price is near resistance (within tolerance)
#         elif self.position and self.data.Close[-1] >= self.resistance[-1] * (1 - self.tolerance_pct):
#             self.position.close()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
#     """ Main orchestrator function for the Support/Resistance strategy. """
    
#     lookback_period = kwargs.get('lookback', 30)
#     tolerance_percentage = kwargs.get('tolerance_pct', 0.01)

#     # Set the parameters for the strategy class
#     SupportResistance.lookback_period = lookback_period
#     SupportResistance.tolerance_pct = tolerance_percentage

#     hist_df = get_data(ticker, start_date, end_date, market)
#     if hist_df.empty: 
#         return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
#     bt = Backtest(hist_df, SupportResistance, cash=initial_capital, commission=.002)
#     stats = bt.run(finalize_trades=True)
    
#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     # --- Prepare detailed data for professional plotting ---
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
#     plot_df['Support'] = plot_df['Low'].rolling(lookback_period).min()
#     plot_df['Resistance'] = plot_df['High'].rolling(lookback_period).max()
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Support/Resistance Strategy", layout="wide")
#     st.title("📈 Support/Resistance Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "COST")
#         start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
        
#         st.header("Strategy Parameters")
#         lookback = st.slider("Lookback for Pivots (days)", 10, 100, 30)
#         tolerance_pct = st.slider("Tolerance Band (%)", 0.1, 5.0, 1.0, 0.1) / 100.0
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker,
#                 start_date=start_date,
#                 end_date=end_date,
#                 market="USA",  # Default market for standalone testing
#                 lookback=lookback,
#                 tolerance_pct=tolerance_pct
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
#             st.subheader("Price Chart with Support/Resistance, Trades & Equity")
#             fig = go.Figure()

#             # Price, Support, Resistance, and Equity Curve
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Support'], name='Support Level', line=dict(color='lightgreen', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Resistance'], name='Resistance Level', line=dict(color='lightcoral', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
            
#             # Trade Markers
#             buy_signals = trades_df[trades_df['Size'] > 0]
#             sell_signals = trades_df[trades_df['Size'] < 0]
#             fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy at Support', marker=dict(color='lime', size=10, symbol='triangle-up')))
#             fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell at Resistance', marker=dict(color='red', size=10, symbol='triangle-down')))

#             fig.update_layout(
#                 title_text=f"{ticker} Support/Resistance Backtest",
#                 xaxis_rangeslider_visible=False,
#                 yaxis=dict(title="Price ($)"),
#                 yaxis2=dict(title="Equity ($)", overlaying='y', side='right', showgrid=False)
#             )
#             st.plotly_chart(fig, width='stretch')
# # import pandas as pd
# # from utils.data_loader import get_history
# # from backtesting import Backtest, Strategy
# # import streamlit as st
# # import plotly.graph_objects as go

# # class SupportResistance(Strategy):
# #     lookback = 30
# #     tolerance_pct = 0.01

# #     def init(self):
# #         self.support = self.I(lambda x, n: pd.Series(x).rolling(n).min(), self.data.Low, self.lookback)
# #         self.resistance = self.I(lambda x, n: pd.Series(x).rolling(n).max(), self.data.High, self.lookback)

# #     def next(self):
# #         if not self.position and self.data.Close[-1] <= self.support[-1] * (1 + self.tolerance_pct):
# #             self.buy()
# #         elif self.position and self.data.Close[-1] >= self.resistance[-1] * (1 - self.tolerance_pct):
# #             self.position.close()

# # def run(ticker, start_date, end_date, cash=10_000, commission=.002, **kwargs):
# #     hist_df = get_history(ticker, start_date, end_date)
# #     if hist_df.empty: return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
# #     if isinstance(hist_df.columns, pd.MultiIndex):
# #         hist_df.columns = hist_df.columns.get_level_values(0)
# #     hist_df.columns = [col.title() for col in hist_df.columns]

# #     SupportResistance.lookback = kwargs.get('lookback', 30)
    
# #     bt = Backtest(hist_df, SupportResistance, cash=cash, commission=commission)
# #     # --- FIX: Ensure final open trades are included in stats ---
# #     stats = bt.run(finalize_trades=True)
# #     # --- END OF FIX ---
    
# #     return {"summary": stats.to_dict(), "data": stats._equity_curve}

# # # ... (Streamlit UI remains unchanged) ...
# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="Support/Resistance Strategy", layout="wide")
# #     st.title("📈 Support/Resistance Bounce Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "COST")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         lookback = st.slider("Lookback for Pivots (days)", 10, 100, 30)
# #         run_button = st.button("🔬 Run Backtest", use_container_width=True)
# #     if run_button:
# #         # ... (Streamlit UI is similar to the other strategies)
# #         st.header(f"Results for {ticker}")
# #         results = run(ticker, str(start_date.date()), str(end_date.date()), lookback=lookback)
#         #...
# # import yfinance as yf
# # import pandas as pd
# # import numpy as np
# # import streamlit as st
# # import plotly.graph_objects as go
# # from scipy.signal import argrelextrema
# # from utils.data_loader import get_history
# # from backtesting import Backtest, Strategy
# # # --- Core Strategy & Backtesting Logic ---
# # def get_data(ticker, start, end, interval='1d'):
# #     df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
# #     if df.empty: return pd.DataFrame()
# #     return df[['Open', 'High', 'Low', 'Close', 'Volume']]

# # def generate_signals(df, lookback=30, tolerance_pct=0.01):
# #     df = df.copy()
# #     df['trade'] = 0
# #     for i in range(lookback, len(df)):
# #         window = df.iloc[i-lookback:i]
# #         lows_idx = argrelextrema(window['Low'].values, np.less_equal, order=3)[0]
# #         support = window.iloc[lows_idx]['Low'].min() if len(lows_idx) > 0 else window['Low'].min()
# #         price = df.iloc[i]['Close']
# #         tol = tolerance_pct * price
# #         if (price - support) <= tol and df.iloc[i]['Close'] > df.iloc[i]['Open']:
# #             df.iloc[i, df.columns.get_loc('trade')] = 1
# #     return df

# # def run_backtest(df, hold_days=7, init_cash=100000):
# #     df = df.copy().reset_index()
# #     cash, position, shares, entry_idx = init_cash, 0, 0, None
# #     trades = []
# #     df['equity'] = init_cash
# #     if df.empty: return pd.DataFrame(), []
# #     for i in range(len(df)-1):
# #         trade_signal = df.loc[i, 'trade']
# #         next_day_open = df.loc[i+1, 'Open']
# #         if trade_signal == 1 and position == 0:
# #             shares_to_buy = cash // next_day_open
# #             if shares_to_buy > 0:
# #                 cash -= shares_to_buy * next_day_open
# #                 position, shares, entry_idx = 1, shares_to_buy, i + 1
# #                 trades.append({'date': df.loc[i+1, 'Date'], 'type': 'BUY', 'price': next_day_open, 'shares': shares})
# #         if position == 1 and entry_idx is not None and (i + 1 - entry_idx) >= hold_days:
# #             cash += shares * next_day_open
# #             trades.append({'date': df.loc[i+1, 'Date'], 'type': 'SELL', 'price': next_day_open, 'shares': shares})
# #             shares, position, entry_idx = 0, 0, None
# #         df.loc[i, 'equity'] = cash + (shares * df.loc[i, 'Close'])
# #     df.loc[len(df)-1, 'equity'] = cash + (shares * df.loc[len(df)-1, 'Close'])
# #     return df.set_index('Date'), trades

# # def calculate_performance_metrics(backtest_df, trades_list, initial_capital):
# #     if backtest_df.empty or not trades_list: return {}
# #     final_equity = backtest_df['equity'].iloc[-1]
# #     total_return_pct = (final_equity / initial_capital - 1) * 100
# #     daily_returns = backtest_df['equity'].pct_change().dropna()
# #     sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
# #     peak = backtest_df['equity'].cummax()
# #     drawdown = (backtest_df['equity'] - peak) / peak
# #     max_drawdown_pct = drawdown.min() * 100
# #     trades_df = pd.DataFrame(trades_list)
# #     buy_prices = trades_df[trades_df['type'] == 'BUY']['price']
# #     sell_prices = trades_df[trades_df['type'] == 'SELL']['price']
# #     min_len = min(len(buy_prices), len(sell_prices))
# #     trade_returns = (sell_prices.values[:min_len] - buy_prices.values[:min_len]) / buy_prices.values[:min_len]
# #     win_rate = (trade_returns > 0).mean() * 100 if len(trade_returns) > 0 else 0
# #     return {
# #         "Total Return %": f"{total_return_pct:.2f}", "Sharpe Ratio": f"{sharpe_ratio:.2f}",
# #         "Max Drawdown %": f"{max_drawdown_pct:.2f}", "Win Rate %": f"{win_rate:.2f}",
# #         "Number of Trades": len(trades_list) // 2
# #     }
    
# # # --- Orchestrator/API Entry Point ---


# # def run(ticker, start_date, end_date, cash=10_000, commission=.002):
# #     class SupportResistance(Strategy):
# #         n1 = 20  # Window for finding support/resistance

# #         def init(self):
# #             # Define indicators in init() to ensure alignment
# #             self.support = self.I(lambda x, n: pd.Series(x).rolling(n).min(), self.data.Low, self.n1)
# #             self.resistance = self.I(lambda x, n: pd.Series(x).rolling(n).max(), self.data.High, self.n1)

# #         def next(self):
# #             # Buy near support
# #             if self.data.Close[-1] <= self.support[-1] * 1.01: # 1% threshold
# #                 self.buy()
# #             # Sell near resistance
# #             elif self.data.Close[-1] >= self.resistance[-1] * 0.99: # 1% threshold
# #                 self.sell()

# #     hist_df = get_history(ticker, start_date, end_date)
# #     if hist_df.empty: return {"error": "Could not fetch data."}
# #     bt = Backtest(hist_df, SupportResistance, cash=cash, commission=commission)
# #     stats = bt.run()
# #     return {"summary": stats.to_dict(), "plot": bt.plot(open_browser=False)}

# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="Support/Resistance Strategy", layout="wide")
# #     st.title("📈 Support/Resistance Bounce Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "COST")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         lookback = st.slider("Lookback for Pivots (days)", 10, 100, 30)
# #         hold_days = st.slider("Holding Period (days)", 3, 30, 7)
# #         run_button = st.button("🔬 Run Backtest", use_container_width=True)
# #     if run_button:
# #         st.header(f"Results for {ticker}")
# #         with st.spinner("Running backtest..."):
# #             results = run(ticker, str(start_date), str(end_date), lookback=lookback, hold_days=hold_days)
# #             summary = results.get("summary", {})
# #             backtest_df = results.get("data", pd.DataFrame())
# #             trades_list = results.get("trades", [])
# #             if "Error" in summary:
# #                 st.error(summary["Error"])
# #             else:
# #                 st.subheader("Performance Summary")
# #                 cols = st.columns(5)
# #                 cols[0].metric("Total Return", f"{summary.get('Total Return %', 0)}%")
# #                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', 0))
# #                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', 0)}%")
# #                 cols[3].metric("Win Rate", f"{summary.get('Win Rate %', 0)}%")
# #                 cols[4].metric("Trades", summary.get('Number of Trades', 0))
# #                 st.subheader("Price Chart with Signals & Equity Curve")
# #                 fig = go.Figure()
# #                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
# #                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['equity'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
# #                 trades_df = pd.DataFrame(trades_list)
# #                 if not trades_df.empty:
# #                     buy_signals = trades_df[trades_df['type'] == 'BUY']
# #                     sell_signals = trades_df[trades_df['type'] == 'SELL']
# #                     fig.add_trace(go.Scatter(x=buy_signals['date'], y=buy_signals['price'], mode='markers', name='Buy Signal', marker=dict(color='green', size=10, symbol='triangle-up')))
# #                     fig.add_trace(go.Scatter(x=sell_signals['date'], y=sell_signals['price'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))
# #                 fig.update_layout(title_text=f"{ticker} Backtest: Support/Resistance", xaxis_rangeslider_visible=False, yaxis=dict(title="Price ($)"), yaxis2=dict(title="Equity ($)", overlaying='y', side='right'))
# #                 st.plotly_chart(fig, use_container_width=True)