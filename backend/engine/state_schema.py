from typing import TypedDict, Dict, Any, List, Optional

class AgentState(TypedDict):
    query: str
    ticker: Optional[str]
    market: str
    session_id: str
    emotion: Dict[str, Any]
    financial: Dict[str, Any]
    web: Dict[str, Any]
    sector: Dict[str, Any]
    divergence: List[str]
    confidence: float
    report: str
    discovery: List[Dict[str, Any]] # Result from screener if applicable
