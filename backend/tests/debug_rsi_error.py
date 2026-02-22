
import pandas as pd
import datetime

try:
    print("--- Starting Debug ---")
    end_date = pd.Timestamp.now()
    print(f"end_date: {end_date} (Type: {type(end_date)})")
    
    period = "1y"
    buffer = pd.DateOffset(days=365)
    print(f"buffer: {buffer} (Type: {type(buffer)})")
    
    start_date = end_date - pd.DateOffset(years=1) - buffer
    print(f"start_date: {start_date} (Type: {type(start_date)})")
    
    # Check string conversion
    if isinstance(start_date, pd.Timestamp):
        start_date_str = start_date.strftime('%Y-%m-%d')
    else:
        start_date_str = str(start_date)
    print(f"start_date_str: {start_date_str}")
    
    # Check strict start calculation (the new logic)
    strict_start = end_date - pd.DateOffset(years=1)
    print(f"strict_start: {strict_start} (Type: {type(strict_start)})")
    
    strict_start_str = strict_start.strftime('%Y-%m-%d')
    print(f"strict_start_str: {strict_start_str}")
    
    print("--- Date Logic Seems OK ---")

except Exception as e:
    print(f"Error caught: {e}")
    import traceback
    traceback.print_exc()
