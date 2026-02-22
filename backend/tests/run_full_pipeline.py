import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.backend1.orchestrator.theme_router import ThemeRouter

async def test_full_pipeline():
    print("=== QUANT RESEARCH TERMINAL: FULL PIPELINE TEST ===")
    router = ThemeRouter()
    
    # query that targets India + Short Term mapping
    user_query = "Suggest some Indian banking stocks for short term investment"
    risk_profile = "moderate"
    
    print(f"\n[QUERY] '{user_query}' | Risk: {risk_profile}")
    
    try:
        # Run the full pipeline
        # analyze_limit=2 for speed
        # strategy_limit=1 for speed
        result = await router.route(
            user_query, 
            risk_profile=risk_profile,
            analyze_limit=2,
            strategy_limit=1
        )
        
        if "error" in result:
            print(f"[REJECTED] Error during execution: {result['error']}")
            return

        print("\nPIPELINE EXECUTION SUMMARY")
        print(f"Detected Region: {result.get('features', {}).get('region')}")
        print(f"Detected Horizon: {result.get('features', {}).get('horizon')}")
        print(f"Top Pick: {result.get('top_pick')}")
        
        # Verify News Agent Success
        ranked = result.get("ranked", [])
        if ranked:
            best_stock = ranked[0]
            news_data = best_stock.get("news", {})
            sentiment = news_data.get("score")
            print(f"News Sentiment Score for {best_stock['ticker']}: {sentiment}")
            if sentiment != 5.0 or news_data.get("reasons"):
                print("   -> News Agent successfully retrieved and analyzed data.")
            else:
                print("   -> News Agent returned fallback/neutral values. Verify GNews connectivity.")

        # Verify Backtesting
        strategy = result.get("strategy_analysis", {})
        if strategy:
            print(f"Strategy Engine triggered for {len(strategy)} stocks.")
            for ticker, res in strategy.items():
                periods = list(res.keys())
                print(f"   -> {ticker} analysis periods: {periods}")
        else:
            print("   -> Strategy analysis not found in result.")

        print("\nSYSTEM REASONING:")
        print(result.get("explanation")[:500] + "...")
        
    except Exception as e:
        print(f"Pipeline Crash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
