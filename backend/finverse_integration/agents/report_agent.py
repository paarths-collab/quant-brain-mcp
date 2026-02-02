from state import WealthState
from langchain_core.messages import HumanMessage, SystemMessage

class ReportDraftingAgent:
    """Final Stage: Synthesize comprehensive report"""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        
    def __call__(self, state: WealthState) -> WealthState:
        try:
            prompt = f"""Create a PROFESSIONAL Investment Strategy Report.
            
            1. User Profile: {state.get('user_profile')}
            
            2. Asset Allocation: {state.get('allocation_strategy')}
            
            3. Stock Pick ({state.get('selected_sector')}):
               - Ticker: {state.get('selected_stock', {}).get('Ticker')}
               - Reason: {state.get('selected_stock', {}).get('Reason')}
               - Research: {state.get('stock_research')}
               
            4. Mutual Fund: {state.get('selected_mf')}
            
            5. Bonds (Macro: {state.get('macro_indicators')}): {state.get('selected_bonds')}
            
            Write a structured Markdown report with:
            - Executive Summary
            - Portfolio Breakdown (Pie Chart description)
            - Deep Dive: Why {state.get('selected_stock', {}).get('Ticker')}? (Cite clients/suppliers)
            - Risk Analysis
            - Recommended Action Plan
            """
            
            response = self.llm_manager.invoke([HumanMessage(content=prompt)])
            
            return {
                **state,
                "investment_report": response.content,
                "messages": ["✓ Report Generated"]
            }
        except Exception as e:
            return {**state, "errors": [f"Report Gen Failed: {e}"]}
