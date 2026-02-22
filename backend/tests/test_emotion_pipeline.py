"""
Quick integration test for emotion advisor pipeline with market data
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from backend.services.emotion_advisor_service import analyze_emotion_safe_advice


def test_pipeline_with_market_data():
    """Test with panic message and real ticker"""
    print("\n" + "="*60)
    print("Testing Emotion Advisor Pipeline")
    print("="*60)
    
    result = analyze_emotion_safe_advice(
        message="I'm panicking! The market is crashing and I should sell all my AAPL now!",
        tickers=["AAPL"],
        market="us",
        time_horizon_years=5,
        risk_tolerance="moderate",
        include_market_data=True,
        include_news=False,  # Skip news to avoid API limits
    )
    
    print(f"\n✅ Message: {result['message']}")
    print(f"\n📊 Bias Analysis:")
    print(f"   - Emotion Intensity: {result['bias_analysis']['emotion_intensity']:.2f}")
    print(f"   - Dominant Bias: {result['bias_analysis']['dominant_bias']}")
    print(f"   - Detected Biases: {len(result['bias_analysis']['biases'])}")
    
    print(f"\n🎯 Action Recommendation: {result['action_recommendation']}")
    
    if result['market_context']:
        print(f"\n📈 Market Context (AAPL):")
        aapl_data = result['market_context'].get('AAPL', {})
        if not aapl_data.get('error'):
            print(f"   - Last Price: ${aapl_data.get('last_price', 'N/A')}")
            print(f"   - 30d Volatility: {aapl_data.get('volatility_30d_pct', 'N/A')}%")
            print(f"   - Current Drawdown: {aapl_data.get('current_drawdown_pct', 'N/A')}%")
            print(f"   - Volatility State: {aapl_data.get('volatility_state', 'N/A')}")
    
    if result['guidance']:
        print(f"\n💡 Guidance ({len(result['guidance'])} items):")
        for idx, item in enumerate(result['guidance'][:3], 1):
            print(f"   {idx}. {item['title']}: {item['message'][:80]}...")
    
    if result['nudge']:
        print(f"\n🔔 Nudge: {result['nudge'][:100]}...")
    
    print("\n" + "="*60)
    print("✅ Pipeline test completed successfully!")
    print("="*60)
    
    # Verify required fields
    assert 'action_recommendation' in result
    assert result['action_recommendation'] in ['HOLD', 'REVIEW', 'CONSIDER_SELL']
    assert 'bias_analysis' in result
    assert 'guidance' in result
    assert 'market_context' in result
    
    return result


def test_pipeline_minimal():
    """Test without market data (fast test)"""
    print("\n" + "="*60)
    print("Testing Minimal Pipeline (No Market Data)")
    print("="*60)
    
    result = analyze_emotion_safe_advice(
        message="This stock is going to the moon! I need to buy more NOW!",
        tickers=None,
        include_market_data=False,
        include_news=False,
    )
    
    print(f"\n✅ Message: {result['message']}")
    print(f"📊 Emotion Intensity: {result['bias_analysis']['emotion_intensity']:.2f}")
    print(f"🎯 Action Recommendation: {result['action_recommendation']}")
    print(f"💡 Guidance Items: {len(result['guidance'])}")
    
    assert result['action_recommendation'] in ['HOLD', 'REVIEW', 'CONSIDER_SELL']
    print("\n✅ Minimal pipeline test passed!")
    
    return result


if __name__ == "__main__":
    # Run minimal test first (fast)
    test_pipeline_minimal()
    
    # Run full test with market data
    test_pipeline_with_market_data()
    
    print("\n🎉 All pipeline tests completed successfully!")
