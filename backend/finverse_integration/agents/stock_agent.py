import os
import json
import praw
import yfinance as yf
import pandas as pd
import finnhub
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from tavily import TavilyClient
import requests

from ..state import WealthState
# from ..utils.portfolio_engine import PortfolioEngine
# from ..utils.data_loader import DataLoader
from ..utils.llm_manager import LLMManager

class StockSelectionAgent:
    """Stage 3: Select, Validate (Reddit), Backtest, and Deep Dive (Supply Chain)"""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        # Clients
        try:
            self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        except:
            self.tavily = None
            
        try:
            self.finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))
        except:
            self.finnhub_client = None
            
        # Initialize Reddit (Fail silently if credentials missing)
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT")
            )
        except:
            self.reddit = None
        
    def __call__(self, state: WealthState) -> WealthState:
        """Execute stock selection pipeline"""
        
        try:
            print("🔍 Starting Stock Selection...")
            sector = state.get('selected_sector', 'Technology')
            market = state.get('market', 'US')
            
            # 1. Screen Candidates (Basic Logic + LLM)
            candidates = self._screen_stocks(sector, market)
            
            # 2. Analyze Social Sentiment (Reddit)
            sentiment_scores = self._analyze_reddit_sentiment(candidates)
            
            # 3. Backtest Strategies
            backtest_results = self._run_backtests(candidates)
            
            # 4. Select Winner
            best_ticker = self._select_winner(candidates, sentiment_scores, backtest_results)
            print(f"🏆 Winner: {best_ticker}")
            
            # 5. Deep Dive (Tavily -> Fallback NewsDataIO -> Fallback Finnhub)
            research = self._deep_research_robust(best_ticker)
            
            # NEW: Determine Investment Mode (SIP vs Lumpsum)
            inv_mode = self._determine_investment_mode(best_ticker, state.get('user_profile', {}))
            
            # 6. Recommendation Object
            price = self._get_current_price_robust(best_ticker)
            
            selected_stock = {
                "Ticker": best_ticker,
                "Name": best_ticker,
                "Sector": sector,
                "Price": price,
                "InvestmentStrategy": inv_mode,
                "Reason": "Strong structural fundamentals & sentiment"
            }
            
            return {
                **state,
                "candidate_stocks": [{"Ticker": t} for t in candidates],
                "stock_backtests": backtest_results,
                "selected_stock": selected_stock,
                "stock_research": research,
                "messages": [f"✓ Selected Stock: {best_ticker} ({inv_mode})"]
            }
            
        except Exception as e:
            return {
                **state,
                "errors": [f"Stock selection failed: {str(e)}"]
            }

    def _determine_investment_mode(self, ticker, user_profile):
        """Decide SIP vs Lumpsum based on Volatility and User Cash Flow"""
        mode = "Lumpsum"
        reason = "Standard"
        
        # 1. Check User Financials (Income vs Savings)
        fin = user_profile.get('financial_snapshot', {})
        monthly_surplus = fin.get('investable_surplus', 0)
        savings = fin.get('savings', 0)
        
        # If surplus is high relative to savings, prefer SIP
        if monthly_surplus > (savings * 0.1): 
            mode = "SIP (Systematic Investment)"
            reason = "High recurring surplus"
        elif savings > (monthly_surplus * 12):
             mode = "One-Time Lumpsum"
             reason = "Large capital available"
             
        # 2. Check Market Volatility (Beta)
        try:
            beta = yf.Ticker(ticker).info.get('beta', 1.0)
            if beta > 1.3:
                mode = "SIP (Staggered Entry)" # High volatility -> SIP to average cost
                reason = "High Stock Volatility"
        except:
            pass
            
        return f"{mode} - Reason: {reason}"

    def _screen_stocks(self, sector: str, market: str) -> List[str]:
        """Simple screener using LLM to get sector leaders"""
        try:
            prompt = f"""List 5 top stock tickers for the {sector} sector in the {market} market. 
            Return ONLY a JSON list of strings, e.g. ["AAPL", "MSFT"]. 
            Do not include markdown formatting."""
            
            response = self.llm_manager.invoke([HumanMessage(content=prompt)])
            return json.loads(response.content.replace('```json', '').replace('```', '').strip())
        except:
            print("⚠️ Screener LLM failed. No candidates generated.")
            return []

    def _analyze_reddit_sentiment(self, tickers: List[str]) -> Dict[str, float]:
        """Check r/stocks and r/investing for sentiment"""
        scores = {}
        if not self.reddit:
            return {t: 0 for t in tickers}
            
        for ticker in tickers:
            try:
                score = 0
                count = 0
                for sub in ['stocks', 'investing', 'wallstreetbets']:
                    try:
                        subreddit = self.reddit.subreddit(sub)
                        for post in subreddit.search(ticker, time_filter='week', limit=5):
                            score += post.score 
                            count += 1
                    except:
                        continue # Skip individual sub failures
                scores[ticker] = score / count if count > 0 else 0
            except:
                scores[ticker] = 0 # Silent fail per ticker
        return scores

    def _run_backtests(self, tickers: List[str]) -> Dict[str, Any]:
        results = {}
        for ticker in tickers:
            try:
                hist = yf.download(ticker, period="1y", progress=False)
                if not hist.empty:
                    ret = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                    results[ticker] = {"return_1y": round(float(ret), 2)}
                else:
                    results[ticker] = {"return_1y": 0.0}
            except:
                results[ticker] = {"return_1y": 0.0}
        return results

    def _select_winner(self, candidates, sentiment, backtests):
        if not candidates:
            return "SPY"
        best_score = -float('inf')
        winner = candidates[0]
        for t in candidates:
            ret = backtests.get(t, {}).get('return_1y', 0)
            sent = sentiment.get(t, 0)
            norm_sent = min(sent, 100)
            score = (ret * 0.4) + (norm_sent * 0.6)
            if score > best_score:
                best_score = score
                winner = t
        return winner

    def _deep_research_robust(self, ticker: str) -> Dict[str, Any]:
        """Deep Dive with prioritized fallbacks (Tavily -> NewsDataIO -> Finnhub)"""
        research = {}
        
        # 0. Ask Gemini to generate the best search queries for this specific stock
        try:
            print(f"   🧠 Asking Gemini for best search queries on {ticker}...")
            query_prompt = f"Generate 1 targeted search query to find {ticker}'s key suppliers, risks, or major recent contracts. Return ONLY the raw query string."
            search_query = self.llm_manager.invoke([HumanMessage(content=query_prompt)]).content.strip().replace('"', '')
            print(f"   ➤ Gemini suggested: '{search_query}'")
        except:
            search_query = f"{ticker} supply chain risks and major contracts"

        # 1. Try Tavily (Primary)
        if self.tavily:
            try:
                print("   Trying Tavily...")
                res = self.tavily.search(search_query, max_results=3)
                research['summary'] = [r['content'] for r in res.get('results', [])]
                research['source'] = 'Tavily'
                return research # Success, return early
            except Exception as e:
                print(f"   ⚠️ Tavily failed ({e}), trying fallback...")

        # 2. Try NewsDataIO (Fallback A)
        news_key = os.getenv("NEWSDATAIO_API_KEY")
        if news_key:
            try:
                print("   Trying NewsDataIO...")
                url = "https://newsdata.io/api/1/news"
                # NewsDataIO has strict query limits, use simpler query here
                params = {
                    "apikey": news_key,
                    "q": f"{ticker} AND (supplier OR client)",
                    "language": "en"
                }
                r = requests.get(url, params=params)
                data = r.json()
                if data.get('results'):
                    research['summary'] = [a['title'] for a in data.get('results', [])[:3]]
                    research['source'] = 'NewsDataIO'
                    return research
            except Exception as e:
                print(f"   ⚠️ NewsDataIO failed ({e}), trying fallback...")

        # 3. Try Finnhub (Fallback B)
        if self.finnhub_client:
            try:
                print("   Trying Finnhub...")
                news = self.finnhub_client.company_news(ticker, _from="2024-01-01", to="2025-01-01")
                if news:
                    research['summary'] = [n['headline'] for n in news[:3]]
                    research['source'] = 'Finnhub'
                    return research
            except:
                pass
        
        research['summary'] = ["No specific supply chain data found."]
        return research

    def _get_current_price_robust(self, ticker):
        """Get price from YFinance, fallback to Finnhub"""
        # 1. YFinance
        try:
            return yf.Ticker(ticker).fast_info.last_price
        except:
            pass
            
        # 2. Finnhub
        if self.finnhub_client:
            try:
                quote = self.finnhub_client.quote(ticker)
                if quote and quote['c']:
                    return quote['c']
            except:
                pass
        
        return 0.0
