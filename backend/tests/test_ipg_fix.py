"""
Test script to check if IPG symbol issues are resolved
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

# Load environment
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(env_path)

# Test the sector intel functionality
from database.connection import get_db_session, init_db
from services.sector_intel_service import get_sector_constituents, _fetch_yf_price_metrics

def test_communication_services_symbols():
    """Test Communication Services sector symbols for IPG issues"""
    print("Testing Communication Services sector...")
    
    # Get constituents
    constituents = get_sector_constituents("US", "Communication Services", limit=20)
    print(f"Found {len(constituents)} constituents in Communication Services sector")
    
    # Check if IPG is still there
    symbols = [c["symbol"] for c in constituents]
    if "IPG" in symbols:
        print("ERROR: IPG is still in the constituent list!")
        return False
    else:
        print("✓ IPG successfully removed from constituent list")
    
    # Test fetching metrics for these symbols
    print(f"Testing price metrics for symbols: {symbols[:5]}")
    try:
        metrics = _fetch_yf_price_metrics(symbols[:5], "3mo")
        print(f"✓ Successfully fetched metrics for {len(metrics)} symbols")
        return True
    except Exception as e:
        print(f"ERROR fetching metrics: {e}")
        return False

if __name__ == "__main__":
    init_db()
    success = test_communication_services_symbols()
    if success:
        print("\n✓ All tests passed! IPG issue appears to be resolved.")
    else:
        print("\n✗ Tests failed. IPG issue may still exist.")