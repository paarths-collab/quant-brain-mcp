from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class SuperAgentResponse(BaseModel):
    emotion: Dict[str, Any]
    financial: Dict[str, Any]
    web: Dict[str, Any]
    sector: Dict[str, Any]
    macro: Dict[str, Any]
    insider: Dict[str, Any]
    risk: Dict[str, Any]
    divergence: List[str]
    confidence: float
    report: str
    discovery: Optional[List[Dict[str, Any]]] = None
    strategy: Optional[Dict[str, Any]] = None
    portfolio_optimization: Optional[Dict[str, Any]] = None
    rl_strategy: Optional[Dict[str, Any]] = None
    # trade_execution: Optional[Dict[str, Any]] = None # Removed
    risk_engine: Optional[Dict[str, Any]] = None
