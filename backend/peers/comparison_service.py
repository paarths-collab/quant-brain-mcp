from __future__ import annotations
import os
import requests
import yfinance as yf
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE_URL = os.getenv("FMP_BASE_URL", "https://financialmodelingprep.com/api/v4")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
PEERS_PREMIUM = False

try:
    import finnhub
except Exception:  # pragma: no cover
    finnhub = None

INDIA_PEER_OVERRIDES: Dict[str, List[str]] = {
    "RELIANCE.NS": [
        "ONGC.NS",
        "IOC.NS",
        "BPCL.NS",
        "HINDPETRO.NS",
        "GAIL.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "TATAPOWER.NS",
    ],
}

INDIA_FALLBACK_UNIVERSE: List[str] = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "LT.NS",
    "KOTAKBANK.NS",
    "HCLTECH.NS",
    "AXISBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "BAJFINANCE.NS",
    "BHARTIARTL.NS",
    "SUNPHARMA.NS",
    "ULTRACEMCO.NS",
    "TITAN.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "ONGC.NS",
    "TATAMOTORS.NS",
    "ADANIPORTS.NS",
    "ADANIENT.NS",
    "BAJAJFINSV.NS",
    "BAJAJ-AUTO.NS",
    "BRITANNIA.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "DIVISLAB.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "GRASIM.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "INDUSINDBK.NS",
    "JSWSTEEL.NS",
    "M&M.NS",
    "NESTLEIND.NS",
    "SBILIFE.NS",
    "SHRIRAMFIN.NS",
    "TECHM.NS",
    "TATASTEEL.NS",
    "WIPRO.NS",
    "BPCL.NS",
    "HDFCLIFE.NS",
    "APOLLOHOSP.NS",
    "TRENT.NS",
    "LTIM.NS",
]


def _is_demo_allowed(symbol: str) -> bool:
    return symbol.upper() in INDIA_FALLBACK_UNIVERSE


def _india_peer_fallback(symbol: str, limit: int) -> List[str]:
    sym = symbol.upper()
    if sym in INDIA_PEER_OVERRIDES:
        peers = INDIA_PEER_OVERRIDES[sym]
    else:
        peers = [s for s in INDIA_FALLBACK_UNIVERSE if s != sym]
    return peers[: max(0, limit)]


def _load_india_peers_from_json(symbol: str, limit: int) -> List[str]:
    """Load India peer mappings from JSON file."""
    try:
        import json
        json_path = os.path.join(os.path.dirname(__file__), "../data/india_peers.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                peers_map = json.load(f)
            sym = symbol.upper()
            if sym in peers_map and isinstance(peers_map[sym], dict) and "peers" in peers_map[sym]:
                return peers_map[sym]["peers"][: max(0, limit)]
    except Exception as e:
        print(f"Failed to load India peers from JSON: {e}")
    return []



def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _is_india_symbol(symbol: str) -> bool:
    sym = symbol.upper()
    return sym.endswith(".NS") or sym.endswith(".BO")


def _finnhub_symbol(symbol: str) -> Optional[str]:
    sym = symbol.strip().upper()
    if sym.startswith("^") or _is_india_symbol(sym):
        return None
    if "." in sym:
        sym = sym.split(".")[0]
    return sym


def _fetch_json(url: str) -> Any:
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _fetch_json_params(base_url: str, params: Dict[str, Any]) -> Any:
    try:
        r = requests.get(base_url, params=params, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _is_valid_list(data: Any) -> bool:
    if not isinstance(data, list) or len(data) == 0:
        return False
    if isinstance(data[0], dict) and (data[0].get("Error Message") or data[0].get("error")):
        return False
    return True


def _fetch_list(urls: List[str]) -> List[Dict[str, Any]]:
    for url in urls:
        data = _fetch_json(url)
        if _is_valid_list(data):
            return data
    return []


def _growth_pct(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous * 100


def _fmp_profile(symbol: str) -> Dict[str, Any]:
    urls = [
        f"https://financialmodelingprep.com/stable/profile?symbol={symbol}&apikey={FMP_API_KEY}",
        f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={FMP_API_KEY}",
    ]
    data = _fetch_list(urls)
    return data[0] if data else {}


def _fmp_screener_peers(symbol: str, limit: int = 8) -> List[str]:
    profile = _fmp_profile(symbol)
    sector = profile.get("sector")
    industry = profile.get("industry")
    exchange = profile.get("exchangeShortName") or profile.get("exchange")
    if not sector and not industry:
        try:
            info = yf.Ticker(symbol).info or {}
            sector = info.get("sector")
            industry = info.get("industry")
            exchange = exchange or info.get("exchange")
        except Exception:
            sector = sector or None
            industry = industry or None
    params: Dict[str, Any] = {"limit": limit, "apikey": FMP_API_KEY}
    if industry:
        params["industry"] = str(industry)
    elif sector:
        params["sector"] = str(sector)
    if exchange:
        exchange_str = str(exchange).upper()
        exchange_str = {
            "NMS": "NASDAQ",
            "NAS": "NASDAQ",
            "NGM": "NASDAQ",
            "NCM": "NASDAQ",
            "NYQ": "NYSE",
        }.get(exchange_str, exchange_str)
        if exchange_str in {"NASDAQ", "NYSE", "AMEX", "BATS", "OTC", "OTCQX", "OTCQB"}:
            params["exchange"] = exchange_str
    if "exchange" not in params and _is_india_symbol(symbol):
        params["exchange"] = "NSE" if symbol.upper().endswith(".NS") else "BSE"
    data = None
    for base_url in (
        "https://financialmodelingprep.com/stable/company-screener",
        "https://financialmodelingprep.com/api/v3/stock-screener",
    ):
        data = _fetch_json_params(base_url, params)
        if _is_valid_list(data):
            break
    if not _is_valid_list(data):
        data = []
    peers: List[str] = []
    for item in data:
        sym = item.get("symbol")
        if sym and sym not in peers:
            peers.append(sym)
    return peers


def _extract_quarter_values(ticker: yf.Ticker, label: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        qf = ticker.quarterly_financials
        if qf is None or qf.empty:
            return None, None
        if label not in qf.index:
            return None, None
        series = qf.loc[label]
        latest = series.iloc[0] if len(series) > 0 else None
        prev = series.iloc[1] if len(series) > 1 else None
        return _safe_float(latest), _safe_float(prev)
    except Exception:
        return None, None


def _yf_basic_metrics(symbol: str, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        ticker = yf.Ticker(symbol)
        info = {}
        fast = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        try:
            fast = ticker.fast_info or {}
        except Exception:
            fast = {}

        price = _safe_float(fast.get("last_price") or fast.get("lastPrice") or info.get("currentPrice"))
        if price is None:
            try:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    price = _safe_float(hist["Close"].iloc[-1])
            except Exception:
                price = None

        market_cap = _safe_float(fast.get("market_cap") or info.get("marketCap"))
        pe = _safe_float(info.get("trailingPE"))
        div_yield = _safe_float(info.get("dividendYield"))
        if div_yield is not None:
            div_yield = div_yield * 100

        roce = _safe_float(info.get("returnOnCapitalEmployed"))
        if roce is not None and roce <= 1:
            roce = roce * 100

        return {
            "symbol": symbol,
            "name": name or info.get("longName") or info.get("shortName") or symbol,
            "price": price,
            "pe": pe,
            "market_cap": market_cap,
            "div_yield": div_yield,
            "roce": roce,
        }
    except Exception:
        return None


def _yf_quarterly_metrics(symbol: str, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        ticker = yf.Ticker(symbol)
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        net_income, prev_net_income = _extract_quarter_values(ticker, "Net Income")
        revenue, prev_revenue = _extract_quarter_values(ticker, "Total Revenue")

        return {
            "symbol": symbol,
            "name": name or info.get("longName") or info.get("shortName") or symbol,
            "net_profit_q": net_income,
            "profit_q_var": _growth_pct(net_income, prev_net_income),
            "sales_q": revenue,
            "sales_q_var": _growth_pct(revenue, prev_revenue),
        }
    except Exception:
        return None


def _finnhub_company_name(symbol: str) -> Optional[str]:
    if not FINNHUB_API_KEY or finnhub is None:
        return None
    try:
        client = finnhub.Client(api_key=FINNHUB_API_KEY)
        profile = client.company_profile2(symbol=symbol) or {}
        return profile.get("name") or profile.get("ticker")
    except Exception:
        return None


def _finnhub_peers(symbol: str) -> List[str]:
    if not FINNHUB_API_KEY or finnhub is None:
        return []
    try:
        client = finnhub.Client(api_key=FINNHUB_API_KEY)
        data = client.company_peers(symbol)
        if isinstance(data, list):
            peers = data
        elif isinstance(data, dict):
            peers = data.get("peers", [])
        else:
            peers = []
        return [p for p in peers if isinstance(p, str) and p != symbol]
    except Exception:
        return []


def fetch_peer_comparison(symbol: str, limit: int = 12, debug: bool = False) -> Dict[str, Any]:
    sym = _normalize_symbol(symbol)
    fh_sym = _finnhub_symbol(sym)
    premium_enabled = PEERS_PREMIUM

    if premium_enabled and not FINNHUB_API_KEY and not FMP_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY or FMP_API_KEY must be configured")

    # Logic Update:
    # 1. Premium users: All allowed.
    # 2. Non-premium:
    #    - India (.NS/.BO): Restricted to INDIA_FALLBACK_UNIVERSE.
    #    - US/Global: All allowed (Bypass premium check).

    is_india = _is_india_symbol(sym)
    
    if not premium_enabled:
        # If India, enforce strict list
        if is_india and not _is_demo_allowed(sym):
             return {
                "symbol": sym,
                "count": 0,
                "rows": [],
                "restricted": True,
                "message": (
                    "Indian peer comparison is limited to specific demo stocks. "
                    "Please try RELIANCE, TCS, HDFCBANK, etc."
                ),
                "allowed_symbols": INDIA_FALLBACK_UNIVERSE,
            }
        # If NOT India (US/Global), we allow it! (Unlock feature)

    symbols: List[str] = []
    peers_from_fmp: List[str] = []
    name_map: Dict[str, str] = {}
    
    # Finnhub peers + company names (preferred)
    peers_from_finnhub: List[str] = []
    
    # Attempt Finnhub if key present (regardless of premium, if we have key)
    if FINNHUB_API_KEY and fh_sym:
        try:
            fh_peers = _finnhub_peers(fh_sym)
            for p in fh_peers:
                if p not in symbols:
                    symbols.append(p)
            peers_from_finnhub = fh_peers
            base_name = _finnhub_company_name(fh_sym)
            if base_name:
                name_map[sym] = base_name
            for p in fh_peers[: max(1, limit)]:
                name = _finnhub_company_name(p)
                if name:
                    name_map[p] = name
        except Exception:
            pass

    # Fallback: FMP peers if Finnhub returned none
    peers_data = None
    if not symbols and FMP_API_KEY:
        peers_urls = [
            f"https://financialmodelingprep.com/stable/stock-peers?symbol={sym}&apikey={FMP_API_KEY}",
            f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={sym}&apikey={FMP_API_KEY}",
            f"{FMP_BASE_URL}/stock_peers?symbol={sym}&apikey={FMP_API_KEY}",
        ]
        for url in peers_urls:
            peers_data = _fetch_json(url)
            if isinstance(peers_data, list) and len(peers_data) > 0:
                break
            if isinstance(peers_data, dict) and isinstance(peers_data.get("peersList"), list) and len(peers_data.get("peersList", [])) > 0:
                break
        if isinstance(peers_data, dict) and isinstance(peers_data.get("peersList"), list):
            for s in peers_data.get("peersList", []):
                if s and s not in symbols:
                    symbols.append(s)
                    peers_from_fmp.append(s)
        elif isinstance(peers_data, list):
            for item in peers_data:
                s = item.get("symbol") if isinstance(item, dict) else None
                if isinstance(item, dict) and s and item.get("companyName"):
                    name_map[s] = item.get("companyName")
                if s and s not in symbols:
                    symbols.append(s)
                    peers_from_fmp.append(s)
        elif isinstance(peers_data, dict) and isinstance(peers_data.get("peers"), list):
            for s in peers_data.get("peers", []):
                if s and s not in symbols:
                    symbols.append(s)
                    peers_from_fmp.append(s)

    # Try screener as additional source
    peers_from_screener: List[str] = []
    if not symbols and FMP_API_KEY:
        screener_peers = _fmp_screener_peers(sym, limit=limit)
        for p in screener_peers:
            if p not in symbols:
                symbols.append(p)
        peers_from_screener = screener_peers

    # India fallback: STRICTLY enforce list for Indian stocks if they are in the universe
    india_fallback: List[str] = []
    # If it's an India stock, we want to ensure we get good peers.
    # Even if APIs returned something, if it's garbage, we prefer our list.
    # But for now, let's append our list if symbols are few.
    if is_india and (len(symbols) <= 2 or sym in INDIA_FALLBACK_UNIVERSE):
         # Try loading from JSON file first
         fallback_peers = _load_india_peers_from_json(sym, limit=limit)
         # Fall back to hardcoded list if JSON doesn't have it
         if not fallback_peers:
             fallback_peers = _india_peer_fallback(sym, limit=limit)
         for p in fallback_peers:
            if p not in symbols:
                symbols.append(p)
         india_fallback = fallback_peers

    # Ensure the original symbol is first
    if sym not in symbols:
        symbols.insert(0, sym)
    elif symbols[0] != sym:
        symbols.remove(sym)
        symbols.insert(0, sym)

    symbols = symbols[: max(1, limit)]

    rows: List[Dict[str, Any]] = []

    def build_row(peer: str) -> Optional[Dict[str, Any]]:
        try:
            base = _yf_basic_metrics(peer, name_map.get(peer))
            if base is None:
                base = {"symbol": peer, "name": name_map.get(peer) or peer}
            quarterly = _yf_quarterly_metrics(peer, name_map.get(peer)) or {}
            merged = {**base, **quarterly}
            return merged
        except Exception as e:
            print(f"Error building row for {peer}: {e}")
            return {"symbol": peer, "name": name_map.get(peer) or peer}

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(build_row, peer): peer for peer in symbols}
        for future in as_completed(future_map):
            try:
                row = future.result()
                if row:
                    rows.append(row)
            except Exception as e:
                peer_name = future_map.get(future, "unknown")
                print(f"Exception from future for {peer_name}: {e}")
                continue

    result = {
        "symbol": sym,
        "count": len(rows),
        "rows": rows,
    }
    
    # If we got no data and it's an India stock, ensure at least name fallback
    if not rows and is_india and sym in INDIA_FALLBACK_UNIVERSE:
        # Return with at least the symbol and basic names from overrides
        fallback_symbols = _india_peer_fallback(sym, limit=limit)
        for fallback_sym in fallback_symbols:
            rows.append({
                "symbol": fallback_sym,
                "name": fallback_sym,
                "price": None,
                "pe": None,
                "market_cap": None,
                "div_yield": None,
                "roce": None,
            })
        result["rows"] = rows
        result["count"] = len(rows)
        result["note"] = "Showing India peer list (metrics may not be available)"
    
    if debug:
        result["debug"] = {
            "fmp_peers": peers_from_fmp,
            "finnhub_peers": peers_from_finnhub,
            "screener_peers": peers_from_screener,
            "india_fallback": india_fallback,
            "premium_enabled": premium_enabled,
            "final_symbols": symbols,
        }
    return result


