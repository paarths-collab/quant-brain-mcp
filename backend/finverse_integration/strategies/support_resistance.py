import yfinance as yf
import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy

# @st.cache_data 
def get_data(ticker, start, end, market):
    """ Standardized data fetching function. """
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    
    # Handle multi-level columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
    }, inplace=True, errors='ignore')
    
    # Safely convert column names to title case, handling potential tuples
    try:
        df.columns = [col[0].title() if isinstance(col, tuple) else col.title() for col in df.columns]
    except:
        df.columns = [str(col).title() for col in df.columns]
        
    # Ensure we have the required columns
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    available_cols = [col for col in required_cols if col in df.columns]
    if len(available_cols) >= len(required_cols) - 1:  # Allow for missing volume
        return df[available_cols]
    else:
        return pd.DataFrame()  # Return empty if missing critical columns

class SupportResistance(Strategy):
    """
    Support/Resistance Strategy implementation for backtesting.py library.
    
    This strategy buys when the price is near support levels (within tolerance)
    and sells when the price is near resistance levels (within tolerance).
    """
    finalize_trades = True
    
    def init(self):
        # Use rolling min/max of Low/High to define support/resistance bands
        self.support = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low, self.lookback_period)
        self.resistance = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).max(), self.data.High, self.lookback_period)

    def next(self):
        # Buy if price is near support (within tolerance)
        if not self.position and self.data.Close[-1] <= self.support[-1] * (1 + self.tolerance_pct):
            self.buy()
        # Sell if price is near resistance (within tolerance)
        elif self.position and self.data.Close[-1] >= self.resistance[-1] * (1 - self.tolerance_pct):
            self.position.close()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
    """ Main orchestrator function for the Support/Resistance strategy. """
    
    lookback_period = kwargs.get('lookback', 30)
    tolerance_percentage = kwargs.get('tolerance_pct', 0.01)

    # Set the parameters for the strategy class
    SupportResistance.lookback_period = lookback_period
    SupportResistance.tolerance_pct = tolerance_percentage

    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty: 
        return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
    bt = Backtest(hist_df, SupportResistance, cash=initial_capital, commission=.002)
    stats = bt.run(finalize_trades=True)
    
    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    
    # --- Prepare detailed data for professional plotting ---
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    plot_df['Support'] = plot_df['Low'].rolling(lookback_period).min()
    plot_df['Resistance'] = plot_df['High'].rolling(lookback_period).max()
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
