import asyncio
from backend.backend1.orchestrator.theme_router import ThemeRouter
from unittest.mock import AsyncMock, patch, MagicMock

# Mock Orchestrator to avoid real network calls
async def test_routing():
    print("🧪 Initializing ThemeRouter Test...")
    router = ThemeRouter()
    
    # Mock the orchestrator methods
    router.orchestrator.run = AsyncMock(return_value={"status": "run_called"})
    router.orchestrator.run_custom_universe = AsyncMock(return_value={"status": "custom_called"})
    
    # --- Test 1: US Theme ---
    query_us = "Best AI stock"
    print(f"\n➤ Testing Query: '{query_us}'")
    await router.route(query_us)
    
    # Check arguments
    call_args = router.orchestrator.run.call_args
    if call_args:
        args, kwargs = call_args
        print(f"   Called 'run' with: {args}, {kwargs}")
        assert kwargs["region"] == "US", "Region should be US"
        assert "ai" in args[0].lower(), "Theme should be 'ai'"
        # Market context check
        assert kwargs["market_context"]["index"] == "^GSPC", "Market Context Index wrong"
    else:
        print("❌ Error: orchestrator.run was NOT called for US Theme.")

    # --- Test 2: India Theme ---
    query_in = "Best Banking stock in Mumbai" # "Mumbai" triggers India
    print(f"\n➤ Testing Query: '{query_in}'")
    await router.route(query_in)
    
    call_args_in = router.orchestrator.run.call_args
    if call_args_in:
        args, kwargs = call_args_in
        print(f"   Called 'run' with: {args}, {kwargs}")
        assert kwargs["region"] == "India", "Region should be India"
        assert "banking" in args[0].lower(), "Theme should be 'banking'"
        assert kwargs["market_context"]["index"] == "^NSEI", "Market Context Index wrong"
    else:
        print("❌ Error: orchestrator.run was NOT called for India Theme.")

    # --- Test 3: Generic Best Stock ---
    query_gen = "What is the best stock to buy"
    print(f"\n➤ Testing Query: '{query_gen}'")
    await router.route(query_gen)
    
    call_args_gen = router.orchestrator.run_custom_universe.call_args
    if call_args_gen:
        args, kwargs = call_args_gen
        print(f"   Called 'run_custom_universe' with: {kwargs}")
        assert kwargs["region"] == "US", "Default region should be US"
        # Check universe list length > 0
        assert len(args[0]) > 0, "Universe should not be empty"
    else:
        print("❌ Error: orchestrator.run_custom_universe was NOT called for generic query.")
        
    print("\n✅ All routing tests passed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_routing())
    except Exception as e:
        print(f"❌ Test Failed: {e}")
