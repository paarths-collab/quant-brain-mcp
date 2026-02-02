# core/strategies/fibonacci_pullback.py

import pandas as pd
from .base import Strategy


class FibonacciPullbackStrategy(Strategy):
    """
    Fibonacci Pullback Strategy (Trend Continuation)

    Long Entry:
    - Price pulls back to ~38.2% of recent swing
    - Current candle closes higher than previous (bullish confirmation)

    Exit:
    - Price breaks above recent swing high
    """

    name = "Fibonacci Pullback"

    def __init__(self, lookback: int = 50):
        self.lookback = lookback

    def parameters(self) -> dict:
        return {
            "lookback": self.lookback
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- Swing points ---
        df["swing_high"] = df["High"].rolling(self.lookback).max()
        df["swing_low"] = df["Low"].rolling(self.lookback).min()

        # --- Fibonacci levels ---
        swing_range = df["swing_high"] - df["swing_low"]

        df["fib_38_2"] = df["swing_high"] - 0.382 * swing_range
        df["fib_50_0"] = df["swing_high"] - 0.500 * swing_range
        df["fib_61_8"] = df["swing_high"] - 0.618 * swing_range

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Entry condition ---
        pullback_zone = df["Close"] < df["fib_38_2"]
        bullish_confirmation = df["Close"] > df["Close"].shift(1)

        long_entry = pullback_zone & bullish_confirmation

        # --- Exit condition ---
        exit_long = df["Close"] > df["swing_high"]

        df.loc[long_entry, "signal"] = 1
        df.loc[long_entry, "entry_long"] = df["Close"]

        # Flat / exit handled by backtesting engine
        df.loc[exit_long, "signal"] = 0

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

# class FibonacciPullback(Strategy):
#     """
#     Fibonacci Pullback Strategy implementation for backtesting.py library.
    
#     This strategy looks for pullbacks to Fibonacci levels (specifically 38.2%) after an uptrend
#     and enters long positions when price starts moving up again at these levels.
#     """
#     finalize_trades = True
    
#     def init(self):
#         self.highest_high = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).max(), self.data.High, self.lookback_period)
#         self.lowest_low = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low, self.lookback_period)

#     def next(self):
#         swing_range = self.highest_high[-1] - self.lowest_low[-1]
#         if swing_range > 0:
#             # Buy on a pullback to the 38.2% level if price starts moving up
#             fib_level_38 = self.highest_high[-1] - 0.382 * swing_range
#             if not self.position and self.data.Close[-1] < fib_level_38 and self.data.Close[-1] > self.data.Close[-2]:
#                 self.buy()
#             # Exit if the price breaks the recent swing high
#             elif self.position and self.data.Close[-1] > self.highest_high[-1]:
#                 self.position.close()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
#     """ Main orchestrator function for the Fibonacci Pullback strategy. """
    
#     lookback_period = kwargs.get('lookback', 50)
    
#     # Set the parameters for the strategy class
#     FibonacciPullback.lookback_period = lookback_period

#     hist_df = get_data(ticker, start_date, end_date, market)
#     if hist_df.empty: 
#         return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
#     bt = Backtest(hist_df, FibonacciPullback, cash=initial_capital, commission=.002)
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
    
#     # Recalculate indicators for plotting
#     plot_df['Swing_High'] = plot_df['High'].rolling(lookback_period).max()
#     plot_df['Swing_Low'] = plot_df['Low'].rolling(lookback_period).min()
#     swing_range = plot_df['Swing_High'] - plot_df['Swing_Low']
#     plot_df['Fib_38.2%'] = plot_df['Swing_High'] - 0.382 * swing_range
#     plot_df['Fib_50.0%'] = plot_df['Swing_High'] - 0.500 * swing_range
#     plot_df['Fib_61.8%'] = plot_df['Swing_High'] - 0.618 * swing_range
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Fibonacci Pullback Strategy", layout="wide")
#     st.title("📈 Fibonacci Pullback Strategy (Standalone)")
    
#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "NVDA")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
        
#         st.header("Strategy Parameters")
#         lookback = st.slider("Lookback for Swings (days)", 20, 200, 50)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)
        
#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker, 
#                 start_date=start_date, 
#                 end_date=end_date, 
#                 market="USA",  # Default market for standalone testing
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
#             st.subheader("Price Chart with Fibonacci Levels, Trades & Equity")
#             fig = go.Figure()

#             # Price and Equity Curve
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
            
#             # Fibonacci Levels
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Swing_High'], name='Swing High', line=dict(color='grey', dash='dot')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Swing_Low'], name='Swing Low', line=dict(color='grey', dash='dot')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Fib_38.2%'], name='Fib 38.2%', line=dict(color='rgba(255, 165, 0, 0.5)', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Fib_50.0%'], name='Fib 50.0%', line=dict(color='rgba(255, 165, 0, 0.5)', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Fib_61.8%'], name='Fib 61.8%', line=dict(color='rgba(255, 165,0, 0.5)', dash='dash')))

#             # Trade Markers
#             buy_signals = trades_df[trades_df['Size'] > 0]
#             sell_signals = trades_df[trades_df['Size'] < 0]
#             fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')))
#             fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

#             fig.update_layout(
#                 title_text=f"{ticker} Fibonacci Pullback Backtest",
#                 xaxis_rangeslider_visible=False,
#                 yaxis=dict(title="Price ($)"),
#                 yaxis2=dict(title="Equity ($)", overlaying='y', side='right', showgrid=False)
#             )
#             st.plotly_chart(fig, use_container_width=True)
# # import pandas as pd

# # from utils.data_loader import get_history
# # from backtesting import Backtest, Strategy
# # import streamlit as st
# # import plotly.graph_objects as go

# # class FibonacciPullback(Strategy):
# #     lookback_period = 50

# #     def init(self):
# #         self.highest_high = self.I(lambda x, n: pd.Series(x).rolling(n).max(), self.data.High, self.lookback_period)
# #         self.lowest_low = self.I(lambda x, n: pd.Series(x).rolling(n).min(), self.data.Low, self.lookback_period)

# #     def next(self):
# #         swing_range = self.highest_high[-1] - self.lowest_low[-1]
# #         if swing_range > 0:
# #             fib_level_38 = self.highest_high[-1] - 0.382 * swing_range
# #             if self.data.Close[-1] < fib_level_38 and self.data.Close[-1] > self.data.Close[-2]:
# #                 self.buy()
# #             elif self.position and self.data.Close[-1] > self.highest_high[-1]:
# #                 self.position.close()

# # def run(ticker, start_date, end_date, cash=10_000, commission=.002, **kwargs):
# #     hist_df = get_history(ticker, start_date, end_date)
# #     if hist_df.empty: return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
# #     if isinstance(hist_df.columns, pd.MultiIndex):
# #         hist_df.columns = hist_df.columns.get_level_values(0)
# #     hist_df.columns = [col.title() for col in hist_df.columns]

# #     FibonacciPullback.lookback_period = kwargs.get('lookback', 50)
    
# #     bt = Backtest(hist_df, FibonacciPullback, cash=cash, commission=commission)
# #     # --- FIX: Ensure final open trades are included in stats ---
# #     stats = bt.run(finalize_trades=True)
# #     # --- END OF FIX ---
    
# #     return {"summary": stats.to_dict(), "data": stats._equity_curve}

# # # ... (Streamlit UI remains unchanged) ...

# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="Fibonacci Pullback Strategy", layout="wide")
# #     st.title("📈 Fibonacci Pullback Strategy Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "NVDA")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         lookback = st.slider("Lookback for Swings (days)", 20, 200, 50)
# #         run_button = st.button("🔬 Run Backtest", use_container_width=True)
# #     if run_button:
# #         st.header(f"Results for {ticker}")
# #         with st.spinner("Running backtest..."):
# #             results = run(ticker, str(start_date.date()), str(end_date.date()), lookback=lookback)
# #             summary = results.get("summary", {})
# #             equity_curve = results.get("data", pd.DataFrame())
# #             if "Error" in summary:
# #                 st.error(summary["Error"])
# #             elif not equity_curve.empty:
# #                 st.subheader("Performance Summary")
# #                 cols = st.columns(4)
# #                 cols[0].metric("Return [%]", f"{summary.get('Return [%]', 0):.2f}")
# #                 # ... (rest of the Streamlit UI is the same)
# #                 st.subheader("Equity Curve")
# #                 fig = go.Figure(go.Scatter(x=equity_curve.index, y=equity_curve['Equity']))
# #                 st.plotly_chart(fig, use_container_width=True)
# # import yfinance as yf
# # import pandas as pd
# # import numpy as np
# # import streamlit as st
# # import plotly.graph_objects as go
# # from utils.data_loader import get_history
# # from backtesting import Backtest, Strategy

# # # --- Core Strategy & Backtesting Logic ---
# # def get_data(ticker, start, end, interval='1d'):
# #     df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
# #     if df.empty: return pd.DataFrame()
# #     return df[['Open', 'High', 'Low', 'Close', 'Volume']]

# # def generate_signals(df, lookback=50):
# #     df = df.copy()
# #     df['trade'] = 0
# #     levels = [0.382, 0.5, 0.618]
# #     for i in range(lookback, len(df)):
# #         window_df = df.iloc[i-lookback:i]
# #         low, high = window_df['Low'].min(), window_df['High'].max()
# #         move = high - low
# #         if move <= 0: continue
# #         price = df.iloc[i]['Close']
# #         tol = 0.005 * price
# #         for lvl in levels:
# #             fib_level_price = high - lvl * move
# #             if abs(price - fib_level_price) <= tol:
# #                 df.iloc[i, df.columns.get_loc('trade')] = 1
# #                 break
# #     return df

# # def run_backtest(df, hold_days=10, init_cash=100000):
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
# #     class FibonacciPullback(Strategy):
# #         lookback_period = 50

# #         def init(self):
# #             # Indicators defined in init
# #             self.highest_high = self.I(lambda x, n: pd.Series(x).rolling(n).max(), self.data.High, self.lookback_period)
# #             self.lowest_low = self.I(lambda x, n: pd.Series(x).rolling(n).min(), self.data.Low, self.lookback_period)

# #         def next(self):
# #             if self.highest_high[-1] > self.lowest_low[-1]:
# #                 fib_level_38 = self.highest_high[-1] - 0.382 * (self.highest_high[-1] - self.lowest_low[-1])
# #                 if self.data.Close[-1] < fib_level_38 and self.data.Close[-1] > self.data.Close[-2]:
# #                     self.buy()
# #                 elif self.position and self.data.Close[-1] > self.highest_high[-1]:
# #                     self.position.close()

# #     hist_df = get_history(ticker, start_date, end_date)
# #     if hist_df.empty: return {"error": "Could not fetch data."}
# #     bt = Backtest(hist_df, FibonacciPullback, cash=cash, commission=commission)
# #     stats = bt.run()
# #     return {"summary": stats.to_dict(), "plot": bt.plot(open_browser=False)}
    
# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="Fibonacci Pullback Strategy", layout="wide")
# #     st.title("📈 Fibonacci Pullback Strategy Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "NVDA")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         lookback = st.slider("Lookback Period for Swings (days)", 20, 200, 50)
# #         hold_days = st.slider("Holding Period (days)", 3, 30, 10)
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
# #                 fig.update_layout(title_text=f"{ticker} Backtest: Fibonacci Pullback", xaxis_rangeslider_visible=False, yaxis=dict(title="Price ($)"), yaxis2=dict(title="Equity ($)", overlaying='y', side='right'))
# #                 st.plotly_chart(fig, use_container_width=True)