from fastapi import APIRouter, HTTPException
from .core.graph_service import get_network_graph

router = APIRouter(prefix="", tags=["Network Graph"])

@router.get("/{symbol}")
def get_graph(symbol: str):
    """
    Returns nodes and links for D3 Force-Directed Graph.
    """
    try:
        data = get_network_graph(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
