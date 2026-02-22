import asyncio
import sys
import os
from dotenv import load_dotenv

# Load env before imports - .env is in backend/ directory
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.backend1.orchestrator.sector_decision_orchestrator import SectorDecisionOrchestrator

async def main():
    print("Initializing Orchestrator...")
    orchestrator = SectorDecisionOrchestrator()
    
    sector = "Technology"
    print(f"Running analysis for: {sector}")
    
    result = await orchestrator.run(sector, risk_profile="aggressive")
    
    print("\n--- DECISION RESULT ---")
    if "top_pick" in result:
        print(f"Top Pick: {result['top_pick']}")
        print(f"Explanation:\n{result['explanation']}")
        print("\nRankings:")
        for stock in result["ranked"]:
            print(f"- {stock['ticker']}: {stock['final_score']} (Fund: {stock['fundamental']['score']}, Tech: {stock['technical']['score']})")
        if "strategy_analysis" in result:
            sa = result["strategy_analysis"]
            tickers = result.get("strategy_tickers", [])
            
            print(f"\nStrategy Engine data present for: {', '.join(tickers)}")
            print("check console for Quant Research Terminal output & charts...")
            
    else:
        print("Error/No result:", result)

if __name__ == "__main__":
    # Fix for Windows console emoji support
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
