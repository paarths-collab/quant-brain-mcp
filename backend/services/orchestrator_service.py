from functools import lru_cache
from pathlib import Path
import yaml
from backend.agents.orchestrator import Orchestrator

_orchestrator_instance = None

def get_orchestrator() -> Orchestrator:
    """
    Get or initialize the global Orchestrator instance.
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        # Load config
        # Assuming config.yaml is in the project root or a known location
        # Adjust path as necessary based on project structure
        try:
            config_path = Path("config.yaml")
            if not config_path.exists():
                # Try one level up if in backend
                config_path = Path("../config.yaml")
            
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
            else:
                print("Warning: config.yaml not found. Using empty config.")
                config = {}
                
            _orchestrator_instance = Orchestrator(config)
        except Exception as e:
            print(f"Error initializing orchestrator: {e}")
            # Fallback to empty config to prevent crash
            _orchestrator_instance = Orchestrator({})
            
    return _orchestrator_instance
