from gnews import GNews
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from backend.backend1.core.llm_client import LLMClient
import json
import re
import os
import random
import time

class GNewsIntelligenceAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.vader = SentimentIntensityAnalyzer()
        self.ticker_map = self._load_mappings()
        
        # Institutional Financial Keywords for Weighting
        self.impact_keywords = {
            "bullish": {
                "upgrade": 1.5,
                "buy rating": 1.5,
                "outperform": 1.2,
                "earnings beat": 2.0,
                "revenue growth": 1.2,
                "acquisition": 1.5,
                "partnership": 1.1,
                "dividend increase": 1.3,
                "breakout": 1.1,
                "order win": 1.4,
                "expansion": 1.1
            },
            "bearish": {
                "downgrade": 1.5,
                "sell rating": 1.5,
                "underperform": 1.2,
                "earnings miss": 2.0,
                "profit warning": 2.0,
                "layoffs": 1.3,
                "lawsuit": 1.4,
                "investigation": 1.4,
                "scam": 2.0,
                "default": 2.0,
                "debt concern": 1.3
            }
        }

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
        if not name:
            return ""
            
        suffixes = [
            " Ltd.", " Ltd", " Limited", " Pvt.", " Pvt", " Inc.", " Inc", 
            " Corp.", " Corp", " Corporation", " plc", " PLC", " N.V.", 
            " AG", " S.A.", " SE", " (India)", " (The)", " Holdings", " Industries"
        ]
        clean = name
        for suffix in suffixes:
            clean = re.sub(re.escape(suffix) + r'\b', '', clean, flags=re.IGNORECASE)
            
        return clean.strip()

    def fetch_news(self, ticker, region="US"):
        # Determine company name
        company_name = self.ticker_map.get(ticker)
        clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
        
        target_name = company_name if company_name else clean_ticker
        clean_target = self._clean_company_name(target_name)

        print(f"[{ticker}] Fetching Google News for '{clean_target}' ({region})...")
        
        # Configure GNews
        if ".NS" in ticker or ".BO" in ticker:
            country = 'IN'
        elif region == "India":
            country = 'IN'
        else:
            country = 'US'

        google_news = GNews(
            language='en',
            country=country,
            max_results=5,
            period='7d'
        )

        try:
            # Query: Name + stock news
            query = f'"{clean_target}" stock news'
            articles = google_news.get_news(query)
        except Exception as e:
            print(f"News fetch error for {ticker}: {e}")
            return [], clean_target

        return articles, clean_target

    def _calculate_quant_score(self, articles):
        """Deterministic news scoring using VADER + Financial Keyword Matching."""
        if not articles:
            return 0.5, 0.0 # Neutral

        total_compound = 0
        impact_multiplier = 1.0
        
        for a in articles:
            text = f"{a.get('title', '')} {a.get('description', '')}".lower()
            
            # VADER Score
            vs = self.vader.polarity_scores(text)
            total_compound += vs['compound']
            
            # Keyword Impact
            for kw, weight in self.impact_keywords["bullish"].items():
                if kw in text:
                    impact_multiplier += (weight - 1.0)
            
            for kw, weight in self.impact_keywords["bearish"].items():
                if kw in text:
                    impact_multiplier -= (weight - 1.0)

        # Average sentiment
        avg_sentiment = total_compound / len(articles)
        
        # Blend & Clamp
        # Map -1 to 1 into 0 to 1 range
        final_score = (avg_sentiment * impact_multiplier + 1) / 2
        final_score = max(0.0, min(1.0, final_score))
        
        # Confidence based on agreement
        agreement = 1.0 - abs(avg_sentiment) # Simpler proxy: if very polarized, high signal
        
        return final_score, agreement

    def format_articles(self, articles):
        if not articles:
            return ""

        formatted = ""
        for a in articles:
            formatted += f"Title: {a.get('title')}\n"
            pub = a.get('publisher')
            if isinstance(pub, dict):
                pub = pub.get('title', 'Unknown')
            formatted += f"Source: {pub}\n"
            formatted += f"Date: {a.get('published date')}\n"
            formatted += f"Link: {a.get('url')}\n"
            formatted += "\n"

        return formatted.strip()

    def analyze(self, ticker, company_name, articles_text, quant_score):
        if not articles_text:
             return {
                "sentiment": "Neutral",
                "sentiment_score": quant_score,
                "bullish_catalysts": [],
                "risks": [],
                "short_term_impact": "Neutral",
                "confidence": 0.1
            }

        prompt = f"""
You are a professional financial news analyst.

Stock: {ticker}
Company: {company_name}
Quant Scorer Sentiment: {quant_score:.2f} (0=Bearish, 0.5=Neutral, 1=Bullish)

Recent Articles:
{articles_text}

Analyze:
1. Overall sentiment (Bullish/Neutral/Bearish)
2. Top 3 bullish catalysts
3. Top 3 risks
4. Evaluation of short-term market impact.
5. Give confidence score between 0 and 1.

Return structured JSON only.
Format:
{{
  "sentiment": "Bullish | Neutral | Bearish",
  "sentiment_score": 0.0-1.0,
  "bullish_catalysts": [],
  "risks": [],
  "short_term_impact": "Positive | Neutral | Negative",
  "confidence": 0.0-1.0
}}
"""
        try:
             response = self.llm.run_model(
                model="validator",
                messages=[
                    {"role": "system", "content": "You are a professional financial news analyst. Return structured JSON only. Do not hallucinate."},
                    {"role": "user", "content": prompt}
                ]
            )
             match = re.search(r'\{.*\}', response, re.DOTALL)
             if match:
                 analysis = json.loads(match.group(0))
                 # Blend with Quant Score (70% LLM, 30% Quant)
                 analysis["sentiment_score"] = (analysis.get("sentiment_score", 0.5) * 0.7) + (quant_score * 0.3)
                 return analysis
        except Exception as e:
             print(f"LLM analysis error: {e}")
        
        return {
                "sentiment": "Neutral",
                "sentiment_score": quant_score,
                "bullish_catalysts": [],
                "risks": [],
                "short_term_impact": "Neutral",
                "confidence": 0.1
            }

    def run(self, ticker, region="US"):
        articles, company_name = self.fetch_news(ticker, region)
        
        # 1. Deterministic Quant Scorer
        quant_score, quant_confidence = self._calculate_quant_score(articles)
        
        # 2. LLM Analysis
        formatted = self.format_articles(articles)
        analysis = self.analyze(ticker, company_name, formatted, quant_score)
        
        # Merge for compatibility
        analysis["articles"] = articles
        analysis["ticker"] = ticker
        analysis["quant_score"] = quant_score
        
        # Legacy fields
        analysis["bullish_signals"] = analysis.get("bullish_catalysts", [])
        analysis["bearish_signals"] = analysis.get("risks", [])
        analysis["risk_flags"] = analysis.get("risks", [])
        analysis["catalysts"] = analysis.get("bullish_catalysts", [])
        
        # Ensure sentiment_score is captured
        if "sentiment_score" not in analysis:
            analysis["sentiment_score"] = quant_score
            
        return analysis

