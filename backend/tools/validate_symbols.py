"""
Utility to validate stock symbols and identify potentially delisted ones.
Run this periodically to clean up the stock universe data.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Set
import yfinance as yf
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_stock_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load stock data from JSON file."""
    if not file_path.exists():
        return []
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return []

def validate_symbols(symbols: List[str], batch_size: int = 50) -> Dict[str, bool]:
    """
    Validate symbols by attempting to fetch basic info.
    Returns dict of symbol -> is_valid
    """
    results = {}
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        logger.info(f"Validating batch {i//batch_size + 1}: {len(batch)} symbols")
        
        for symbol in batch:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1mo", auto_adjust=True)
                
                # Consider valid if we can get basic info and recent price data
                is_valid = (
                    info and 
                    hist is not None and 
                    not hist.empty and 
                    len(hist) > 0
                )
                results[symbol] = is_valid
                
                if not is_valid:
                    logger.warning(f"Invalid symbol: {symbol}")
                    
            except Exception as e:
                logger.warning(f"Error validating {symbol}: {e}")
                results[symbol] = False
    
    return results

def find_delisted_symbols(data_file: Path) -> Set[str]:
    """Find potentially delisted symbols in the data file."""
    stocks = load_stock_data(data_file)
    if not stocks:
        return set()
    
    symbols = [stock.get("Symbol") or stock.get("symbol") for stock in stocks if stock.get("Symbol") or stock.get("symbol")]
    logger.info(f"Found {len(symbols)} symbols to validate")
    
    validation_results = validate_symbols(symbols)
    
    delisted = {symbol for symbol, is_valid in validation_results.items() if not is_valid}
    
    logger.info(f"Found {len(delisted)} potentially delisted symbols")
    if delisted:
        logger.info(f"Delisted symbols: {', '.join(sorted(delisted))}")
    
    return delisted

def main():
    """Main function to validate US and Indian stock symbols."""
    data_dir = Path(__file__).resolve().parents[1] / "data"
    
    # Validate US stocks
    us_file = data_dir / "us_stocks.json"
    if us_file.exists():
        logger.info("Validating US stocks...")
        delisted_us = find_delisted_symbols(us_file)
        if delisted_us:
            logger.warning(f"US delisted symbols: {', '.join(sorted(delisted_us))}")
    
    # Validate Indian stocks  
    in_file = data_dir / "nifty500.json"
    if in_file.exists():
        logger.info("Validating Indian stocks...")
        delisted_in = find_delisted_symbols(in_file)
        if delisted_in:
            logger.warning(f"Indian delisted symbols: {', '.join(sorted(delisted_in))}")

if __name__ == "__main__":
    main()