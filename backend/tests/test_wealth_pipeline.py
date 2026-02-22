"""
Test script for AI Advisor Wealth Management Pipeline
Tests the multi-agent orchestrator end-to-end
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from backend.finverse_integration.agents.wealth_orchestrator import WealthOrchestrator

async def test_wealth_pipeline():
    """Test the complete wealth management pipeline"""
    
    print("=" * 80)
    print("AI ADVISOR PIPELINE TEST")
    print("=" * 80)
    
    # Test input - moderate risk investor
    user_input = """
    I'm 32 years old earning $8000/month. I have $50,000 in savings. 
    I have a home loan with $2000 EMI for 15 years and car loan with $500 EMI for 3 years. 
    My monthly expenses are around $3000. I want to invest for retirement (long-term). 
    I'm comfortable with moderate risk.
    """
    
    print("\n📝 User Input:")
    print(user_input.strip())
    print("\n" + "=" * 80)
    
    try:
        # Initialize orchestrator
        print("\n🔧 Initializing Wealth Orchestrator...")
        orchestrator = WealthOrchestrator()
        
        # Run workflow
        print("🚀 Running multi-agent workflow...\n")
        result = await orchestrator.run_workflow(user_input, market="US")
        
        print("\n" + "=" * 80)
        print("✅ WORKFLOW COMPLETE")
        print("=" * 80)
        
        # Display results
        print("\n📊 RESULTS:")
        print("-" * 80)
        
        # User Profile
        if result.get('user_profile'):
            profile = result['user_profile']
            print("\n👤 User Profile:")
            print(f"  Market: {result.get('market', 'N/A')}")
            print(f"  Risk Tolerance: {profile.get('preferences', {}).get('risk_tolerance', 'N/A')}")
            print(f"  Investment Horizon: {profile.get('preferences', {}).get('horizon', 'N/A')}")
            print(f"  Investable Amount: ${result.get('investable_amount', 0):,.2f}")
        
        # Sector Selection
        if result.get('selected_sector'):
            print(f"\n🏭 Selected Sector: {result['selected_sector']}")
        
        # Stock Recommendation
        if result.get('selected_stock'):
            stock = result['selected_stock']
            print("\n📈 Stock Recommendation:")
            print(f"  Ticker: {stock.get('Ticker', 'N/A')}")
            print(f"  Price: ${stock.get('Price', 0):.2f}")
            print(f"  Strategy: {stock.get('InvestmentStrategy', 'N/A')}")
            print(f"  Reason: {stock.get('Reason', 'N/A')}")
        
        # Asset Allocation
        if result.get('allocation_strategy'):
            alloc = result['allocation_strategy']
            print("\n💼 Allocation Snapshot:")
            print(f"  Stocks: {alloc.get('stocks', 0) * 100:.0f}%")
            print(f"  Cash: {alloc.get('CASH', alloc.get('cash', 0)) * 100:.0f}%")
        
        # Execution Log
        if result.get('execution_log'):
            print("\n📋 Execution Log:")
            for log in result['execution_log']:
                print(f"  {log}")
        
        # Errors
        if result.get('errors'):
            print("\n⚠️ Errors:")
            for error in result['errors']:
                print(f"  ❌ {error}")
        
        # Investment Report
        if result.get('investment_report'):
            print("\n📄 Investment Report:")
            print("-" * 80)
            print(result['investment_report'][:500] + "..." if len(result['investment_report']) > 500 else result['investment_report'])
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
        
        # Save full result to file
        output_file = "test_wealth_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Full result saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n🧪 Starting AI Advisor Pipeline Test...\n")
    result = asyncio.run(test_wealth_pipeline())
    
    if result:
        print("\n✅ Pipeline is working!")
    else:
        print("\n❌ Pipeline failed - check errors above")
