import asyncio
import os
import sys
import logging

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")

# Add project root to path
sys.path.append(os.getcwd())

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("VERIFY_AI")

async def test_ai_strategy_pipeline():
    logger.info("🚀 STARTING AI STRATEGY VERIFICATION 🚀")
    
    try:
        from backend.engine.pipeline import InvestmentPipeline
        pipeline = InvestmentPipeline()
        
        # Test 1: Trend Case (NVDA - likely trending)
        logger.info("\n--- Test Case 1: NVDA (Expect Trend / High Vol?) ---")
        result = await pipeline.run("Analyze NVDA", ticker="NVDA", session_id="test_ai_strat")
        
        strat_data = result["strategy"]
        regime = strat_data["regime"]
        chosen = strat_data["best_strategy"]["strategy"]
        reasoning = strat_data["ai_reasoning"]
        
        logger.info(f"📊 Market Regime: {regime['regime']} (Vol: {regime['volatility']:.2%})")
        logger.info(f"🤖 AI Chosen Strategy: {chosen}")
        logger.info(f"🧠 Reasoning: {reasoning}")
        
        # Test 2: Stable/Bear Case (PFE or something slow)
        logger.info("\n--- Test Case 2: KO (Expect Sideways/Low Vol) ---")
        result_ko = await pipeline.run("Analyze KO", ticker="KO", session_id="test_ai_strat_2")
        
        strat_data_ko = result_ko["strategy"]
        regime_ko = strat_data_ko["regime"]
        chosen_ko = strat_data_ko["best_strategy"]["strategy"]
        
        logger.info(f"📊 Market Regime: {regime_ko['regime']} (Vol: {regime_ko['volatility']:.2%})")
        logger.info(f"🤖 AI Chosen Strategy: {chosen_ko}")
        
    except Exception as e:
        logger.error(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_strategy_pipeline())
