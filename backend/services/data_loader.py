# # # File: utils/data_loader.py
# # # This is the final, master data utility for your entire application.



# import pandas as pd
# import yfinance as yf
# import logging
# from functools import lru_cache
# from pathlib import Path
# from typing import Dict, Any

# from backend.services.market_utils import get_market_config

# logger = logging.getLogger(__name__)

# # ------------------------------------------------
# # TICKER FORMATTING
# # ------------------------------------------------

# @lru_cache(maxsize=1)
# def _get_indian_symbols_set():
#     try:
#         project_root = Path(__file__).parent.parent
#         equity_file = project_root / "data" / "nifty500.csv"
#         if equity_file.exists():
#             df = pd.read_csv(equity_file)
#             return set(df['Symbol'].str.upper())
#     except Exception as e:
#         logger.error(e)
#     return set()

# def format_ticker(ticker: str, market: str) -> str:
#     ticker_upper = ticker.upper().replace(".NS", "")
#     market_upper = market.upper()

#     if market_upper in ["IN", "INDIA"]:
#         return f"{ticker_upper}.NS"

#     return ticker_upper


# # ------------------------------------------------
# # CORE DATA FETCHING
# # ------------------------------------------------

# def get_ohlcv(
#     ticker: str,
#     start: str,
#     end: str,
#     market: str,
# ) -> pd.DataFrame:
#     yf_ticker = format_ticker(ticker, market)
#     logger.info(f"Fetching OHLCV for {yf_ticker}")

#     df = yf.download(
#         yf_ticker,
#         start=start,
#         end=end,
#         progress=False,
#         auto_adjust=False
#     )

#     if df.empty:
#         raise ValueError(f"No market data for {ticker}")

#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)

#     df.columns = [c.title() for c in df.columns]

#     required = ["Open", "High", "Low", "Close", "Volume"]
#     if not all(col in df.columns for col in required):
#         raise ValueError("Missing OHLCV columns")

#     return df[required]

# def get_history(
#     ticker: str,
#     start: str,
#     end: str,
#     market: str,
#     interval: str = "1d"
# ) -> pd.DataFrame:
#     yf_ticker = format_ticker(ticker, market)
#     df = yf.download(
#         yf_ticker,
#         start=start,
#         end=end,
#         interval=interval,
#         progress=False,
#         auto_adjust=True
#     )

#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)

#     df.columns = [c.title() for c in df.columns]
#     return df

# def get_company_snapshot(ticker: str, market: str) -> Dict[str, Any]:
#     market_config = get_market_config(market)
#     yf_ticker = format_ticker(ticker, market)

#     stock = yf.Ticker(yf_ticker)
#     info = stock.info or {}

#     return {
#         "symbol": ticker,
#         "currency": market_config["currency_symbol"],
#         **info
#     }


# def get_benchmark_returns(symbol: str, start: str, end: str) -> pd.Series:
#     """
#     Fetches benchmark returns for comparison against strategy performance.
#     """
#     logger.info(f"Fetching benchmark data for {symbol} from {start} to {end}...")
#     try:
#         # Determine market for formatting if needed, defaulting to US for now or infer
#         # For simplicity, assume symbol is already correct or handled
#         # Benchmark usually indices like ^GSPC, ^NSEI
#         benchmark_data = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
#         if benchmark_data.empty:
#             logger.warning(f"No benchmark data found for {symbol}.")
#             return pd.Series(dtype=float)
            
#         return benchmark_data['Close'].pct_change().dropna()
        
#     except Exception as e:
#         logger.error(f"Failed to fetch benchmark data for {symbol}: {e}")
#         return pd.Series(dtype=float)

# # Alias for backward compatibility with strategies
# get_data = get_ohlcv

"""
Central Market Data Loader
--------------------------
Single trusted gateway for:
- OHLCV data
- Historical prices
- Returns
- Company fundamentals snapshot
- Benchmark returns

All strategies, engines, and APIs must use this module.
"""

import json
import pandas as pd
import yfinance as yf
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from backend.services.market_utils import get_market_config

logger = logging.getLogger(__name__)


# ============================================================
# TICKER FORMATTING (MARKET-AWARE)
# ============================================================

@lru_cache(maxsize=1)
def _get_indian_symbols_set() -> set:
    """
    Loads Indian equity symbols once (used for .NS suffix validation)
    """
    try:
        # services -> backend
        backend_root = Path(__file__).parent.parent
        equity_file = backend_root / "data" / "nifty500.json"
        
        if equity_file.exists():
            with equity_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return set(
                item["Symbol"].upper()
                for item in data
                if isinstance(item, dict) and item.get("Symbol")
            )
        else:
            logger.warning(f"Indian symbols file not found at: {equity_file}")
    except Exception as e:
        logger.error(f"Failed loading Indian symbols: {e}")
    return set()


def format_ticker(ticker: str, market: str) -> str:
    """
    Formats ticker symbol based on market conventions.
    For Indian market, always adds .NS suffix (NSE exchange).
    """
    ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
    market = market.upper()

    if market in {"IN", "INDIA"}:
        # Always add .NS suffix for Indian market (NSE is primary)
        # Even if nifty500.csv isn't loaded, this ensures correct format
        return f"{ticker}.NS"

    return ticker


# ============================================================
# INTERNAL RAW FETCHERS (NOT CACHED)
# ============================================================

def _fetch_history_raw(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str,
    auto_adjust: bool,
) -> pd.DataFrame:

    yf_ticker = format_ticker(ticker, market)
    logger.info(f"Fetching history: {yf_ticker}")

    df = yf.download(
        yf_ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
    )

    if df.empty:
        raise ValueError(f"No market data for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.title() for c in df.columns]
    return df


# ============================================================
# CACHED MARKET DATA
# ============================================================

def _history_cache_key(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str,
    auto_adjust: bool,
) -> str:
    return f"{ticker}|{start}|{end}|{market}|{interval}|{auto_adjust}"


@lru_cache(maxsize=128)
def _cached_history(key: str) -> pd.DataFrame:
    ticker, start, end, market, interval, auto_adjust = key.split("|")
    return _fetch_history_raw(
        ticker=ticker,
        start=start,
        end=end,
        market=market,
        interval=interval,
        auto_adjust=auto_adjust == "True",
    )


def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Returns adjusted historical price data
    """
    key = _history_cache_key(ticker, start, end, market, interval, True)
    return _cached_history(key)


def get_ohlcv(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.DataFrame:
    """
    Returns OHLCV data (non-adjusted, backtesting-ready)
    """
    key = _history_cache_key(ticker, start, end, market, "1d", False)
    df = _cached_history(key)

    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        raise ValueError("Missing OHLCV columns")

    return df[list(required)]


# Backward compatibility alias
get_data = get_ohlcv


# ============================================================
# RETURNS HELPERS
# ============================================================

def get_returns(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.Series:
    """
    Returns daily percentage returns
    """
    df = get_history(ticker, start, end, market)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)

    return df["Close"].pct_change().dropna()


def get_benchmark_returns(
    symbol: str,
    start: str,
    end: str,
) -> pd.Series:
    """
    Fetches benchmark returns (indices like ^GSPC, ^NSEI)
    """
    try:
        df = yf.download(
            symbol,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            return pd.Series(dtype=float)
        return df["Close"].pct_change().dropna()
    except Exception as e:
        logger.error(f"Benchmark fetch failed: {e}")
        return pd.Series(dtype=float)


# ============================================================
# COMPANY FUNDAMENTALS SNAPSHOT
# ============================================================

_ALLOWED_INFO_FIELDS = {
    "shortName",
    "sector",
    "industry",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "dividendYield",
    "payoutRatio",
    "returnOnEquity",
    "debtToEquity",
    "revenueGrowth",
    "earningsGrowth",
}


def get_company_snapshot(
    ticker: str,
    market: str,
) -> Dict[str, Any]:
    """
    Returns a clean, stable subset of company fundamentals
    """
    market_cfg = get_market_config(market)
    yf_ticker = format_ticker(ticker, market)

    stock = yf.Ticker(yf_ticker)
    info = stock.info or {}

    filtered_info = {k: info.get(k) for k in _ALLOWED_INFO_FIELDS}

    return {
        "symbol": ticker,
        "market": market_cfg["market_name"],
        "currency": market_cfg["currency_symbol"],
        **filtered_info,
    }


def get_comprehensive_stock_data(
    ticker: str,
    market: str,
) -> Dict[str, Any]:
    """
    Returns ALL available yfinance data for a stock including:
    - Full company info
    - Price data (current, changes, ranges)
    - Financials & ratios
    - Analysts data
    - News
    - Calendar events
    - Holders information
    - Historical metrics
    """
    from datetime import datetime, timedelta
    
    market_cfg = get_market_config(market)
    yf_ticker = format_ticker(ticker, market)
    
    stock = yf.Ticker(yf_ticker)
    info = stock.info or {}
    
    # Calculate time periods
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    one_month_ago = today - timedelta(days=30)
    
    # Get historical data for calculations
    try:
        hist_1y = stock.history(period="1y")
        hist_1m = stock.history(period="1mo")
        hist_5d = stock.history(period="5d")
    except Exception:
        hist_1y = pd.DataFrame()
        hist_1m = pd.DataFrame()
        hist_5d = pd.DataFrame()
    
    # Calculate price metrics
    current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    previous_close = info.get("previousClose", 0)
    
    if previous_close and current_price:
        daily_change = current_price - previous_close
        daily_change_pct = (daily_change / previous_close) * 100
    else:
        daily_change = 0
        daily_change_pct = 0
    
    # Calculate historical returns
    returns = {}
    if not hist_1y.empty and "Close" in hist_1y.columns:
        try:
            # 1 week return
            if len(hist_5d) >= 2:
                returns["1_week"] = ((hist_5d["Close"].iloc[-1] / hist_5d["Close"].iloc[0]) - 1) * 100
            
            # 1 month return
            if len(hist_1m) >= 2:
                returns["1_month"] = ((hist_1m["Close"].iloc[-1] / hist_1m["Close"].iloc[0]) - 1) * 100
            
            # 3 month return
            if len(hist_1y) >= 63:  # ~3 months of trading days
                returns["3_month"] = ((hist_1y["Close"].iloc[-1] / hist_1y["Close"].iloc[-63]) - 1) * 100
            
            # 6 month return
            if len(hist_1y) >= 126:  # ~6 months of trading days
                returns["6_month"] = ((hist_1y["Close"].iloc[-1] / hist_1y["Close"].iloc[-126]) - 1) * 100
            
            # 1 year return
            if len(hist_1y) >= 2:
                returns["1_year"] = ((hist_1y["Close"].iloc[-1] / hist_1y["Close"].iloc[0]) - 1) * 100
            
            # Volatility (30-day std)
            if len(hist_1m) >= 5:
                returns["volatility_30d"] = hist_1m["Close"].pct_change().std() * (252 ** 0.5) * 100  # Annualized
        except Exception as e:
            logger.warning(f"Return calculation error: {e}")
    
    # Get 52-week high/low
    week_52_high = info.get("fiftyTwoWeekHigh", 0)
    week_52_low = info.get("fiftyTwoWeekLow", 0)
    
    # Get news (yfinance v2 structure has content nested)
    news_items = []
    try:
        news = stock.news or []
        for item in news[:10]:  # Limit to 10 news items
            # Handle both old and new yfinance news format
            # New format: news data is nested under 'content' key
            content = item.get("content", item)  # Fallback to item itself if no content key
            
            # Extract provider/publisher
            provider = content.get("provider", {})
            publisher = provider.get("displayName", "") if isinstance(provider, dict) else content.get("publisher", "")
            
            # Extract thumbnail
            thumbnail = ""
            thumb_data = content.get("thumbnail", {})
            if thumb_data and isinstance(thumb_data, dict):
                resolutions = thumb_data.get("resolutions", [])
                if resolutions and len(resolutions) > 0:
                    thumbnail = resolutions[0].get("url", "")
            
            # Extract canonical URL or preview URL
            link = ""
            canonical = content.get("canonicalUrl", {})
            if isinstance(canonical, dict) and canonical.get("url"):
                link = canonical.get("url", "")
            else:
                link = content.get("previewUrl", "") or content.get("link", "")
            
            news_items.append({
                "title": content.get("title", ""),
                "publisher": publisher,
                "link": link,
                "published": content.get("pubDate", content.get("providerPublishTime", "")),
                "summary": content.get("summary", ""),
                "type": content.get("contentType", content.get("type", "")),
                "thumbnail": thumbnail
            })
    except Exception as e:
        logger.warning(f"News fetch error: {e}")
    
    # Get analyst recommendations
    recommendations = {}
    try:
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            recent_recs = recs.tail(10)
            recommendations = {
                "count": len(recent_recs),
                "recent": recent_recs.to_dict("records") if len(recent_recs) <= 10 else []
            }
    except Exception:
        pass
    
    # Get analyst price targets
    price_targets = {}
    try:
        targets = stock.analyst_price_targets
        if targets:
            price_targets = {
                "low": targets.get("low"),
                "current": targets.get("current"),
                "mean": targets.get("mean"),
                "median": targets.get("median"),
                "high": targets.get("high")
            }
    except Exception:
        pass
    
    # Get institutional holders (top 5)
    holders = {}
    try:
        inst = stock.institutional_holders
        if inst is not None and not inst.empty:
            holders["institutional"] = inst.head(5).to_dict("records")
        
        major = stock.major_holders
        if major is not None and not major.empty:
            holders["major"] = major.to_dict()
    except Exception:
        pass
    
    # Get upcoming events (earnings, dividends)
    calendar = {}
    try:
        cal = stock.calendar
        if cal is not None:
            if isinstance(cal, dict):
                calendar = cal
            elif hasattr(cal, 'to_dict'):
                calendar = cal.to_dict()
    except Exception:
        pass
    
    # Get earnings history
    earnings = {}
    try:
        earn = stock.earnings_history
        if earn is not None and not earn.empty:
            earnings["history"] = earn.tail(4).to_dict("records")
        
        earn_dates = stock.earnings_dates
        if earn_dates is not None and not earn_dates.empty:
            earnings["upcoming"] = earn_dates.head(2).to_dict("records")
    except Exception:
        pass
    
    # Get dividends info
    dividends = {}
    try:
        div = stock.dividends
        if div is not None and not div.empty:
            dividends["recent"] = div.tail(4).to_dict()
            dividends["total_annual"] = info.get("dividendRate", 0)
            dividends["yield"] = info.get("dividendYield", 0)
    except Exception:
        pass
    
    # Build comprehensive response
    return {
        # Identifiers
        "symbol": ticker,
        "yf_symbol": yf_ticker,
        "market": market_cfg["market_name"],
        "currency": market_cfg["currency_symbol"],
        
        # Company Info
        "company_name": info.get("shortName") or info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "website": info.get("website", ""),
        "description": info.get("longBusinessSummary", "")[:500] + "..." if info.get("longBusinessSummary") else "",
        "employees": info.get("fullTimeEmployees", 0),
        "country": info.get("country", ""),
        "exchange": info.get("exchange", ""),
        
        # Price Data
        "current_price": current_price,
        "previous_close": previous_close,
        "open": info.get("open") or info.get("regularMarketOpen", 0),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh", 0),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow", 0),
        "daily_change": round(daily_change, 2),
        "daily_change_pct": round(daily_change_pct, 2),
        "volume": info.get("volume") or info.get("regularMarketVolume", 0),
        "avg_volume": info.get("averageVolume", 0),
        "avg_volume_10d": info.get("averageVolume10days", 0),
        
        # 52-Week Range
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "week_52_change_pct": info.get("52WeekChange", 0) * 100 if info.get("52WeekChange") else 0,
        
        # Returns
        "returns": returns,
        
        # Valuation
        "market_cap": info.get("marketCap", 0),
        "enterprise_value": info.get("enterpriseValue", 0),
        "trailing_pe": info.get("trailingPE", 0),
        "forward_pe": info.get("forwardPE", 0),
        "peg_ratio": info.get("pegRatio", 0),
        "price_to_book": info.get("priceToBook", 0),
        "price_to_sales": info.get("priceToSalesTrailing12Months", 0),
        "ev_to_revenue": info.get("enterpriseToRevenue", 0),
        "ev_to_ebitda": info.get("enterpriseToEbitda", 0),
        
        # Profitability
        "profit_margin": info.get("profitMargins", 0),
        "operating_margin": info.get("operatingMargins", 0),
        "gross_margin": info.get("grossMargins", 0),
        "return_on_equity": info.get("returnOnEquity", 0),
        "return_on_assets": info.get("returnOnAssets", 0),
        
        # Growth
        "revenue_growth": info.get("revenueGrowth", 0),
        "earnings_growth": info.get("earningsGrowth", 0),
        "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth", 0),
        
        # Financial Health
        "total_cash": info.get("totalCash", 0),
        "total_debt": info.get("totalDebt", 0),
        "debt_to_equity": info.get("debtToEquity", 0),
        "current_ratio": info.get("currentRatio", 0),
        "quick_ratio": info.get("quickRatio", 0),
        "free_cash_flow": info.get("freeCashflow", 0),
        "operating_cash_flow": info.get("operatingCashflow", 0),
        
        # Per Share Data
        "eps_trailing": info.get("trailingEps", 0),
        "eps_forward": info.get("forwardEps", 0),
        "book_value": info.get("bookValue", 0),
        "revenue_per_share": info.get("revenuePerShare", 0),
        
        # Dividends
        "dividend_rate": info.get("dividendRate", 0),
        "dividend_yield": info.get("dividendYield", 0),
        "payout_ratio": info.get("payoutRatio", 0),
        "ex_dividend_date": info.get("exDividendDate", ""),
        "dividends_detail": dividends,
        
        # Analyst Data
        "analyst_rating": info.get("recommendationKey", ""),
        "analyst_rating_score": info.get("recommendationMean", 0),
        "target_high": info.get("targetHighPrice", 0),
        "target_low": info.get("targetLowPrice", 0),
        "target_mean": info.get("targetMeanPrice", 0),
        "target_median": info.get("targetMedianPrice", 0),
        "num_analysts": info.get("numberOfAnalystOpinions", 0),
        "price_targets": price_targets,
        "recommendations": recommendations,
        
        # Ownership
        "holders": holders,
        "insider_ownership": info.get("heldPercentInsiders", 0),
        "institution_ownership": info.get("heldPercentInstitutions", 0),
        "short_ratio": info.get("shortRatio", 0),
        "short_pct_of_float": info.get("shortPercentOfFloat", 0),
        
        # Calendar & Earnings
        "calendar": calendar,
        "earnings": earnings,
        
        # News
        "news": news_items,
        
        # Beta & Risk
        "beta": info.get("beta", 0),
        
        # Timestamps
        "last_updated": datetime.now().isoformat(),
    }
