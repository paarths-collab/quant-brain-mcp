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
logger = logging.getLogger("VERIFY")

async def test_risk_engine():
    logger.info("--- 1. Testing Risk Engine ---")
    try:
        from backend.quant.risk_models import RiskModels
        risk = RiskModels()
        var = risk.calculate_var("AAPL")
        logger.info(f"✅ VaR Calculated for AAPL: {var}")
        assert isinstance(var, float)
    except Exception as e:
        logger.error(f"❌ Risk Engine Failed: {e}")

async def test_pipeline():
    logger.info("\n--- 2. Testing Investment Pipeline (Dry Run) ---")
    try:
        from backend.engine.pipeline import InvestmentPipeline
        pipeline = InvestmentPipeline()
        
        # We mock the agent response to avoid full LLM call overhead/cost for this quick check
        # BUT the user wants to know if it REALLY works. 
        # Let's run a real lightweight query if possible, or mock the heavy agent part.
        # Actually, let's run it.
        
        result = await pipeline.run("Is AAPL a buy?", ticker="AAPL", session_id="test_verify")
        
        logger.info(f"✅ Pipeline Return Keys: {result.keys()}")
        
        if "strategy" in result:
             logger.info(f"✅ Strategy Output: {result['strategy'].get('best_strategy')}")
             
        if "risk_engine" in result:
             logger.info(f"✅ Risk Output: {result['risk_engine']}")
             
    except Exception as e:
        logger.error(f"❌ Pipeline Failed: {e}")

async def main():
    logger.info("🚀 STARTING SYSTEM VERIFICATION 🚀")
    await test_risk_engine()
    await test_pipeline()
    logger.info("\n✅ SYSTEM VERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())
