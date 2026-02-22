import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.engine.pipeline import InvestmentPipeline

# Mock portfolio
PORTFOLIO_MOCK = {
    "cash": 100000.0,
    "holdings": {
        "AAPL": 10,
        "MSFT": 5
    }
}

async def run_manual_test():
    print("Initializing Pipeline...")
    pipeline = InvestmentPipeline()

    print("\n--- TEST 1: NVDA (Bullish) ---")
    try:
        result = await pipeline.run(
            query="Analyze NVDA and tell me if I should buy.",
            ticker="NVDA",
            portfolio=PORTFOLIO_MOCK
        )
        print(f"Ticker: {result['financial']['ticker']}")
        print(f"Best Strategy: {result['strategy'].get('best_strategy', {}).get('strategy', 'N/A')}")
        print(f"Action: {result['trade_execution'].get('action', 'N/A')}")
        print(f"Risk VaR: {result['risk_engine'].get('VaR', 'N/A')}")
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- TEST 2: Optimization ---")
    try:
        result_opt = await pipeline.run(
            query="Optimize my portfolio",
            ticker="TSLA", # Adding TSLA
            portfolio=PORTFOLIO_MOCK
        )
        opt = result_opt.get("portfolio_optimization", {})
        print(f"Optimal Weights: {opt.get('optimal_weights', 'N/A')}")
        print(f"Sharpe: {opt.get('expected_sharpe', 'N/A')}")
    except Exception as e:
        print(f"❌ Test 2 Failed: {e}")
    
    print("\n--- TEST 3: RL Learning ---")
    try:
        rl_data = result_opt.get("rl_strategy", {})
        print(f"Chosen Strategy: {rl_data.get('chosen', 'N/A')}")
        print(f"Q-Table len: {len(rl_data.get('q_table', {}))}")
    except Exception as e:
         print(f"❌ Test 3 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_manual_test())
