from ddgs import DDGS
from backend.backend1.core.llm_client import LLMClient
from backend.backend1.agents.web_search_agent import WebSearchAgent
import json
import os
import re
import time
import random

class NewsFetcher:
    def __init__(self):
        self.web_agent = WebSearchAgent()
        self.ticker_map = self._load_mappings()

    def _load_mappings(self):
        """Loads ticker to company name mappings from JSON files."""
        mapping = {}
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "..", "..", "data")
            
            # Load India
            india_path = os.path.join(data_dir, "nifty500.json")
            if os.path.exists(india_path):
                with open(india_path, "r") as f:
                    data = json.load(f)
                    for item in data:
                        symbol = item.get("Symbol")
                        name = item.get("Company Name")
                        if symbol and name:
                            mapping[f"{symbol}.NS"] = name
                            mapping[f"{symbol}.BO"] = name
            
            # Load US
            us_path = os.path.join(data_dir, "us_stocks.json")
            if os.path.exists(us_path):
                with open(us_path, "r") as f:
                    data = json.load(f)
                    for item in data:
                        symbol = item.get("Symbol")
                        name = item.get("Company Name")
                        if symbol and name:
                            mapping[symbol] = name
                            
        except Exception as e:
            print(f"⚠️ Warning: Could not load ticker mappings: {e}")
            
        return mapping

    def _clean_company_name(self, name):
        """Removes common corporate suffixes for cleaner search queries."""
        suffixes = [
            " Ltd.", " Ltd", " Limited", " Inc.", " Inc", " Corp.", " Corp", 
            " Corporation", " plc", " PLC", " N.V.", " AG", " S.A.", " SE",
            " (India)", " (The)"
        ]
        clean = name
        for suffix in suffixes:
            clean = clean.replace(suffix, "")
        return clean.strip()

    def fetch(self, ticker, max_results=8):
        print(f"[{ticker}] Fetching DDG news...")
        
        # RATE LIMIT: Random sleep 1-3s to prevent 202
        time.sleep(random.uniform(1.0, 3.0))

        # 1. Cleaner Query Construction
        company_name = self.ticker_map.get(ticker)
        clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
        
        if company_name:
            # Clean the name (e.g. "Tata Consultancy Services Ltd." -> "Tata Consultancy Services")
            clean_name = self._clean_company_name(company_name)
            # "Tata Consultancy Services stock news last 7 days India"
            suffix = " India" if ".NS" in ticker or ".BO" in ticker else ""
            query = f'"{clean_name}" stock news last 7 days{suffix}'
            print(f"🔎 Searching for: {query}")
        else:
            # Fallback
            query = f"{clean_ticker} stock news last 7 days"
            print(f"🔎 Searching for: {query}")

        results = []

        try:
            # 2. Deterministic DDG Search
            # DDGS might not support context manager in all versions, check usage if error
            with DDGS() as ddgs:
                # Use news search if available, fallback to text
                news_gen = ddgs.news(query, max_results=max_results)
                if not news_gen:
                    news_gen = ddgs.text(query, max_results=max_results)
                    
                if news_gen:
                    for r in news_gen:
                        results.append({
                            "title": r.get("title"),
                            "snippet": r.get("body") or r.get("snippet"),
                            "url": r.get("href") or r.get("url"),
                            "date": r.get("date")
                        })
        except Exception as e:
            print(f"News fetch error for {ticker}: {e}")
            
        # GUARD: If no articles found, skip AI summary to save time/cost
        if not results:
             print(f"⚠️ No articles found for {ticker}. Skipping AI Summary.")
             return {
                 "articles": [],
                 "ai_summary": ""
             }

        # 3. AI Summary via WebSearchAgent (Compound)
        ai_summary = ""
        try:
             print(f"[{ticker}] Generating AI Summary...")
             target_name = self._clean_company_name(company_name) if company_name else clean_ticker
             summary_query = f"Recent major news and market sentiment for {target_name} stock"
             ai_result = self.web_agent.run(summary_query)
             ai_summary = ai_result.get("summary", "")
        except Exception as e:
             print(f"AI Summary fetch error: {e}")

        return {
            "articles": results,
            "ai_summary": ai_summary,
            "company_name": company_name or clean_ticker
        }


class NewsAnalysisAgent:
    def __init__(self):
        self.llm = LLMClient()

    def analyze(self, ticker, news_data):
        print(f"[{ticker}] Analyzing news structure...")
        
        # Guard against dumb calls
        if not news_data.get("articles") and not news_data.get("ai_summary"):
             return self._get_fallback_sentiment()

        # Limit context to avoid overflow/cost
        articles = news_data.get("articles", [])[:6]
        ai_summary = news_data.get("ai_summary", "")[:1000]
        company_name = news_data.get("company_name", ticker)

        articles_text = json.dumps(articles, indent=2)

        prompt = f"""
        Stock: {ticker}
        Company: {company_name}

        Recent Articles (last 7 days):
        {articles_text}
        
        AI Context:
        {ai_summary}

        Instructions:
        1. Determine overall sentiment.
        2. Extract top 3 bullish catalysts.
        3. Extract top 3 risks.
        4. Evaluate short-term market impact.
        5. Give confidence score between 0 and 1.

        Return JSON in this exact format:

        {{
          "sentiment": "Bullish | Neutral | Bearish",
          "sentiment_score": 0.0 to 1.0,
          "bullish_catalysts": ["catalyst 1", "catalyst 2"],
          "risks": ["risk 1", "risk 2"],
          "short_term_impact": "Positive | Neutral | Negative",
          "confidence": 0.0 to 1.0
        }}
        """

        try:
            response = self.llm.run_model(
                model="validator", # Use medium model
                messages=[
                    {"role": "system", "content": "You are a professional financial news analyst. Return structured JSON only. Do not hallucinate."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            print(f"News analysis error for {ticker}: {e}")
            raise e # Re-raise to allow Orchestrator to handle 429 global cooldown
            
        return self._get_fallback_sentiment()

    def _get_fallback_sentiment(self):
        return {
            "sentiment": "Neutral",
            "sentiment_score": 0.5,
            "bullish_catalysts": [],
            "risks": [],
            "short_term_impact": "Neutral",
            "confidence": 0.1
        }

class StockNewsAgent:
    def __init__(self):
        self.fetcher = NewsFetcher()
        self.analyzer = NewsAnalysisAgent()

    def run(self, ticker):
        news_data = self.fetcher.fetch(ticker)
        
        # Check if we have any data
        if not news_data.get("articles") and not news_data.get("ai_summary"):
            return {
                "ticker": ticker,
                "articles": [],
                "sentiment_score": 0.5,
                "bullish_signals": [],
                "bearish_signals": [],
                "risk_flags": [],
                "catalysts": [],
                "sentiment": "Neutral",
                "confidence": 0.0
            }
            
        analysis = self.analyzer.analyze(ticker, news_data)

        # Merge results & Normalize for backward compatibility
        return {
            "ticker": ticker,
            "articles": news_data.get("articles", []),
            
            # New Keys
            **analysis,
            
            # Legacy mapping for SummaryBuilder
            "bullish_signals": analysis.get("bullish_catalysts", []),
            "bearish_signals": analysis.get("risks", []),
            "risk_flags": analysis.get("risks", []),
            "catalysts": analysis.get("bullish_catalysts", [])
        }
