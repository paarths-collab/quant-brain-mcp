# File: strategies/ema_crossover.py

import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data

class EmaCross(Strategy):
    """
    EMA Crossover Strategy implementation for backtesting.py library.
    
    This strategy generates buy signals when the fast EMA crosses above the slow EMA
    and sell signals when the fast EMA crosses below the slow EMA.
    """
    
    def init(self):
        self.ema1 = self.I(lambda x, n: pd.Series(x).ewm(span=n, adjust=False).mean(), self.data.Close, self.fast_ema_period)
        self.ema2 = self.I(lambda x, n: pd.Series(x).ewm(span=n, adjust=False).mean(), self.data.Close, self.slow_ema_period)

    def next(self):
        if crossover(self.ema1, self.ema2):
            self.buy()
        elif crossover(self.ema2, self.ema1):
            self.sell()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
    """ Main orchestrator function for the EMA Crossover strategy. """
    
    fast_period = kwargs.get('fast', 20)
    slow_period = kwargs.get('slow', 50)
    
    # Set the parameters for the strategy class
    EmaCross.fast_ema_period = fast_period
    EmaCross.slow_ema_period = slow_period # type: ignore

    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty:
        return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
    bt = Backtest(hist_df, EmaCross, cash=initial_capital, commission=.002, finalize_trades=True)
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
    plot_df['EMA_Fast'] = plot_df['Close'].ewm(span=fast_period, adjust=False).mean()
    plot_df['EMA_Slow'] = plot_df['Close'].ewm(span=slow_period, adjust=False).mean()
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit UI for Standalone Testing ---
