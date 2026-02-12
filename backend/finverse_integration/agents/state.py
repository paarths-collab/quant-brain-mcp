from typing import TypedDict, List, Dict, Any, Annotated
import operator

class WealthState(TypedDict, total=False):
    """Shared state across the Investment AI (LangGraph) workflow"""
    # Input - these fields use "last write wins" to allow updates from multiple nodes
    raw_input: Annotated[str, lambda x, y: y]
    market: Annotated[str, lambda x, y: y]

    # User Profile & Goals
    user_profile: Dict[str, Any]
    goals: Dict[str, Any]
    risk_score: int
    time_horizon: int
    investable_amount: float

    # Market & News Context
    market_data: Dict[str, Any]
    news_context: Dict[str, Any]

    # Sector & Stock Selection
    discovered_sectors: List[str]
    selected_sector: str  # Back-compat: first item of discovered_sectors
    candidate_stocks: List[Dict[str, Any]]
    selected_stocks: List[Dict[str, Any]]
    selected_stock: Dict[str, Any]  # Back-compat: first item of selected_stocks
    stock_research: Dict[str, Any]

    # Allocation & Output
    allocation_strategy: Dict[str, Any]
    investment_report: str

    # Metadata / Diagnostics
    execution_log: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    is_blocked: bool
    critic_score: float
    critic_feedback: str
    failure_reasons: List[str]
    optimization_attempts: int
