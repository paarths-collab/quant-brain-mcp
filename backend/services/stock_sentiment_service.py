"""
Stock Sentiment Pipeline Service
Fetches stock data from yfinance, Reddit sentiment, and AI analysis via Gemini.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import json
import re

import yfinance as yf
from backend.services.supply_chain_service import fetch_supply_chain

try:
    from duckduckgo_search import DDGS as DDGSClient
    DDGS_AVAILABLE = True
except Exception:
    try:
        from ddgs import DDGS as DDGSClient
        DDGS_AVAILABLE = True
    except Exception:
        DDGS_AVAILABLE = False
        DDGSClient = None

# Optional Reddit integration
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

# Google Generative AI deprecated - stubbed out
# LLM functionality can be added via modern provider (OpenAI, Groq, etc.)
GEMINI_AVAILABLE = False
genai = None  # Stub


# =====================================================
# CONFIG
# =====================================================

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "stock-sentiment-bot")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini configuration removed - deprecated
# if GEMINI_AVAILABLE and GEMINI_API_KEY:
#     genai.configure(api_key=GEMINI_API_KEY)


# =====================================================
# CURRENCY UTILITIES
# =====================================================

def get_currency_symbol(market: str) -> str:
    """Get currency symbol based on market"""
    if market in ('IN', 'NSE', 'BSE', 'india'):
        return '₹'
    return '$'


def detect_market(symbol: str) -> str:
    """Detect market from symbol"""
    if '.NS' in symbol or '.BO' in symbol:
        return 'IN'
    return 'US'


def format_large_number(value, market: str) -> str:
    """Format large numbers with appropriate suffix"""
    if value is None:
        return '-'
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        return '-'
    
    symbol = get_currency_symbol(market)
    
    if market in ('IN', 'NSE', 'BSE', 'india'):
        # Indian numbering (Crores, Lakhs)
        if value >= 1e7:
            return f"{symbol}{value / 1e7:.2f} Cr"
        if value >= 1e5:
            return f"{symbol}{value / 1e5:.2f} L"
        if value >= 1e3:
            return f"{symbol}{value / 1e3:.2f} K"
        return f"{symbol}{value:.2f}"
    
    # Western numbering (T, B, M, K)
    if value >= 1e12:
        return f"{symbol}{value / 1e12:.2f}T"
    if value >= 1e9:
        return f"{symbol}{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{symbol}{value / 1e6:.2f}M"
    if value >= 1e3:
        return f"{symbol}{value / 1e3:.2f}K"
    return f"{symbol}{value:.2f}"


# =====================================================
# YFINANCE DATA
# =====================================================

def fetch_stock_data(symbol: str) -> Dict:
    """
    Fetch price, returns, volume, fundamentals from yfinance
    """
    ticker = yf.Ticker(symbol)
    market = detect_market(symbol)
    currency_sym = get_currency_symbol(market)
    
    try:
        hist = ticker.history(period="6mo")
        info = ticker.info
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

    if hist.empty:
        return {"error": "No market data found", "symbol": symbol}

    latest = hist.iloc[-1]
    oldest = hist.iloc[0]

    price_change_pct = (
        (latest["Close"] - oldest["Close"]) / oldest["Close"]
    ) * 100 if oldest["Close"] else 0

    # Get 1-day change
    day_change = 0
    day_change_pct = 0
    if len(hist) >= 2:
        prev_close = hist.iloc[-2]["Close"]
        day_change = latest["Close"] - prev_close
        day_change_pct = (day_change / prev_close) * 100 if prev_close else 0

    ex_dividend_raw = info.get("exDividendDate")
    ex_dividend_date = None
    if ex_dividend_raw:
        try:
            ex_dividend_date = datetime.utcfromtimestamp(int(ex_dividend_raw)).strftime("%Y-%m-%d")
        except Exception:
            ex_dividend_date = None

    # Quarterly snapshot (best-effort)
    quarterly = {}
    try:
        qf = ticker.quarterly_financials
        if qf is not None and not qf.empty:
            latest_col = qf.columns[0] if len(qf.columns) > 0 else None

            def _get_metric(label: str):
                if label not in qf.index:
                    return None, None
                series = qf.loc[label]
                latest = series.iloc[0] if len(series) > 0 else None
                prev = series.iloc[1] if len(series) > 1 else None
                return latest, prev

            net_income, prev_net_income = _get_metric("Net Income")
            revenue, prev_revenue = _get_metric("Total Revenue")

            def _growth(curr, prev):
                try:
                    if curr is None or prev in (None, 0):
                        return None
                    return (float(curr) - float(prev)) / float(prev) * 100
                except Exception:
                    return None

            quarter_end = None
            if latest_col is not None:
                try:
                    quarter_end = latest_col.date().isoformat()  # type: ignore
                except Exception:
                    quarter_end = str(latest_col)

            quarterly_revenue = []
            if "Total Revenue" in qf.index:
                rev_series = qf.loc["Total Revenue"]
                for idx, col in enumerate(rev_series.index[:4]):
                    label = f"Q{idx + 1}"
                    period = None
                    try:
                        period = col.date().isoformat()  # type: ignore
                    except Exception:
                        period = str(col)
                    val = rev_series.iloc[idx] if idx < len(rev_series) else None
                    quarterly_revenue.append({
                        "quarter": label,
                        "period": period,
                        "revenue": float(val) if val is not None else None
                    })

            quarterly = {
                "quarter_end": quarter_end,
                "net_profit_q": float(net_income) if net_income is not None else None,
                "profit_q_var": _growth(net_income, prev_net_income),
                "sales_q": float(revenue) if revenue is not None else None,
                "sales_q_var": _growth(revenue, prev_revenue),
                "quarterly_revenue": quarterly_revenue,
            }
    except Exception:
        quarterly = {}

    return {
        "symbol": symbol,
        "company_name": info.get("longName") or info.get("shortName", symbol),
        "business_summary": info.get("longBusinessSummary"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market": market,
        "currency": currency_sym,
        "current_price": round(latest["Close"], 2),
        "previous_close": round(hist.iloc[-2]["Close"], 2) if len(hist) >= 2 else None,
        "day_change": round(day_change, 2),
        "day_change_pct": round(day_change_pct, 2),
        "price_change_6m_pct": round(price_change_pct, 2),
        "volume": int(latest["Volume"]),
        "avg_volume": info.get("averageVolume"),
        "market_cap": info.get("marketCap"),
        "market_cap_formatted": format_large_number(info.get("marketCap"), market),
        # Valuation
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "enterprise_value": info.get("enterpriseValue"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        # Financial health
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "free_cashflow": info.get("freeCashflow"),
        # Profitability
        "roe": info.get("returnOnEquity"),
        "operating_margins": info.get("operatingMargins"),
        # Dividends
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "ex_dividend_date": ex_dividend_date,
        # Risk
        "beta": info.get("beta"),
        "short_ratio": info.get("shortRatio"),
        "short_percent_float": info.get("shortPercentOfFloat"),
        # Growth
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "revenue": info.get("totalRevenue"),
        "revenue_formatted": format_large_number(info.get("totalRevenue"), market),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "eps_growth": info.get("earningsGrowth"),
        # Analyst
        "target_mean_price": info.get("targetMeanPrice"),
        "recommendation_key": info.get("recommendationKey", "").upper(),
        "analyst_count": info.get("numberOfAnalystOpinions"),
        # Quarterly snapshot
        **quarterly,
    }

def fetch_duckduckgo_news(company_name: str, symbol: str, limit: int = 8) -> Dict[str, Any]:
    """
    Fetch recent news articles via DuckDuckGo News.
    Returns a dict with query + articles.
    """
    from backend.services.news_service import news_service

    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    company = company_name or clean_symbol
    query = f"\"{company}\" {clean_symbol} stock news"

    try:
        # Use centralized news service
        results = news_service.get_news(query, limit)
        
        articles = []
        for r in results:
            articles.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "source": r.get("source", "DuckDuckGo"),
                "published": r.get("date", ""),
                "snippet": r.get("body", ""),
            })
        return {"source": "duckduckgo", "query": query, "articles": articles}
    except Exception as e:
        print(f"DuckDuckGo news error: {e}")
        return {"source": "duckduckgo", "query": query, "articles": []}


# =====================================================
# REDDIT SENTIMENT
# =====================================================

def fetch_reddit_posts(
    query: str,
    limit: int = 30,
    days: int = 7
) -> List[Dict]:
    """
    Fetch recent Reddit post titles + bodies mentioning the stock
    """
    if not PRAW_AVAILABLE or not REDDIT_CLIENT_ID:
        return []
    
    try:
        reddit = praw.Reddit( # type: ignore
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)
        posts = []

        subreddits = ["wallstreetbets", "stocks", "investing", "IndianStreetBets"]
        
        for submission in reddit.subreddit("+".join(subreddits)).search(
            query=query,
            sort="new",
            limit=limit
        ):
            created = datetime.utcfromtimestamp(submission.created_utc)
            if created >= cutoff:
                posts.append({
                    "title": submission.title,
                    "text": submission.selftext[:500] if submission.selftext else "",
                    "score": submission.score,
                    "subreddit": str(submission.subreddit),
                    "created": created.isoformat(),
                    "url": f"https://reddit.com{submission.permalink}",
                })

        return posts
    except Exception as e:
        print(f"Reddit fetch error: {e}")
        return []


def summarize_reddit_sentiment(posts: List[Dict]) -> Dict:
    """
    Analyze Reddit posts for sentiment
    """
    if not posts:
        return {
            "post_count": 0,
            "avg_score": 0,
            "summary": "No significant Reddit discussion found.",
            "top_posts": [],
        }

    total_score = sum(p.get("score", 0) for p in posts)
    avg_score = total_score / len(posts) if posts else 0
    
    # Sort by score and get top posts
    sorted_posts = sorted(posts, key=lambda x: x.get("score", 0), reverse=True)
    top_posts = sorted_posts[:5]
    
    # Simple sentiment from post content
    combined_text = " ".join([p["title"] + " " + p.get("text", "") for p in posts[:15]])

    return {
        "post_count": len(posts),
        "avg_score": round(avg_score, 1),
        "summary": combined_text[:3000],
        "top_posts": top_posts,
    }


# =====================================================
# GEMINI ANALYSIS
# =====================================================

def analyze_with_gemini(
    stock_data: Dict,
    reddit_summary: Dict
) -> Dict:
    """
    Ask Gemini to classify sentiment and provide analysis
    """
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        # Fallback to simple heuristic analysis
        return generate_fallback_analysis(stock_data, reddit_summary)

    try:
        prompt = f"""
You are a professional equity analyst. Analyze this stock and provide a structured assessment.

STOCK DATA:
- Symbol: {stock_data.get('symbol')}
- Company: {stock_data.get('company_name')}
- Sector: {stock_data.get('sector')}
- Current Price: {stock_data.get('currency')}{stock_data.get('current_price')}
- 6-Month Change: {stock_data.get('price_change_6m_pct')}%
- P/E Ratio: {stock_data.get('pe_ratio')}
- Market Cap: {stock_data.get('market_cap_formatted')}
- Analyst Recommendation: {stock_data.get('recommendation_key')}

REDDIT DISCUSSION ({reddit_summary.get('post_count', 0)} posts, avg score {reddit_summary.get('avg_score', 0)}):
{reddit_summary.get('summary', 'No discussion found')[:2000]}

Respond in this exact JSON format:
{{
    "outlook": "Bullish|Neutral|Bearish",
    "sentiment_score": 0.0 to 1.0,
    "recommendation": "STRONG BUY|BUY|HOLD|SELL|STRONG SELL",
    "target_price": number or null,
    "summary": "2-3 sentence analysis",
    "risks": ["risk1", "risk2", "risk3"],
    "catalysts": ["catalyst1", "catalyst2", "catalyst3"],
    "confidence": 0.0 to 1.0
}}
"""

        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash")) # type: ignore
        response = model.generate_content(prompt)
        
        # Parse JSON from response
        text = response.text.strip()
        # Extract JSON from markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        result = json.loads(text)
        return {
            "source": "gemini",
            **result
        }
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return generate_fallback_analysis(stock_data, reddit_summary)


def generate_fallback_analysis(stock_data: Dict, reddit_summary: Dict) -> Dict:
    """
    Generate analysis without AI API (rule-based)
    """
    sentiment_score = 0.5
    
    # Factor in price momentum
    change_6m = stock_data.get("price_change_6m_pct", 0)
    if change_6m > 20:
        sentiment_score += 0.2
    elif change_6m > 10:
        sentiment_score += 0.1
    elif change_6m < -20:
        sentiment_score -= 0.2
    elif change_6m < -10:
        sentiment_score -= 0.1
    
    # Factor in analyst recommendation
    rec = stock_data.get("recommendation_key", "").lower()
    if rec in ("buy", "strong_buy", "outperform"):
        sentiment_score += 0.15
    elif rec in ("sell", "underperform"):
        sentiment_score -= 0.15
    
    # Factor in Reddit sentiment (if available)
    if reddit_summary.get("post_count", 0) > 10:
        avg_score = reddit_summary.get("avg_score", 0)
        if avg_score > 100:
            sentiment_score += 0.1
        elif avg_score < 10:
            sentiment_score -= 0.05
    
    # Clamp to 0-1
    sentiment_score = max(0, min(1, sentiment_score))
    
    # Determine outlook
    if sentiment_score >= 0.6:
        outlook = "Bullish"
        recommendation = "BUY"
    elif sentiment_score >= 0.4:
        outlook = "Neutral"
        recommendation = "HOLD"
    else:
        outlook = "Bearish"
        recommendation = "SELL"
    
    # Calculate target price
    current_price = stock_data.get("current_price", 0)
    analyst_target = stock_data.get("target_mean_price")
    if analyst_target:
        target_price = round(analyst_target, 2)
    else:
        # Estimate based on sentiment
        multiplier = 1 + (sentiment_score - 0.5) * 0.2
        target_price = round(current_price * multiplier, 2)
    
    # Generate summary
    company = stock_data.get("company_name", stock_data.get("symbol"))
    sector = stock_data.get("sector", "N/A")
    summary = f"{company} in the {sector} sector shows {outlook.lower()} signals. "
    summary += f"6-month price change of {change_6m:.1f}%. "
    if reddit_summary.get("post_count", 0) > 0:
        summary += f"Reddit discussion activity: {reddit_summary['post_count']} posts."
    
    # Generate risks and catalysts based on sector
    risks = ["Market volatility", "Sector headwinds", "Macroeconomic uncertainty"]
    catalysts = ["Strong fundamentals", "Sector tailwinds", "Growth potential"]
    
    if change_6m < 0:
        risks.insert(0, "Negative price momentum")
    if change_6m > 15:
        catalysts.insert(0, "Strong price momentum")
    
    return {
        "source": "heuristic",
        "outlook": outlook,
        "sentiment_score": round(sentiment_score, 2),
        "recommendation": recommendation,
        "target_price": target_price,
        "summary": summary,
        "risks": risks[:3],
        "catalysts": catalysts[:3],
        "confidence": 0.65
    }


# =====================================================
# PIPELINE
# =====================================================

def analyze_stock_sentiment(symbol: str) -> Dict:
    """
    End-to-end sentiment analysis pipeline
    """
    # Normalize symbol
    symbol = symbol.upper().strip()
    market = detect_market(symbol)
    
    # Fetch stock data
    stock_data = fetch_stock_data(symbol)
    
    if "error" in stock_data:
        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "error": stock_data["error"],
        }
    
    # Fetch Reddit posts using company name or symbol
    query = stock_data.get("company_name") or symbol.split(".")[0]
    reddit_posts = fetch_reddit_posts(query)
    reddit_summary = summarize_reddit_sentiment(reddit_posts)

    # Fetch recent news via DuckDuckGo
    news = fetch_duckduckgo_news(stock_data.get("company_name", ""), symbol)

    # Supply chain extraction (SEC for US, DDG crawler for India)
    supply_chain = fetch_supply_chain(symbol, stock_data.get("company_name", ""))
    
    # Run AI analysis
    ai_analysis = analyze_with_gemini(stock_data, reddit_summary)
    
    # Build metrics for frontend
    metrics = {
        "pe": stock_data.get("pe_ratio"),
        "eps": stock_data.get("eps"),
        "revenue": stock_data.get("revenue_formatted"),
        "marketCap": stock_data.get("market_cap_formatted"),
    }
    
    return {
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "market": market,
        "name": stock_data.get("company_name", symbol),
        "price": stock_data.get("current_price"),
        "day_change": stock_data.get("day_change"),
        "day_change_pct": stock_data.get("day_change_pct"),
        "recommendation": ai_analysis.get("recommendation", "HOLD"),
        "targetPrice": ai_analysis.get("target_price"),
        "sentiment": ai_analysis.get("sentiment_score", 0.5),
        "outlook": ai_analysis.get("outlook", "Neutral"),
        "summary": ai_analysis.get("summary", ""),
        "metrics": metrics,
        "risks": ai_analysis.get("risks", []),
        "catalysts": ai_analysis.get("catalysts", []),
        "confidence": ai_analysis.get("confidence", 0.5),
        "reddit_posts_count": reddit_summary.get("post_count", 0),
        "reddit_top_posts": reddit_summary.get("top_posts", []),
        "analysis_source": ai_analysis.get("source", "unknown"),
        "market_data": stock_data,
        "news": news,
        "supply_chain": supply_chain,
    }


# =====================================================
# BATCH ANALYSIS
# =====================================================

def analyze_multiple_stocks(symbols: List[str], max_workers: int = 5) -> List[Dict]:
    """
    Analyze multiple stocks in parallel
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_stock_sentiment, s): s for s in symbols}
        for future in futures:
            try:
                result = future.result(timeout=60)
                results.append(result)
            except Exception as e:
                results.append({
                    "symbol": futures[future],
                    "error": str(e),
                })
    return results


# =====================================================
# CLI TEST
# =====================================================

if __name__ == "__main__":
    # Test with US stock
    print("Testing AAPL (US)...")
    result = analyze_stock_sentiment("AAPL")
    print(json.dumps(result, indent=2, default=str))
    
    # Test with Indian stock
    print("\nTesting RELIANCE.NS (India)...")
    result = analyze_stock_sentiment("RELIANCE.NS")
    print(json.dumps(result, indent=2, default=str))
