"""
Treemap Service - Fetches index and stock prices for treemap visualization
"""
import json
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
from pathlib import Path


# Cache for indices data
_indices_cache: Dict[str, Any] = {}


def load_indices_data(market: str = "india") -> Dict[str, Any]:
    """Load indices data from JSON file"""
    global _indices_cache
    
    if market.lower() in _indices_cache:
        return _indices_cache[market.lower()]
    
    base_path = Path(__file__).parent.parent / "data"
    
    if market.lower() == "india":
        file_path = base_path / "indian_indices.json"
    else:
        # Add US indices later
        file_path = base_path / "us_indices.json"
    
    if not file_path.exists():
        return {"market": market, "indices": []}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    _indices_cache[market.lower()] = data
    return data


def fetch_single_quote(symbol: str) -> Dict[str, Any]:
    """Fetch quote for a single symbol"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        hist = ticker.history(period="2d")
        
        if hist.empty:
            return {
                "symbol": symbol,
                "price": None,
                "change": None,
                "change_percent": None,
                "error": "No data"
            }
        
        current_price = hist['Close'].iloc[-1] if len(hist) > 0 else None
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        
        if current_price and prev_close:
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100
        else:
            change = 0
            change_percent = 0
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2) if current_price else None,
            "prev_close": round(prev_close, 2) if prev_close else None,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": int(hist['Volume'].iloc[-1]) if len(hist) > 0 else None
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "error": str(e)
        }


def fetch_multiple_quotes(symbols: List[str], max_workers: int = 10) -> Dict[str, Dict]:
    """Fetch quotes for multiple symbols in parallel"""
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(fetch_single_quote, symbol): symbol 
            for symbol in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                results[symbol] = {
                    "symbol": symbol,
                    "price": None,
                    "change": None,
                    "change_percent": None,
                    "error": str(e)
                }
    
    return results


class TreemapService:
    """Service for treemap data with live prices"""
    
    def __init__(self):
        self.india_data = load_indices_data("india")
    
    def get_all_indices(self, market: str = "india") -> List[Dict[str, Any]]:
        """Get list of all indices for a market (without prices)"""
        data = load_indices_data(market)
        
        indices = []
        for idx in data.get("indices", []):
            indices.append({
                "id": idx["id"],
                "name": idx["name"],
                "symbol": idx["symbol"],
                "exchange": idx["exchange"],
                "type": idx["type"],
                "description": idx["description"],
                "constituents_count": len(idx.get("constituents", []))
            })
        
        return indices
    
    def get_indices_with_prices(self, market: str = "india") -> List[Dict[str, Any]]:
        """Get all indices with live prices from yfinance"""
        data = load_indices_data(market)
        indices = data.get("indices", [])
        
        # Get all index symbols
        symbols = [idx["symbol"] for idx in indices]
        
        # Fetch prices in parallel
        quotes = fetch_multiple_quotes(symbols)
        
        result = []
        for idx in indices:
            symbol = idx["symbol"]
            quote = quotes.get(symbol, {})
            
            result.append({
                "id": idx["id"],
                "name": idx["name"],
                "symbol": symbol,
                "exchange": idx["exchange"],
                "type": idx["type"],
                "description": idx["description"],
                "constituents_count": len(idx.get("constituents", [])),
                "price": quote.get("price"),
                "change": quote.get("change"),
                "change_percent": quote.get("change_percent"),
                "currency": "₹" if market.lower() == "india" else "$"
            })
        
        return result
    
    def get_index_constituents(self, index_id: str, market: str = "india") -> Dict[str, Any]:
        """Get constituents of an index with live prices"""
        data = load_indices_data(market)
        
        # Find the index
        index_data = None
        actual_market = market
        for idx in data.get("indices", []):
            if idx["id"] == index_id:
                index_data = idx
                break
        
        # If not found, try the other market
        if not index_data:
            other_market = "us" if market.lower() == "india" else "india"
            other_data = load_indices_data(other_market)
            for idx in other_data.get("indices", []):
                if idx["id"] == index_id:
                    index_data = idx
                    actual_market = other_market
                    break
        
        if not index_data:
            return {"error": f"Index {index_id} not found"}
        
        constituents = index_data.get("constituents", [])
        symbols = [c["symbol"] for c in constituents]
        
        # Fetch prices in parallel
        quotes = fetch_multiple_quotes(symbols, max_workers=15)
        
        # Build result with prices
        stocks = []
        currency = "₹" if actual_market.lower() == "india" else "$"
        for c in constituents:
            symbol = c["symbol"]
            quote = quotes.get(symbol, {})
            
            stocks.append({
                "symbol": symbol,
                "name": c["name"],
                "price": quote.get("price"),
                "prev_close": quote.get("prev_close"),
                "change": quote.get("change"),
                "change_percent": quote.get("change_percent"),
                "volume": quote.get("volume"),
                "currency": currency
            })
        
        # Sort by change_percent (gainers first)
        stocks.sort(key=lambda x: x.get("change_percent") or 0, reverse=True)
        
        return {
            "index": {
                "id": index_data["id"],
                "name": index_data["name"],
                "symbol": index_data["symbol"],
                "exchange": index_data["exchange"],
                "type": index_data["type"],
                "description": index_data["description"]
            },
            "stocks": stocks,
            "summary": {
                "total": len(stocks),
                "gainers": len([s for s in stocks if (s.get("change_percent") or 0) > 0]),
                "losers": len([s for s in stocks if (s.get("change_percent") or 0) < 0]),
                "unchanged": len([s for s in stocks if (s.get("change_percent") or 0) == 0])
            }
        }
    
    def get_treemap_data(self, market: str = "india", index_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get data formatted for treemap visualization.
        If index_id is provided, returns stocks. Otherwise returns indices.
        """
        if index_id:
            # Return stocks for the specific index
            return self.get_index_constituents(index_id, market)
        else:
            # Return all indices
            indices = self.get_indices_with_prices(market)
            
            # Group by type for treemap
            grouped = {}
            for idx in indices:
                idx_type = idx["type"]
                if idx_type not in grouped:
                    grouped[idx_type] = []
                grouped[idx_type].append(idx)
            
            return {
                "market": market,
                "currency": "₹" if market.lower() == "india" else "$",
                "indices": indices,
                "grouped": grouped,
                "summary": {
                    "total": len(indices),
                    "gainers": len([i for i in indices if (i.get("change_percent") or 0) > 0]),
                    "losers": len([i for i in indices if (i.get("change_percent") or 0) < 0])
                }
            }
    
    def get_gainers_losers(self, index_id: str, market: str = "india", top_n: int = 5) -> Dict[str, Any]:
        """Get top gainers and losers for an index"""
        data = self.get_index_constituents(index_id, market)
        
        if "error" in data:
            return data
        
        stocks = data["stocks"]
        
        gainers = [s for s in stocks if (s.get("change_percent") or 0) > 0][:top_n]
        losers = [s for s in stocks if (s.get("change_percent") or 0) < 0]
        losers = sorted(losers, key=lambda x: x.get("change_percent") or 0)[:top_n]
        
        return {
            "index": data["index"],
            "gainers": gainers,
            "losers": losers
        }
    
    def search_stocks(self, query: str, market: str = "india") -> List[Dict[str, Any]]:
        """Search for stocks across all indices"""
        data = load_indices_data(market)
        query_lower = query.lower()
        
        results = []
        seen_symbols = set()
        
        for idx in data.get("indices", []):
            for c in idx.get("constituents", []):
                symbol = c["symbol"]
                if symbol in seen_symbols:
                    continue
                
                if query_lower in c["name"].lower() or query_lower in symbol.lower():
                    results.append({
                        "symbol": symbol,
                        "name": c["name"],
                        "index": idx["name"],
                        "index_id": idx["id"]
                    })
                    seen_symbols.add(symbol)
        
        return results[:20]  # Limit results

    def get_stock_details(self, symbol: str, market: str = "india") -> Dict[str, Any]:
        """Get comprehensive stock details from yfinance"""
        try:
            # Add market suffix if needed
            if market.lower() == "india":
                if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
                    yf_symbol = f"{symbol}.NS"
                else:
                    yf_symbol = symbol
            else:
                yf_symbol = symbol
            
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
            # Get historical data
            hist = ticker.history(period="5d")
            hist_1y = ticker.history(period="1y")
            
            # Calculate price data
            current_price = hist['Close'].iloc[-1] if not hist.empty else None
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            
            if current_price and prev_close:
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0
            
            # Calculate 52-week high/low
            week_52_high = hist_1y['High'].max() if not hist_1y.empty else None
            week_52_low = hist_1y['Low'].min() if not hist_1y.empty else None
            
            # Build comprehensive response
            return {
                "symbol": symbol,
                "yf_symbol": yf_symbol,
                "name": info.get("longName") or info.get("shortName", symbol),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "currency": info.get("currency", "INR" if market == "india" else "USD"),
                
                # Price data
                "price": {
                    "current": round(current_price, 2) if current_price else None,
                    "previous_close": round(prev_close, 2) if prev_close else None,
                    "open": round(hist['Open'].iloc[-1], 2) if not hist.empty else None,
                    "day_high": round(hist['High'].iloc[-1], 2) if not hist.empty else None,
                    "day_low": round(hist['Low'].iloc[-1], 2) if not hist.empty else None,
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "week_52_high": round(week_52_high, 2) if week_52_high else None,
                    "week_52_low": round(week_52_low, 2) if week_52_low else None
                },
                
                # Volume
                "volume": {
                    "current": int(hist['Volume'].iloc[-1]) if not hist.empty else None,
                    "avg_10d": int(info.get("averageVolume10days", 0)),
                    "avg_3m": int(info.get("averageVolume", 0))
                },
                
                # Valuation
                "valuation": {
                    "market_cap": info.get("marketCap"),
                    "enterprise_value": info.get("enterpriseValue"),
                    "pe_ratio": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "peg_ratio": info.get("pegRatio"),
                    "price_to_book": info.get("priceToBook"),
                    "price_to_sales": info.get("priceToSalesTrailing12Months"),
                    "ev_to_revenue": info.get("enterpriseToRevenue"),
                    "ev_to_ebitda": info.get("enterpriseToEbitda")
                },
                
                # Financials
                "financials": {
                    "revenue": info.get("totalRevenue"),
                    "revenue_per_share": info.get("revenuePerShare"),
                    "gross_profit": info.get("grossProfits"),
                    "ebitda": info.get("ebitda"),
                    "net_income": info.get("netIncomeToCommon"),
                    "eps_trailing": info.get("trailingEps"),
                    "eps_forward": info.get("forwardEps"),
                    "profit_margin": info.get("profitMargins"),
                    "operating_margin": info.get("operatingMargins"),
                    "gross_margin": info.get("grossMargins"),
                    "return_on_equity": info.get("returnOnEquity"),
                    "return_on_assets": info.get("returnOnAssets")
                },
                
                # Dividends
                "dividends": {
                    "dividend_rate": info.get("dividendRate"),
                    "dividend_yield": info.get("dividendYield"),
                    "payout_ratio": info.get("payoutRatio"),
                    "ex_dividend_date": info.get("exDividendDate"),
                    "five_year_avg_yield": info.get("fiveYearAvgDividendYield")
                },
                
                # Balance Sheet
                "balance_sheet": {
                    "total_cash": info.get("totalCash"),
                    "total_debt": info.get("totalDebt"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "quick_ratio": info.get("quickRatio"),
                    "book_value": info.get("bookValue")
                },
                
                # Analyst Data
                "analyst": {
                    "target_high": info.get("targetHighPrice"),
                    "target_low": info.get("targetLowPrice"),
                    "target_mean": info.get("targetMeanPrice"),
                    "target_median": info.get("targetMedianPrice"),
                    "recommendation": info.get("recommendationKey"),
                    "recommendation_mean": info.get("recommendationMean"),
                    "num_analysts": info.get("numberOfAnalystOpinions")
                },
                
                # Company Info
                "company": {
                    "website": info.get("website"),
                    "phone": info.get("phone"),
                    "address": info.get("address1"),
                    "city": info.get("city"),
                    "country": info.get("country"),
                    "employees": info.get("fullTimeEmployees"),
                    "description": info.get("longBusinessSummary")
                },
                
                # Trading Info
                "trading": {
                    "exchange": info.get("exchange"),
                    "quote_type": info.get("quoteType"),
                    "beta": info.get("beta"),
                    "shares_outstanding": info.get("sharesOutstanding"),
                    "float_shares": info.get("floatShares"),
                    "shares_short": info.get("sharesShort"),
                    "short_ratio": info.get("shortRatio"),
                    "short_percent_of_float": info.get("shortPercentOfFloat")
                }
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "error": str(e)
            }

