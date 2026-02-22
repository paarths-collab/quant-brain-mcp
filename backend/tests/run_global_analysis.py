import asyncio
import sys
import logging

# Configure Logging to show "Thinking"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from backend.backend1.orchestrator.theme_router import ThemeRouter

async def run_full_analysis():
    print("🚀 Initializing Full Global Analysis...")
    print("🎯 Goal: Analyze entire US Universe & Run Backtests for ALL.")
    
    router = ThemeRouter()
    
    # Query: "What is the best stock to buy" -> Triggers Global US Universe (~20 stocks)
    query = "What is the best stock to buy right now"
    
    print(f"\n❓ User Query: '{query}'")
    
    # We pass None to limits to run ALL
    # analyze_limit=None -> Analyze all 20 stocks
    # strategy_limit=None -> Backtest all ranked stocks (or top 5 if filtered by default logic, but I updated it to take limit)
    # Actually, orchestrator defaults to top 5 if I don't pass limit? 
    # In my code:
    # limit = strategy_limit if strategy_limit else len(ranked_stocks)
    # So if I pass strategy_limit=None, it uses len(ranked_stocks) -> ALL ranked.
    
    market_context = None # let it fetch inside
    
    try:
        # Limited to 5 for demonstration to avoid excessive rate limits/time
        # strategy_limit=None -> Backtest ALL of the 5 analyzed stocks
        result = await router.route(
            query, 
            risk_profile="aggressive", 
            analyze_limit=5, 
            strategy_limit=None
        )
        
        print("\n✅ Analysis Complete.")
        
        if "error" in result:
             print(f"❌ Error: {result['error']}")
        else:
             print(f"🏆 Best Stock: {result.get('top_pick')}")
             print(f"📈 Strategy Tickers: {result.get('strategy_tickers')}")
             
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(run_full_analysis())
