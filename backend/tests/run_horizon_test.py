import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.backend1.orchestrator.theme_router import ThemeRouter

async def test_horizon():
    print("🚀 Initializing Horizon Test...")
    router = ThemeRouter()
    
    # Test Short Term
    query = "Best AI stock for short term swing trade"
    print(f"\n❓ User Query: '{query}'")
    
    result = await router.route(
        query, 
        risk_profile="aggressive", 
        analyze_limit=3, # Fast test
        strategy_limit=1
    )
    
    if "error" in result:
         print(f"❌ Error: {result['error']}")
    else:
         print(f"🏆 Best Stock: {result.get('top_pick')}")
         print(f"⏳ Horizon Used: {result.get('features', {}).get('horizon', 'Unknown')}")
         print(f"📄 Explanation Snippet: {result.get('explanation')[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_horizon())
