import os
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from fredapi import Fred


from .state import WealthState
from .sentiment_agent import SentimentAgent


import json


class MutualFundAgent:
    """Stage 4a: MF Selection using Guardian News + Reddit Logic"""
    
    def __init__(self, llm_manager, sentiment_agent: SentimentAgent = None):
        self.llm_manager = llm_manager
        self.sentiment_agent = sentiment_agent
        self.guardian_key = os.getenv("GUARDIAN_API_KEY")

    async def __call__(self, state: WealthState) -> WealthState:
        # Check allocation
        if state.get('allocation_strategy', {}).get('mutual_funds', 0) <= 0:
            return {**state, "execution_log": state.get("execution_log", []) + ["⚠️ Skipping MF (0% allocation)"]}
            
        try:
            # Fetch 'Best Mutual Funds' news
            news = await asyncio.to_thread(self._get_mf_news)
            
            # --- REDDIT SENTIMENT ---
            sentiment_summary = "No sentiment data"
            if self.sentiment_agent:
                market = state.get('market', 'US')
                topics = [f"Mutual Funds {market}", "Index Funds vs Active"]
                summaries = await self.sentiment_agent.analyze_batch(topics)
                sentiment_summary = "\n".join(summaries)
            
            # Recommend
            prompt = f"""Recommend a mutual fund category based on news, sentiment and user profile.
            
            User Profile: {state.get('user_profile', {})}
            News Headlines: {[n['title'] for n in news[:5]]}
            Reddit Sentiment: {sentiment_summary}
            
            Return JSON: {{ "category": "Large Cap", "rationale": "..." }}
            """
            
            response = await self.llm_manager.ainvoke([HumanMessage(content=prompt)])
            rec = json.loads(response.content.replace('```json','').replace('```','').strip())
            
            return {
                "selected_mf": rec,
                "execution_log": [f"✓ MF Strategy: {rec['category']}"]
            }
        except Exception as e:
             return {**state, "errors": state.get("errors", []) + [f"MF Agent Failed: {e}"]}

    def _get_mf_news(self):
        url = "https://content.guardianapis.com/search"
        params = {"api-key": self.guardian_key, "q": "mutual funds investment", "section": "business"}
        try:
            r = requests.get(url, params=params)
            return [{"title": x['webTitle']} for x in r.json()['response']['results']]
        except:
            return []


class BondAgent:
    """Stage 4b: Bond Selection using FRED Data + Reddit"""
    
    def __init__(self, llm_manager, sentiment_agent: SentimentAgent = None):
        self.llm_manager = llm_manager
        self.sentiment_agent = sentiment_agent
        self.fred = Fred(api_key=os.getenv("FRED_API_KEY"))

    async def __call__(self, state: WealthState) -> WealthState:
        if state.get('allocation_strategy', {}).get('bonds', 0) <= 0:
             return {**state, "execution_log": state.get("execution_log", []) + ["⚠️ Skipping Bonds (0% allocation)"]}
            
        try:
            # Fetch 10Y Treasury Yield
            yield_10y = self.fred.get_series('DGS10').iloc[-1]
            inflation = self.fred.get_series('CPIAUCSL').pct_change(12).iloc[-1] * 100
            
            macro_data = {"10y_yield": yield_10y, "inflation": inflation}
            
            # --- REDDIT SENTIMENT ---
            sentiment_summary = "No sentiment data"
            if self.sentiment_agent:
                # E.g. "Bond Market" or "Treasury Yields"
                summaries = await self.sentiment_agent.analyze_batch(["Bond Market Outlook", "Rates Interest Prediction"])
                sentiment_summary = "\n".join(summaries)
            
            prompt = f"""Recommend bond strategy given:
            10Y Yield: {yield_10y:.2f}%
            Inflation: {inflation:.2f}%
            sentiment: {sentiment_summary}
            User Profile: {state.get('user_profile')}
            
            Return JSON: {{ "bond_type": "Govt/Corp", "duration": "Short/Long", "rationale": "..." }}
            """
            
            response = await self.llm_manager.ainvoke([HumanMessage(content=prompt)])
            rec = json.loads(response.content.replace('```json','').replace('```','').strip())
            
            return {
                "macro_indicators": macro_data,
                "selected_bonds": rec,
                "execution_log": [f"✓ Bond Strategy: {rec['bond_type']} ({rec['duration']})"]
            }
        except Exception as e:
            return {**state, "errors": state.get("errors", []) + [f"Bond Agent Failed: {e}"]}
