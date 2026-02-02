
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.data_loader import get_ohlcv
from backend.services.strategies.strategy_adapter import STRATEGY_REGISTRY, get_strategy

def test_with_real_data(ticker="AAPL", market="US"):
    print(f"\n--- Testing Strategies with Real Data for {ticker} ({market}) ---")
    
    # 1. Fetch real data
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        df = get_ohlcv(ticker, start_date, end_date, market)
        print(f"Successfully fetched {len(df)} rows of data.")
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    # 2. Run all strategies
    results = []
    
    for strategy_name in STRATEGY_REGISTRY:
        # Skip pairs trading as it needs special data
        if strategy_name == "pairs_trading":
            continue
            
        try:
            strategy = get_strategy(strategy_name)
            signals = strategy.generate_signals(df)
            
            # Count signals
            buy_signals = (signals["signal"] == 1).sum()
            sell_signals = (signals["signal"] == -1).sum()
            
            results.append({
                "Strategy": strategy_name,
                "Status": "✅ Success",
                "Buy Signals": buy_signals,
                "Sell Signals": sell_signals
            })
            
        except Exception as e:
            results.append({
                "Strategy": strategy_name,
                "Status": f"❌ Failed: {str(e)}",
                "Buy Signals": 0,
                "Sell Signals": 0
            })

    # 3. Print Summary
    summary_df = pd.DataFrame(results)
    print("\n" + summary_df.to_string(index=False))

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    test_with_real_data(ticker)
