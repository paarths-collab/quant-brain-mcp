from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

class WealthState(TypedDict):
    """Shared state across all agents in the workflow"""
    # Input
    raw_input: str
    market: str
    # User Profile
    user_profile: Dict[str, Any]
    allocation_strategy: Dict[str, float]
    investable_amount: float
    # Market Context
    current_season: str
    # Sector Analysis
    sector_rankings: List[Dict[str, Any]]
    selected_sector: str
    sector_news: List[Dict[str, str]]
    # Stock Selection
    candidate_stocks: List[Dict[str, Any]]
    stock_backtests: Dict[str, Any]
    selected_stock: Dict[str, Any]
    stock_research: Dict[str, Any]
    # MF & Bond & Gold Selection
    selected_mf: Dict[str, Any]
    selected_bonds: Dict[str, Any]
    selected_gold: Dict[str, Any]
    macro_indicators: Dict[str, Any]
    # Output
    investment_report: str
    # Reducers for logging to allow parallel writes
    execution_log: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    is_blocked: bool
    # Critic Loop State
    critic_score: float
    critic_feedback: str
    optimization_attempts: int
