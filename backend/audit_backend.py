import os
import sys
import importlib
from pathlib import Path

# Add the project root to sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

modules_to_test = [
    "sectors", "markets", "technical", "chat", "portfolio", 
    "backtest", "peers", "research", "dashboard", "network", 
    "news", "screener", "profile"
]

results = {}

print("--- Starting Backend Module Audit ---")

for mod in modules_to_test:
    module_path = f"backend.{mod}.main"
    print(f"Testing {module_path}...", end=" ", flush=True)
    try:
        # Import the module dynamically
        importlib.import_module(module_path)
        print("Γ£ô OK")
        results[mod] = "OK"
    except Exception as e:
        import traceback
        err = str(e)
        print(f"Γ¥î FAILED: {err}")
        results[mod] = f"ERROR: {err}"
        # Print first few lines of traceback to identify the file
        # traceback.print_exc(limit=3)

print("\n--- Audit Summary ---")
for mod, status in results.items():
    print(f"{mod:12}: {status}")

with open("audit.txt", "w") as f:
    for mod, status in results.items():
        f.write(f"{mod}: {status}\n")
