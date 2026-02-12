# import streamlit as st
import pandas as pd
import os

# Optional Alpaca trading imports
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ModuleNotFoundError:
    ALPACA_AVAILABLE = False
    TradingClient = None
    MarketOrderRequest = None
    OrderSide = None
    TimeInForce = None

class ExecutionAgent:
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        """Initializes the trading client for Alpaca."""
        self.api = None
        
        if not ALPACA_AVAILABLE:
            return
            
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
