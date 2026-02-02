from backend.services.market_data_service import fetch_candles, calculate_indicators
import json

def test_market_data():
    symbol = "AAPL"
    print(f"Testing fetch_candles for {symbol}...")
    candles = fetch_candles(symbol, interval="1d", period="1mo")
    if candles:
        print(f"Success! Got {len(candles)} candles.")
        print("Sample:", json.dumps(candles[0], indent=2))
    else:
        print("Failed to fetch candles.")

    print(f"\nTesting calculate_indicators for {symbol}...")
    indicators = calculate_indicators(symbol, period="1mo", interval="1d")
    if indicators:
        print("Success! Got indicators.")
        print("Keys:", list(indicators.keys()))
        if indicators.get('rsi'):
            print("RSI Sample:", indicators['rsi'][-5:])
    else:
        print("Failed to calculate indicators.")

if __name__ == "__main__":
    test_market_data()
