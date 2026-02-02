from backend.services.macro_service import fetch_macro_prices, get_geo_data
from backend.services.graph_service import get_network_graph
import json

def test_phase2():
    print("--- Testing Macro ---")
    prices = fetch_macro_prices()
    if prices:
        print(f"Fetched {len(prices)} macro indicators.")
        print("Sample:", prices[0])
    else:
        print("Failed to fetch macro prices.")
        
    geo = get_geo_data("oil")
    if geo:
        print(f"Fetched {len(geo)} oil locations.")
        
    print("\n--- Testing Network Graph ---")
    symbol = "AAPL"
    graph = get_network_graph(symbol)
    if graph and graph.get("nodes"):
        print(f"Success! Graph has {len(graph['nodes'])} nodes and {len(graph['links'])} links.")
    else:
        print("Failed to build graph.")

if __name__ == "__main__":
    test_phase2()
