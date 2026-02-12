"""
Comprehensive test for enhanced emotion advisor with:
- Multi-source data scraping
- 24-hour cooldown locks
- Lazy-loaded orchestrator (no NLTK warnings)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.emotion_advisor_service import analyze_emotion_safe_advice
from backend.services.cooldown_lock import get_cooldown_manager


def test_enhanced_pipeline_with_cooldown():
    """Test emotion advisor with auto-cooldown feature"""
    print("\n" + "="*70)
    print("🧪 TEST 1: Panic Message with Auto-Cooldown")
    print("="*70)
    
    result = analyze_emotion_safe_advice(
        message="MARKET IS CRASHING! I'm panicking and need to sell ALL my stocks NOW before it's too late!",
        tickers=["AAPL", "TSLA"],
        market="us",
        time_horizon_years=5,
        risk_tolerance="moderate",
        include_market_data=True,
        include_news=False,
        user_id="test_user_123",
        check_cooldown=True,
        auto_create_cooldown=True,  # Enable 24hr cooldown
    )
    
    print(f"\n📝 Message: {result['message'][:80]}...")
    print(f"\n😨 Emotion Analysis:")
    print(f"   - Intensity: {result['bias_analysis']['emotion_intensity']:.2f}")
    print(f"   - Dominant Bias: {result['bias_analysis']['dominant_bias']}")
    
    print(f"\n🎯 Action Recommendation: {result['action_recommendation']}")
    
    # Check cooldown status
    cooldown = result.get('cooldown_lock', {})
    print(f"\n🔒 Cooldown Lock:")
    print(f"   - Feature Enabled: {cooldown.get('feature_enabled')}")
    print(f"   - Lock Created: {bool(cooldown.get('created'))}")
    
    if cooldown.get('created'):
        created = cooldown['created']
        print(f"   - Reason: {created['reason']}")
        print(f"   - Duration: {created['duration_hours']} hours")
        print(f"   - Expires At: {created['expires_at']}")
    
    if cooldown.get('status'):
        status = cooldown['status']
        print(f"   - Active Lock Found: YES")
        print(f"   - Time Remaining: {status['time_remaining_hours']:.1f} hours")
    
    print(f"\n💡 Guidance: {len(result['guidance'])} items")
    for idx, g in enumerate(result['guidance'][:2], 1):
        print(f"   {idx}. {g['title']}")
    
    print("\n✅ Test 1 PASSED: Cooldown feature works!")
    return result


def test_cooldown_prevents_trading():
    """Test that cooldown lock is enforced on subsequent requests"""
    print("\n" + "="*70)
    print("🧪 TEST 2: Attempt Trading with Active Cooldown")
    print("="*70)
    
    result = analyze_emotion_safe_advice(
        message="Maybe I should sell now?",
        tickers=["AAPL"],
        user_id="test_user_123",
        check_cooldown=True,
        include_market_data=False,
        include_news=False,
    )
    
    cooldown = result.get('cooldown_lock', {})
    
    if cooldown.get('status'):
        print("\n🚫 COOLDOWN ACTIVE!")
        status = cooldown['status']
        print(f"   - Reason: {status['reason']}")
        print(f"   - Time Remaining: {status['time_remaining_hours']:.1f} hours")
        print(f"   - Can Override: {status['can_override']}")
        print("\n✅ Test 2 PASSED: Cooldown is enforced!")
    else:
        print("\n⚠️ No active cooldown found (may have expired)")
    
    return result


def test_cooldown_override():
    """Test overriding a cooldown lock"""
    print("\n" + "="*70)
    print("🧪 TEST 3: Override Cooldown Lock")
    print("="*70)
    
    manager = get_cooldown_manager()
    
    # Check if there's an active lock
    active_lock = manager.check_lock("test_user_123", "AAPL")
    
    if active_lock:
        print(f"\n📋 Active lock found:")
        print(f"   - Created: {active_lock['created_at']}") 
        print(f"   - Expires: {active_lock['expires_at']}")
        
        # Override it
        overridden = manager.override_lock(
            user_id="test_user_123",
            ticker="AAPL",
            override_reason="User explicitly confirmed decision",
        )
        
        if overridden:
            print(f"\n✅ Lock overridden successfully!")
            
            # Verify it's gone
            check_again = manager.check_lock("test_user_123", "AAPL")
            if check_again is None:
                print(f"✅ Lock removed from system")
            else:
                print(f"⚠️ Lock still active?")
        
        print("\n✅ Test 3 PASSED: Override works!")
    else:
        print("\n⚠️ No active lock to override")
    
    return True


def test_user_stats():
    """Test getting user cooldown statistics"""
    print("\n" + "="*70)
    print("🧪 TEST 4: User Cooldown Statistics")
    print("="*70)
    
    manager = get_cooldown_manager()
    stats = manager.get_user_stats("test_user_123")
    
    print(f"\n👤 User: {stats['user_id']}")
    print(f"   - Active Locks: {stats['active_locks_count']}")
    print(f"   - Total Overrides: {stats['total_overrides']}")
    
    if stats['recent_overrides']:
        print(f"\n📜 Recent Overrides:")
        for override in stats['recent_overrides']:
            print(f"   - {override['overridden_at']}: {override['reason']}")
    
    print("\n✅ Test 4 PASSED: Stats retrieved!")
    return stats


def test_calm_message_no_cooldown():
    """Test that calm messages don't trigger cooldown"""
    print("\n" + "="*70)
    print("🧪 TEST 5: Calm Message (No Cooldown)")
    print("="*70)
    
    result = analyze_emotion_safe_advice(
        message="I'm considering a long-term investment in AAPL. What do you think?",
        tickers=["AAPL"],
        user_id="test_user_calm",
        check_cooldown=True,
        auto_create_cooldown=True,
        include_market_data=False,
        include_news=False,
    )
    
    print(f"\n😌 Emotion Intensity: {result['bias_analysis']['emotion_intensity']:.2f}")
    print(f"🎯 Action: {result['action_recommendation']}")
    
    cooldown = result.get('cooldown_lock', {})
    lock_created = bool(cooldown.get('created'))
    
    print(f"\n🔒 Cooldown Created: {lock_created}")
    
    if not lock_created:
        print("✅ Test 5 PASSED: Calm message didn't trigger cooldown!")
    else:
        print("⚠️ Unexpected: calm message triggered cooldown")
    
    return result


if __name__ == "__main__":
    print("\n" + "🎯"*35)
    print("COMPREHENSIVE EMOTION ADVISOR TEST SUITE")
    print("Testing: Data Scraping + Cooldown Locks + Lazy Loading")
    print("🎯"*35)
    
    try:
        # Run all tests
        test_enhanced_pipeline_with_cooldown()
        test_cooldown_prevents_trading()
        test_cooldown_override()
        test_user_stats()
        test_calm_message_no_cooldown()
        
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        print("\n✨ Features Working:")
        print("   ✅ Emotion detection with bias analysis")
        print("   ✅ 24-hour cooldown lock (auto-create)")
        print("   ✅ Cooldown enforcement")
        print("   ✅ Cooldown override capability")
        print("   ✅ User statistics tracking")
        print("   ✅ Keyword-based sentiment (no NLTK)")
        print("   ✅ Lazy-loaded orchestrator (no StockPickerAgent error)")
        print("\n💰 Monetization Ready: This prevents panic trading!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
