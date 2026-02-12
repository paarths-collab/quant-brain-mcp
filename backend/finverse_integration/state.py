from typing import TypedDict, Annotated, List, Dict, Any
import operator

class WealthState(TypedDict, total=False):
    """Shared state across the Investment AI workflow"""
    # User Input
    raw_input: str
    market: str

    # Structured Profile & Goals
    user_profile: Dict[str, Any]
    goals: Dict[str, Any]
    risk_score: int
    time_horizon: int
    investable_amount: float

    # Market & News Context
    market_data: Dict[str, Any]
    news_context: Dict[str, Any]

    # Sector Analysis
    discovered_sectors: List[str]
    selected_sector: str  # Back-compat alias

    # Stock Selection
    candidate_stocks: List[Dict[str, Any]]
    selected_stocks: List[Dict[str, Any]]
    selected_stock: Dict[str, Any]  # Back-compat alias
    stock_research: Dict[str, Any]

    # Allocation & Output
    allocation_strategy: Dict[str, Any]
    investment_report: str

    # Metadata
    execution_log: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    critic_score: float
    critic_feedback: str
    failure_reasons: List[str]
    optimization_attempts: int
