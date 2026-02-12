"""
Backtest Agent API Routes
Lightweight, agent-style backtest execution.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.backtest_agent_service import run_backtest_agent

router = APIRouter(prefix="/api/backtest-agent", tags=["Backtest Agent"])


class BacktestAgentRequest(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")
    strategy: str = Field(..., description="Strategy name (e.g., ema_crossover)")
    range: Optional[str] = Field(default="1y", description="Backtest range (e.g., 1y, 6mo)")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Strategy parameters")
    run_backtest: bool = Field(default=True, description="Execute backtest or return stub")


@router.post("/run")
def run_agent_backtest(request: BacktestAgentRequest):
    if not request.symbol.strip():
        raise HTTPException(status_code=400, detail="Symbol cannot be empty.")
    if not request.strategy.strip():
        raise HTTPException(status_code=400, detail="Strategy cannot be empty.")

    try:
        return run_backtest_agent(
            symbol=request.symbol,
            strategy=request.strategy,
            range_period=request.range or "1y",
            params=request.params,
            run_backtest=request.run_backtest,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
