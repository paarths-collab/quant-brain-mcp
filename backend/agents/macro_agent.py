import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List

import pandas as pd
import yfinance as yf
import pytz
import requests
import json
from pathlib import Path

# Optional dependencies
try:
    from fredapi import Fred
    HAS_FRED = True
except ImportError:
    Fred = None
    HAS_FRED = False

try:
    from nsetools import Nse
    HAS_NSETOOLS = True
except ImportError:
    Nse = None
    HAS_NSETOOLS = False


# --------------------------------------------------
# 🕒 Time Utilities
# --------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))


def ist_now() -> datetime:
    return datetime.now(IST)


def nse_market_status() -> str:
    now = ist_now()
    if now.weekday() >= 5:
        return "Closed"

    open_t = now.replace(hour=9, minute=15, second=0)
    close_t = now.replace(hour=15, minute=30, second=0)

    return "Open" if open_t <= now <= close_t else "Closed"


# --------------------------------------------------
# 📊 Market Breadth (Yahoo fallback)
# --------------------------------------------------

def load_universe_json(path: str) -> List[str]:
    try:
        file_path = Path(path)
        if not file_path.is_absolute():
            backend_root = Path(__file__).resolve().parents[1]
            file_path = backend_root / file_path

        if not file_path.exists():
            return ["^NSEI"]

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        symbols = [
            item.get("Symbol")
            for item in data
            if isinstance(item, dict) and item.get("Symbol")
        ]

        if not symbols:
            return ["^NSEI"]
        return [str(s) + ".NS" for s in symbols]
    except Exception:
        return ["^NSEI"]


def breadth_from_yfinance(symbols: List[str]) -> Tuple[int, int, int]:
    if not symbols:
        return 0, 0, 0

    data = yf.download(symbols, period="2d", progress=False)
    if "Close" not in data:
        return 0, 0, 0

    close = data["Close"].iloc[-2:]
    diff = close.diff().iloc[-1]

    advances = int((diff > 0).sum())
    declines = int((diff < 0).sum())
    unchanged = int((diff == 0).sum())

    return advances, declines, unchanged


# --------------------------------------------------
# 🌍 MacroAgent
# --------------------------------------------------

class MacroAgent:
    """
    Global + Indian macro intelligence engine.
    """

    def __init__(self, fred_api_key: str | None = None):
        self.fred = None
        self.nse = None

        if HAS_FRED and fred_api_key:
            try:
                self.fred = Fred(api_key=fred_api_key)
                logging.info("FRED client initialized")
            except Exception as e:
                logging.warning(f"FRED init failed: {e}")

        if HAS_NSETOOLS:
            try:
                self.nse = Nse()
                logging.info("NSETools client initialized")
            except Exception as e:
                logging.warning(f"NSETools init failed: {e}")

    # --------------------------------------------------
    # 🌐 Global Risk Indicators
    # --------------------------------------------------

    def get_global_indicators(self) -> Dict[str, str]:
        try:
            return {
                "VIX": f"{yf.Ticker('^VIX').history(period='5d')['Close'].iloc[-1]:.2f}",
                "US 10Y Yield": f"{yf.Ticker('^TNX').history(period='5d')['Close'].iloc[-1]:.2f}",
                "Gold": f"${yf.Ticker('GC=F').history(period='5d')['Close'].iloc[-1]:,.2f}",
                "Crude Oil": f"${yf.Ticker('CL=F').history(period='5d')['Close'].iloc[-1]:,.2f}",
            }
        except Exception as e:
            return {"Error": str(e)}

    # --------------------------------------------------
    # 🇺🇸 US Macro (FRED)
    # --------------------------------------------------

    def analyze_us_market(self) -> Dict[str, str]:
        if not self.fred:
            return {"Error": "FRED unavailable"}

        try:
            return {
                "GDP": f"{self.fred.get_series('GDP').iloc[-1]:,.2f}",
                "CPI": f"{self.fred.get_series('CPIAUCSL').iloc[-1]:.2f}",
                "Unemployment %": f"{self.fred.get_series('UNRATE').iloc[-1]:.2f}",
                "Fed Funds %": f"{self.fred.get_series('FEDFUNDS').iloc[-1]:.2f}",
            }
        except Exception as e:
            return {"Error": str(e)}

    # --------------------------------------------------
    # 🇮🇳 Indian Market Snapshot
    # --------------------------------------------------

    def analyze_indian_market(self) -> Dict[str, str]:
        data = {
            "Timestamp": ist_now().strftime("%d %b %Y %I:%M %p IST"),
            "Market Status": nse_market_status(),
        }

        # Indices
        for name, symbol in {
            "Nifty 50": "^NSEI",
            "Sensex": "^BSESN",
        }.items():
            try:
                hist = yf.Ticker(symbol).history(period="2d")
                last, prev = hist["Close"].iloc[-1], hist["Close"].iloc[-2]
                data[name] = f"{last:,.2f}"
                data[f"{name} Change"] = f"{last-prev:+.2f} ({(last-prev)/prev:.2%})"
            except Exception:
                data[name] = "N/A"

        # Market Breadth
        breadth = self._get_market_breadth()
        data.update(breadth)

        return data

    # --------------------------------------------------
    # 📈 Breadth Engine (Live → Fallback)
    # --------------------------------------------------

    def _get_market_breadth(self) -> Dict[str, str]:
        # 1️⃣ NSETools (live)
        if self.nse:
            try:
                adv_dec = self.nse.get_advances_declines()[0]
                adv, dec = adv_dec["advances"], adv_dec["declines"]
                return {
                    "Advances": adv,
                    "Declines": dec,
                    "Adv/Dec Ratio": round(adv / max(dec, 1), 2),
                    "Source": "NSETools",
                }
            except Exception:
                pass

        # 2️⃣ Yahoo Finance fallback
        symbols = load_universe_json("data/nifty500.json")
        adv, dec, _ = breadth_from_yfinance(symbols)

        return {
            "Advances": adv,
            "Declines": dec,
            "Adv/Dec Ratio": round(adv / max(dec, 1), 2),
            "Source": "Yahoo Finance",
        }





# import pandas as pd
# from fredapi import Fred
# from typing import Dict, Any,Tuple,List
# import logging
# from datetime import datetime
# import  yfinance as yf
# from nsetools import Nse
# import pytz
# from nsepython import nsefetch
# import requests
# import json
# import os
# import requests
# from bs4 import BeautifulSoup
# from nsetools import Nse



# # ✅ Selenium imports only if needed
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# import time
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import requests




# # --- Primary Data Source for Indian Market Data ---
# # --- FRED API for US Data ---
# try:
#     from fredapi import Fred
#     _HAS_FRED = True
# except ImportError:
#     Fred = None
#     _HAS_FRED = False

# # --- Nsetools for Indian Data ---
# # --- NSEPython for Indian Data ---
# import requests
# # --- add near top of file ---
# import datetime as _dt



# def _load_universe_csv(path: str) -> list[str]:
#     """
#     Loads a list of stock symbols from a CSV file from the 'Symbol' column
#     and formats them for yfinance by appending '.NS'.
#     """
#     try:
#         df = pd.read_csv(path)
        
#         # Check if the required 'Symbol' column exists in the CSV
#         if "Symbol" not in df.columns:
#             logging.error(f"FATAL: The CSV file at {path} does not have a 'Symbol' column.")
#             # Fallback to a single index to avoid crashing
#             return ["^NSEI"] 

#         # Get the list of symbols, drop any empty rows, and convert to string
#         symbols = df["Symbol"].dropna().astype(str).tolist()
        
#         # Append '.NS' to each symbol for Yahoo Finance to recognize it as an NSE stock
#         formatted_symbols = [s + ".NS" for s in symbols]
        
#         print(f"[SUCCESS] Loaded {len(formatted_symbols)} symbols from {path}.")
#         return formatted_symbols

#     except FileNotFoundError:
#         logging.warning(f"Universe file not found at {path}, using fallback (^NSEI).")
#         return ["^NSEI"]  # <-- Safe fallback if the file doesn't exist
#     except Exception as e:
#         logging.error(f"Error processing universe file {path}: {e}. Using fallback (^NSEI).")
#         return ["^NSEI"]

#     df = pd.read_csv(path)
#     # NSE CSV has 'Symbol' column
#     return (df["Symbol"].astype(str) + ".NS").tolist()
# def _ist_now():
#     from datetime import timezone, timedelta
#     IST = timezone(timedelta(hours=5, minutes=30))
#     return _dt.datetime.now(IST)

# def _market_status_ist() -> str:
#     """Heuristic: NSE regular hours 09:15–15:30 IST, Mon–Fri (no holiday calendar)."""
#     now = _ist_now()
#     if now.weekday() >= 5:  # Sat/Sun
#         return "Closed"
#     open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
#     close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
#     return "Open" if open_t <= now <= close_t else "Closed"


    


# # note: list may include duplicates (e.g., ONGC twice). We'll deduplicate below.



# def _breadth_from_yfinance(symbols: list[str]) -> Tuple[int, int, int]:
#     """
#     Downloads 2-day price data and robustly calculates the number of
#     advancing, declining, and unchanged stocks.
#     """
#     import yfinance as yf
#     import pandas as pd

#     if not symbols:
#         logging.warning("No tickers provided for breadth calculation.")
#         return 0, 0, 0

#     print(f"--> [Breadth] Downloading data for {len(symbols)} symbols...")
    
#     # Use group_by='ticker' which is more efficient for multiple tickers
#     data = yf.download(
#         symbols,
#         period="2d",
#         progress=False,
#         auto_adjust=False
#     )
    
#     # The data for multiple tickers comes in a wide format with multi-level columns
#     # We need to access the 'Close' prices
#     try:
#         close_prices = data['Close']
#     except (KeyError, TypeError):
#         logging.error("[Breadth] Could not find 'Close' column in yfinance output. Structure may have changed.")
#         return 0, 0, 0

#     if close_prices.empty or len(close_prices) < 2:
#         logging.warning("[Breadth] Not enough data for comparison (less than 2 days).")
#         return 0, 0, 0
        
#     # Get the last two rows of closing prices
#     last_two_days = close_prices.iloc[-2:]
    
#     # Calculate the difference between the last day and the day before
#     # A positive difference means the stock advanced, negative means it declined
#     diff = last_two_days.diff().iloc[-1]
    
#     # Count advances (diff > 0), declines (diff < 0), and unchanged (diff == 0)
#     advances = (diff > 0).sum()
#     declines = (diff < 0).sum()
#     unchanged = (diff == 0).sum()
    
#     print(f"--> [Breadth] Calculation Complete: Advances={advances}, Declines={declines}, Unchanged={unchanged}")
#     return int(advances), int(declines), int(unchanged)

# def fetch_nse_json():
#     url = "https://www.nseindia.com/api/marketTurnover"
#     headers = {"User-Agent": "Mozilla/5.0"}
#     session = requests.Session()
#     session.headers.update(headers)
#     r = session.get(url, timeout=10)
#     return r.json()

# def clean_universe(symbols):
#     valid = []
#     for sym in symbols:
#         try:
#             df = yf.download(sym, period="5d", interval="1d", progress=False)
#             if not df.empty:
#                 valid.append(sym)
#         except Exception:
#             continue
#     return valid

# def safe_download(symbols, retries=3, delay=5):
#     for attempt in range(retries):
#         try:
#             return yf.download(symbols, period="2d", interval="1d", group_by="ticker", progress=False)
#         except Exception as e:
#             print(f"[WARNING] Attempt {attempt+1} failed: {e}")
#             time.sleep(delay)
#     return None


# def fetch_nse_adv_dec_selenium():
#     options = Options()
#     options.add_argument("--headless")
#     options.add_argument("--disable-blink-features=AutomationControlled")

#     driver = webdriver.Chrome(options=options)
#     driver.get("https://www.nseindia.com/market-data/advance-decline")

#     time.sleep(5)  # wait for JS to load

#     try:
#         rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
#         advances, declines = 0, 0

#         for row in rows:
#             cols = row.text.split()
#             if len(cols) >= 3:
#                 advances += int(cols[1])
#                 declines += int(cols[2])

#         driver.quit()
#         return {"advances": advances, "declines": declines, "source": "selenium"}
#     except Exception as e:
#         driver.quit()
#         return {"Error": f"Selenium scrape failed: {e}"}

# class MacroAgent:
#     def __init__(self, fred_api_key: str = None):
#         """
#         Initializes clients for both US (FRED) and Indian (NSE) market data.
#         """
#         self.fred_client = None
#         self.nse_client = None
        
  
#         # Initialize NSE client using nsetools with error handling
#         try:
#             self.nse = Nse()
#             print("[SUCCESS] MacroAgent: NSE client initialized.")
#         except Exception as e:
#             print(f"[WARNING] MacroAgent: NSE client initialization failed: {e}. Indian market data features may be limited.")
#             self.nse = None
        
#         # Initialize FRED client
#         if _HAS_FRED and fred_api_key:
#             try:
#                 self.fred_client = Fred(api_key=fred_api_key)
#                 print("[SUCCESS] MacroAgent: FRED client initialized.")
#             except Exception as e:
#                 print(f"[ERROR] WARNING: FRED client initialization failed: {e}")
#         else:
#             print("[ERROR] WARNING: FRED API key not provided or fredapi not installed.")
        

#     def get_global_indicators(self) -> dict:
#         """Fetches key global risk indicators using yfinance."""
#         print("MacroAgent: Fetching global indicators...")
#         try:
#             vix_data = yf.Ticker("^VIX").history(period="5d")
#             tnx_data = yf.Ticker("^TNX").history(period="5d")
#             gold_data = yf.Ticker("GC=F").history(period="5d")
#             oil_data = yf.Ticker("CL=F").history(period="5d")
            
#             # Check if data is available and 'Close' column exists
#             if vix_data.empty or 'Close' not in vix_data.columns or len(vix_data) < 1:
#                 return {"Error": "Could not fetch VIX data"}
#             if tnx_data.empty or 'Close' not in tnx_data.columns or len(tnx_data) < 1:
#                 return {"Error": "Could not fetch US 10Y Yield data"}
#             if gold_data.empty or 'Close' not in gold_data.columns or len(gold_data) < 1:
#                 return {"Error": "Could not fetch Gold data"}
#             if oil_data.empty or 'Close' not in oil_data.columns or len(oil_data) < 1:
#                 return {"Error": "Could not fetch Crude Oil data"}
            
#             vix = vix_data['Close'].iloc[-1]
#             tnx = tnx_data['Close'].iloc[-1]
#             gold = gold_data['Close'].iloc[-1]
#             oil = oil_data['Close'].iloc[-1]
#             return {
#                 "VIX (Fear Index)": f"{vix:.2f}",
#                 "US 10Y Yield %": f"{tnx:.2f}",
#                 "Gold Price (USD)": f"${gold:,.2f}",
#                 "Crude Oil (WTI)": f"${oil:,.2f}",
#             }
#         except Exception as e:
#             return {"Error": f"Failed to fetch global indicators: {e}"}

#     def analyze_us_market(self) -> dict:
#         """Fetches key US macroeconomic indicators from FRED."""
#         if not self.fred_client: return {"Error": "FRED client not available."}
#         print("MacroAgent: Fetching US data from FRED...")
#         try:
#             gdp = self.fred_client.get_series('GDP').iloc[-1]
#             cpi = self.fred_client.get_series('CPIAUCSL').iloc[-1]
#             unrate = self.fred_client.get_series('UNRATE').iloc[-1]
#             fedfunds = self.fred_client.get_series('FEDFUNDS').iloc[-1]
#             return {
#                 "US GDP (Billions $)": f"{gdp:,.2f}", "US CPI (Inflation Index)": f"{cpi:.2f}",
#                 "US Unemployment Rate %": f"{unrate:.2f}", "US Fed Funds Rate %": f"{fedfunds:.2f}"
#             }
#         except Exception as e:
#             return {"Error": f"US Macro data fetch failed: {e}"}


#     def analyze_indian_market(self) -> dict:
#         """
#         Fetches a complete Indian market snapshot with a "live first" fallback strategy.
#         This version uses a robust individual fetch for indices to prevent 'nan' errors.
#         """
#         print("MacroAgent: Fetching Indian market snapshot with live-first strategy...")
        
#         # --- 1. Generate Timestamp ---
#         try:
#             ist_tz = pytz.timezone('Asia/Kolkata')
#             now_ist = datetime.now(ist_tz)
#             timestamp_str = now_ist.strftime('%B %d, %Y, %I:%M %p %Z')
#         except Exception:
#             timestamp_str = "Timestamp not available"

#         final_data = {"Data Timestamp": timestamp_str}
        
#         # --- 2. Fetch Indices (Robust Individual Method) ---
#         # Nifty 50
#         try:
#             nifty_ticker = yf.Ticker("^NSEI")
#             nifty_hist = nifty_ticker.history(period="2d")
#             # CRITICAL CHECK: Ensure we have at least 2 days of data and 'Close' column exists
#             if not nifty_hist.empty and 'Close' in nifty_hist.columns and len(nifty_hist) >= 2:
#                 nifty_close = nifty_hist['Close'].iloc[-1]
#                 nifty_prev = nifty_hist['Close'].iloc[-2]
#                 final_data["Nifty 50"] = f"{nifty_close:,.2f}"
#                 final_data["Nifty 50 Change"] = f"{nifty_close - nifty_prev:,.2f} ({(nifty_close - nifty_prev)/nifty_prev:.2%})"
#             else:
#                 # Handle case where download succeeds but returns incomplete data
#                 final_data["Nifty 50"] = "Data unavailable"
#                 final_data["Nifty 50 Change"] = "N/A"
#         except Exception as e:
#             print(f"[ERROR] yfinance failed for Nifty 50 (^NSEI): {e}")
#             final_data["Nifty 50"] = "Error"
#             final_data["Nifty 50 Change"] = "N/A"

#         # BSE Sensex
#         try:
#             sensex_ticker = yf.Ticker("^BSESN")
#             sensex_hist = sensex_ticker.history(period="2d")
#             # CRITICAL CHECK: Ensure we have at least 2 days of data and 'Close' column exists
#             if not sensex_hist.empty and 'Close' in sensex_hist.columns and len(sensex_hist) >= 2:
#                 sensex_close = sensex_hist['Close'].iloc[-1]
#                 sensex_prev = sensex_hist['Close'].iloc[-2]
#                 final_data["Sensex"] = f"{sensex_close:,.2f}"
#                 final_data["Sensex Change"] = f"{sensex_close - sensex_prev:,.2f} ({(sensex_close - sensex_prev)/sensex_prev:.2%})"
#             else:
#                 final_data["Sensex"] = "Data unavailable"
#                 final_data["Sensex Change"] = "N/A"
#         except Exception as e:
#             print(f"[ERROR] yfinance failed for BSE Sensex (^BSESN): {e}")
#             final_data["Sensex"] = "Error"
#             final_data["Sensex Change"] = "N/A"

#         # --- 3. Attempt to get Market Breadth from Live Sources ---
#         breadth_data = {}
#         breadth_success = False

#         # (The rest of your live-first fallback logic for breadth remains unchanged)
#         # Method 1: nsetools
#         if not breadth_success and self.nse is not None:
#             try:
#                 print("--> [Breadth] Trying live source 1: nsetools...")
#                 adv_dec = self.nse.get_advances_declines()
#                 advances = adv_dec[0]['advances']
#                 declines = adv_dec[0]['declines']
#                 breadth_data = {
#                     "NSE Market Status": _market_status_ist(),
#                     "NSE Advances": advances,
#                     "NSE Declines": declines,
#                     "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2),
#                     "Source": "nsetools (Live)"
#                 }
#                 breadth_success = True
#                 print("[SUCCESS] Fetched live breadth using nsetools.")
#             except Exception as e:
#                 print(f"[ERROR] nsetools failed: {e}")

#         # Method 2: Moneycontrol
#         if not breadth_success:
#             try:
#                 print("--> [Breadth] Trying live source 2: Moneycontrol...")
#                 r = requests.get("https://www.moneycontrol.com/stocksmarketsindia/", headers={"User-Agent": "Mozilla/50"})
#                 import re
#                 adv = re.search(r"Advances\s*</span>\s*<strong>(\d+)</strong>", r.text)
#                 dec = re.search(r"Declines\s*</span>\s*<strong>(\d+)</strong>", r.text)
#                 if adv and dec and (int(adv.group(1)) > 0 or int(dec.group(1)) > 0):
#                     advances, declines = int(adv.group(1)), int(dec.group(1))
#                     breadth_data = { "NSE Market Status": _market_status_ist(), "NSE Advances": advances, "NSE Declines": declines, "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2), "Source": "Moneycontrol (Live)"}
#                     breadth_success = True
#                     print("✅ Fetched live breadth using Moneycontrol.")
#                 else:
#                      print("[ERROR] Moneycontrol scrape returned no data.")
#             except Exception as e:
#                 print(f"[ERROR] Moneycontrol failed: {e}")

#         # Method 3 (Last Resort): yfinance calculation
#         if not breadth_success:
#             try:
#                 print("[WARNING] Live data sources failed. Falling back to yfinance calculation...")
#                 universe_symbols = _load_universe_csv("data/nifty500.csv")
#                 adv, dec, unch = _breadth_from_yfinance(universe_symbols)
#                 breadth_data = { "NSE Market Status": _market_status_ist(), "NSE Advances": adv, "NSE Declines": dec, "NSE Adv/Dec Ratio": round(adv / max(dec, 1), 2), "Source": "yfinance (Fallback)"}
#                 print("✅ Calculated breadth using yfinance fallback.")
#             except Exception as e:
#                 print(f"[ERROR] All breadth methods failed, including yfinance: {e}")
#                 breadth_data["Error"] = "All breadth data sources failed."

#         # --- 4. Combine and Return ---
#         final_data.update(breadth_data)
#         return final_data
    

    
#     # def analyze_indian_market(self):
#     #     india_data = {}

#     #     # 1️⃣ Try NSETOOLS
#     #     try:
#     #         adv_dec = self.nse.get_advances_declines()
#     #         advances = adv_dec[0]['advances']
#     #         declines = adv_dec[0]['declines']
#     #         india_data = {
#     #             "NSE Market Status": "Open",
#     #             "NSE Advances": advances,
#     #             "NSE Declines": declines,
#     #             "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2),
#     #             "Source": "nsetools"
#     #         }
#     #         return india_data
#     #     except Exception as e:
#     #         print(f"nsetools failed: {e}")

#     #     # 2️⃣ Try NSEPYTHON
#     #     try:
#     #         adv_dec = nsefetch("https://www.nseindia.com/api/marketTurnover")
#     #         advances = adv_dec["data"][0]["advances"]
#     #         declines = adv_dec["data"][0]["declines"]
#     #         india_data = {
#     #             "NSE Market Status": "Open",
#     #             "NSE Advances": advances,
#     #             "NSE Declines": declines,
#     #             "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2),
#     #             "Source": "nsepython"
#     #         }
#     #         return india_data
#     #     except Exception as e:
#     #         print(f"nsepython failed: {e}")

#     #     # 3️⃣ Try NSE JSON API directly
#     #     try:
#     #         session = requests.Session()
#     #         session.headers.update({"User-Agent": "Mozilla/5.0"})
#     #         r = session.get("https://www.nseindia.com/api/marketTurnover", timeout=10)
#     #         data = r.json()
#     #         data = fetch_nse_json()
#     #         advances = data["data"][0]["advances"]
#     #         declines = data["data"][0]["declines"]

#     #         india_data = {
#     #             "NSE Market Status": "Open",
#     #             "NSE Advances": advances,
#     #             "NSE Declines": declines,
#     #             "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2),
#     #             "Source": "nse_json_api"
#     #         }
#     #         return india_data
#     #     except Exception as e:
#     #         print(f"NSE JSON API failed: {e}")

#     #     # 4️⃣ Try Moneycontrol
#     #     try:
#     #         r = requests.get("https://www.moneycontrol.com/stocksmarketsindia/", headers={"User-Agent": "Mozilla/5.0"})
#     #         text = r.text
#     #         # simple regex to pull advances/declines
#     #         import re
#     #         adv = re.search(r"Advances\s*</span>\s*<strong>(\d+)</strong>", text)
#     #         dec = re.search(r"Declines\s*</span>\s*<strong>(\d+)</strong>", text)
#     #         advances = int(adv.group(1)) if adv else 0
#     #         declines = int(dec.group(1)) if dec else 0
#     #         india_data = {
#     #             "NSE Market Status": "Open",
#     #             "NSE Advances": advances,
#     #             "NSE Declines": declines,
#     #             "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2) if declines else "∞",
#     #             "Source": "Moneycontrol"
#     #         }
#     #         return india_data
#     #     except Exception as e:
#     #         print(f"Moneycontrol failed: {e}")

#     #     # 5️⃣ Last resort → Selenium
#     #     try:
#     #         options = Options()
#     #         options.add_argument("--headless")
#     #         options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
#     #         driver = webdriver.Chrome(options=options)
#     #         driver.get("https://www.nseindia.com/market-data/advances-declines")
#     #         rows = WebDriverWait(driver, 15).until(
#     #             EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr"))
#     #         )
#     #         advances = int(rows[0].find_elements(By.TAG_NAME, "td")[1].text.strip())
#     #         declines = int(rows[0].find_elements(By.TAG_NAME, "td")[2].text.strip())
#     #         driver.quit()
#     #         india_data = {
#     #             "NSE Market Status": "Open",
#     #             "NSE Advances": advances,
#     #             "NSE Declines": declines,
#     #             "NSE Adv/Dec Ratio": round(advances / max(declines, 1), 2),
#     #             "Source": "Selenium"
#     #         }
#     #         return india_data
#     #     except Exception as e:
#     #         print(f"Selenium failed: {e}")

#     #     # ❌ If everything fails
#     #     return {"Error": "All fallbacks failed"}
#     #             # ---------- NEW: yfinance self-computed breadth (robust, no scraping) ----------
#     #     try:
#     #         adv, dec, unch = _breadth_from_yfinance(_nifty50_list())
#     #         # If we got at least some coverage and not all zeros, use it
#     #         if (adv + dec + unch) > 0 and not (adv == 0 and dec == 0):
#     #             ratio = round(adv / max(dec, 1), 2) if dec > 0 else "∞"
#     #             return {
#     #                 "NSE Market Status": _market_status_ist(),
#     #                 "NSE Advances": int(adv),
#     #                 "NSE Declines": int(dec),
#     #                 "NSE Adv/Dec Ratio": ratio,
#     #                 "Universe": "NIFTY 50 (Yahoo Finance)",
#     #                 "Source": "yfinance (computed)"
#     #             }
#     #     except ImportError:
#     #         # yfinance not installed
#     #         pass
#     #     except Exception as e:
#     #         print(f"yfinance breadth failed: {e}")



        
#     #     """
#     #     Provides a snapshot of the Indian market using the 'investiny' library.
#     #     """
#     #     if not _HAS_INVESTINY:
#     #         return {"Error": "The 'investiny' library is not installed. Indian market data is unavailable."}

#     #     logger.info("MacroAgent: Fetching Indian market data via investiny...")
#     #     try:
#     #         today_str = datetime.today().strftime('%d/%m/%Y')
#     #         from_date_str = "01/01/2024"

#     #         # Search for the asset IDs for Nifty 50 and Sensex
#     #         nifty_id = investiny.search_assets(query="Nifty 50", limit=1)[0]["investing_id"]
#     #         sensex_id = investiny.search_assets(query="BSE Sensex", limit=1)[0]["investing_id"]
            
#     #         # Fetch recent historical data to get the latest close and change
#     #         nifty_hist = investiny.historical_data(investing_id=nifty_id, from_date=from_date_str, to_date=today_str)
#     #         sensex_hist = investiny.historical_data(investing_id=sensex_id, from_date=from_date_str, to_date=today_str)
            
#     #         nifty_latest = nifty_hist.iloc[-1]
#     #         sensex_latest = sensex_hist.iloc[-1]

#     #         return {
#     #             "Nifty 50": f"{nifty_latest['close']:,.2f}",
#     #             "Nifty 50 Change": f"{nifty_latest['change_percent']}",
#     #             "Sensex": f"{sensex_latest['close']:,.2f}",
#     #             "Sensex Change": f"{sensex_latest['change_percent']}"
#     #         }
#     #     except Exception as e:
#     #         logger.error(f"investiny data fetch failed: {e}")
#     #         return {"Error": f"Failed to fetch Indian market data via investiny: {e}"}






# # ## **Summary of the Definitive Changes**

# # # 1.  **Correct Library Import:** The import is now `from nsepython import nse_market_status, nse_adv_dec, nse_fiidii`. This is clean and imports only the functions we need.
# # # 2.  **No Client Initialization:** `nsepython` uses direct function calls, so the `__init__` method correctly no longer tries to create a client instance.
# # # 3.  **Correct Function Calls:** The `analyze_indian_market` method now correctly calls `nse_market_status()` and `nse_adv_dec()` as intended by the `nsepython` library.
# # # 4.  **Professional Enhancement (FII/DII Data):** I've added a call to `nse_fiidii()`. The net flow of Foreign Institutional Investors (FII) and Domestic Institutional Investors (DII) is a **critical** data point that professional brokers watch every single day. It's a strong indicator of "smart money" sentiment. The agent now fetches this data, and the Streamlit UI has been updated to display it.
# # # 5.  **Robustness:** The code remains resilient. If `nsepython` is not installed, the Indian market analysis will be gracefully disabled.

# # # This version is now definitively correct and aligned with the `nsepython` library you have installed. It will resolve the errors and provide a richer, more professional set of data for your Indian market analysis.



# # import os
# # import streamlit as st
# # import pandas as pd
# # import yfinance as yf
# # import plotly.express as px

# # # --- FRED API for US Data ---
# # try:
# #     from fredapi import Fred
# #     _HAS_FRED = True
# # except ImportError:
# #     Fred = None
# #     _HAS_FRED = False

# # # --- Nsetools for Indian Data ---
# # # --- NSEPython for Indian Data ---
# # try:
# #     from nsepython import nse_market_status, nse_adv_dec
# #     _HAS_NSE = True
# # except ImportError:
# #     nse_market_status, nse_adv_dec, nse_fiidii = None, None, None
# #     _HAS_NSE = False


# # class MacroAgent:
# #     def __init__(self, fred_api_key: str = None):
# #         """
# #         Initializes clients for both US (FRED) and Indian (NSE) market data.
# #         """
# #         self.fred_client = None
# #         self.nse_client = None
        
# #         # Initialize FRED client
# #         if _HAS_FRED and fred_api_key:
# #             try:
# #                 self.fred_client = Fred(api_key=fred_api_key)
# #                 print("✅ MacroAgent: FRED client initialized.")
# #             except Exception as e:
# #                 print(f"❌ WARNING: FRED client initialization failed: {e}")
# #         else:
# #             print("❌ WARNING: FRED API key not provided or fredapi not installed.")

# #         # Initialize NSE client using nsetools
# #         if _HAS_NSE:
# #             try:
# #                 self.nse_client = Nse()
# #                 print("✅ MacroAgent: nsetools client initialized.")
# #             except Exception as e:
# #                  print(f"❌ WARNING: nsetools client initialization failed: {e}")
# #         else:
# #             print("❌ WARNING: 'nsetools' library not installed. Indian Market data disabled.")

# #     def get_global_indicators(self) -> dict:
# #         """Fetches key global risk indicators using yfinance."""
# #         print("MacroAgent: Fetching global indicators...")
# #         try:
# #             vix = yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1]
# #             tnx = yf.Ticker("^TNX").history(period="5d")['Close'].iloc[-1]
# #             gold = yf.Ticker("GC=F").history(period="5d")['Close'].iloc[-1]
# #             oil = yf.Ticker("CL=F").history(period="5d")['Close'].iloc[-1]
# #             return {
# #                 "VIX (Fear Index)": f"{vix:.2f}",
# #                 "US 10Y Yield %": f"{tnx:.2f}",
# #                 "Gold Price (USD)": f"${gold:,.2f}",
# #                 "Crude Oil (WTI)": f"${oil:,.2f}",
# #             }
# #         except Exception as e:
# #             return {"Error": f"Failed to fetch global indicators: {e}"}

# #     def analyze_us_market(self) -> dict:
# #         """Fetches key US macroeconomic indicators from FRED."""
# #         if not self.fred_client: return {"Error": "FRED client not available."}
# #         print("MacroAgent: Fetching US data from FRED...")
# #         try:
# #             gdp = self.fred_client.get_series('GDP').iloc[-1]
# #             cpi = self.fred_client.get_series('CPIAUCSL').iloc[-1]
# #             unrate = self.fred_client.get_series('UNRATE').iloc[-1]
# #             fedfunds = self.fred_client.get_series('FEDFUNDS').iloc[-1]
# #             return {
# #                 "US GDP (Billions $)": f"{gdp:,.2f}", "US CPI (Inflation Index)": f"{cpi:.2f}",
# #                 "US Unemployment Rate %": f"{unrate:.2f}", "US Fed Funds Rate %": f"{fedfunds:.2f}"
# #             }
# #         except Exception as e:
# #             return {"Error": f"US Macro data fetch failed: {e}"}

# #     # In agents/macro_agent.py

# #     # ... (the __init__ and analyze_us_market methods are unchanged) ...

# #     def analyze_indian_market(self) -> dict:
   
# #         if not _HAS_NSE:
# #             return {"Error": "nsepython library not available."}
            
# #         print("MacroAgent: Fetching NSE market data...")
# #         # =========================
# # # Indian Market Indicators
# # # =========================
# #         st.write("🇮🇳 Indian Market Indicators (from NSE)")

# #         try:
# #             import nsepython as nse

# #             nifty = nse.nse_eq("NIFTY 50")
# #             st.write(nifty)

# #         except ImportError:
# #             st.error("❌ nsepython not installed in this environment.")
# #         except Exception as e:
# #             st.error(f"⚠️ NSE fetch failed: {e}")

# #             # --- THIS IS THE CORRECT LOGIC FOR 'nsetools' ---
            
# #             # 1. Check Market Status
# #             # 'nsetools' determines status by checking if a quote can be fetched.
# #             # is_market_open() returns True or False.
# #             is_open = self.nse_client.is_market_open()
# #             market_status_message = "Market is Open" if is_open else "Market is Closed"

# #             # 2. Get Advances and Declines
# #             # This function returns a dictionary like {'advances': 1326, 'declines': 744, ...}
# #             adv_dec = self.nse_client.get_advances_declines()
            
# #             adv = adv_dec.get('advances', 0)
# #             dec = adv_dec.get('declines', 0)

# #             return {
# #                 "NSE Market Status": market_status_message,
# #                 "NSE Advances": adv,
# #                 "NSE Declines": dec,
# #                 "NSE Adv/Dec Ratio": round(adv / dec, 2) if dec > 0 else "N/A"
# #             }
# #             # --- END OF CORRECT LOGIC ---
# #         except Exception as e:
# #             # This can happen if the NSE website changes or is down
# #             return {"Error": f"NSE market data fetch failed: {e}. The NSE website may be temporarily unavailable."}

# #     # ... (the rest of the file and the Streamlit part are unchanged) ...
        
# #     def get_historical_fred_data(self, series_id: str, years: int = 5) -> pd.DataFrame:
# #         """Fetches historical data for a given FRED series."""
# #         if not self.fred_client: return pd.DataFrame()
# #         end_date = pd.Timestamp.now()
# #         start_date = end_date - pd.DateOffset(years=years)
# #         return self.fred_client.get_series(series_id, start_date, end_date)

# # # --- Streamlit Visualization (Frontend Part) ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="Macro Dashboard", layout="wide")
# #     st.title("🌎 Global Macro & Market Dashboard")

# #     FRED_API_KEY = st.secrets.get("FRED_API_KEY", os.getenv("FRED_API_KEY"))
# #     agent = MacroAgent(fred_api_key=FRED_API_KEY)

# #     st.header("🌐 Global Risk Indicators")
# #     with st.spinner("Fetching global indicators..."):
# #         global_data = agent.get_global_indicators()
# #         if "Error" in global_data: st.error(global_data["Error"])
# #         else:
# #             cols = st.columns(4)
# #             cols[0].metric("VIX (Fear Index)", global_data.get("VIX (Fear Index)", "N/A"))
# #             cols[1].metric("US 10Y Yield", f"{global_data.get('US 10Y Yield %', 'N/A')}%")
# #             cols[2].metric("Gold Price", global_data.get("Gold Price (USD)", "N/A"))
# #             cols[3].metric("Crude Oil (WTI)", global_data.get("Crude Oil (WTI)", "N/A"))

# #     st.header("🇺🇸 US Economic Indicators (from FRED)")
# #     with st.spinner("Fetching US data..."):
# #         us_data = agent.analyze_us_market()
# #         if "Error" in us_data: st.error(us_data["Error"])
# #         else:
# #             cols = st.columns(4)
# #             cols[0].metric("GDP", us_data.get("US GDP (Billions $)", "N/A"))
# #             cols[1].metric("CPI", us_data.get("US CPI (Inflation Index)", "N/A"))
# #             cols[2].metric("Unemployment Rate", f"{us_data.get('US Unemployment Rate %', 'N/A')}%")
# #             cols[3].metric("Fed Funds Rate", f"{us_data.get('US Fed Funds Rate %', 'N/A')}%")
        
# #         if agent.fred_client:
# #             st.subheader("Historical Trends (5 Years)")
# #             cpi_hist = agent.get_historical_fred_data('CPIAUCSL')
# #             if not cpi_hist.empty:
# #                 st.plotly_chart(px.line(cpi_hist, title="US CPI (Inflation) Trend"), use_container_width=True)

# #     st.header("🇮🇳 Indian Market Indicators (from NSE)")
# #     with st.spinner("Fetching NSE data..."):
# #         india_data = agent.analyze_indian_market()
# #         if "Error" in india_data: st.error(india_data["Error"])
# #         else:
# #             cols = st.columns(4)
# #             market_status = india_data.get("NSE Market Status", "Unknown")
# #             status_color = "green" if "open" in market_status.lower() else "red"
# #             cols[0].markdown(f"**Market Status:** <span style='color:{status_color};'>**{market_status}**</span>", unsafe_allow_html=True)
# #             cols[1].metric("Advances 👍", india_data.get("NSE Advances", "N/A"))
# #             cols[2].metric("Declines 👎", india_data.get("NSE Declines", "N/A"))
# #             cols[3].metric("Adv/Dec Ratio", india_data.get("NSE Adv/Dec Ratio", "N/A"))

# #-----------------------------------------------------------------------------------------------------------------------------------------------------------
# # # import os
# # # import streamlit as st
# # # import pandas as pd
# # # from datetime import datetime
# # # from nsetools import Nse
# # # nse = Nse()
# # # # --- FRED API for US Data ---
# # # try:
# # #     from fredapi import Fred
# # #     _HAS_FRED = True
# # # except ImportError:
# # #     Fred = None
# # #     _HAS_FRED = False

# # # # --- NSE Stock Lib for Indian Data ---
# # # try:
# # #     nse=Nse()
# # #     _HAS_NSE = True
# # # except ImportError:
# # #     nse = None
# # #     _HAS_NSE = False

# # # class MacroAgent:
# # #     def __init__(self, fred_api_key: str = None):
# # #         """
# # #         Initializes clients for both US (FRED) and Indian (NSE) market data.
# # #         """
# # #         self.fred_client = None
# # #         self.nse_client = None
        
# # #         # Initialize FRED client
# # #         if _HAS_FRED and fred_api_key:
# # #             try:
# # #                 self.fred_client = Fred(api_key=fred_api_key)
# # #                 print("✅ MacroAgent: FRED client initialized.")
# # #             except Exception as e:
# # #                 print(f"❌ WARNING: FRED client initialization failed: {e}")
# # #         else:
# # #             print("❌ WARNING: FRED API key not provided or fredapi not installed. US Macro data disabled.")

# # #         # Initialize NSE client
# # #         if _HAS_NSE:
# # #             self.nse_client = nse
# # #             print("✅ MacroAgent: NSE client initialized.")
# # #         else:
# # #             print("❌ WARNING: nse-stock-lib not installed. Indian Market data disabled.")

# # #     def analyze_us_market(self) -> dict:
# # #         """Fetches key US macroeconomic indicators from FRED."""
# # #         if not self.fred_client:
# # #             return {"Error": "FRED client not available."}
        
# # #         print("MacroAgent: Fetching US data from FRED...")
# # #         try:
# # #             gdp_series = self.fred_client.get_series('GDP')
# # #             cpi_series = self.fred_client.get_series('CPIAUCSL')
# # #             unrate_series = self.fred_client.get_series('UNRATE')
# # #             fedfunds_series = self.fred_client.get_series('FEDFUNDS')
            
# # #             # Get the most recent value for each series
# # #             return {
# # #                 "US GDP (Billions $)": f"{gdp_series.iloc[-1]:,.2f}",
# # #                 "US CPI (Inflation Index)": f"{cpi_series.iloc[-1]:.2f}",
# # #                 "US Unemployment Rate %": f"{unrate_series.iloc[-1]:.2f}",
# # #                 "US Fed Funds Rate %": f"{fedfunds_series.iloc[-1]:.2f}"
# # #             }
# # #         except Exception as e:
# # #             return {"Error": f"US Macro data fetch failed: {e}"}

# # #     def analyze_indian_market(self) -> dict:
# # #         """Fetches key Indian market status indicators from NSE."""
# # #         if not self.nse_client:
# # #             return {"Error": "NSE client not available."}
            
# # #         print("MacroAgent: Fetching NSE market status...")
# # #         try:
# # #             status = self.nse_client.status()
# # #             adv_dec = self.nse_client.advanceDecline()
            
# # #             adv = adv_dec['data'][0]['advances']
# # #             dec = adv_dec['data'][0]['declines']

# # #             return {
# # #                 "NSE Market Status": status.get('marketState', [{}])[0].get('marketStatus', "Unknown"),
# # #                 "NSE Advances": adv,
# # #                 "NSE Declines": dec,
# # #                 "NSE Adv/Dec Ratio": round(adv / dec, 2) if dec > 0 else "N/A"
# # #             }
# # #         except Exception as e:
# # #             return {"Error": f"NSE market data fetch failed: {e}"}

# # # # --- Streamlit Visualization (Frontend Part) ---
# # # if __name__ == "__main__":
# # #     st.set_page_config(page_title="Macroeconomic Dashboard", layout="wide")
# # #     st.title("🌎 Macroeconomic & Market Indicator Dashboard")

# # #     # This part would typically be handled by the Orchestrator loading config.yaml
# # #     # For standalone testing, we get the key from Streamlit secrets or env vars.
# # #     FRED_API_KEY = st.secrets.get("FRED_API_KEY", os.getenv("FRED_API_KEY"))

# # #     if not FRED_API_KEY:
# # #         st.error("FRED_API_KEY not found! Please set it in your Streamlit secrets or as an environment variable to test the US data.")
    
# # #     agent = MacroAgent(fred_api_key=FRED_API_KEY)

# # #     st.header("🇺🇸 US Economic Indicators (from FRED)")
# # #     with st.spinner("Fetching US data..."):
# # #         us_data = agent.analyze_us_market()
# # #         if "Error" in us_data:
# # #             st.error(us_data["Error"])
# # #         else:
# # #             cols = st.columns(4)
# # #             cols[0].metric("GDP", us_data.get("US GDP (Billions $)", "N/A"))
# # #             cols[1].metric("CPI", us_data.get("US CPI (Inflation Index)", "N/A"))
# # #             cols[2].metric("Unemployment", f"{us_data.get('US Unemployment Rate %', 'N/A')}")
# # #             cols[3].metric("Interest Rate", f"{us_data.get('US Fed Funds Rate %', 'N/A')}")

# # #     st.header("🇮🇳 Indian Market Indicators (from NSE)")
# # #     with st.spinner("Fetching NSE data..."):
# # #         india_data = agent.analyze_indian_market()
# # #         if "Error" in india_data:
# # #             st.error(india_data["Error"])
# # #         else:
# # #             cols = st.columns(4)
# # #             market_status = india_data.get("NSE Market Status", "Unknown")
# # #             status_color = "green" if market_status == "Open" else "red"
# # #             cols[0].markdown(f"**Market Status:** <span style='color:{status_color};'>**{market_status}**</span>", unsafe_allow_html=True)
# # #             cols[1].metric("Advances 👍", india_data.get("NSE Advances", "N/A"))
# # #             cols[2].metric("Declines 👎", india_data.get("NSE Declines", "N/A"))
# # #             cols[3].metric("Adv/Dec Ratio", india_data.get("NSE Adv/Dec Ratio", "N/A"))
