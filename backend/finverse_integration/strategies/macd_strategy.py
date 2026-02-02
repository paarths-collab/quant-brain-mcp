import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import ta # Make sure you have the 'ta' library installed (pip install ta)

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data
from ..utils.market_utils import get_market_config

class MacdCross(Strategy):
    """
    MACD Crossover Strategy implementation for backtesting.py library.
    
    This strategy generates buy signals when the MACD line crosses above the signal line
    and sell signals when the MACD line crosses below the signal line.
    """
    
    def init(self):
        close = pd.Series(self.data.Close)
        self.macd_line = self.I(ta.trend.macd, close, window_fast=self.fast_ema, window_slow=self.slow_ema)
        self.macd_signal_line = self.I(ta.trend.macd_signal, close, window_fast=self.fast_ema, window_slow=self.slow_ema, window_sign=self.signal_ema)

    def next(self):
        if crossover(self.macd_line, self.macd_signal_line):
            self.position.close()
            self.buy()
        elif crossover(self.macd_signal_line, self.macd_line):
            self.position.close()
            self.sell()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market: str = "US", initial_capital=100000, **kwargs):
    """ Main orchestrator function for the MACD Crossover strategy. """
    
    # Get strategy-specific parameters from kwargs
    fast_period = kwargs.get('fast', 12)
    slow_period = kwargs.get('slow', 26)
    signal_period = kwargs.get('signal', 9)
    
    # Set the parameters for the strategy class
    MacdCross.fast_ema = fast_period
    MacdCross.slow_ema = slow_period
    MacdCross.signal_ema = signal_period

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
    
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    
    return {"summary": summary, "data": plot_df}

# --- Streamlit UI for Standalone Testing ---
# This part only runs when you execute this script directly
