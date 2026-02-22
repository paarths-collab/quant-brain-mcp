"""
stock_analyzer.py

A standalone stock analysis module that uses yfinance directly.
This module provides comprehensive stock analysis without requiring
external API calls that may be rate-limited.

Used by the AI Chat and Research Agent for automatic stock analysis.
"""

import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Any, Optional, List, Tuple
import re
import json
from pathlib import Path
from functools import lru_cache


def ai_analyze_query(query: str, llm_agent=None) -> Dict[str, Any]:
    """
    Use AI to analyze a user's query and determine:
    1. Is this a stock-related question?
    2. What are the actual stock tickers mentioned (not false positives)?
    3. What is the user's actual intent?
    
    Args:
        query: User's question
        llm_agent: The LLM agent to use for analysis
        
    Returns:
        Dictionary with query analysis results
    """
    # Company name to ticker mapping
    name_to_ticker = {
        'APPLE': 'AAPL',
        'GOOGLE': 'GOOGL',
        'ALPHABET': 'GOOGL',
        'AMAZON': 'AMZN',
        'NVIDIA': 'NVDA',
        'MICROSOFT': 'MSFT',
        'TESLA': 'TSLA',
        'FACEBOOK': 'META',
        'NETFLIX': 'NFLX',
        'DISNEY': 'DIS',
        'INTEL': 'INTC',
        'AMD': 'AMD',
        'PAYPAL': 'PYPL',
        'COINBASE': 'COIN',
        'UBER': 'UBER',
        'AIRBNB': 'ABNB',
        'RELIANCE': 'RELIANCE',
        'INFOSYS': 'INFY',
        'TATA': 'TATAMOTORS',
        'WIPRO': 'WIPRO',
        'HDFC': 'HDFCBANK',
        'ICICI': 'ICICIBANK',
    }
    
    if not llm_agent:
        # Fall back to regex-based detection if no LLM available
        return {
            "is_stock_question": True,
            "tickers": detect_tickers_in_text(query, validate=False),
            "intent": "general",
            "should_analyze_stocks": True
        }
    
    analysis_prompt = f"""Analyze this user question and respond with ONLY valid JSON (no markdown, no explanation):

User Question: "{query}"

Determine:
1. Is this primarily a stock/investment question that needs stock analysis?
2. What are the stock TICKER SYMBOLS mentioned? Convert company names to tickers:
   - Apple -> AAPL
   - Google/Alphabet -> GOOGL
   - Amazon -> AMZN
   - Microsoft -> MSFT
   - Tesla -> TSLA
   - Nvidia -> NVDA
   - Meta/Facebook -> META
3. What is the user's intent?

IMPORTANT: Return TICKER SYMBOLS not company names. "Apple" should return "AAPL", not "APPLE".

Respond with this JSON format only:
{{"is_stock_question": true/false, "tickers": ["AAPL", "MSFT"], "intent": "stock_analysis|comparison|general_question|market_overview", "should_analyze_stocks": true/false}}"""

    try:
        response = llm_agent.generate_response(prompt=analysis_prompt, model="llama-3.3-70b-versatile")
        
        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()
        
        result = json.loads(response)
        
        # Validate and fix tickers
        if result.get("tickers"):
            validated = []
            for ticker in result["tickers"]:
                ticker = ticker.upper().strip()
                # Skip obviously wrong ones
                if len(ticker) < 2 or len(ticker) > 12:
                    continue
                # Convert company names to tickers
                if ticker in name_to_ticker:
                    ticker = name_to_ticker[ticker]
                validated.append(ticker)
            result["tickers"] = validated
        
        return result
        
    except Exception as e:
        print(f"AI query analysis failed: {e}")
        # Fall back to traditional detection
        return {
            "is_stock_question": True,
            "tickers": detect_tickers_in_text(query, validate=False),
            "intent": "general",
            "should_analyze_stocks": True
        }


@lru_cache(maxsize=1)
def load_stock_database() -> pd.DataFrame:
    """
    Load and cache stock databases from CSV files.
    Combines Indian (Nifty 500) and US (S&P 500) stocks.
    
    Returns:
        DataFrame with columns: Symbol, Company Name, Industry, Market
    """
    data_dir = Path(__file__).parent.parent / "data"
    all_stocks = []
    
    # Load Indian stocks (Nifty 500)
    indian_file = data_dir / "nifty500.csv"
    if indian_file.exists():
        try:
            df = pd.read_csv(indian_file)
            df = df.rename(columns={
                'Symbol': 'Symbol',
                'Company Name': 'Company Name',
                'Industry': 'Industry'
            })
            df['Market'] = 'INDIA'
            df['Exchange'] = 'NSE/BSE'
            all_stocks.append(df[['Symbol', 'Company Name', 'Industry', 'Market', 'Exchange']])
        except Exception as e:
            print(f"Error loading Indian stocks: {e}")
    
    # Load US stocks (S&P 500)
    us_file = data_dir / "us_stocks.csv"
    if us_file.exists():
        try:
            df = pd.read_csv(us_file)
            # Handle different column names
            if 'Company Name' not in df.columns and 'Name' in df.columns:
                df = df.rename(columns={'Name': 'Company Name'})
            if 'Symbol' not in df.columns and 'Ticker' in df.columns:
                df = df.rename(columns={'Ticker': 'Company Name'})
            df['Market'] = 'US'
            df['Exchange'] = 'NYSE/NASDAQ'
            all_stocks.append(df[['Symbol', 'Company Name', 'Industry', 'Market', 'Exchange']])
        except Exception as e:
            print(f"Error loading US stocks: {e}")
    
    if all_stocks:
        combined = pd.concat(all_stocks, ignore_index=True)
        # Create search-friendly columns
        combined['search_name'] = combined['Company Name'].str.lower().str.strip()
        combined['search_symbol'] = combined['Symbol'].str.lower().str.strip()
        return combined
    
    return pd.DataFrame(columns=['Symbol', 'Company Name', 'Industry', 'Market', 'Exchange', 'search_name', 'search_symbol'])


def search_stock(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for stocks by company name, symbol, or industry.
    Uses fuzzy matching to find relevant stocks.
    
    Args:
        query: Search query (company name, partial name, or symbol)
        limit: Maximum number of results to return
        
    Returns:
        List of matching stocks with Symbol, Company Name, Industry, Market, Exchange
    """
    db = load_stock_database()
    if db.empty:
        return []
    
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    
    # Score each stock based on match quality
    scores = []
    for idx, row in db.iterrows():
        score = 0
        name = row['search_name']
        symbol = row['search_symbol']
        
        # Exact symbol match (highest priority)
        if symbol == query_lower:
            score += 100
        # Symbol starts with query
        elif symbol.startswith(query_lower):
            score += 80
        # Symbol contains query
        elif query_lower in symbol:
            score += 60
        
        # Exact name match
        if name == query_lower:
            score += 90
        # Name starts with query
        elif name.startswith(query_lower):
            score += 70
        # Name contains query
        elif query_lower in name:
            score += 50
        
        # Check individual words
        for word in query_words:
            if len(word) >= 3:  # Skip short words
                if word in name:
                    score += 30
                if word in symbol:
                    score += 25
        
        if score > 0:
            scores.append((idx, score))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top results
    results = []
    for idx, score in scores[:limit]:
        row = db.iloc[idx]
        results.append({
            'symbol': row['Symbol'],
            'company_name': row['Company Name'],
            'industry': row['Industry'],
            'market': row['Market'],
            'exchange': row['Exchange'],
            'match_score': score
        })
    
    return results


def search_and_get_ticker(query: str) -> Optional[str]:
    """
    Search for a stock and return the best matching ticker.
    
    Args:
        query: Search query (e.g., "idfc bank", "reliance")
        
    Returns:
        Best matching ticker symbol or None
    """
    results = search_stock(query, limit=1)
    if results and results[0]['match_score'] >= 30:
        return results[0]['symbol']
    return None


def validate_ticker_with_yfinance(ticker: str) -> bool:
    """
    Validate if a ticker symbol exists by checking yfinance.
    
    Args:
        ticker: Potential ticker symbol
        
    Returns:
        True if ticker is valid, False otherwise
    """
    try:
        # Try both US and Indian (NSE) versions
        for suffix in ['', '.NS', '.BO']:
            test_ticker = f"{ticker}{suffix}" if suffix else ticker
            stock = yf.Ticker(test_ticker)
            info = stock.info
            # Check if we got valid data
            if info and (info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')):
                return True
        return False
    except:
        return False


def detect_tickers_in_text(text: str, validate: bool = True) -> List[str]:
    """
    Detect stock ticker symbols in user text.
    Now detects ANY potential ticker and validates with yfinance.
    
    Args:
        text: User input text
        validate: If True, validate unknown tickers against yfinance
        
    Returns:
        List of detected ticker symbols
    """
    # Common words to exclude (expanded list)
    common_words = {
        'I', 'A', 'THE', 'AND', 'OR', 'FOR', 'TO', 'OF', 'IN', 'ON', 'IS', 'IT', 
        'MY', 'VS', 'WHAT', 'HOW', 'WHY', 'WHEN', 'WHERE', 'WHICH', 'WHO', 'ARE',
        'BE', 'HAS', 'HAVE', 'DO', 'DOES', 'DID', 'CAN', 'COULD', 'WOULD', 'SHOULD',
        'WILL', 'ALL', 'ANY', 'BUT', 'IF', 'AT', 'BY', 'SO', 'UP', 'DOWN', 'OUT',
        'AS', 'NO', 'NOT', 'TOP', 'BUY', 'SELL', 'HOLD', 'STOCK', 'STOCKS', 'SHARE',
        'SHARES', 'PRICE', 'HIGH', 'LOW', 'MARKET', 'FALL', 'FALLING', 'RISE', 'RISING',
        'GOOD', 'BAD', 'BEST', 'WORST', 'GROWTH', 'VALUE', 'PE', 'EPS', 'NOW', 'TODAY',
        'BANK', 'BANKS', 'COMPANY', 'CORP', 'INC', 'LTD', 'LIMITED', 'ABOUT', 'THIS',
        'THAT', 'THESE', 'THOSE', 'THEM', 'THEY', 'THEIR', 'WAS', 'WERE', 'BEEN',
        'BEING', 'ALSO', 'JUST', 'ONLY', 'THAN', 'THEN', 'WITH', 'FROM', 'INTO',
        'OVER', 'UNDER', 'AGAIN', 'FURTHER', 'ONCE', 'HERE', 'THERE', 'EACH', 'FEW',
        'MORE', 'MOST', 'OTHER', 'SOME', 'SUCH', 'VERY', 'SAME', 'OWN', 'TOO',
        'INVEST', 'INVESTING', 'INVESTMENT', 'ANALYSIS', 'ANALYZE', 'SHOULD', 'TELL',
        'ME', 'PLEASE', 'GIVE', 'SHOW', 'GET', 'LOOK', 'FIND', 'SEARCH', 'CHECK'
    }
    
    # Well-known stock tickers (fast path - skip validation)
    known_tickers = {
        # US Stocks
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC',
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA', 'PYPL', 'DIS', 'NFLX', 'CRM', 'ORCL',
        'IBM', 'CSCO', 'QCOM', 'TXN', 'AVGO', 'ADBE', 'UBER', 'ABNB', 'SQ', 'COIN',
        'PFE', 'JNJ', 'UNH', 'MRK', 'ABBV', 'LLY', 'TMO', 'BMY', 'AMGN', 'GILD', 'MRNA',
        'KO', 'PEP', 'WMT', 'COST', 'TGT', 'MCD', 'SBUX', 'NKE', 'HD', 'LOW',
        'XOM', 'CVX', 'COP', 'SLB', 'BKR', 'OXY',
        'BA', 'CAT', 'DE', 'GE', 'HON', 'UPS', 'FDX', 'LMT', 'RTX', 'NOC',
        # Indian Stocks (NSE)
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN',
        'BHARTIARTL', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 'TITAN',
        'SUNPHARMA', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 'HCLTECH', 'TATAMOTORS',
        'BAJFINANCE', 'TATASTEEL', 'JSWSTEEL', 'POWERGRID', 'NTPC', 'ONGC', 'COALINDIA',
        'TARIL', 'ADANIENT', 'ADANIPORTS', 'ADANIPOWER', 'DRREDDY', 'CIPLA', 'DIVISLAB',
        # Indian Banks
        'IDFCFIRSTB', 'BANDHANBNK', 'FEDERALBNK', 'INDUSINDBK', 'PNB', 'BANKBARODA',
        'CANBK', 'RBLBANK', 'YESBANK', 'AUBANK', 'IDBI', 'BANKINDIA', 'UNIONBANK',
        'INDIANB', 'MAHABANK', 'CENTRALBK', 'UCOBANK', 'IOB', 'PSB'
    }
    
    # Common company name aliases to ticker mappings
    name_to_ticker = {
        'IDFC': 'IDFCFIRSTB',
        'HDFC': 'HDFCBANK',
        'ICICI': 'ICICIBANK',
        'KOTAK': 'KOTAKBANK',
        'AXIS': 'AXISBANK',
        'INDUSIND': 'INDUSINDBK',
        'BANDHAN': 'BANDHANBNK',
        'FEDERAL': 'FEDERALBNK',
        'PUNJAB': 'PNB',
        'APPLE': 'AAPL',
        'GOOGLE': 'GOOGL',
        'AMAZON': 'AMZN',
        'NVIDIA': 'NVDA',
        'MICROSOFT': 'MSFT',
        'TESLA': 'TSLA',
        'FACEBOOK': 'META',
        'NETFLIX': 'NFLX',
        'RELIANCE': 'RELIANCE',
        'INFOSYS': 'INFY',
        'TATA': 'TATAMOTORS',
        'WIPRO': 'WIPRO'
    }
    
    # Extract potential tickers (alphanumeric, 2-15 chars)
    # NOTE: use real word-boundaries; previous pattern accidentally matched literal "\b".
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{1,14}\b', text)
    tickers = []
    candidates_to_validate = []
    
    for word in words:
        upper_word = word.upper()
        
        # Skip common words
        if upper_word in common_words:
            continue
        
        # Check if it's a company name alias
        if upper_word in name_to_ticker:
            ticker = name_to_ticker[upper_word]
            if ticker not in tickers:
                tickers.append(ticker)
            continue
        
        # Check if it's a known ticker (instant add)
        if upper_word in known_tickers:
            if upper_word not in tickers:
                tickers.append(upper_word)
        # For unknown words that look like tickers (2-12 chars), queue for validation
        elif len(upper_word) >= 2 and len(upper_word) <= 12:
            if upper_word not in candidates_to_validate and upper_word not in tickers:
                candidates_to_validate.append(upper_word)
    
    # Validate unknown candidates with yfinance (limit to first 3 to avoid slowdown)
    if validate and candidates_to_validate:
        for candidate in candidates_to_validate[:3]:
            if len(tickers) >= 3:
                break
            if validate_ticker_with_yfinance(candidate):
                tickers.append(candidate)
    
    # If no tickers found, try searching by company name
    if not tickers:
        # Use the full query for search
        search_results = search_stock(text, limit=3)
        for result in search_results:
            if result['match_score'] >= 30:  # Only include good matches
                tickers.append(result['symbol'])
    
    return tickers[:3]  # Limit to 3 tickers


def detect_market_from_ticker(ticker: str) -> str:
    """
    Detect market (US or India) from ticker symbol.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        'india' or 'us'
    """
    indian_tickers = {
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN',
        'BHARTIARTL', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 'TITAN',
        'SUNPHARMA', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 'HCLTECH', 'TATAMOTORS',
        'BAJFINANCE', 'TATASTEEL', 'JSWSTEEL', 'POWERGRID', 'NTPC', 'ONGC', 'COALINDIA',
        'TARIL', 'ADANIENT', 'ADANIPORTS', 'ADANIPOWER', 'DRREDDY', 'CIPLA', 'DIVISLAB',
        # Indian Banks
        'IDFCFIRSTB', 'IDFC', 'BANDHANBNK', 'FEDERALBNK', 'INDUSINDBK', 'PNB', 'BANKBARODA',
        'CANBK', 'RBLBANK', 'YESBANK', 'AUBANK', 'IDBI', 'BANKINDIA', 'UNIONBANK',
        'INDIANB', 'MAHABANK', 'CENTRALBK', 'UCOBANK', 'IOB', 'PSB'
    }
    
    if ticker.upper() in indian_tickers or '.NS' in ticker.upper() or '.BO' in ticker.upper():
        return 'india'
    return 'us'


def format_ticker_for_yfinance(ticker: str, market: str) -> str:
    """
    Format ticker symbol for yfinance.
    
    Args:
        ticker: Raw ticker symbol
        market: 'us' or 'india'
        
    Returns:
        Properly formatted ticker for yfinance
    """
    ticker = ticker.upper().strip()
    
    # If already has suffix, return as-is
    if '.NS' in ticker or '.BO' in ticker:
        return ticker
    
    # Add suffix for Indian stocks
    if market.lower() == 'india':
        return f"{ticker}.NS"
    
    return ticker


def analyze_stock(ticker: str, market: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform comprehensive stock analysis using yfinance.
    
    Args:
        ticker: Stock ticker symbol
        market: 'us' or 'india' (auto-detected if not provided)
        
    Returns:
        Dictionary containing comprehensive analysis
    """
    # Auto-detect market if not provided
    if market is None:
        market = detect_market_from_ticker(ticker)
    
    # Format ticker for yfinance
    formatted_ticker = format_ticker_for_yfinance(ticker, market)
    currency = "INR" if market.lower() == 'india' else "USD"
    currency_symbol = "Rs." if market.lower() == 'india' else "$"
    
    result = {
        "ticker": ticker,
        "formatted_ticker": formatted_ticker,
        "market": market.upper(),
        "currency": currency,
        "success": False,
        "error": None
    }
    
    try:
        stock = yf.Ticker(formatted_ticker)
        info = stock.info
        
        if not info or info.get('regularMarketPrice') is None:
            result["error"] = f"Could not fetch data for {formatted_ticker}"
            return result
        
        result["success"] = True
        
        # === Basic Company Info ===
        result["company"] = {
            "name": info.get('longName', ticker),
            "symbol": info.get('symbol', formatted_ticker),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "country": info.get('country', 'N/A'),
            "website": info.get('website', 'N/A'),
            "description": info.get('longBusinessSummary', '')[:500] + '...' if info.get('longBusinessSummary') else 'N/A'
        }
        
        # === Current Price ===
        current_price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
        prev_close = info.get('regularMarketPreviousClose', info.get('previousClose', 0))
        
        result["price"] = {
            "current": current_price,
            "previous_close": prev_close,
            "change": current_price - prev_close if current_price and prev_close else 0,
            "change_percent": ((current_price - prev_close) / prev_close) * 100 if prev_close else 0,
            "day_high": info.get('dayHigh', 0),
            "day_low": info.get('dayLow', 0),
            "52_week_high": info.get('fiftyTwoWeekHigh', 0),
            "52_week_low": info.get('fiftyTwoWeekLow', 0)
        }
        
        # === Valuation Metrics ===
        market_cap = info.get('marketCap', 0)
        if market_cap >= 1e12:
            market_cap_str = f"{market_cap/1e12:.2f} Trillion"
        elif market_cap >= 1e9:
            market_cap_str = f"{market_cap/1e9:.2f} Billion"
        elif market_cap >= 1e7:
            market_cap_str = f"{market_cap/1e7:.2f} Crore"
        else:
            market_cap_str = f"{market_cap:,.0f}"
        
        result["valuation"] = {
            "market_cap": market_cap,
            "market_cap_formatted": f"{currency_symbol}{market_cap_str}",
            "pe_ratio": info.get('trailingPE', info.get('forwardPE', 0)),
            "forward_pe": info.get('forwardPE', 0),
            "pb_ratio": info.get('priceToBook', 0),
            "ps_ratio": info.get('priceToSalesTrailing12Months', 0),
            "peg_ratio": info.get('pegRatio', 0),
            "enterprise_value": info.get('enterpriseValue', 0),
            "ev_to_ebitda": info.get('enterpriseToEbitda', 0)
        }
        
        # === Profitability ===
        result["profitability"] = {
            "eps": info.get('trailingEps', 0),
            "forward_eps": info.get('forwardEps', 0),
            "profit_margin": info.get('profitMargins', 0),
            "operating_margin": info.get('operatingMargins', 0),
            "gross_margin": info.get('grossMargins', 0),
            "roe": info.get('returnOnEquity', 0),
            "roa": info.get('returnOnAssets', 0)
        }
        
        # === Dividends ===
        result["dividends"] = {
            "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            "dividend_rate": info.get('dividendRate', 0),
            "payout_ratio": info.get('payoutRatio', 0),
            "ex_dividend_date": str(info.get('exDividendDate', 'N/A'))
        }
        
        # === Risk Metrics ===
        result["risk"] = {
            "beta": info.get('beta', 0),
            "52_week_change": info.get('52WeekChange', 0),
            "short_ratio": info.get('shortRatio', 0),
            "short_percent": info.get('shortPercentOfFloat', 0)
        }
        
        # === Historical Performance ===
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        try:
            hist = stock.history(start=str(start_date), end=str(end_date))
            
            if not hist.empty:
                first_close = hist['Close'].iloc[0]
                last_close = hist['Close'].iloc[-1]
                total_return = ((last_close - first_close) / first_close) * 100
                
                # Calculate volatility
                daily_returns = hist['Close'].pct_change().dropna()
                volatility = daily_returns.std() * (252 ** 0.5) * 100
                
                # Moving averages
                sma_20 = hist['Close'].tail(20).mean() if len(hist) >= 20 else None
                sma_50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else None
                sma_200 = hist['Close'].tail(200).mean() if len(hist) >= 200 else None
                
                # Weekly and monthly returns
                week_return = ((last_close - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100 if len(hist) >= 6 else 0
                month_return = ((last_close - hist['Close'].iloc[-22]) / hist['Close'].iloc[-22]) * 100 if len(hist) >= 22 else 0
                
                result["performance"] = {
                    "1_year_return": round(total_return, 2),
                    "1_month_return": round(month_return, 2),
                    "1_week_return": round(week_return, 2),
                    "volatility": round(volatility, 2),
                    "avg_volume": int(hist['Volume'].mean()),
                    "sma_20": round(sma_20, 2) if sma_20 else None,
                    "sma_50": round(sma_50, 2) if sma_50 else None,
                    "sma_200": round(sma_200, 2) if sma_200 else None
                }
                
                # === Technical Signals ===
                signals = []
                
                # Moving average signals
                if sma_50 and sma_200:
                    if sma_50 > sma_200:
                        signals.append("BULLISH: Golden Cross (50-day SMA > 200-day SMA)")
                    else:
                        signals.append("BEARISH: Death Cross (50-day SMA < 200-day SMA)")
                
                if sma_50 and current_price:
                    if current_price > sma_50:
                        signals.append("BULLISH: Price above 50-day SMA")
                    else:
                        signals.append("BEARISH: Price below 50-day SMA")
                
                # Momentum signals
                if total_return > 50:
                    signals.append(f"STRONG MOMENTUM: Stock up {total_return:.1f}% YoY")
                elif total_return > 20:
                    signals.append(f"POSITIVE MOMENTUM: Stock up {total_return:.1f}% YoY")
                elif total_return < -20:
                    signals.append(f"NEGATIVE MOMENTUM: Stock down {abs(total_return):.1f}% YoY")
                
                # 52-week position
                w52_high = info.get('fiftyTwoWeekHigh', 0)
                w52_low = info.get('fiftyTwoWeekLow', 0)
                if w52_high and w52_low and current_price:
                    position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                    if position > 80:
                        signals.append(f"Near 52-week HIGH (at {position:.0f}% of range)")
                    elif position < 20:
                        signals.append(f"Near 52-week LOW (at {position:.0f}% of range)")
                
                result["signals"] = signals
        except Exception as e:
            result["performance"] = {"error": str(e)}
            result["signals"] = []
        
        # === Generate Investment Insights ===
        insights = []
        risks = []
        
        # Valuation insights
        pe = result["valuation"]["pe_ratio"]
        if pe:
            if pe < 15:
                insights.append(f"LOW P/E ({pe:.1f}): Potentially undervalued")
            elif pe > 40:
                risks.append(f"HIGH P/E ({pe:.1f}): May be overvalued or high-growth")
            else:
                insights.append(f"MODERATE P/E ({pe:.1f}): Fairly valued")
        
        # Dividend insights
        div_yield = result["dividends"]["dividend_yield"]
        if div_yield > 4:
            insights.append(f"HIGH DIVIDEND YIELD ({div_yield:.2f}%): Good for income investors")
        
        # Margin insights
        profit_margin = result["profitability"]["profit_margin"]
        if profit_margin and profit_margin > 0.2:
            insights.append(f"HIGH PROFIT MARGIN ({profit_margin*100:.1f}%): Strong profitability")
        elif profit_margin and profit_margin < 0.05:
            risks.append(f"LOW PROFIT MARGIN ({profit_margin*100:.1f}%): Slim margins")
        
        # Beta insights
        beta = result["risk"]["beta"]
        if beta:
            if beta > 1.5:
                risks.append(f"HIGH BETA ({beta:.2f}): More volatile than market")
            elif beta < 0.5:
                insights.append(f"LOW BETA ({beta:.2f}): Less volatile than market")
        
        result["insights"] = insights
        result["risks"] = risks
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def format_analysis_for_display(analysis: Dict[str, Any]) -> str:
    """
    Format analysis results as a readable markdown string.
    
    Args:
        analysis: Analysis dictionary from analyze_stock()
        
    Returns:
        Formatted markdown string
    """
    if not analysis.get("success"):
        return f"**Error analyzing {analysis.get('ticker', 'stock')}:** {analysis.get('error', 'Unknown error')}"
    
    currency = "Rs." if analysis["market"] == "INDIA" else "$"
    company = analysis["company"]
    price = analysis["price"]
    valuation = analysis["valuation"]
    performance = analysis.get("performance", {})
    signals = analysis.get("signals", [])
    insights = analysis.get("insights", [])
    risks = analysis.get("risks", [])
    
    output = []
    
    # Header
    output.append(f"## {company['name']} ({analysis['ticker']})")
    output.append(f"**Exchange:** {analysis['market']} | **Sector:** {company['sector']} | **Industry:** {company['industry']}")
    output.append("")
    
    # Current Price
    change_sign = "+" if price['change'] >= 0 else ""
    output.append(f"### Current Price: {currency}{price['current']:,.2f}")
    output.append(f"**Day Change:** {change_sign}{currency}{price['change']:.2f} ({change_sign}{price['change_percent']:.2f}%)")
    output.append(f"**52-Week Range:** {currency}{price['52_week_low']:,.2f} - {currency}{price['52_week_high']:,.2f}")
    output.append("")
    
    # Key Metrics
    pe_val = valuation.get('pe_ratio', 0)
    pb_val = valuation.get('pb_ratio', 0)
    eps_val = analysis['profitability'].get('eps', 0)
    beta_val = analysis['risk'].get('beta', 0)
    
    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) and pe_val else 'N/A'
    pb_str = f"{pb_val:.2f}" if isinstance(pb_val, (int, float)) and pb_val else 'N/A'
    eps_str = f"{currency}{eps_val:.2f}" if isinstance(eps_val, (int, float)) and eps_val else 'N/A'
    beta_str = f"{beta_val:.2f}" if isinstance(beta_val, (int, float)) and beta_val else 'N/A'
    
    output.append("### Key Metrics")
    output.append(f"| Metric | Value |")
    output.append(f"|--------|-------|")
    output.append(f"| Market Cap | {valuation['market_cap_formatted']} |")
    output.append(f"| P/E Ratio | {pe_str} |")
    output.append(f"| P/B Ratio | {pb_str} |")
    output.append(f"| EPS | {eps_str} |")
    output.append(f"| Dividend Yield | {analysis['dividends']['dividend_yield']:.2f}% |")
    output.append(f"| Beta | {beta_str} |")
    output.append("")
    
    # Performance
    if performance and not performance.get('error'):
        output.append("### Performance")
        output.append(f"- **1-Year Return:** {performance.get('1_year_return', 0):+.2f}%")
        output.append(f"- **1-Month Return:** {performance.get('1_month_return', 0):+.2f}%")
        output.append(f"- **1-Week Return:** {performance.get('1_week_return', 0):+.2f}%")
        output.append(f"- **Volatility:** {performance.get('volatility', 0):.2f}% (annualized)")
        output.append("")
        
        # Moving Averages
        output.append("### Moving Averages")
        if performance.get('sma_20'):
            output.append(f"- 20-Day SMA: {currency}{performance['sma_20']:,.2f}")
        if performance.get('sma_50'):
            output.append(f"- 50-Day SMA: {currency}{performance['sma_50']:,.2f}")
        if performance.get('sma_200'):
            output.append(f"- 200-Day SMA: {currency}{performance['sma_200']:,.2f}")
        output.append("")
    
    # Technical Signals
    if signals:
        output.append("### Technical Signals")
        for signal in signals:
            if "BULLISH" in signal or "POSITIVE" in signal or "STRONG" in signal:
                output.append(f"- [+] {signal}")
            elif "BEARISH" in signal or "NEGATIVE" in signal:
                output.append(f"- [-] {signal}")
            else:
                output.append(f"- {signal}")
        output.append("")
    
    # Investment Insights
    if insights or risks:
        output.append("### Investment Analysis")
        
        if insights:
            output.append("**Positives:**")
            for insight in insights:
                output.append(f"- {insight}")
        
        if risks:
            output.append("\n**Risks/Concerns:**")
            for risk in risks:
                output.append(f"- {risk}")
        output.append("")
    
    # Company Description
    if company.get('description') and company['description'] != 'N/A':
        output.append("### About the Company")
        output.append(company['description'])
        output.append("")
    
    # Disclaimer
    output.append("---")
    output.append("*This analysis is for informational purposes only. Always do your own research before investing.*")
    
    return "\n".join(output)


def analyze_multiple_stocks(tickers: List[str], market: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze multiple stocks at once.
    
    Args:
        tickers: List of stock ticker symbols
        market: 'us' or 'india' (auto-detected if not provided)
        
    Returns:
        List of analysis dictionaries
    """
    results = []
    for ticker in tickers[:5]:  # Limit to 5 stocks
        analysis = analyze_stock(ticker, market)
        results.append(analysis)
    return results


def search_and_analyze(query: str) -> Dict[str, Any]:
    """
    Detect stocks in a query and analyze them.
    
    Args:
        query: User's question or query text
        
    Returns:
        Dictionary with detected tickers and their analyses
    """
    tickers = detect_tickers_in_text(query)
    
    if not tickers:
        return {
            "tickers_found": [],
            "analyses": [],
            "message": "No stock tickers detected in your query. Please mention specific stock symbols like AAPL, MSFT, TARIL, etc."
        }
    
    analyses = []
    for ticker in tickers:
        analysis = analyze_stock(ticker)
        analyses.append(analysis)
    
    return {
        "tickers_found": tickers,
        "analyses": analyses,
        "formatted_reports": [format_analysis_for_display(a) for a in analyses]
    }


# For command-line testing
if __name__ == "__main__":
    # Test with TARIL
    print("Testing stock analyzer with TARIL...\n")
    result = analyze_stock("TARIL", "india")
    print(format_analysis_for_display(result))
    
    print("\n" + "="*50 + "\n")
    
    # Test ticker detection
    test_query = "Why is TARIL stock falling? Should I invest in AAPL instead?"
    print(f"Testing query: {test_query}")
    detected = detect_tickers_in_text(test_query)
    print(f"Detected tickers: {detected}")
