from typing import Dict, Any, List
from .peers_service import fetch_stock_peers

def get_network_graph(symbol: str) -> Dict[str, Any]:
    """
    Constructs a graph representation of the stock and its peers.
    """
    symbol = symbol.upper()
    
    # 1. Fetch Competitors (Nodes)
    competitors = fetch_stock_peers(symbol)
    
    # 2. Construct Nodes
    # Root Node
    nodes = [{
        "id": symbol,
        "group": "root",
        "radius": 20, # Larger for root
        "marketCap": "N/A" # Can fetch if needed
    }]
    
    # Peer Nodes
    # Limit to top 10 to avoid overcrowding
    for peer in competitors[:10]:
        nodes.append({
            "id": peer['symbol'],
            "group": "competitor",
            "radius": 10,
            "marketCap": peer.get('marketCap')
        })
        
    # 3. Construct Links (Root <-> Peer)
    links = []
    for peer in competitors[:10]:
        links.append({
            "source": symbol,
            "target": peer['symbol'],
            "value": 1
        })
        
    # Future: Add Supplier/Customer nodes here if data source available
    
    return {
        "nodes": nodes,
        "links": links
    }
