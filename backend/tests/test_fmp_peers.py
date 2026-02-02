from backend.services.peers_service import fetch_stock_peers

def test_peers():
    print("Testing FMP Peers for AAPL...")
    try:
        peers = fetch_stock_peers("AAPL")
        print(f"Success! Found {len(peers)} peers.")
        for p in peers[:5]:
             print(f"- {p.get('symbol')}: {p.get('companyName')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_peers()
