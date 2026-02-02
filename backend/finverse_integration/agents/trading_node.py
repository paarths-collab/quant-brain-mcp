from backend.finverse_integration.state import WealthState
from backend.agents.execution_agent import ExecutionAgent
import os

class TradingExecutor:
    """Optional Stage: Execute Paper Trade if approved"""
    
    def __init__(self):
        # Initialize the existing ExecutionAgent (Alpaca Wrapper)
        self.alpaca = ExecutionAgent(
            api_key=os.getenv("ALPACA_API_KEY"),
            api_secret=os.getenv("ALPACA_SECRET_KEY"),
            paper=True 
        )

    def __call__(self, state: WealthState) -> WealthState:
        # Only execute if user EXPLICITLY confirmed logic implies it
        # In this autonomous run, we will NOT execute automatically for safety,
        # but we will check buying power to verify connectivity.
        
        try:
            account = self.alpaca.get_account_info()
            if "error" in account:
                return {**state, "messages": [f"⚠️ Alpaca Error: {account['error']}"]}
            
            buying_power = account.get('buying_power', '0')
            msg = f"✓ Trading Connected (Buying Power: ${buying_power})"
            
            # If we wanted to trade:
            # ticker = state['selected_stock']['Ticker']
            # self.alpaca.submit_market_order(ticker, 1, "buy")
            
            return {
                **state,
                "messages": [msg]
            }
        except Exception as e:
            return {**state, "errors": [f"Trading Executor Failed: {e}"]}
