from datetime import datetime
from backend.services.long_term_strategy import run_long_term_strategy
import json

def test_long_term_endpoint_logic():
    print("Testing Long-Term Strategy Logic...")
    
    ticker = "AAPL"
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    market = "US"
    capital = 10000
    risk_profile = "moderate"
    monthly_investment = 500

    try:
        results = run_long_term_strategy(
            ticker=ticker,
            start=start_date,
            end=end_date,
            market=market,
            capital=capital,
            risk_profile=risk_profile,
            monthly_investment=monthly_investment
        )
        
        print(f"\n✅ Analysis Successful for {ticker}")
        print(f"Risk Profile: {results['metadata']['risk_profile']}")
        print("Active Strategies:", list(results['results'].keys()))
        
        if 'dca' in results['results']:
            dca = results['results']['dca']
            print(f"DCA Return: {dca.get('absolute_return_pct', 0)}%")
            
        return True
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        return False

if __name__ == "__main__":
    test_long_term_endpoint_logic()
