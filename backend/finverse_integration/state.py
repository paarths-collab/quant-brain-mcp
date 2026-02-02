from typing import TypedDict, Annotated, List, Dict, Any
import operator

class WealthState(TypedDict):
    """Shared state across all agents"""
    # User Input
    raw_input: str
    
    # Structured Profile
    user_profile: Dict[str, Any]
    allocation_strategy: Dict[str, float]  # {stocks: 0.6, mf: 0.3, bonds: 0.1}
    
    # Market Context
    market: str
    current_season: str
    
    # Sector Analysis
    sector_rankings: List[Dict[str, Any]]
    selected_sector: str
    sector_news: List[Dict[str, Any]]
    
    # Stock Selection
    candidate_stocks: List[Dict[str, Any]]
    stock_backtests: Dict[str, Any]
    selected_stock: Dict[str, Any]
    stock_research: Dict[str, Any]
    
    # MF Selection
    mf_candidates: List[Dict[str, Any]]
    selected_mf: Dict[str, Any]
    
    # Bond Selection
    macro_indicators: Dict[str, Any]
    selected_bonds: Dict[str, Any]
    
    # Final Output
    investment_report: str
    
    # Metadata
    messages: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
