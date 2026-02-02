import os
import requests
import finnhub
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage

from .state import WealthState

import json

class SectorDiscoveryAgent:
    """Stage 2: Identify booming sectors using Guardian News & Finnhub Data"""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))
        self.guardian_key = os.getenv("GUARDIAN_API_KEY")
        
    def __call__(self, state: WealthState) -> WealthState:
        """Analyze sectors and consider seasonality"""
        
        try:
            print("🔍 Starting Sector Analysis...")
            
            # 1. Get Market Context from Finnhub (Basic Market Status)
            market_status = self._get_market_status()
            
            # 2. Get Sector News from Guardian
            sector_news = self._get_guardian_sector_news()
            
            # 3. Determine Season
            month = datetime.now().month
            season = self._get_season(month)
            
            # 4. LLM Analysis to pick Top Sector
            selected_sector, rationale = self._analyze_with_llm(
                state.get('user_profile', {}),
                market_status,
                sector_news,
                season
            )
            
            return {
                "current_season": season,
                "sector_news": sector_news,
                "selected_sector": selected_sector,
                "execution_log": [f"✓ Selected Sector: {selected_sector} ({rationale[:50]}...)"]
            }
            
        except Exception as e:
            return {
                **state,
                "errors": [f"Sector discovery failed: {str(e)}"]
            }
    
    def _get_market_status(self):
        """Fetch general market news/sentiment from Finnhub"""
        try:
            # Get general market news
            news = self.finnhub_client.general_news('general', min_id=0)
            return news[:5] if news else []
        except Exception as e:
            print(f"⚠️ Finnhub Error: {e}")
            return []

    def _get_guardian_sector_news(self):
        """Fetch business/tech news from Guardian"""
        url = "https://content.guardianapis.com/search"
        params = {
            "api-key": self.guardian_key,
            "section": "business",
            "q": "market OR economy OR sector OR technology OR energy OR healthcare OR finance OR consumer OR utilities",
            "order-by": "newest",
            "page-size": 10
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            results = data.get('response', {}).get('results', [])
            return [{"title": r['webTitle'], "url": r['webUrl']} for r in results]
        except Exception as e:
            print(f"⚠️ Guardian API Error: {e}")
            return []

    def _get_season(self, month: int) -> str:
        seasons = {
            (12, 1, 2): "winter",
            (3, 4, 5): "spring",
            (6, 7, 8): "summer",
            (9, 10, 11): "fall"
        }
        for months, season in seasons.items():
            if month in months:
                return season
        return "unknown"

    def _analyze_with_llm(self, user_profile, market_news, sector_news, season):
        """Decide the best sector based on data"""
        
        prompt = f"""Act as a Chief Investment Strategist. Identify the single best sector to invest in RIGHT NOW.

Date: {datetime.now().strftime("%Y-%m-%d")}
Season: {season}

1. Market Context (from Finnhub):
{json.dumps(market_news[:3], indent=2)}

2. Recent Headlines (from Guardian):
{json.dumps(sector_news[:5], indent=2)}

3. User Risk Profile:
{user_profile.get('preferences', {}).get('risk_tolerance', 'Moderate')}

Task:
- Identify ONE booming sector (e.g., Technology, Healthcare, Energy, Finance, Consumer Discretionary).
- Provide a brief 1-sentence rationale citing a specific trend/news.

Return JSON:
{{
  "sector": "Sector Name",
  "rationale": "Reasoning..."
}}
"""
        response = self.llm_manager.invoke([
            SystemMessage(content="You are a market strategist."),
            HumanMessage(content=prompt)
        ])
        
        try:
            # robust cleanup
            clean_content = response.content.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_content)
            return result['sector'], result['rationale']
        except:
            return "Technology", "Fallback: Tech is generally strong (LLM parsing error)."

