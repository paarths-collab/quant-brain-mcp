import requests
import streamlit as st
import pandas as pd
from typing import Dict, Any

class SystemHealthAgent:
    def __init__(self, finnhub_key: str, rapidapi_config: dict, fred_key: str):
        self.finnhub_key = finnhub_key
        self.rapidapi_key = rapidapi_config.get("key")
        self.hosts = rapidapi_config.get("hosts", {})
        self.fred_key = fred_key

    def _check_endpoint(self, name: str, url: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """A generic function to test an API endpoint."""
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status() # Will raise an error for 4xx/5xx status codes
            return {"service": name, "status": "✅ Operational", "details": f"OK ({r.status_code})"}
        except requests.exceptions.RequestException as e:
            # Extract status code if available
            status_code = e.response.status_code if e.response is not None else "N/A"
            return {"service": name, "status": "❌ Failed", "details": f"Error ({status_code}): {str(e)}"}

    def run_all_checks(self) -> pd.DataFrame:
        """
        Runs a health check on all critical external API dependencies.
        """
        print("SystemHealthAgent: Running all API health checks...")
        checks = []

        # 1. Finnhub Check (Quote for a reliable symbol)
        finnhub_url = "https://finnhub.io/api/v1/quote"
        checks.append(self._check_endpoint("Finnhub", finnhub_url, params={"symbol": "AAPL", "token": self.finnhub_key}))

        # 2. FRED Check (Fetch a simple series)
        fred_url = "https://api.stlouisfed.org/fred/series"
        checks.append(self._check_endpoint("FRED", fred_url, params={"series_id": "GDP", "api_key": self.fred_key, "file_type": "json"}))

        # 3. RapidAPI - FMP Check
        fmp_host = self.hosts.get("fmp")
        if fmp_host:
            fmp_url = f"https://{fmp_host}/v3/profile/AAPL"
            checks.append(self._check_endpoint("RapidAPI (FMP)", fmp_url, headers={"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": fmp_host}))
        
        # 4. RapidAPI - TradingView Ping Check
        tv_host = self.hosts.get("tradingview")
        if tv_host:
            tv_url = f"https://{tv_host}/ping"
            checks.append(self._check_endpoint("RapidAPI (TradingView)", tv_url, headers={"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": tv_host}))

        print("SystemHealthAgent: Health checks complete.")
        return pd.DataFrame(checks)

# --- Streamlit Visualization ---
if __name__ == "__main__":
    st.set_page_config(page_title="System Health Monitor", layout="centered")
    st.title("🛰️ System Health & API Status Monitor")

    # For standalone testing, load config manually
    import yaml
    import os
    try:
        with open("quant-company-insights-agent/config.yaml", "r") as f:
            config = yaml.safe_load(f)
        API_KEYS = config.get("api_keys", {})
        RAPIDAPI_CONFIG = config.get("rapidapi", {})
    except FileNotFoundError:
        st.error("Config file not found. Make sure you are running from the project root.")
        API_KEYS, RAPIDAPI_CONFIG = {}, {}

    if not all([API_KEYS, RAPIDAPI_CONFIG]):
        st.warning("Could not load full configuration.")
    
    agent = SystemHealthAgent(
        finnhub_key=API_KEYS.get("finnhub"),
        rapidapi_config=RAPIDAPI_CONFIG,
        fred_key=API_KEYS.get("fred")
    )

    if st.button("🚦 Run API Health Checks", use_container_width=True):
        with st.spinner("Pinging all external API endpoints..."):
            health_df = agent.run_all_checks()
            
            st.subheader("API Status")
            
            # Use color formatting for the status column
            def style_status(val):
                color = 'green' if 'Operational' in val else 'red'
                return f'color: {color}; font-weight: bold;'
            
            st.dataframe(
                health_df.style.applymap(style_status, subset=['status']),
                use_container_width=True)