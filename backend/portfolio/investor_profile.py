"""
Investor Profile API — Save & Load user profiles from PostgreSQL.
Routes: POST /save, GET /load
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investor-profile", tags=["Investor Profile"])


class ProfilePayload(BaseModel):
    user_id: str = Field(default="default")
    name: Optional[str] = None
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    monthly_savings: Optional[float] = None
    risk_tolerance: Optional[str] = Field(default="moderate")
    horizon_years: Optional[int] = Field(default=5)
    primary_goal: Optional[str] = None
    existing_investments: Optional[str] = None
    market: Optional[str] = Field(default="US")


@router.post("/save")
def save_profile(payload: ProfilePayload, db=Depends(get_db)):
    """Save or update an investor profile."""
    try:
        db.execute(
            text("""
                INSERT INTO user_profiles
                    (user_id, name, age, monthly_income, monthly_savings,
                     risk_tolerance, horizon_years, primary_goal,
                     existing_investments, market, updated_at)
                VALUES
                    (:user_id, :name, :age, :monthly_income, :monthly_savings,
                     :risk_tolerance, :horizon_years, :primary_goal,
                     :existing_investments, :market, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    age = EXCLUDED.age,
                    monthly_income = EXCLUDED.monthly_income,
                    monthly_savings = EXCLUDED.monthly_savings,
                    risk_tolerance = EXCLUDED.risk_tolerance,
                    horizon_years = EXCLUDED.horizon_years,
                    primary_goal = EXCLUDED.primary_goal,
                    existing_investments = EXCLUDED.existing_investments,
                    market = EXCLUDED.market,
                    updated_at = CURRENT_TIMESTAMP
            """),
            {
                "user_id": payload.user_id,
                "name": payload.name,
                "age": payload.age,
                "monthly_income": payload.monthly_income,
                "monthly_savings": payload.monthly_savings,
                "risk_tolerance": payload.risk_tolerance,
                "horizon_years": payload.horizon_years,
                "primary_goal": payload.primary_goal,
                "existing_investments": payload.existing_investments,
                "market": payload.market,
            },
        )
        db.commit()
        return {"status": "ok", "message": "Profile saved"}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save profile")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load")
def load_profile(user_id: str = "default", db=Depends(get_db)):
    """Load an investor profile."""
    try:
        row = db.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).mappings().first()

        if not row:
            return {"status": "not_found", "profile": None}

        profile = dict(row)
        # Convert datetime fields to ISO strings
        for key in ("created_at", "updated_at"):
            if profile.get(key):
                profile[key] = profile[key].isoformat()
        return {"status": "ok", "profile": profile}
    except Exception as e:
        logger.exception("Failed to load profile")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Portfolio / Trading
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Portfolio / Trading
# ---------------------------------------------------------------------------
import json
from datetime import datetime
from backend.services.market_data import market_service

class TradeRequest(BaseModel):
    user_id: str = "default"
    symbol: str
    amount: float = 0.0  # Amount to invest (for Buy) or sell value
    quantity: float = 0.0 # Number of shares (alternative to amount)
    price: Optional[float] = None # Execution price (optional, else fetches live)
    side: str = Field(..., pattern="^(buy|sell)$") # buy or sell

@router.post("/trade")
def execute_trade(trade: TradeRequest, db=Depends(get_db)):
    """
    Execute a mock trade (Buy/Sell) and update portfolio in DB.
    """
    try:
        # 1. Load Profile
        row = db.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :uid"),
            {"uid": trade.user_id},
        ).mappings().first()

        if not row:
            # Create default if not exists? Or error. Let's error.
            raise HTTPException(status_code=404, detail="User profile not found. Create one first.")

        profile = dict(row)
        investments_json = profile.get("existing_investments")
        portfolio = json.loads(investments_json) if investments_json else {}

        # 2. Get Price
        exec_price = trade.price
        if not exec_price:
            live_price = market_service.get_price(trade.symbol)
            if not live_price:
                raise HTTPException(status_code=400, detail=f"Could not fetch price for {trade.symbol}")
            exec_price = live_price

        # 3. Calculate Quantity/Amount
        if trade.quantity > 0:
            qty = trade.quantity
            amount = qty * exec_price
        elif trade.amount > 0:
            amount = trade.amount
            qty = amount / exec_price
        else:
            raise HTTPException(status_code=400, detail="Must specify amount or quantity")

        symbol = trade.symbol.upper()
        current_holding = portfolio.get(symbol, {"quantity": 0, "avg_price": 0, "total_invested": 0})
        
        # 4. Update Logic
        if trade.side.lower() == "buy":
            new_qty = current_holding["quantity"] + qty
            new_total = current_holding["total_invested"] + amount
            new_avg = new_total / new_qty if new_qty > 0 else 0
            
            portfolio[symbol] = {
                "quantity": new_qty,
                "avg_price": new_avg,
                "total_invested": new_total
            }
        else: # Sell
            if current_holding["quantity"] < qty:
                 raise HTTPException(status_code=400, detail=f"Not enough shares to sell. Own: {current_holding['quantity']}")
            
            # FIFO / Moving Avg logic? Simplified: reduce quantity, keep avg price same (realized P/L is diff topic)
            new_qty = current_holding["quantity"] - qty
            pct_sold = qty / current_holding["quantity"]
            cost_basis_sold = current_holding["total_invested"] * pct_sold
            new_total = current_holding["total_invested"] - cost_basis_sold
            
            if new_qty < 1e-6:
                del portfolio[symbol]
            else:
                portfolio[symbol] = {
                    "quantity": new_qty,
                    "avg_price": current_holding["avg_price"], # Avg price doesn't change on sell
                    "total_invested": new_total
                }

        # 5. Save back to DB
        db.execute(
            text("""
                UPDATE user_profiles 
                SET existing_investments = :port, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :uid
            """),
            {"port": json.dumps(portfolio), "uid": trade.user_id}
        )
        db.commit()

        return {
            "status": "ok",
            "message": f"{trade.side.upper()} {qty:.4f} {symbol} @ ${exec_price:.2f}",
            "portfolio": portfolio
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Trade failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
def get_portfolio(user_id: str = "default", db=Depends(get_db)):
    """
    Get portfolio with live valuation and P/L.
    """
    try:
        row = db.execute(
            text("SELECT existing_investments FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).mappings().first()

        if not row:
            return {"pairtfolio": [], "total_value": 0, "total_pl": 0}

        investments_json = row.get("existing_investments")
        portfolio_map = json.loads(investments_json) if investments_json else {}

        holdings = []
        total_value = 0.0
        total_invested = 0.0

        for symbol, data in portfolio_map.items():
            qty = data.get("quantity", 0)
            avg = data.get("avg_price", 0)
            invested = data.get("total_invested", 0)
            
            # Fetch live price
            current_price = market_service.get_price(symbol) or avg # performant fallback? Maybe 0
            
            current_val = qty * current_price
            pl = current_val - invested
            pl_pct = (pl / invested * 100) if invested > 0 else 0

            holdings.append({
                "symbol": symbol,
                "quantity": qty,
                "avg_price": avg,
                "current_price": current_price,
                "current_value": current_val,
                "pl": pl,
                "pl_pct": pl_pct
            })
            
            total_value += current_val
            total_invested += invested

        total_pl = total_value - total_invested
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

        return {
            "holdings": sorted(holdings, key=lambda x: x["current_value"], reverse=True),
            "total_value": total_value,
            "total_invested": total_invested,
            "total_pl": total_pl,
            "total_pl_pct": total_pl_pct
        }
    except Exception as e:
        logger.exception("Portfolio fetch failed")
        raise HTTPException(status_code=500, detail=str(e))
