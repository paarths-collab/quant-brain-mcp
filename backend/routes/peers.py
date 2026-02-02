from fastapi import APIRouter, HTTPException
from backend.services.peers_service import fetch_stock_peers

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
