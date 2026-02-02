from backend.services.backtest_service import run_backtest_service
import json

def test_backtest():
    print("Testing Backtest Engine...")
    
    # Test EMA Crossover
    result = run_backtest_service(
        symbol="AAPL",
        strategy_name="ema_crossover",
        range_period="6mo",
        fast=10,
        slow=20
    )
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Success! Backtest complete for {result['symbol']} using {result['strategy']}.")
        print("Metrics:", json.dumps(result['metrics'], indent=2))
        print(f"Total Data Points: {len(result['chartData'])}")
        print(f"Total Trades: {len(result['trades'])}")
        if result['chartData']:
            print("Latest Equity:", result['chartData'][-1]['equity'])

if __name__ == "__main__":
    test_backtest()
