# File: routes/wealth_routes.py
"""
FastAPI routes for Autonomous Wealth Management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
import json
import os
from datetime import datetime

from ..agents.wealth_orchestrator import AutonomousWealthManager
# from ..agents.sector_agent import SectorAgent
from ..agents.stock_picker_agent import StockPickerAgent
from ..agents.sentiment_agent import SentimentAgent
from ..agents.macro_agent import MacroAgent
from ..utils.news_fetcher import NewsFetcher
from ..utils.portfolio_engine import PortfolioEngine

router = APIRouter(prefix="/api/wealth", tags=["Wealth Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class WealthAnalysisRequest(BaseModel):
    """Request model for wealth analysis"""
    user_input: str = Field(..., description="Natural language description of financial situation")
    market: str = Field(default="US", description="Market (US, IN, EU, etc.)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_input": """I'm 32 years old earning $8000/month. I have $50,000 in savings. 
                I have a home loan with $2000 EMI for 15 years and car loan with $500 EMI for 3 years. 
                My monthly expenses are around $3000. I want to invest for retirement (long-term). 
                I'm comfortable with moderate risk.""",
                "market": "US"
            }
        }

class WealthAnalysisResponse(BaseModel):
    """Response model for wealth analysis"""
    success: bool
    report: str
    profile: Optional[Dict[str, Any]] = None
    allocation: Optional[Dict[str, float]] = None
    selected_stock: Optional[Dict[str, Any]] = None
    selected_mf: Optional[Dict[str, Any]] = None
    selected_bonds: Optional[Dict[str, Any]] = None
    execution_log: List[str] = []
    errors: List[str] = []
    timestamp: str

# ============================================================================
# GLOBAL WEALTH MANAGER INSTANCE
# ============================================================================

_wealth_manager: Optional[AutonomousWealthManager] = None

def get_wealth_manager() -> AutonomousWealthManager:
    """Singleton pattern for wealth manager"""
    global _wealth_manager
    
    if _wealth_manager is None:
        # Initialize all required agents
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")  # Optional
        
        if not gemini_api_key:
            # Fallback for demo if key missing in env but maybe loaded elsewhere
            # But better to raise error
            print("⚠️ GEMINI_API_KEY not found in env")
        
        _wealth_manager = AutonomousWealthManager(
            gemini_api_key=gemini_api_key,
            sector_agent=None, # Legacy agent not needed in new architecture
            stock_picker=StockPickerAgent(),
            portfolio_engine=PortfolioEngine(),
            news_fetcher=NewsFetcher(),
            sentiment_agent=SentimentAgent(),
            macro_agent=MacroAgent(),
            tavily_api_key=tavily_api_key
        )
    
    return _wealth_manager

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=WealthAnalysisResponse)
async def analyze_wealth(request: WealthAnalysisRequest):
    """
    Main endpoint: Analyze user's financial situation and generate investment recommendations
    """
    try:
        # Get wealth manager instance
        manager = get_wealth_manager()
        
        # Run analysis
        result = await manager.run(
            raw_user_input=request.user_input,
            market=request.market
        )
        
        # Return response
        return WealthAnalysisResponse(
            success=result["success"],
            report=result["report"],
            profile=result.get("profile"),
            allocation=result.get("allocation"),
            selected_stock=result.get("selected_stock"),
            selected_mf=result.get("selected_mf"),
            selected_bonds=result.get("selected_bonds"),
            execution_log=result.get("execution_log", []),
            errors=result.get("errors", []),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Wealth analysis failed: {str(e)}"
        )

from ..agents.execution_agent import ExecutionAgent

# Global Execution Agent
_execution_agent: Optional[ExecutionAgent] = None

def get_execution_agent() -> ExecutionAgent:
    global _execution_agent
    if _execution_agent is None:
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        _execution_agent = ExecutionAgent(api_key, secret_key, paper=True)
    return _execution_agent

# ... existing imports ...

class TradeRequest(BaseModel):
    ticker: str
    amount: float = 1.0 # Fraction or qty
    side: str = "buy"
    market: str = "US" # US or IN

@router.post("/trade/execute")
async def execute_trade(request: TradeRequest):
    """
    Execute trade: Real for US (Alpaca), Simulated for IN
    """
    try:
        if request.market == "US":
            agent = get_execution_agent()
            # For simplicity, assuming amount is quantity for now. 
            # In real app, calculate qty = amount / price
            result = agent.submit_market_order(request.ticker, request.amount, request.side)
            if "error" in result:
                 raise HTTPException(status_code=400, detail=result["error"])
            return {"success": True, "data": result, "message": f"Order executed via Alpaca for {request.ticker}"}
        
        elif request.market == "IN":
            # Mock Execution for India
            await asyncio.sleep(1) # Simulate network delay
            return {
                "success": True, 
                "data": {"id": "mock_in_123", "symbol": request.ticker, "status": "filled"},
                "message": f"Order executed on NSE for {request.ticker} (Simulated)"
            }
            
        else:
            return {"success": False, "message": "Market not supported for auto-execution"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/stream")
async def analyze_wealth_stream(user_input: str, market: str = "US"):
    """
    Streaming endpoint: Get real-time progress updates during analysis
    """
    async def event_generator():
        """Generate SSE events for each stage using real-time graph streaming"""
        
        try:
            manager = get_wealth_manager()
            
            # Initial State
            initial_state = {
                "raw_input": user_input,
                "market": market,
                "execution_log": [],
                "errors": []
            }
            
            # Stage 1: Input Structuring (Manual start)
            yield f"data: {json.dumps({'stage': 'input', 'message': 'Analyzing your financial profile...', 'progress': 10})}\n\n"
            
            # Stream the graph execution
            # 'astream' yields dictionary of {node_name: state_update}
            current_state = initial_state.copy()
            
            async for output in manager.workflow.astream(initial_state):
                for node_name, state_update in output.items():
                    # Accumulate state to ensure we have the complete picture at the end
                    # Note: LangGraph state updates are typically full state if typeddict, but merging ensures safety
                    current_state.update(state_update)
                    
                    # Logic to map Nodes -> UI Stages
                    if node_name == "structure_input":
                        msg = "Profile structured successfully."
                        if state_update.get("user_profile"):
                            risk = state_update['user_profile']['preferences']['risk_tolerance']
                            msg = f"Profile: {risk.capitalize()} investor identified."
                        yield f"data: {json.dumps({'stage': 'profile', 'message': msg, 'progress': 25})}\n\n"
                        
                    elif node_name == "discover_sector":
                        sector = state_update.get("selected_sector", "Unknown")
                        yield f"data: {json.dumps({'stage': 'sector', 'message': f'Identified high-growth sector: {sector}', 'progress': 40})}\n\n"
                        
                    elif node_name == "select_stock":
                        ticker = state_update.get("selected_stock", {}).get("Ticker", "N/A")
                        yield f"data: {json.dumps({'stage': 'stock', 'message': f'Selected top pick: {ticker}', 'progress': 60})}\n\n"
                        
                    elif node_name == "select_mf":
                         mf = state_update.get("selected_mf", {}).get("subcategory", "Fund")
                         yield f"data: {json.dumps({'stage': 'mf', 'message': f'Recommended Mutual Fund: {mf}', 'progress': 75})}\n\n"
                         
                    elif node_name == "select_bonds":
                         bond = state_update.get("selected_bonds", {}).get("bond_type", "Bond")
                         yield f"data: {json.dumps({'stage': 'bonds', 'message': f'Fixed Income Strategy: {bond}', 'progress': 85})}\n\n"
                    
                    elif node_name == "draft_report":
                        yield f"data: {json.dumps({'stage': 'report', 'message': 'Finalizing investment report...', 'progress': 95})}\n\n"
            
            # Final result - Send accumulated state
            yield f"data: {json.dumps({'stage': 'complete', 'message': 'Analysis complete!', 'progress': 100, 'data': current_state})}\n\n"
            
        except Exception as e:
            error_data = {'stage': 'error', 'message': str(e), 'progress': 0}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
