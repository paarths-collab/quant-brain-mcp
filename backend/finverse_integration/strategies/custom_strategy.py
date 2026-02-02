import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import ta

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data
from ..utils.market_utils import get_market_config

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market: str = "US", initial_capital=100000, **kwargs):
    """ Main orchestrator function for the MACD Crossover strategy. """
    
    fast_period = kwargs.get('fast', 12)
    slow_period = kwargs.get('slow', 26)
    signal_period = kwargs.get('signal', 9)
    
    class MacdCross(Strategy):
        fast = fast_period
        slow = slow_period
        signal = signal_period

        def init(self):
            close = pd.Series(self.data.Close)
            self.macd_line = self.I(ta.trend.macd, close, window_fast=self.fast, window_slow=self.slow)
            self.macd_signal_line = self.I(ta.trend.macd_signal, close, window_fast=self.fast, window_slow=self.slow, window_sign=self.signal)

        def next(self):
            if crossover(self.macd_line, self.macd_signal_line):
                self.position.close()
                self.buy()
            elif crossover(self.macd_signal_line, self.macd_line):
                self.position.close()
                self.sell()

    # --- CORRECT: Call the centralized get_data function with the market ---
    hist_df = get_data(ticker, start_date, end_date, market=market)
    if hist_df.empty:
        return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
    bt = Backtest(hist_df, MacdCross, cash=initial_capital, commission=.002, finalize_trades=True)
    stats = bt.run()

    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    
    # --- Prepare detailed data for professional plotting ---
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    plot_df['MACD_Line'] = ta.trend.macd(plot_df['Close'], window_fast=fast_period, window_slow=slow_period)
    plot_df['MACD_Signal'] = ta.trend.macd_signal(plot_df['Close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
    plot_df['MACD_Hist'] = ta.trend.macd_diff(plot_df['Close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
