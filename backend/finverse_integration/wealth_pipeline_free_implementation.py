# Finverse Wealth Pipeline - FREE Implementation
# Uses: Google Gemini (Free), Yahoo Finance (Free), DuckDuckGo (Free)

"""
Installation:
pip install langchain-google-genai langgraph yfinance duckduckgo-search pydantic python-dotenv

Required API Keys (ALL FREE):
- Google Gemini: https://makersuite.google.com/app/apikey
"""

import os
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field
import json
import pandas as pd
import re
import ast
import math

# Free LLM - Google Gemini (legacy)
from langchain_google_genai import ChatGoogleGenerativeAI

# Free Data Sources
import yfinance as yf
try:
    from ddgs import DDGS  # renamed package
except Exception:
    DDGS = None

try:
    from gnews import GNews
except Exception:
    GNews = None

try:
    from groq import Groq
except Exception:
    Groq = None

# LangGraph
from langgraph.graph import StateGraph, END

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Free resources configuration"""
    
    # Google Gemini (Free - 60 requests/minute)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Get from https://makersuite.google.com/app/apikey
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
    
    # Data sources (all free)
    ENABLE_YAHOO_FINANCE = True
    ENABLE_DUCKDUCKGO = True
    
    # Smart defaults
    DEFAULT_MARKET = "IN"  # India
    MAX_STOCKS = 5
    MAX_NEWS_RESULTS = int(os.getenv("MAX_NEWS_RESULTS", "2"))
    MAX_SECTOR_NEWS_SECTORS = int(os.getenv("MAX_SECTOR_NEWS_SECTORS", "0"))  # 0=all
    MAX_STOCK_NEWS_STOCKS = int(os.getenv("MAX_STOCK_NEWS_STOCKS", "0"))  # 0=all
    MAX_STOCK_INFO_STOCKS = int(os.getenv("MAX_STOCK_INFO_STOCKS", "0"))  # 0=all
    MAX_STOCK_LLM_CANDIDATES = int(os.getenv("MAX_STOCK_LLM_CANDIDATES", "50"))  # limit prompt size
    YF_PRICE_PERIOD = os.getenv("YF_PRICE_PERIOD", "6mo")
    MAX_SECTOR_SAMPLES = 5
    MAX_STOCK_CANDIDATES = 20
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "10"))
    CHUNK_TOP_K = int(os.getenv("CHUNK_TOP_K", "2"))


# =============================================================================
# UNIVERSE HELPERS (JSON)
# =============================================================================

def _data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def _load_universe(market: str) -> List[Dict[str, Any]]:
    market_code = (market or Config.DEFAULT_MARKET).upper()
    file_path = _data_dir() / ("us_stocks.json" if market_code in ["US", "USA"] else "nifty500.json")
    if not file_path.exists():
        return []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _get_sector_key(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "Industry"
    # Prefer Industry, then Sector
    sample = records[0]
    if "Industry" in sample:
        return "Industry"
    if "Sector" in sample:
        return "Sector"
    # Find any record with industry/sector
    for rec in records:
        if "Industry" in rec:
            return "Industry"
        if "Sector" in rec:
            return "Sector"
    return "Industry"


def _normalize_sector(value: Any) -> str:
    return str(value).strip()


def _limit_list(items: List[Any], limit: int) -> List[Any]:
    if limit and limit > 0:
        return items[:limit]
    return items


def _chunk_list(items: List[Any], size: int) -> List[List[Any]]:
    if size <= 0:
        return [items]
    return [items[i:i + size] for i in range(0, len(items), size)]


def _normalize_news_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": item.get("title") or item.get("heading") or "",
        "snippet": item.get("body") or item.get("snippet") or item.get("description") or "",
        "url": item.get("url") or item.get("href") or "",
        "source": item.get("source") or "",
        "date": item.get("date") or item.get("published") or "",
    }


def _fetch_ddg_news(ddg: Any, query: str, max_results: int) -> List[Dict[str, Any]]:
    if not ddg:
        return []
    results: List[Dict[str, Any]] = []
    try:
        results = list(ddg.news(keywords=query, max_results=max_results))
    except Exception:
        try:
            results = list(ddg.news(query=query, max_results=max_results))
        except Exception:
            try:
                results = list(ddg.text(keywords=query, max_results=max_results))
            except Exception:
                results = []
    return [_normalize_news_item(r) for r in results if isinstance(r, dict)]


def _fetch_gnews_news(query: str, max_results: int, market: str) -> List[Dict[str, Any]]:
    if not GNews:
        return []

    q = (query or "").strip()
    if not q:
        return []

    market_code = (market or Config.DEFAULT_MARKET).upper()
    country = "IN" if market_code in ["IN", "INDIA"] else "US"

    try:
        google_news = GNews(language="en", country=country, max_results=max_results, period="7d")
        articles = google_news.get_news(q) or []
    except Exception:
        return []

    normalized: List[Dict[str, Any]] = []
    for a in articles:
        if not isinstance(a, dict):
            continue
        publisher = a.get("publisher")
        source = publisher.get("title") if isinstance(publisher, dict) else (publisher or "")
        normalized.append(
            {
                "title": a.get("title") or "",
                "snippet": a.get("description") or "",
                "url": a.get("url") or "",
                "source": source or "",
                "date": a.get("published date") or a.get("published") or "",
            }
        )
    return normalized


def _fetch_free_news(ddg: Any, query: str, max_results: int, market: str) -> List[Dict[str, Any]]:
    # Prefer GNews; fallback to DDG.
    results = _fetch_gnews_news(query, max_results, market)
    if results:
        return results
    return _fetch_ddg_news(ddg, query, max_results)

def _strip_asterisks(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("*", "").strip()
    return value


def _fetch_yf_price_metrics(symbols: List[str], period: str) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    try:
        data = yf.download(
            " ".join(symbols),
            period=period,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception:
        return {}

    metrics: Dict[str, Dict[str, Any]] = {}

    def _compute(close: pd.Series) -> Dict[str, Any]:
        close = close.dropna()
        if close.empty:
            return {}
        current = float(close.iloc[-1])
        first = float(close.iloc[0]) if len(close) > 0 else current
        total_return = ((current - first) / first * 100) if first else 0.0
        lookback = 21 if len(close) >= 21 else 1
        past = float(close.iloc[-lookback]) if len(close) >= lookback else first
        momentum_1m = ((current - past) / past * 100) if past else 0.0
        daily = close.pct_change().dropna()
        vol = float(daily.std() * (252 ** 0.5) * 100) if len(daily) > 1 else 0.0
        return {
            "current_price": current,
            "return_period_pct": total_return,
            "momentum_1m_pct": momentum_1m,
            "volatility_annualized_pct": vol,
        }

    try:
        if hasattr(data, "columns") and isinstance(data.columns, pd.MultiIndex):
            for sym in symbols:
                try:
                    if sym in data.columns.levels[0]: # type: ignore
                        close = data[sym]["Close"]
                        metrics[sym] = _compute(close)
                except Exception:
                    continue
        else:
            close = data["Close"]
            metrics[symbols[0]] = _compute(close)
    except Exception:
        pass

    return metrics


def _safe_json_loads(content: str) -> Any:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = re.sub(r"//.*", "", text)
    text = text.strip()

    match = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if match:
        text = match.group(1)

    try:
        return json.loads(text)
    except Exception:
        text2 = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(text2)
        except Exception:
            text3 = (
                text2.replace("null", "None")
                .replace("true", "True")
                .replace("false", "False")
            )
    return ast.literal_eval(text3)


def _is_valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _format_symbol(symbol: str, market: str) -> str:
    market_code = (market or Config.DEFAULT_MARKET).upper()
    sym = str(symbol).strip()
    if market_code in ["IN", "INDIA"]:
        return sym if sym.endswith(".NS") else f"{sym}.NS"
    return sym

# =============================================================================
# STATE MODELS
# =============================================================================

class ExtractedProfile(BaseModel):
    """Smart extraction from any input format"""
    age: Optional[int] = None
    income_annual: Optional[str] = None  # "5L", "10-15L", "1Cr"
    investment_amount: Optional[str] = None
    time_horizon_years: Optional[int] = None
    risk_tolerance: Optional[str] = None  # "conservative", "moderate", "aggressive"
    primary_goal: Optional[str] = None
    existing_investments: Optional[str] = None
    confidence_score: float = Field(default=0.0, description="0-1 confidence in extraction")
    missing_fields: List[str] = Field(default_factory=list)

class StockRecommendation(BaseModel):
    symbol: str
    name: str
    sector: str
    rationale: str
    allocation_percent: float
    current_price: Optional[float] = None

class WealthState(BaseModel):
    """Dynamic state - no rigid templates"""
    
    # Input (any format)
    raw_input: str = ""
    input_channel: str = "chat"  # chat, email, voice, whatsapp
    market: str = Config.DEFAULT_MARKET  # IN or US
    
    # Extracted user data (progressive)
    extracted_profile: Optional[ExtractedProfile] = None
    risk_score: int = 5  # 1-10
    
    # Market intelligence
    market_data: Dict[str, Any] = Field(default_factory=dict)
    news_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Recommendations
    recommended_sectors: List[str] = Field(default_factory=list)
    stock_recommendations: List[StockRecommendation] = Field(default_factory=list)
    selection_rationale: List[Dict[str, Any]] = Field(default_factory=list)
    rejection_rationale: List[Dict[str, Any]] = Field(default_factory=list)
    allocation: Dict[str, float] = Field(default_factory=dict)
    trade_plans: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Communication
    clarification_questions: List[str] = Field(default_factory=list)
    final_report: str = ""
    
    # Execution
    current_step: str = ""
    errors: List[str] = Field(default_factory=list)
    execution_log: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True

# =============================================================================
# FREE LLM SETUP
# =============================================================================

class _GroqLLM:
    def __init__(self, api_key: Optional[str], model: str, temperature: float):
        if Groq is None:
            raise RuntimeError("Groq SDK not installed. Install `groq` to use Groq LLM.")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing.")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return type("GroqResponse", (), {"content": content})


def get_free_llm(temperature: float = 0.7):
    """Initialize LLM (Groq only)"""
    if Config.LLM_PROVIDER != "groq":
        # Force Groq usage regardless of env
        provider = "groq"
    else:
        provider = "groq"

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", Config.GROQ_API_KEY)
        model_name = os.getenv("GROQ_MODEL", Config.GROQ_MODEL)
        return _GroqLLM(api_key=api_key, model=model_name, temperature=temperature)

    # Fallback (should not reach when using only Groq)
    model_name = os.getenv("GEMINI_MODEL", Config.GEMINI_MODEL)
    api_key = os.getenv("GEMINI_API_KEY", Config.GEMINI_API_KEY)
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
    )

# =============================================================================
# SMART AGENTS (FREE RESOURCES)
# =============================================================================

class SmartIntakeAgent:
    """Extracts structured data from ANY input format using free LLM"""
    
    def __init__(self):
        self.llm = get_free_llm(temperature=0.3)
    
    def run(self, state: WealthState) -> WealthState:
        """Extract user profile from raw input"""
        state.current_step = "intelligent_intake"
        state.execution_log.append("🧠 Smart extraction started")
        
        prompt = f"""You are an expert at understanding investment queries.
        
Extract information from this user input:
"{state.raw_input}"

Extract ONLY what is clearly stated. Don't assume.

Return JSON with:
{{
    "age": <int or null>,
    "income_annual": "<amount or null>",  // e.g., "5L", "10-15L", "50000"
    "investment_amount": "<amount or null>",
    "time_horizon_years": <int or null>,
    "risk_tolerance": "<conservative|moderate|aggressive or null>",
    "primary_goal": "<goal or null>",  // e.g., "retirement", "child education"
    "existing_investments": "<details or null>",
    "confidence_score": <0.0-1.0>,  // how confident are you in this extraction?
    "missing_fields": [<list of critical missing info>]
}}

Be conservative with confidence. If input is vague, confidence should be low.
"""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Parse JSON from response
            content = response.content
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            extracted_data = _safe_json_loads(content)
            state.extracted_profile = ExtractedProfile(**extracted_data)
            
            state.execution_log.append(f"✅ Extracted with {state.extracted_profile.confidence_score:.0%} confidence")
            
        except Exception as e:
            state.errors.append(f"Extraction failed: {str(e)}")
            state.extracted_profile = ExtractedProfile(confidence_score=0.0)
        
        return state

class SmartClarificationAgent:
    """Generates smart follow-up questions"""
    
    def __init__(self):
        self.llm = get_free_llm(temperature=0.7)
    
    def run(self, state: WealthState) -> WealthState:
        """Generate clarification questions if needed"""
        state.current_step = "clarification"
        
        if not state.extracted_profile:
            return state
        
        # Only ask if confidence is low
        if state.extracted_profile.confidence_score >= 0.7:
            state.execution_log.append("✅ Sufficient information, skipping clarification")
            return state
        
        state.execution_log.append("❓ Generating clarification questions")
        
        missing = state.extracted_profile.missing_fields
        questions = []
        
        # Smart, contextual questions
        if not state.extracted_profile.investment_amount or "investment_amount" in missing:
            questions.append("💰 How much are you looking to invest?")
        
        if not state.extracted_profile.time_horizon_years or "time_horizon" in missing:
            questions.append("⏰ What's your investment timeframe? (e.g., 1 year, 5 years, 10+ years)")
        
        if not state.extracted_profile.risk_tolerance or "risk_tolerance" in missing:
            questions.append(
                "📊 How comfortable are you with market ups and downs?\n"
                "   • Conservative (I want stability)\n"
                "   • Moderate (I can handle some volatility)\n"
                "   • Aggressive (I want maximum growth)"
            )
        
        if not state.extracted_profile.primary_goal or "goal" in missing:
            questions.append("🎯 What's the main goal for this investment? (e.g., retirement, buying a house, child's education)")
        
        state.clarification_questions = questions
        
        if questions:
            state.execution_log.append(f"Generated {len(questions)} clarification questions")
        
        return state

class SmartRiskProfiler:
    """Converts fuzzy risk descriptions to numeric score"""
    
    def __init__(self):
        self.llm = get_free_llm(temperature=0.2)
    
    def run(self, state: WealthState) -> WealthState:
        """Calculate risk score 1-10"""
        state.current_step = "risk_profiling"
        state.execution_log.append("📈 Calculating risk profile")
        
        if not state.extracted_profile:
            state.risk_score = 5
            return state
        
        profile = state.extracted_profile
        
        # Smart risk calculation using LLM
        prompt = f"""Calculate investment risk score (1-10) based on:

Age: {profile.age or 'unknown'}
Income: {profile.income_annual or 'unknown'}
Time Horizon: {profile.time_horizon_years or 'unknown'} years
Risk Tolerance: {profile.risk_tolerance or 'unknown'}
Goal: {profile.primary_goal or 'unknown'}

Risk Score Guide:
1-3: Conservative (capital preservation, minimal volatility)
4-6: Moderate (balanced growth, acceptable volatility)
7-10: Aggressive (maximum growth, high volatility tolerance)

Consider:
- Longer time horizon → higher risk possible
- Younger age → higher risk possible
- Stable income → higher risk possible
- Explicit risk preference is most important

Return ONLY a single number between 1 and 10.
"""
        
        try:
            response = self.llm.invoke(prompt)
            score = int(response.content.strip()) # type: ignore
            state.risk_score = max(1, min(10, score))  # Clamp to 1-10
            state.execution_log.append(f"✅ Risk score: {state.risk_score}/10")
        except:
            state.risk_score = 5  # Safe default
            state.execution_log.append("⚠️ Using default risk score: 5/10")
        
        return state

class FreeMarketDataAgent:
    """Fetches market data from FREE sources"""
    
    def __init__(self):
        self.ddg = DDGS() if DDGS else None
        self.llm = get_free_llm()
    
    def run(self, state: WealthState) -> WealthState:
        """Fetch news and market data"""
        state.current_step = "market_data_fetch"
        state.execution_log.append("📰 Fetching free market data")
        
        try:
            # 1. Get current market sentiment (DuckDuckGo - FREE)
            market_code = (state.market or Config.DEFAULT_MARKET).upper()
            if market_code in ["US", "USA"]:
                news_query = "US stock market today S&P 500"
            else:
                news_query = "India stock market today NSE Nifty"
            news_results = _fetch_free_news(self.ddg, news_query, Config.MAX_NEWS_RESULTS, market_code)
            
            state.news_context["market_news"] = [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "url": r.get("url", "")
                }
                for r in news_results
            ]
            
            # 2. Get sector-specific news if sectors discovered
            if state.recommended_sectors:
                sector_news = {}
                for sector in state.recommended_sectors[:3]:  # Limit to avoid rate limits
                    sector_query = f"India {sector} stocks news today"
                    sector_results = _fetch_free_news(self.ddg, sector_query, Config.MAX_NEWS_RESULTS, market_code)
                    sector_news[sector] = [r.get("title", "") for r in sector_results]
                
                state.news_context["sector_news"] = sector_news
            
            # 3. Get market indices (Yahoo Finance - FREE)
            if market_code in ["US", "USA"]:
                indices = ["^GSPC", "^DJI", "^IXIC"]  # S&P 500, Dow, Nasdaq
            else:
                indices = ["^NSEI", "^NSEBANK"]  # Nifty 50, Bank Nifty
            index_data = {}
            
            for idx in indices:
                try:
                    ticker = yf.Ticker(idx)
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change_pct = ((current - prev) / prev * 100)
                        
                        index_data[idx] = {
                            "current": float(current),
                            "change_percent": float(change_pct),
                            "trend": "up" if change_pct > 0 else "down"
                        }
                except:
                    pass
            
            state.market_data["indices"] = index_data
            state.execution_log.append(f"✅ Fetched news + market data")
            
        except Exception as e:
            state.errors.append(f"Market data fetch error: {str(e)}")
            state.execution_log.append("⚠️ Limited market data available")
        
        return state

class SmartSectorDiscovery:
    """AI-powered sector discovery using free LLM + sector news"""

    def __init__(self):
        self.llm = get_free_llm(temperature=0.5)
        self.ddg = DDGS() if DDGS else None
        self._news_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _get_news(self, query: str, market_code: str) -> List[Dict[str, Any]]:
        cache_key = f"{(market_code or Config.DEFAULT_MARKET).upper()}::{query}"
        if cache_key in self._news_cache:
            return self._news_cache[cache_key]
        results = _fetch_free_news(self.ddg, query, Config.MAX_NEWS_RESULTS, market_code)
        self._news_cache[cache_key] = results
        return results

    def run(self, state: WealthState) -> WealthState:
        """Discover the single best sector using sector news + profiles"""
        state.current_step = "sector_discovery"
        state.execution_log.append("🔍 AI sector discovery")

        market_code = (state.market or Config.DEFAULT_MARKET).upper()
        market_label = "US" if market_code in ["US", "USA"] else "Indian"

        universe = _load_universe(market_code)
        sector_key = _get_sector_key(universe)

        # Build sector profiles from JSON universe
        sector_profiles: Dict[str, Dict[str, Any]] = {}
        for rec in universe:
            sec = _normalize_sector(rec.get(sector_key, ""))
            sym = rec.get("Symbol") or rec.get("Ticker") or rec.get("symbol")
            if not sec or not sym:
                continue
            symbol = _format_symbol(sym, market_code)
            name = rec.get("Company Name") or rec.get("name") or rec.get("Company") or symbol
            bucket = sector_profiles.setdefault(
                sec, {"sector": sec, "symbols": [], "companies": []}
            )
            bucket["symbols"].append(symbol)
            if name:
                bucket["companies"].append(name)

        if not sector_profiles:
            state.errors.append("No sector data found in JSON universe")
            return state

        # De-duplicate and finalize profiles
        for sec, bucket in sector_profiles.items():
            bucket["symbols"] = list(dict.fromkeys(bucket["symbols"]))
            bucket["companies"] = list(dict.fromkeys(bucket["companies"]))
            bucket["count"] = len(bucket["symbols"])

        sector_list = sorted(sector_profiles.keys())
        sector_news: Dict[str, List[Dict[str, Any]]] = {}

        sector_targets = _limit_list(sector_list, Config.MAX_SECTOR_NEWS_SECTORS)
        for sector in sector_targets:
            query = f"{market_label} {sector} sector stocks news"
            sector_news[sector] = self._get_news(query, market_code)

        state.news_context["sector_news"] = sector_news
        state.market_data["sector_profiles"] = sector_profiles

        # Market sentiment from indices
        market_sentiment = "neutral"
        indices = state.market_data.get("indices", {})
        if market_code in ["US", "USA"]:
            idx = indices.get("^GSPC", {}) or indices.get("^DJI", {}) or {}
        else:
            idx = indices.get("^NSEI", {}) or indices.get("^NSEBANK", {}) or {}
        if idx.get("trend") == "up":
            market_sentiment = "bullish"
        elif idx.get("trend") == "down":
            market_sentiment = "bearish"

        news_summary = ""
        if state.news_context.get("market_news"):
            news_summary = "\n".join(
                [f"- {n.get('title','')}" for n in state.news_context["market_news"][:3]]
            )

        horizon = state.extracted_profile.time_horizon_years if state.extracted_profile else None
        goal = state.extracted_profile.primary_goal if state.extracted_profile else None

        # Build lightweight sector payload for LLM
        sector_payload: Dict[str, Any] = {}
        for sector, payload in sector_profiles.items():
            sector_payload[sector] = {
                "sector": sector,
                "count": payload.get("count", 0),
                "sample_companies": payload.get("companies", [])[:3],
                "news_titles": [n.get("title", "") for n in sector_news.get(sector, [])[:2]],
            }

        # Chunked sector selection
        chunk_results: List[Dict[str, Any]] = []
        for chunk in _chunk_list(sector_list, Config.CHUNK_SIZE):
            chunk_data = {s: sector_payload.get(s, {}) for s in chunk}
            prompt = f"""You are an expert {market_label} stock market analyst.

Pick the top {Config.CHUNK_TOP_K} sectors from this chunk for this investor.

USER REQUEST:
{state.raw_input}

INVESTOR PROFILE:
- Risk Score: {state.risk_score}/10
- Time Horizon: {horizon if horizon is not None else 'unknown'} years
- Goal: {goal if goal else 'unknown'}

CURRENT MARKET:
- Sentiment: {market_sentiment}
- Recent Market News:
{news_summary}

SECTOR CHUNK (JSON):
{json.dumps(chunk_data, ensure_ascii=False)}

Return ONLY JSON:
{{
  "top_sectors": ["SectorA", "SectorB"],
  "reasons": {{"SectorA": "reason", "SectorB": "reason"}}
}}

Rules:
- Choose only from the chunk keys.
- No markdown, no code fences, no bullet symbols, no asterisks.
"""
            try:
                response = self.llm.invoke(prompt)
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                data = _safe_json_loads(content)
                top = data.get("top_sectors", []) or []
                reasons = data.get("reasons", {}) or {}
                chunk_results.append({"top_sectors": top, "reasons": reasons})
            except Exception:
                # Fallback to largest sectors within chunk
                ranked = sorted(
                    [(s, sector_profiles.get(s, {}).get("count", 0)) for s in chunk],
                    key=lambda x: x[1],
                    reverse=True,
                )
                top = [s for s, _ in ranked[: Config.CHUNK_TOP_K]]
                chunk_results.append({"top_sectors": top, "reasons": {}})

        state.market_data["sector_chunk_results"] = chunk_results

        # Build final candidate set from chunk winners
        candidate_sectors: List[str] = []
        candidate_reasons: Dict[str, str] = {}
        for res in chunk_results:
            for s in res.get("top_sectors", []):
                if s not in candidate_sectors:
                    candidate_sectors.append(s)
            for s, r in (res.get("reasons") or {}).items():
                if s and r:
                    candidate_reasons[s] = r

        candidate_data = {s: sector_payload.get(s, {}) for s in candidate_sectors}
        prompt_final = f"""You are an expert {market_label} stock market analyst.

Choose the SINGLE best sector for this investor from the shortlisted candidates.

USER REQUEST:
{state.raw_input}

INVESTOR PROFILE:
- Risk Score: {state.risk_score}/10
- Time Horizon: {horizon if horizon is not None else 'unknown'} years
- Goal: {goal if goal else 'unknown'}

CURRENT MARKET:
- Sentiment: {market_sentiment}
- Recent Market News:
{news_summary}

CANDIDATE SECTORS (JSON):
{json.dumps(candidate_data, ensure_ascii=False)}

CHUNK REASONS (JSON):
{json.dumps(candidate_reasons, ensure_ascii=False)}

Return ONLY JSON:
{{"best_sector": "<one sector name from candidates>"}}

Rules:
- Choose exactly one sector from candidate keys.
- No markdown, no code fences, no bullet symbols, no asterisks.
"""

        try:
            response = self.llm.invoke(prompt_final)
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            data = _safe_json_loads(content)
            best_sector = data.get("best_sector")
            if best_sector not in sector_profiles:
                raise ValueError("Best sector not in profiles")
            state.recommended_sectors = [best_sector]
            state.execution_log.append(f"✅ Selected sector: {best_sector}")
        except Exception:
            ranked = sorted(
                sector_profiles.items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True,
            )
            best = ranked[0][0] if ranked else ""
            if best:
                state.recommended_sectors = [best]
            state.execution_log.append("⚠️ Using data-driven sector fallback from JSON universe")

        return state

class SmartStockSelector:
    """AI-powered stock selection using sector news + full stock universe"""

    def __init__(self):
        self.llm = get_free_llm(temperature=0.4)
        self.ddg = DDGS() if DDGS else None
        self._news_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _get_news(self, query: str, market_code: str) -> List[Dict[str, Any]]:
        cache_key = f"{(market_code or Config.DEFAULT_MARKET).upper()}::{query}"
        if cache_key in self._news_cache:
            return self._news_cache[cache_key]
        results = _fetch_free_news(self.ddg, query, Config.MAX_NEWS_RESULTS, market_code)
        self._news_cache[cache_key] = results
        return results

    def run(self, state: WealthState) -> WealthState:
        """Select stocks using AI + Yahoo Finance data + per-stock news"""
        state.current_step = "stock_selection"
        state.execution_log.append("🎯 AI stock selection")

        if not state.recommended_sectors:
            state.errors.append("No sectors to select stocks from")
            return state

        market_code = (state.market or Config.DEFAULT_MARKET).upper()
        universe = _load_universe(market_code)
        sector_key = _get_sector_key(universe)

        # Use the best sector (first)
        selected_sector = state.recommended_sectors[0]

        records = [
            rec for rec in universe
            if _normalize_sector(rec.get(sector_key, "")) == selected_sector
        ]
        if not records:
            state.errors.append("No stocks found for selected sector")
            return state

        # Build stock records from JSON universe
        stock_records: List[Dict[str, Any]] = []
        for rec in records:
            sym = rec.get("Symbol") or rec.get("Ticker") or rec.get("symbol")
            if not sym:
                continue
            symbol = _format_symbol(sym, market_code)
            name = rec.get("Company Name") or rec.get("name") or rec.get("Company") or symbol
            stock_records.append({
                "symbol": symbol,
                "name": name,
                "sector": selected_sector,
                "raw": rec,
            })

        if not stock_records:
            state.errors.append("No valid symbols in selected sector")
            return state

        # Limit LLM candidate size to avoid token overload
        candidate_records = _limit_list(stock_records, Config.MAX_STOCK_LLM_CANDIDATES)

        # Fetch price metrics from Yahoo Finance for candidate symbols
        symbols_for_metrics = [r["symbol"] for r in _limit_list(candidate_records, Config.MAX_STOCK_INFO_STOCKS)]
        price_metrics = _fetch_yf_price_metrics(symbols_for_metrics, Config.YF_PRICE_PERIOD)

        # Fetch news for candidate symbols
        stock_news: Dict[str, List[Dict[str, Any]]] = {}
        news_targets = _limit_list(candidate_records, Config.MAX_STOCK_NEWS_STOCKS)
        for rec in news_targets:
            query = f"{rec['name']} {rec['symbol']} stock news"
            stock_news[rec["symbol"]] = self._get_news(query, market_code)

        state.news_context["stock_news"] = stock_news

        # Assemble stock data payload for LLM (bounded)
        stock_data: Dict[str, Any] = {}
        for rec in candidate_records:
            sym = rec["symbol"]
            metrics = price_metrics.get(sym, {})
            stock_data[sym] = {
                "name": rec["name"],
                "sector": rec["sector"],
                "price_metrics": {
                    "current_price": metrics.get("current_price"),
                    "momentum_1m_pct": metrics.get("momentum_1m_pct"),
                    "return_period_pct": metrics.get("return_period_pct"),
                    "volatility_annualized_pct": metrics.get("volatility_annualized_pct"),
                },
                "news_titles": [n.get("title", "") for n in stock_news.get(sym, [])[:2]],
            }

        horizon = state.extracted_profile.time_horizon_years if state.extracted_profile else None

        # Chunked stock selection
        chunk_results: List[Dict[str, Any]] = []
        for chunk in _chunk_list(candidate_records, Config.CHUNK_SIZE):
            chunk_symbols = [r["symbol"] for r in chunk]
            chunk_data = {s: stock_data.get(s, {}) for s in chunk_symbols}
            prompt = f"""You are an expert stock analyst.

Pick the top {Config.CHUNK_TOP_K} stocks from this chunk for this investor.

USER REQUEST:
{state.raw_input}

INVESTOR:
- Risk Score: {state.risk_score}/10
- Time Horizon: {horizon if horizon is not None else 'unknown'} years

CHOSEN SECTOR:
{selected_sector}

STOCK CHUNK (JSON):
{json.dumps(chunk_data, ensure_ascii=False)}

Return ONLY JSON:
{{
  "top_stocks": ["SYM1", "SYM2"],
  "reasons": {{"SYM1": "reason", "SYM2": "reason"}}
}}

Rules:
- Choose only from the chunk keys.
- No markdown, no code fences, no bullet symbols, no asterisks.
"""
            try:
                response = self.llm.invoke(prompt)
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                data = _safe_json_loads(content)
                top = data.get("top_stocks", []) or []
                reasons = data.get("reasons", {}) or {}
                chunk_results.append({"top_stocks": top, "reasons": reasons})
            except Exception:
                # Fallback to top momentum in this chunk
                ranked = sorted(
                    chunk,
                    key=lambda x: price_metrics.get(x["symbol"], {}).get("momentum_1m_pct", 0),
                    reverse=True,
                )
                top = [r["symbol"] for r in ranked[: Config.CHUNK_TOP_K]]
                chunk_results.append({"top_stocks": top, "reasons": {}})

        state.market_data["stock_chunk_results"] = chunk_results

        # Build final candidate set from chunk winners
        candidate_symbols: List[str] = []
        candidate_reasons: Dict[str, str] = {}
        for res in chunk_results:
            for s in res.get("top_stocks", []):
                if s not in candidate_symbols:
                    candidate_symbols.append(s)
            for s, r in (res.get("reasons") or {}).items():
                if s and r:
                    candidate_reasons[s] = r

        final_data = {s: stock_data.get(s, {}) for s in candidate_symbols}
        prompt_final = f"""You are an expert stock analyst.

Select the best {Config.MAX_STOCKS} stocks from the shortlisted candidates for this investor.
Use the user request, risk score, price metrics, and recent news.

USER REQUEST:
{state.raw_input}

INVESTOR:
- Risk Score: {state.risk_score}/10
- Time Horizon: {horizon if horizon is not None else 'unknown'} years

CHOSEN SECTOR:
{selected_sector}

CANDIDATE STOCKS (JSON):
{json.dumps(final_data, ensure_ascii=False)}

CHUNK REASONS (JSON):
{json.dumps(candidate_reasons, ensure_ascii=False)}

Return ONLY JSON in this exact shape (no markdown, no bullets, no asterisks):
{{
  "selected": [
    {{
      "symbol": "TCS.NS",
      "name": "Tata Consultancy Services",
      "sector": "Technology/IT",
      "rationale": "Short reason",
      "why_selected": "Why it fits this investor",
      "allocation_percent": 25.0,
      "current_price": 3500.0
    }}
  ],
  "rejected": [
    {{
      "symbol": "WIPRO.NS",
      "why_not_selected": "Reason"
    }}
  ],
  "rejected_summary": "Optional brief summary for remaining rejections"
}}

Rules:
- Select exactly {Config.MAX_STOCKS} stocks.
- allocation_percent must sum to 100.
- Provide why_not_selected for every non-selected stock if possible; otherwise include rejected_summary.
- No markdown, no code fences, no bullet symbols, no asterisks.
"""

        try:
            response = self.llm.invoke(prompt_final)
            content = response.content.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = _safe_json_loads(content)
            recommendations = parsed.get("selected", []) or []
            rejections = parsed.get("rejected", []) or []

            # Clean asterisks from text fields
            for r in recommendations:
                for k, v in list(r.items()):
                    r[k] = _strip_asterisks(v)
            for r in rejections:
                for k, v in list(r.items()):
                    r[k] = _strip_asterisks(v)

            # Normalize allocations
            total_alloc = 0.0
            for r in recommendations:
                try:
                    total_alloc += float(r.get("allocation_percent", 0) or 0)
                except Exception:
                    pass
            if total_alloc > 0:
                for r in recommendations:
                    try:
                        r["allocation_percent"] = round(float(r.get("allocation_percent", 0)) / total_alloc * 100, 2)
                    except Exception:
                        r["allocation_percent"] = 0.0

            # Fill missing current_price from metrics
            for r in recommendations:
                sym = r.get("symbol")
                if sym and not r.get("current_price"):
                    metrics = price_metrics.get(sym, {})
                    if metrics.get("current_price"):
                        r["current_price"] = metrics.get("current_price")

            # Enforce exact count
            if len(recommendations) > Config.MAX_STOCKS:
                recommendations = recommendations[: Config.MAX_STOCKS]
            elif len(recommendations) < Config.MAX_STOCKS:
                # Backfill with top momentum
                momentum_rank = sorted(
                    stock_records,
                    key=lambda x: price_metrics.get(x["symbol"], {}).get("momentum_1m_pct", 0),
                    reverse=True,
                )
                selected_syms = {r.get("symbol") for r in recommendations if r.get("symbol")}
                for rec in momentum_rank:
                    if len(recommendations) >= Config.MAX_STOCKS:
                        break
                    if rec["symbol"] in selected_syms:
                        continue
                    metrics = price_metrics.get(rec["symbol"], {})
                    recommendations.append({
                        "symbol": rec["symbol"],
                        "name": rec["name"],
                        "sector": rec["sector"],
                        "rationale": "Backfilled based on momentum within selected sector.",
                        "why_selected": "Backfilled to satisfy required count.",
                        "allocation_percent": round(100 / max(Config.MAX_STOCKS, 1), 2),
                        "current_price": metrics.get("current_price"),
                    })

            state.stock_recommendations = [StockRecommendation(**r) for r in recommendations]
            state.selection_rationale = [
                {
                    "symbol": r.get("symbol"),
                    "why_selected": r.get("why_selected") or r.get("rationale", "")
                }
                for r in recommendations
            ]

            # Build rejection rationale for all other stocks
            selected_symbols = {r.get("symbol") for r in recommendations if r.get("symbol")}
            all_symbols = [r["symbol"] for r in stock_records]
            rejected_symbols = [s for s in all_symbols if s not in selected_symbols]
            rejection_map = {
                r.get("symbol"): r.get("why_not_selected", "")
                for r in rejections if r.get("symbol")
            }
            for sym in rejected_symbols:
                if sym not in rejection_map:
                    rejection_map[sym] = (
                        "Not selected due to lower alignment with user goals, risk profile, "
                        "and/or weaker news or momentum versus selected picks."
                    )
            state.rejection_rationale = [
                {"symbol": sym, "why_not_selected": rejection_map.get(sym, "")}
                for sym in rejected_symbols
            ]

            state.execution_log.append(f"✅ Selected {len(state.stock_recommendations)} stocks")

        except Exception as e:
            state.errors.append(f"Stock selection error: {str(e)}")

            # Fallback: select top momentum from price metrics
            ranked = sorted(
                stock_records,
                key=lambda x: price_metrics.get(x["symbol"], {}).get("momentum_1m_pct", 0),
                reverse=True,
            )
            top = ranked[: Config.MAX_STOCKS]
            state.stock_recommendations = [
                StockRecommendation(
                    symbol=rec["symbol"],
                    name=rec["name"],
                    sector=rec["sector"],
                    rationale="Selected from top momentum in available universe.",
                    allocation_percent=round(100 / max(len(top), 1), 2),
                    current_price=price_metrics.get(rec["symbol"], {}).get("current_price"),
                )
                for rec in top
            ]
            state.selection_rationale = [
                {"symbol": rec.symbol, "why_selected": rec.rationale}
                for rec in state.stock_recommendations
            ]

            remaining = [r["symbol"] for r in ranked[Config.MAX_STOCKS:]]
            state.rejection_rationale = [
                {
                    "symbol": sym,
                    "why_not_selected": "Not selected due to lower momentum vs top picks.",
                }
                for sym in remaining
            ]

        return state


class BacktestTechnicalsAgent:
    """Derive buy/sell/stop using backtests + technicals."""

    def __init__(self):
        # Import lazily to avoid hard dependency at module import time
        from backend.finverse_integration.strategies.sma_crossover import run as run_sma
        from backend.finverse_integration.strategies.support_resistance import run as run_sr
        from backend.finverse_integration.strategies.rsi_strategy import run as run_rsi

        self.strategy_runners = {
            "SMA Crossover": run_sma,
            "Support/Resistance": run_sr,
            "RSI Momentum": run_rsi,
        }

    def run(self, state: WealthState) -> WealthState:
        state.current_step = "backtest_technicals"
        state.execution_log.append("📈 Running backtests + technical analysis")

        if not state.stock_recommendations:
            return state

        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        # Save HTML reports in backend/reports to align with existing /api/backtest/report/download
        reports_dir = Path(__file__).resolve().parents[1] / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        trade_plans: List[Dict[str, Any]] = []

        for rec in state.stock_recommendations:
            symbol = rec.symbol
            market = (state.market or Config.DEFAULT_MARKET).upper()
            strategy_results = {}
            best_strategy = None
            best_sharpe = None

            # Run backtests per strategy
            for name, runner in self.strategy_runners.items():
                try:
                    res = runner(
                        ticker=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        market=market,
                        initial_capital=100000,
                    )
                    summary = res.get("summary", {}) or {}
                    data = res.get("data")
                    trades = res.get("trades")

                    metrics = {
                        "totalReturn": float(str(summary.get("Total Return %", 0)).replace("%", "")),
                        "maxDrawdown": float(str(summary.get("Max Drawdown %", 0)).replace("%", "")),
                        "sharpeRatio": float(str(summary.get("Sharpe Ratio", 0)).replace("%", "")),
                        "totalTrades": int(summary.get("Number of Trades", 0) or 0),
                    }
                    final_equity = None
                    if hasattr(data, "get") or hasattr(data, "__getitem__"):
                        try:
                            if "Equity_Curve" in data.columns:
                                final_equity = float(data["Equity_Curve"].iloc[-1])
                        except Exception:
                            final_equity = None
                    metrics["finalEquity"] = final_equity or 0.0

                    strategy_results[name] = {
                        "metrics": metrics,
                        "data": data,
                        "trades": trades,
                    }

                    sharpe = metrics.get("sharpeRatio")
                    if best_sharpe is None or sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_strategy = name
                except Exception as e:
                    strategy_results[name] = {"error": str(e)}

            # Use support/resistance + SMA data if available
            sr_data = strategy_results.get("Support/Resistance", {}).get("data")
            sma_data = strategy_results.get("SMA Crossover", {}).get("data")

            current_price = None
            support = None
            resistance = None
            sma_short = None
            sma_long = None
            atr = None

            try:
                if sr_data is not None and not sr_data.empty:
                    current_price = float(sr_data["Close"].iloc[-1])
                    support = float(sr_data["Support"].dropna().iloc[-1])
                    resistance = float(sr_data["Resistance"].dropna().iloc[-1])
            except Exception:
                pass

            try:
                if sma_data is not None and not sma_data.empty:
                    current_price = current_price or float(sma_data["Close"].iloc[-1])
                    sma_short = float(sma_data["SMA_Short"].dropna().iloc[-1])
                    sma_long = float(sma_data["SMA_Long"].dropna().iloc[-1])

                    # ATR (14)
                    high = sma_data["High"]
                    low = sma_data["Low"]
                    close = sma_data["Close"]
                    prev_close = close.shift(1)
                    tr = (high - low).abs()
                    tr = tr.combine((high - prev_close).abs(), max)
                    tr = tr.combine((low - prev_close).abs(), max)
                    atr = float(tr.rolling(14).mean().iloc[-1])
            except Exception:
                pass

            # Normalize NaN/invalid numbers
            if not _is_valid_number(current_price):
                current_price = None
            if not _is_valid_number(support):
                support = None
            if not _is_valid_number(resistance):
                resistance = None
            if not _is_valid_number(sma_short):
                sma_short = None
            if not _is_valid_number(sma_long):
                sma_long = None
            if not _is_valid_number(atr):
                atr = None

            # Fallbacks
            if current_price is None:
                current_price = float(rec.current_price or 0) if rec.current_price else 0.0
            if not _is_valid_number(current_price):
                current_price = None
            if support is None and current_price:
                support = current_price * 0.95
            if resistance is None and current_price:
                resistance = current_price * 1.08
            if atr is None and current_price:
                atr = max(current_price * 0.02, 1e-6)

            # If we still don't have a valid price, skip trade levels safely
            if current_price is None or current_price <= 0:
                trade_plans.append(
                    {
                        "symbol": symbol,
                        "market": market,
                        "current_price": None,
                        "buy_at": None,
                        "sell_at": None,
                        "stop_loss": None,
                        "risk_reward": None,
                        "best_strategy": best_strategy,
                        "backtest_metrics": {
                            name: data.get("metrics", {})
                            for name, data in strategy_results.items()
                            if data.get("metrics")
                        },
                        "backtest_report_html": html_report,
                        "backtest_report_url": html_report_url,
                    }
                )
                continue

            # Ensure atr is numeric
            if atr is None or not isinstance(atr, (int, float)) or atr <= 0:
                atr = max(current_price * 0.02, 1e-6)

            # Trade levels
            if current_price and sma_short and sma_long and sma_short >= sma_long:
                buy_at = max(support or current_price * 0.98, sma_short)
            else:
                buy_at = max(support or current_price * 0.98, current_price * 0.98)

            sell_at = max(resistance or current_price * 1.08, buy_at + (2 * atr))
            stop_loss = max(0.0, buy_at - (1.5 * atr))
            rr = None
            if buy_at > stop_loss and sell_at > buy_at:
                rr = (sell_at - buy_at) / (buy_at - stop_loss)

            # Use existing portfolio report HTML (do not generate new files)
            html_report = None
            html_report_url = None
            portfolio_report = reports_dir / "portfolio_report.html"
            if portfolio_report.exists():
                html_report = portfolio_report.name
                html_report_url = f"/api/backtest/report/download/{portfolio_report.name}"

            trade_plans.append(
                {
                    "symbol": symbol,
                    "market": market,
                    "current_price": round(current_price, 2) if current_price else None,
                    "buy_at": round(buy_at, 2) if buy_at else None,
                    "sell_at": round(sell_at, 2) if sell_at else None,
                    "stop_loss": round(stop_loss, 2) if stop_loss else None,
                    "risk_reward": round(rr, 2) if rr else None,
                    "best_strategy": best_strategy,
                    "backtest_metrics": {
                        name: data.get("metrics", {})
                        for name, data in strategy_results.items()
                        if data.get("metrics")
                    },
                    "backtest_report_html": html_report,
                    "backtest_report_url": html_report_url,
                }
            )

        state.trade_plans = trade_plans
        state.execution_log.append("✅ Trade levels computed")
        return state

class SmartReportGenerator:
    """Channel-adaptive report generation"""
    
    def __init__(self):
        self.llm = get_free_llm(temperature=0.7)
    
    def run(self, state: WealthState) -> WealthState:
        """Generate final report adapted to channel"""
        state.current_step = "report_generation"
        state.execution_log.append("📝 Generating report")
        # Build structured report without LLM for consistent formatting
        def _as_dict(obj):
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, "dict"):
                return obj.dict()
            return {}

        recs = [_as_dict(rec) for rec in (state.stock_recommendations or [])]
        trade_plans = state.trade_plans or []

        market_code = (state.market or Config.DEFAULT_MARKET).upper()
        market_label = "United States" if market_code in ["US", "USA"] else "India"

        risk_score = state.risk_score or 5
        if risk_score <= 3:
            risk_profile = "Conservative"
            style = "Defensive Growth"
        elif risk_score <= 6:
            risk_profile = "Moderate"
            style = "Balanced Growth"
        else:
            risk_profile = "Aggressive"
            style = "Aggressive Growth"

        horizon = state.extracted_profile.time_horizon_years if state.extracted_profile else None
        horizon_label = f"{horizon} Years" if horizon else "Medium Term"
        top_sector = state.recommended_sectors[0] if state.recommended_sectors else "N/A"
        top_pick = recs[0].get("symbol") if recs else "N/A"

        total_equity = sum([float(r.get("allocation_percent", 0) or 0) for r in recs])
        equity_weight = f"{round(total_equity, 1)}%" if total_equity else "N/A"

        allocation_rows = "\n".join(
            [
                f"{r.get('symbol','')} | {r.get('name','')} | {round(float(r.get('allocation_percent',0) or 0),2)}%"
                for r in recs
            ]
        )

        highlights = "\n".join(
            [
                f"{r.get('symbol','')}: {r.get('rationale','')}"
                for r in recs
            ]
        )

        selected_why = "\n".join(
            [
                f"{r.get('symbol','')}: {r.get('why_selected','') or r.get('rationale','')}"
                for r in recs
            ]
        )


        trade_rows = "\n".join(
            [
                f"{p.get('symbol','')} | {p.get('buy_at','—')} | {p.get('sell_at','—')} | {p.get('stop_loss','—')} | {p.get('risk_reward','—')} | {p.get('best_strategy','—')}"
                for p in trade_plans
                if p.get("symbol")
            ]
        )

        executive_summary = (
            f"This portfolio targets a {risk_profile.lower()} investor with a {horizon_label} horizon. "
            f"The focus is {top_sector} with a balanced allocation across {len(recs)} stocks. "
            f"Selections are based on sector strength, recent news signals, and price momentum."
        )

        report = "\n".join(
            [
                f"Investment Blueprint — {market_label} Equity Portfolio",
                f"Market: {market_label}",
                f"Risk Profile: {risk_profile}",
                f"Time Horizon: {horizon_label}",
                f"Portfolio Style: {style}",
                f"Equity Allocation: {equity_weight}",
                f"Primary Sector Exposure: {top_sector}",
                f"Top Pick: {top_pick}",
                "",
                "Executive Summary",
                executive_summary,
                "",
                "Portfolio Allocation",
                "Stock | Company | Weight",
                "--- | --- | ---",
                allocation_rows or "N/A",
                "",
                "Investment Rationale (At a Glance)",
                highlights or "N/A",
                "",
                "Why These Picks Were Selected",
                selected_why or "N/A",
                "",
                "Trade Levels",
                "Stock | Buy | Sell | Stop | Risk/Reward | Backtest Strategy",
                "--- | --- | --- | --- | --- | ---",
                trade_rows or "N/A",
                "",
                "Next Steps",
                "1. Implement allocations gradually (DCA preferred).",
                "2. Review quarterly or annually.",
                "3. Rebalance if any position deviates significantly.",
                "4. Adjust risk exposure as your goals approach.",
            ]
        )

        state.final_report = report.replace("*", "")
        state.execution_log.append("✅ Report generated")
        return state

# =============================================================================
# LANGGRAPH WORKFLOW
# =============================================================================

def build_smart_wealth_pipeline():
    """Build the complete LangGraph workflow"""
    
    # Initialize agents
    intake = SmartIntakeAgent()
    clarify = SmartClarificationAgent()
    risk_profiler = SmartRiskProfiler()
    market_data = FreeMarketDataAgent()
    sector_discovery = SmartSectorDiscovery()
    stock_selector = SmartStockSelector()
    technicals = BacktestTechnicalsAgent()
    report_gen = SmartReportGenerator()
    
    # Create graph
    workflow = StateGraph(WealthState)
    
    # Add nodes
    workflow.add_node("intake", intake.run)
    workflow.add_node("clarify", clarify.run)
    workflow.add_node("risk_profile", risk_profiler.run)
    workflow.add_node("market_data", market_data.run)
    workflow.add_node("discover_sectors", sector_discovery.run)
    workflow.add_node("select_stocks", stock_selector.run)
    workflow.add_node("backtest_technicals", technicals.run)
    workflow.add_node("generate_report", report_gen.run)
    
    # Define flow with conditional logic
    def should_clarify(state: WealthState):
        """Check if clarification is needed"""
        if state.clarification_questions:
            return "needs_clarification"
        return "proceed"
    
    def route_after_clarify(state: WealthState):
        """Route after clarification"""
        # In real app, wait for user response here
        # For now, proceed with what we have
        return "risk_profile"
    
    # Build workflow
    workflow.set_entry_point("intake")
    
    workflow.add_edge("intake", "clarify")
    
    workflow.add_conditional_edges(
        "clarify",
        lambda s: "risk_profile",  # Simplified - in real app, wait for user input
        {
            "risk_profile": "risk_profile",
        }
    )
    
    workflow.add_edge("risk_profile", "market_data")
    workflow.add_edge("market_data", "discover_sectors")
    workflow.add_edge("discover_sectors", "select_stocks")
    workflow.add_edge("select_stocks", "backtest_technicals")
    workflow.add_edge("backtest_technicals", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()

# =============================================================================
# INTEGRATION WITH YOUR EXISTING PIPELINE
# =============================================================================

class WealthOrchestrator:
    """
    Drop-in replacement for your existing WealthOrchestrator
    Integrates seamlessly with your PipelineManager
    """
    
    def __init__(self):
        self.workflow = build_smart_wealth_pipeline()
    
    def analyze(self, user_input: dict) -> dict:
        """
        Main entry point - compatible with your existing code
        
        Args:
            user_input: {
                "raw_input": str,  # Any format - chat, email, etc.
                "channel": str,    # "chat", "email", "whatsapp"
            }
        
        Returns:
            {
                "report": str,
                "stocks": List[dict],
                "allocation": dict,
                "clarification_questions": List[str],
                "errors": List[str],
                "execution_log": List[str]
            }
        """
        
        # Initialize state
        initial_state = WealthState(
            raw_input=user_input.get("raw_input", ""),
            input_channel=user_input.get("channel", "chat"),
            market=user_input.get("market", Config.DEFAULT_MARKET),
        )
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)

        def _as_dict(obj):
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, "dict"):
                return obj.dict()
            return {}

        def _as_list(obj):
            if obj is None:
                return []
            return list(obj) if isinstance(obj, (list, tuple)) else []

        recs = _as_list(final_state.get("stock_recommendations", []))
        selection_rationale = _as_list(final_state.get("selection_rationale", []))
        rejection_rationale = _as_list(final_state.get("rejection_rationale", []))
        trade_plans = _as_list(final_state.get("trade_plans", []))

        def _find_reason(symbol: str):
            for r in selection_rationale:
                if isinstance(r, dict) and r.get("symbol") == symbol:
                    return r.get("why_selected")
            return None

        def _find_plan(symbol: str):
            for p in trade_plans:
                if isinstance(p, dict) and p.get("symbol") == symbol:
                    return p
            return None

        stocks_payload = []
        allocation_payload: Dict[str, float] = {}

        for rec in recs:
            rec_dict = _as_dict(rec)
            symbol = rec_dict.get("symbol")
            if not symbol:
                continue
            allocation_pct = rec_dict.get("allocation_percent")
            allocation_payload[symbol] = allocation_pct

            stocks_payload.append(
                {
                    "symbol": symbol,
                    "name": rec_dict.get("name"),
                    "sector": rec_dict.get("sector"),
                    "allocation": allocation_pct,
                    "rationale": rec_dict.get("rationale"),
                    "why_selected": _find_reason(symbol) or rec_dict.get("rationale"),
                    "trade_plan": _find_plan(symbol),
                    "price": rec_dict.get("current_price"),
                }
            )

        return {
            "report": final_state.get("final_report", ""),
            "stocks": stocks_payload,
            "allocation": allocation_payload,
            "sectors": final_state.get("recommended_sectors", []),
            "news_context": final_state.get("news_context", {}) or {},
            "market_data": final_state.get("market_data", {}) or {},
            "risk_score": final_state.get("risk_score", 5),
            "clarification_questions": final_state.get("clarification_questions", []),
            "selection_rationale": selection_rationale,
            "rejection_rationale": rejection_rationale,
            "trade_plans": trade_plans,
            "errors": final_state.get("errors", []),
            "execution_log": final_state.get("execution_log", []),
            "extracted_profile": _as_dict(final_state.get("extracted_profile")),
        }
    
    def run_workflow(self, user_input: dict) -> dict:
        """Alias for analyze() - maintains compatibility"""
        return self.analyze(user_input)

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    
    # Set your FREE Gemini API key
    os.environ["GEMINI_API_KEY"] = "your-gemini-api-key-here"
    
    # Initialize orchestrator
    orchestrator = WealthOrchestrator()
    
    # Example 1: Casual chat input
    result = orchestrator.analyze({
        "raw_input": "Hey, I have 2 lakhs to invest. I'm 28, working in tech, don't want to lose money but okay with some risk. Planning for next 5 years.",
        "channel": "chat"
    })
    
    print("📊 RECOMMENDATIONS:")
    print(result["report"])
    print("\n📈 STOCKS:")
    for stock in result["stocks"]:
        print(f"  {stock['symbol']}: {stock['allocation']}%")
    
    # Example 2: Email format
    result2 = orchestrator.analyze({
        "raw_input": """
        Subject: Investment advice needed
        
        I'm 35 years old with two kids. I want to invest 5 lakhs for my daughter's 
        college education (she's 8 now). I have a stable government job, so I can 
        take some risk but not too much. What would you recommend?
        """,
        "channel": "email"
    })
    
    print("\n\n📧 EMAIL RESPONSE:")
    print(result2["report"])
    
    # Example 3: Voice transcription (messy)
    result3 = orchestrator.analyze({
        "raw_input": """
        Um, so I just got my bonus, it's like 3 lakhs, and I'm thinking, 
        you know, instead of just FD, maybe I should do stocks? 
        I'm 31, IT professional, um, I can handle some risk I guess. 
        Maybe invest for like 3-4 years?
        """,
        "channel": "chat"
    })
    
    print("\n\n🎤 VOICE INPUT RESPONSE:")
    print(result3["report"])
    
    # Check clarification questions
    if result3["clarification_questions"]:
        print("\n❓ CLARIFICATION NEEDED:")
        for q in result3["clarification_questions"]:
            print(f"  {q}")
