"""
Test script for Multi-Agent Chat System
Tests intent routing, pipeline execution, and conversation flow.
"""
import asyncio
import sys
import os

# Add parent directory for backend imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.chat.intent_router import IntentRouter, PipelineType
from backend.chat.orchestrator import ChatOrchestrator


def test_intent_router():
    """Test intent detection and routing"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Intent Router")
    print("="*60)
    
    router = IntentRouter()
    
    test_cases = [
        # (message, expected_ticker, expected_market, expected_emotion)
        ("Should I sell my AAPL shares?", "AAPL", "US", None),
        ("I'm panicking about TSLA crashing!", "TSLA", "US", "panic"),
        ("What's happening with Reliance stock on NSE?", "RELIANCE", "IN", None),
        ("I bought TCS.NS at the top, feeling FOMO now", "TCS", "IN", "fomo"),
        ("Help me build a portfolio for retirement", None, "US", None),
        ("Is INFY a good buy right now?", "INFY", "IN", None),
    ]
    
    passed = 0
    for message, exp_ticker, exp_market, exp_emotion in test_cases:
        intent = router.analyze(message)
        
        ticker_ok = intent.detected_ticker == exp_ticker
        market_ok = intent.detected_market == exp_market
        emotion_ok = intent.user_emotion == exp_emotion
        
        status = "✅" if (ticker_ok and market_ok and emotion_ok) else "❌"
        
        print(f"\n{status} Message: '{message[:50]}...'")
        print(f"   Ticker: {intent.detected_ticker} (expected: {exp_ticker}) {'✓' if ticker_ok else '✗'}")
        print(f"   Market: {intent.detected_market} (expected: {exp_market}) {'✓' if market_ok else '✗'}")
        print(f"   Emotion: {intent.user_emotion} (expected: {exp_emotion}) {'✓' if emotion_ok else '✗'}")
        print(f"   Pipelines: {[p.value for p in intent.pipelines_needed]}")
        print(f"   Confidence: {intent.confidence:.0%}")
        
        if ticker_ok and market_ok:
            passed += 1
    
    print(f"\n📊 Intent Router: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_orchestrator():
    """Test the chat orchestrator conversation flow"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Chat Orchestrator")
    print("="*60)
    
    orchestrator = ChatOrchestrator(auto_confirm=True)
    session_id = "test-session-001"
    
    # Test message
    test_message = "I'm really worried about my AAPL position, should I sell?"
    print(f"\n📨 User: {test_message}")
    
    responses = []
    async for response in orchestrator.process_message(
        session_id=session_id,
        user_message=test_message,
        user_id="test-user"
    ):
        responses.append(response)
        print(f"\n💬 [{response['type']}]")
        print(f"   {response['content'][:200]}...")
    
    print(f"\n📊 Got {len(responses)} response chunks")
    
    # Check we got meaningful responses
    has_thinking = any(r['type'] == 'thinking' for r in responses)
    has_result = any(r['type'] == 'result' for r in responses)
    
    print(f"   Has thinking: {'✅' if has_thinking else '❌'}")
    print(f"   Has result: {'✅' if has_result else '❌'}")
    
    return has_thinking


def test_clarification_flow():
    """Test the clarification question flow"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Clarification Flow")
    print("="*60)
    
    router = IntentRouter()
    
    # Ambiguous message
    intent = router.analyze("I need help with investing")
    
    print(f"\n📨 User: 'I need help with investing'")
    print(f"   Clarification needed: {'✅' if intent.clarification_needed else '❌'}")
    
    if not intent.clarification_needed:
        print("   ❌ Expected clarification to be needed for ambiguous message")
        return False
    
    print(f"\n🤖 AI asks:\n{intent.clarification_question}")
    
    # User responds with "1" (stock analysis) - but no ticker yet
    updated = router.parse_clarification_response("1", intent)
    print(f"\n📨 User: '1' (selected stock analysis)")
    print(f"   New pipelines: {[p.value for p in updated.pipelines_needed]}")
    print(f"   Clarification still needed: {'✅' if updated.clarification_needed else '❌'}")
    
    # Should STILL need clarification because no ticker was provided
    if not updated.clarification_needed:
        print("   ❌ Expected clarification for missing ticker")
        return False
    
    print(f"\n🤖 AI asks:\n{updated.clarification_question}")
    
    # User provides ticker
    final = router.parse_clarification_response("AAPL", updated)
    print(f"\n📨 User: 'AAPL'")
    print(f"   Detected ticker: {final.detected_ticker}")
    print(f"   Clarification still needed: {'✅' if final.clarification_needed else '❌'}")
    
    # Now clarification should be complete
    if final.clarification_needed:
        print("   ❌ Expected no more clarification after ticker provided")
        return False
    
    if final.detected_ticker != "AAPL":
        print(f"   ❌ Expected ticker AAPL, got {final.detected_ticker}")
        return False
    
    print("\n   ✅ Full clarification flow completed correctly!")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("   MULTI-AGENT CHAT SYSTEM TESTS")
    print("🚀"*30)
    
    results = []
    
    # Test 1: Intent Router
    results.append(("Intent Router", test_intent_router()))
    
    # Test 2: Orchestrator
    results.append(("Orchestrator", asyncio.run(test_orchestrator())))
    
    # Test 3: Clarification
    results.append(("Clarification Flow", test_clarification_flow()))
    
    # Summary
    print("\n" + "="*60)
    print("📋 FINAL RESULTS")
    print("="*60)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n{'✅' if passed == len(results) else '⚠️'} Total: {passed}/{len(results)} tests passed")
    
    return passed == len(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
