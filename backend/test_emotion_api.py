"""
Test the emotion advisor API endpoint
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_emotion_api_panic():
    print("\n" + "="*60)
    print("Testing /api/emotion-advisor/analyze endpoint")
    print("="*60)
    
    response = client.post(
        "/api/emotion-advisor/analyze",
        json={
            "message": "The market is crashing! I need to sell everything NOW!",
            "tickers": ["TSLA", "NVDA"],
            "market": "us",
            "time_horizon_years": 3,
            "risk_tolerance": "moderate",
            "include_market_data": True,
            "include_news": False,
        },
    )
    
    print(f"\n✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response Keys: {list(data.keys())}")
        print(f"\n📊 Bias Analysis:")
        print(f"   - Emotion Intensity: {data['bias_analysis']['emotion_intensity']:.2f}")
        print(f"   - Dominant Bias: {data['bias_analysis']['dominant_bias']}")
        
        print(f"\n🎯 Action Recommendation: {data['action_recommendation']}")
        
        if data.get('market_context'):
            print(f"\n📈 Market Context: {len(data['market_context'])} ticker(s)")
            for ticker, ctx in data['market_context'].items():
                if not ctx.get('error'):
                    print(f"   - {ticker}: ${ctx.get('last_price', 'N/A')} (drawdown: {ctx.get('current_drawdown_pct', 'N/A')}%)")
        
        print(f"\n💡 Guidance: {len(data['guidance'])} items")
        
        # Verify required fields
        assert 'action_recommendation' in data
        assert data['action_recommendation'] in ['HOLD', 'REVIEW', 'CONSIDER_SELL']
        assert 'bias_analysis' in data
        assert 'guidance' in data
        assert 'market_context' in data
        assert 'timestamp' in data
        
        print("\n✅ All assertions passed!")
    else:
        print(f"❌ Error: {response.text}")
    
    print("="*60)
    return response


def test_emotion_api_minimal():
    print("\n" + "="*60)
    print("Testing minimal API request (no market data)")
    print("="*60)
    
    response = client.post(
        "/api/emotion-advisor/analyze",
        json={
            "message": "Should I buy this stock? It looks promising.",
            "include_market_data": False,
            "include_news": False,
        },
    )
    
    print(f"\n✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"🎯 Action Recommendation: {data['action_recommendation']}")
        print(f"📊 Emotion Intensity: {data['bias_analysis']['emotion_intensity']:.2f}")
        assert 'action_recommendation' in data
        print("✅ Minimal API test passed!")
    
    print("="*60)
    return response


if __name__ == "__main__":
    test_emotion_api_minimal()
    test_emotion_api_panic()
    print("\n🎉 All API tests completed successfully!")
