import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Use FINANCIAL_MODEL_PREP as primary, fallback to FMP_API_KEY, then default
FMP_API_KEY = os.getenv("FINANCIAL_MODEL_PREP") or os.getenv("FMP_API_KEY") or "SXe42CfXVI89fxEARX39mubDml7biVYH"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v4"
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
PEERS_PREMIUM = os.getenv("PEERS_PREMIUM", "false").strip().lower() in {"1", "true", "yes"}
