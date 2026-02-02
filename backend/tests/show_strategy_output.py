
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.data_loader import get_ohlcv
from backend.services.strategies.strategy_adapter import get_strategy

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def show_output(ticker="AAPL", market="US"):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=200)).strftime('%Y-%m-%d')
    
    # Fetch Data
    df = get_ohlcv(ticker, start_date, end_date, market)
    
    # Run Strategy
    strategy = get_strategy("sma_crossover") # Example strategy
    result_df = strategy.generate_signals(df)
    
    print(f"--- Output DataFrame for SMA Crossover ({ticker}) ---")
    print("\nColumns:", result_df.columns.tolist())
    print("\nLast 5 Rows:\n")
    print(result_df.tail(5))
    
    # Check for a signal
    signals = result_df[result_df['signal'] != 0]
    if not signals.empty:
        print("\nRecent Signals:\n")
        print(signals.tail(3))
    else:
        print("\nNo recent signals found in the last 200 days.")

if __name__ == "__main__":
    show_output()
