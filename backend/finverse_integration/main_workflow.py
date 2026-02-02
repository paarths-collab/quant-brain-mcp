import os
import sys
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

# Load items
load_dotenv()

# Import Agents
from .utils.llm_manager import LLMManager
from .agents.input_agent import InputStructurerAgent
from .agents.sector_agent import SectorDiscoveryAgent
from .agents.stock_agent import StockSelectionAgent
from .agents.mf_bond_agents import MutualFundAgent, BondAgent
from .agents.report_agent import ReportDraftingAgent
from .agents.trading_node import TradingExecutor
from .state import WealthState

def build_graph():
    """Construct the Wealth Management Graph"""
    # 1. Init Infrastructure
    llm = LLMManager() # Handles Gemini Multi-Key
    
    # 2. Init Nodes
    input_node = InputStructurerAgent(llm)
    sector_node = SectorDiscoveryAgent(llm)
    stock_node = StockSelectionAgent(llm)
    mf_node = MutualFundAgent(llm)
    bond_node = BondAgent(llm)
    report_node = ReportDraftingAgent(llm)
    trading_node = TradingExecutor()
    
    # 3. Define Graph
    workflow = StateGraph(WealthState)
    
    workflow.add_node("input", input_node)
    workflow.add_node("sector", sector_node)
    workflow.add_node("stock", stock_node)
    workflow.add_node("mf", mf_node)
    workflow.add_node("bond", bond_node)
    workflow.add_node("report", report_node)
    workflow.add_node("trading", trading_node)
    
    # 4. Define Edges (Sequential)
    workflow.set_entry_point("input")
    workflow.add_edge("input", "sector")
    workflow.add_edge("sector", "stock")
    workflow.add_edge("stock", "mf")
    workflow.add_edge("mf", "bond")
    workflow.add_edge("bond", "report")
    workflow.add_edge("report", "trading")
    workflow.add_edge("trading", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("\n💰 Autonomous Wealth Manager Starting...\n")
    
    # Example Input (You can change this)
    user_input = """
    I earn $9,000/month. Savings: $40k. 
    Loans: Car loan $400/mo. Mortgage $1500/mo.
    Expenses: $3000/mo.
    Goal: Retirement in 25 years. 
    Risk: Moderate-Aggressive.
    """
    
    app = build_graph()
    
    # Run
    inputs = {
        "raw_input": user_input,
        "messages": [],
        "errors": []
    }
    
    try:
        final_state = app.invoke(inputs)
        
        print("\n\n" + "="*50)
        print("FINAL REPORT")
        print("="*50)
        print(final_state.get('investment_report', "No Report Generated"))
        
        print("\n" + "="*50)
        print("EXECUTION LOG")
        print("="*50)
        for msg in final_state.get('messages', []):
            print(msg)
            
        if final_state.get('errors'):
            print("\n❌ Errors Encountered:")
            for err in final_state['errors']:
                print(f"- {err}")
                
    except Exception as e:
        print(f"❌ Critical Failure: {e}")
