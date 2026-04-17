import asyncio
from main import generate_optimized_verdict


async def run_test():
    print("Starting Live Tool-Path Test...")
    try:
        result = generate_optimized_verdict(tickers=["AAPL", "RELIANCE.NS"], amount=10000)

        print("\n--- TEST RESULTS ---")
        print(f"Final Verdict: {result['final_verdict']}")
        print(f"Weights: {result['weights']}")
        print(f"Portfolio Return: {result['performance_metrics']['portfolio_total_return']}")
        print(f"Reasoning: {result['reasoning']}")
        print("--------------------\n")
        print("SUCCESS: The Nervous System is fully operational.")

    except Exception as e:
        print(f"CRITICAL FAILURE: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import pandas as pd
    import inspect

    pd.set_option("display.max_columns", None)

    if inspect.iscoroutinefunction(generate_optimized_verdict):
        asyncio.run(run_test())
    else:
        res = generate_optimized_verdict(tickers=["AAPL", "RELIANCE.NS"], amount=10000)
        print(res)
