import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.backend1.agents.gnews_intelligence import GNewsIntelligenceAgent

def test_news():
    print("🚀 Initializing News Agent Test...")
    agent = GNewsIntelligenceAgent()
    
    tickers = ["TCS.NS", "RELIANCE.NS", "AAPL"]
    
    for ticker in tickers:
        print(f"\n📰 Testing {ticker}...")
        try:
            result = agent.run(ticker)
            
            articles = result.get("articles", [])
            summary = result.get("ai_summary", "")
            sentiment = result.get("sentiment_score", 0.5)
            
            print(f"   -> Articles Found: {len(articles)}")
            print(f"   -> AI Summary Length: {len(summary)}")
            print(f"   -> Sentiment Score: {sentiment}")
            
            if articles:
                print(f"   -> Top Article: {articles[0]['title']}")
            
            if not articles and not summary:
                 print("   ⚠️  NO NEWS FOUND (Check Mapping/Query)")
            else:
                 print("   ✅ News Fetch Successful")
                 
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_news()
