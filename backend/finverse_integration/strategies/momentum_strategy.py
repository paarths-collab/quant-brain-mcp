import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data

class Momentum(Strategy):
    """
    Momentum Strategy implementation for backtesting.py library.
    
    This strategy buys when the momentum (price change over lookback period) is positive
    and sells when the momentum turns negative.
    """
    
    def init(self):
        # Calculate the n-day return series.
        self.returns = self.I(lambda x, n: pd.Series(x).pct_change(n), self.data.Close, self.lookback_period)

    def next(self):
        # Buy if the momentum is positive (price has increased over the lookback period)
        if not self.position and self.returns[-1] > 0:
            self.buy()
        # Sell if the momentum turns negative
        elif self.position and self.returns[-1] < 0:
            self.position.close()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
    """ Main orchestrator function for the Momentum strategy. """
    
    # Get strategy-specific parameters from kwargs
    lookback_period = kwargs.get("lookback", 20)
    
    # Set the lookback period for the strategy class
    Momentum.lookback_period = lookback_period

    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty:
        return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}
            
    bt = Backtest(hist_df, Momentum, cash=initial_capital, commission=.002, finalize_trades=True)
    stats = bt.run()
    
    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }

    # Standardize the output DataFrame
    plot_df = pd.DataFrame({'Equity_Curve': stats._equity_curve['Equity']})
    
    return {"summary": summary, "data": plot_df}

# --- Streamlit Visualization for Standalone Testing ---
