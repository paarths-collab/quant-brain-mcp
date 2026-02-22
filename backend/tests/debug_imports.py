import sys
import os

# Add root to path
sys.path.append(os.getcwd())

print("Testing imports...")
try:
    import backend
    print("backend imported")
except ImportError as e:
    print(f"Failed to import backend: {e}")

try:
    from backend.core.config import settings
    print("backend.core.config imported")
except ImportError as e:
    print(f"Failed: backend.core.config: {e}")

try:
    from backend.core.llm_client import LLMClient
    print("backend.core.llm_client imported")
except ImportError as e:
    print(f"Failed: backend.core.llm_client: {e}")

try:
    from backend.services.market_data_service import MarketDataService
    print("backend.services.market_data_service imported")
except ImportError as e:
    print(f"Failed: backend.services.market_data_service: {e}")

try:
    from backend.services.duckduckgo_service import DuckDuckGoService
    print("backend.services.duckduckgo_service imported")
except ImportError as e:
    print(f"Failed: backend.services.duckduckgo_service: {e}")

try:
    from backend.services.tavily_service import TavilyService
    print("backend.services.tavily_service imported")
except ImportError as e:
    print(f"Failed: backend.services.tavily_service: {e}")

try:
    from backend.agents.super_agent import SuperAgent
    print("backend.agents.super_agent imported")
except ImportError as e:
    print(f"Failed: backend.agents.super_agent: {e}")

print("Import check complete.")
