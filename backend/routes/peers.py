from fastapi import APIRouter, HTTPException, Query
from backend.services.peers_service import fetch_stock_peers
from backend.services.peer_comparison_service import fetch_peer_comparison
from backend.utils.json_safe import make_json_safe

router = APIRouter(prefix="/api/peers", tags=["Peers"])


@router.get("/{symbol}")
def get_peers(symbol: str):
    """
    Get peer companies for a stock.
    """
    try:
        peers = fetch_stock_peers(symbol)

        return {
            "symbol": symbol.upper(),
            "peers": peers,
            "count": len(peers),
            "source": "Financial Modeling Prep",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare/{symbol}")
def get_peer_comparison(
    symbol: str,
    limit: int = Query(12, ge=3, le=40),
    debug: bool = Query(False)
):
    """
    Get peer comparison metrics for a stock.
    """
    try:
        data = fetch_peer_comparison(symbol, limit=limit, debug=debug)
        return make_json_safe(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
