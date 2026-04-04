import sys
import os
from pathlib import Path

# Force project root to the top of sys.path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

import uvicorn

if __name__ == "__main__":
    # Remove emojis to prevent UnicodeEncodeError on Windows redirects
    print(f"Starting Quant Intelligence Backend from {root}...")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'None')}")
    print(f"SYS.PATH: {sys.path[:3]}...")
    
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=False
    )
