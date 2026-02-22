import yfinance as yf

class MarketData:
    
    proxies = {
        "US": {"index": "^GSPC", "etf": "SPY"},
        "IN": {"index": "^NSEI", "etf": "NIFTYBEES.NS"}
    }
    
    def get_market_pe(self, region="US"):
        """
        Fetches P/E for the market index of the given region.
        Uses ETF proxies if Index data is missing.
        """
        mapping = self.proxies.get(region, self.proxies["US"])
        
        index_ticker = mapping["index"]
        etf_ticker = mapping["etf"]
        
        # Try Index first
        pe_data = self._fetch_pe(index_ticker)
        
        # If missing, try ETF
        if not pe_data["trailing_pe"] and not pe_data["forward_pe"]:
            # print(f"Index {index_ticker} PE missing. Using proxy {etf_ticker}...")
            pe_data = self._fetch_pe(etf_ticker)
            
        return pe_data

    def _fetch_pe(self, ticker_symbol):
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return {
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE")
            }
        except Exception as e:
            print(f"Error fetching market data for {ticker_symbol}: {e}")
            return {"trailing_pe": None, "forward_pe": None}
