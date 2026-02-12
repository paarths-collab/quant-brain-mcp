
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load Env
load_dotenv(".env")

# Add path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.finverse_integration.agents.wealth_orchestrator import WealthOrchestrator

async def run_verification():
    print("🚀 Initializing Wealth Orchestrator...")
    try:
        orchestrator = WealthOrchestrator()
    except Exception as e:
        print(f"❌ Init Failed: {e}")
        return

    user_input = """
    I earn $10,000/month. I save $3000.
    I want to invest for a house in 5 years.
    Review my portfolio with a moderate risk profile.
    US Market.
    """

    print(f"\n📨 Sending User Input:\n{user_input}")
    
    try:
        # Run workflow
        final_state = await orchestrator.run_workflow(user_input, market="US")
        
        print("\n✅ Workflow Complete!")
        
        # Write report to file to avoid encoding issues
        with open("debug_output.txt", "w", encoding="utf-8") as f:
            f.write("# Verification Report\n\n")
            f.write("## Execution Log\n")
            for log in final_state.get("execution_log", []):
                f.write(f"- {log}\n")
            
            f.write("\n## Critic Feedback\n")
            f.write(f"- Score: {final_state.get('critic_score')}\n")
            f.write(f"- Feedback: {final_state.get('critic_feedback')}\n")
            
            f.write("\n## Selected Stocks\n")
            f.write(f"```json\n{final_state.get('selected_stocks', [])}\n```\n")

            f.write("\n## Allocation\n")
            f.write(f"```json\n{final_state.get('allocation_strategy', {})}\n```\n")
            
            f.write("\n## Final Report\n")
            f.write(final_state.get('investment_report', 'No Report'))
            
        print("✅ Workflow Complete! Report saved to verification_report.md")

    except Exception as e:
        print(f"❌ Workflow Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_verification())
