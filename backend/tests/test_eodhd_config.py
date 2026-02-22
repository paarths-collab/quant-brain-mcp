from pathlib import Path
from backend.core.config import EODHD_API_KEY

backend_dir = Path(__file__).parent / "backend"
env_path = backend_dir / ".env"

print(f"Backend dir: {backend_dir}")
print(f"Env path: {env_path}")
print(f"Env exists: {env_path.exists()}")
print(f"EODHD_API_KEY length: {len(EODHD_API_KEY) if EODHD_API_KEY else 0}")
print(f"EODHD_API_KEY value: {EODHD_API_KEY[:20] if EODHD_API_KEY else 'EMPTY'}...")

# Now verify what os.getenv returns
import os
print(f"\nos.getenv('EODHD_API_KEY'): {os.getenv('EODHD_API_KEY', 'NOT_SET')[:20] if os.getenv('EODHD_API_KEY') else 'NOT_SET'}...")
