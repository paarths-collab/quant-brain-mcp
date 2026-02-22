import json
import os
import time
import yfinance as yf
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def load_indices(path):
    tickers = []
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            for idx in data.get("indices", []):
                for c in idx.get("constituents", []):
                    tickers.append(c["symbol"])
    return tickers

def build_cache():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    
    us_path = os.path.join(data_dir, "us_indices.json")
    ind_path = os.path.join(data_dir, "indian_indices.json")
    cache_path = os.path.join(data_dir, "ticker_metadata.json")

    print("Loading tickers from indices...")
    us_tickers = load_indices(us_path)
    ind_tickers = load_indices(ind_path)
    
    all_tickers = list(set(us_tickers + ind_tickers))
    print(f"Found {len(all_tickers)} unique tickers to process.")

    # Load existing cache to resume if needed
    metadata = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            try:
                metadata = json.load(f)
            except:
                pass
    
    print(f"Loaded {len(metadata)} existing entries from cache.")
    
    tickers_to_fetch = [t for t in all_tickers if t not in metadata]
    print(f"Fetching metadata for {len(tickers_to_fetch)} new tickers...")

    for i, ticker in enumerate(tickers_to_fetch):
        try:
            print(f"[{i+1}/{len(tickers_to_fetch)}] Fetching {ticker}...", end=" ", flush=True)
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract only what we need to save space
            entry = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "longName": info.get("longName"),
                "country": info.get("country")
            }
            
            if entry["sector"] or entry["industry"]:
                metadata[ticker] = entry
                print("✅ Found: " + str(entry.get("sector")))
            else:
                print("⚠️ No sector data.")
            
            # Save incrementally every 10 tickers
            if i % 10 == 0:
                with open(cache_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            
            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    # Final Save
    with open(cache_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Cache build complete! Saved {len(metadata)} tickers to {cache_path}")

if __name__ == "__main__":
    build_cache()
