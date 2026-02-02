import streamlit as st
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os

class ExecutionAgent:
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        """Initializes the trading client for Alpaca."""
        self.api = None
        if not api_key or not api_secret:
            print("[WARNING] ExecutionAgent: Alpaca API Key or Secret is missing.")
            return
        try:
            self.api = TradingClient(api_key, api_secret, paper=paper)
            account_status = self.api.get_account().status
            if account_status != 'ACTIVE':
                 print(f"[WARNING] ExecutionAgent: Alpaca account is not active. Status: {account_status}")
            else:
                 print(f"[SUCCESS] ExecutionAgent: Alpaca client initialized successfully. Paper Trading: {paper}. Status: {account_status}")
        except Exception as e:
            print(f"[ERROR] ExecutionAgent: Could not initialize Alpaca TradingClient: {e}")

    def get_account_info(self) -> dict:
        """Retrieves key information about the trading account."""
        if not self.api: return {"error": "Alpaca API not initialized."}
        try:
            account = self.api.get_account()
            return {
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "cash": float(account.cash),
                "long_market_value": float(account.long_market_value),
                "status": str(account.status)
            }
        except Exception as e:
            return {"error": f"Failed to get account info: {e}"}

    def submit_market_order(self, ticker: str, qty: float, side: str) -> dict:
        """Submits a market order to Alpaca."""
        if not self.api: return {"error": "Alpaca API not initialized."}
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            market_order_data = MarketOrderRequest(
                symbol=ticker.upper(), qty=qty,
                side=order_side, time_in_force=TimeInForce.DAY
            )
            order = self.api.submit_order(order_data=market_order_data)
            print(f"✅ Submitted market order for {qty} shares of {ticker} ({side}). Order ID: {order.id}")
            return {
                "id": str(order.id), "symbol": order.symbol, "qty": float(order.qty),
                "side": str(order.side), "status": str(order.status)
            }
        except Exception as e:
            print(f"❌ ERROR: Failed to submit market order for {ticker}: {e}")
            return {"error": str(e)}

    def get_open_positions(self) -> list:
        """Retrieves a list of all open positions in the account."""
        if not self.api: return [{"error": "Alpaca API not initialized."}]
        try:
            positions = self.api.get_all_positions()
            return [
                {
                    "Symbol": pos.symbol, "Qty": float(pos.qty),
                    "Avg Entry Price": float(pos.avg_entry_price),
                    "Current Price": float(pos.current_price),
                    "Unrealized P/L": float(pos.unrealized_pl),
                    "Market Value": float(pos.market_value),
                } for pos in positions
            ]
        except Exception as e:
            return [{"error": f"Failed to get open positions: {e}"}]

# --- Streamlit Visualization (Frontend Part) ---
if __name__ == "__main__":
    st.set_page_config(page_title="Paper Trading Terminal", layout="wide")
    st.title("💸 Alpaca Paper Trading Terminal")

    # For standalone testing, get keys from Streamlit secrets or environment variables
    API_KEY = st.secrets.get("ALPACA_KEY_ID", os.getenv("ALPACA_KEY_ID"))
    SECRET_KEY = st.secrets.get("ALPACA_SECRET_KEY", os.getenv("ALPACA_SECRET_KEY"))

    if not API_KEY or not SECRET_KEY:
        st.error("Alpaca API keys not found! Please set them in your Streamlit secrets or environment variables.")
    else:
        # Initialize agent (always in paper mode for the showcase)
        agent = ExecutionAgent(api_key=API_KEY, api_secret=SECRET_KEY, paper=True)

        st.header("📋 Account Status")
        with st.spinner("Fetching account information..."):
            info = agent.get_account_info()
            if "error" in info:
                st.error(f"Could not fetch account info: {info['error']}")
            else:
                cols = st.columns(4)
                cols[0].metric("Equity", f"${info.get('equity'):,.2f}")
                cols[1].metric("Buying Power", f"${info.get('buying_power'):,.2f}")
                cols[2].metric("Cash", f"${info.get('cash'):,.2f}")
                status = info.get('status', 'UNKNOWN')
                status_color = "green" if status == "ACTIVE" else "red"
                cols[3].markdown(f"**Status:** <span style='color:{status_color};'>**{status}**</span>", unsafe_allow_html=True)

        st.header("📈 Open Positions")
        with st.spinner("Fetching open positions..."):
            positions = agent.get_open_positions()
            if positions and "error" in positions[0]:
                st.error(f"Could not fetch positions: {positions[0]['error']}")
            elif not positions:
                st.info("You have no open positions.")
            else:
                st.dataframe(pd.DataFrame(positions).set_index("Symbol"))

        st.header("🛒 Place a Trade")
        with st.form("trade_form"):
            col1, col2, col3, col4 = st.columns(4)
            ticker = col1.text_input("Ticker Symbol", "SPY")
            qty = col2.number_input("Quantity", min_value=0.01, value=1.0, step=0.01)
            side = col3.selectbox("Side", ["Buy", "Sell"])
            submitted = col4.form_submit_button("Submit Market Order")

            if submitted:
                with st.spinner(f"Submitting {side} order for {qty} of {ticker}..."):
                    result = agent.submit_market_order(ticker, qty, side)
                    if "error" in result:
                        st.error(f"Order failed: {result['error']}")
                    else:
                        st.success("Order submitted successfully!")
                        st.json(result)