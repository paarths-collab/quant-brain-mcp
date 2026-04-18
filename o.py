import yfinance as yf

# Example for an Indian stock (HDFC Bank)
# Use '.NS' for NSE or '.BO' for BSE
ticker = yf.Ticker("HDFCBANK.NS")

# Get sector and industry
sector = ticker.info.get('sector')
industry = ticker.info.get('industry')

print(f"Sector: {sector}")
print(f"Industry: {industry}")
from core.data_loader import fetch_data
from core.sector_data import INDIAN_SECTORS

def get_sector_leaderboard():
    """Ranks Indian sectors by 30-day performance and finds leaders."""
    rankings = []
    for name, info in INDIAN_SECTORS.items():
        idx_df, _ = fetch_data(info['index'], period="1mo")
        perf = ((idx_df['Close'].iloc[-1] / idx_df['Close'].iloc[0]) - 1) * 100
        rankings.append({"sector": name, "performance": round(perf, 2), "top_tickers": info['tickers']})
    
    # Sort by performance
    rankings.sort(key=lambda x: x['performance'], reverse=True)
    return rankings

get_sector_leaderboard()