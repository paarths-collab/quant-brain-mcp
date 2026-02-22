import asyncio
import json
from backend.engine.pipeline import InvestmentPipeline

async def main():
    pipeline = InvestmentPipeline()
    
    print("Running Investment Pipeline for 'AAPL'...")
    
    # Run the pipeline
    result = await pipeline.run(
        query="Analyze Apple's current market position and tell me if it's a buy given the recent AI news.",
        ticker="AAPL",
        portfolio={"AAPL": 0.5, "NVDA": 0.5}
    )
    
    # Print the result as formatted JSON
    print("\nPIPELINE RESULT:\n")
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
