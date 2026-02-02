
import os
import yfinance as yf
import json

from .state import WealthState

from .sentiment_agent import SentimentAgent

class GoldAgent:
    """Stage 4c: Gold Strategy based on Price Trend & Reddit Sentiment"""
    
    def __init__(self, llm_manager, sentiment_agent: SentimentAgent):
        self.llm_manager = llm_manager
        self.sentiment_agent = sentiment_agent

    async def __call__(self, state: WealthState) -> WealthState:
        # Check allocation
        allocation = state.get('allocation_strategy', {}).get('gold', 0) if state.get('allocation_strategy') else 0
        if allocation <= 0:
            return {**state, "execution_log": state.get("execution_log", []) + ["⊘ Skipping Gold (0% allocation)"]}
            
        try:
            # 1. Fetch Gold Price Data (GC=F)
            ticker = yf.Ticker("GC=F")
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                current_price = "N/A"
                trend = "Unknown"
            else:
                current_price = hist['Close'].iloc[-1]
                start_p = hist['Close'].iloc[0]
                pct_change = ((current_price - start_p) / start_p) * 100
                trend = f"{pct_change:+.2f}% over last month"

            # 2. Reddit Sentiment
            sentiment_summary = await self.sentiment_agent.analyze_batch(["Gold Price", "Gold Investment"])
            sentiment_text = sentiment_summary[0] if sentiment_summary else "No sentiment data"

            # 3. LLM Recommendation
            prompt = f"""Recommend Gold strategy based on data.
            
            Quantitative:
            - Current Price: ${current_price}
            - Trend: {trend}
            
            Qualitative (Reddit Sentiment):
            {sentiment_text}
            
            User Profile: {state.get('user_profile')}
            Allocation: {allocation * 100}%
            
            Return JSON: {{ "action": "Buy/Hold", "instrument": "SGB/Gold BeES/Physical", "rationale": "..." }}
            """
            
            from langchain_core.messages import HumanMessage
            response = await self.llm_manager.ainvoke([HumanMessage(content=prompt)])
            
            clean = response.content.replace('```json', '').replace('```', '').strip()
            decision = json.loads(clean)
            
            return {
                "selected_gold": {
                    "data": {"price": current_price, "trend": trend},
                    "decision": decision
                },
                "execution_log": [f"✓ Gold Strategy: {decision.get('action')} ({decision.get('instrument')})"]
            }
            
        except Exception as e:
            return {
                **state, 
                "errors": state.get("errors", []) + [f"Gold Agent Failed: {e}"],
                "execution_log": state.get("execution_log", [])
            }
