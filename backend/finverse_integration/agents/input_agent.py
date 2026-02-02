import json
from langchain_core.messages import HumanMessage, SystemMessage
from state import WealthState

class InputStructurerAgent:
    """Stage 1: Structure raw user input into investment profile"""
    
    def __init__(self, llm):
        self.llm = llm
        
    def __call__(self, state: WealthState) -> WealthState:
        """Parse natural language input into structured profile"""
        
        system_prompt = """You are a financial profile structurer. Extract and structure the following from user input:

1. **Financial Snapshot**:
   - Monthly Income (recurring vs non-recurring)
   - Current Savings
   - Active Loans (type, EMI, tenure)
   - Monthly Expenses
   
2. **Investment Preferences**:
   - Investment Horizon (short/medium/long term)
   - Risk Tolerance (conservative/moderate/aggressive)
   - Financial Goals (retirement, home, education, etc.)
   
4. **Market Context**:
   - Market (e.g., 'US', 'IN' for India, 'UK', 'EU') inferred from currency symbols ($, ₹, £, €) or explicit mention. Default to 'US' if ambiguous.

Return ONLY valid JSON with this structure:
{
  "market": "US|IN|UK|EU",
  "financial_snapshot": {
    "monthly_income": float,
    "income_type": "recurring|non_recurring|mixed",
    "savings": float,
    "loans": [{"type": str, "emi": float, "tenure_months": int}],
    "monthly_expenses": float,
    "investable_surplus": float
  },
  "preferences": {
    "horizon": "short|medium|long",
    "risk_tolerance": "conservative|moderate|aggressive",
    "goals": [str]
  },
  "allocation": {
    "stocks": float,
    "mutual_funds": float,
    "bonds": float,
    "reason": str
  }
}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Input:\n{state['raw_input']}")
            ])
            
            # Clean up potential markdown code blocks
            content = response.content.replace('```json', '').replace('```', '').strip()
            profile = json.loads(content)
            
            return {
                **state,
                "user_profile": profile,
                "market": profile.get("market", "US"),
                "allocation_strategy": profile["allocation"],
                "messages": [f"✓ Structured user profile: {profile['preferences']['risk_tolerance']} investor"]
            }
            
        except Exception as e:
            return {
                **state,
                "errors": [f"Input structuring failed: {str(e)}"]
            }
