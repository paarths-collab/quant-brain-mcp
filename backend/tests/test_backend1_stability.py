import sys
import os
import pprint
from dotenv import load_dotenv

# Load env
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_path)
load_dotenv(os.path.join(backend_path, ".env"))

from backend1.orchestrator.execution_engine import ExecutionEngine

def test_backend1():
    print("Testing Backend1 Stability...")
    engine = ExecutionEngine()
    
    # Simulate a Schema (Plan) that causes errors
    # Intent implies NVDA, but agent task is generic
    schema = {
        "intent": "Analyze NVDA valuation",
        "search_queries": ["NVDA revenue growth", "NVIDIA competitive advantage"],
        "selected_agents": ["FinancialAnalystAgent", "WebSearchAgent", "RiskAgent"],
        "agent_tasks": {
            "FinancialAnalystAgent": "Perform valuation analysis", # Missing Ticker
            "WebSearchAgent": "Find latest news",
            "RiskAgent": "Assess volatility"
        }
    }
    
    print("\n--- EXECUTING PLAN ---")
    state = engine.execute(schema)
    
    print("\n--- RESULT ---")
    if "error" in state.get("financial", {}):
        print("❌ FINANCIAL AGENT FAILED: " + str(state["financial"]["error"]))
    else:
        print("✅ FINANCIAL AGENT SUCCESS")
        print(f"Ticker: {state['financial'].get('ticker')}")
        print(f"Price: {state['financial'].get('current_price')}")
        
    pprint.pprint(state)

if __name__ == "__main__":
    test_backend1()
