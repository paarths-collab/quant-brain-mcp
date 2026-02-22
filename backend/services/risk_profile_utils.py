"""
Risk Profile Utilities

Defines standard risk profiles and their associated strategy weights for long-term analysis.
"""

from typing import Dict

# Define standard risk profiles and their strategy allocations
# Weights must sum to 1.0 for each profile
RISK_PROFILES: Dict[str, Dict[str, float]] = {
    "capital_preservation": {
        "dca": 0.40,
        "dividend": 0.35,
        "index": 0.25,
        "value": 0.0,
        "growth": 0.0,
    },
    "conservative": {
        "dca": 0.30,
        "dividend": 0.30,
        "index": 0.20,
        "value": 0.20,
        "growth": 0.0,
    },
    "moderate": {
        "dca": 0.20,
        "dividend": 0.20,
        "index": 0.20,
        "value": 0.20,
        "growth": 0.20,
    },
    "growth": {
        "dca": 0.10,
        "dividend": 0.0,
        "index": 0.10,
        "value": 0.30,
        "growth": 0.50,
    },
    "aggressive": {
        "dca": 0.0,
        "dividend": 0.0,
        "index": 0.0,
        "value": 0.20,
        "growth": 0.80,
    }
}

def get_active_strategies(risk_profile: str) -> Dict[str, float]:
    """
    Returns the strategy weights for a given risk profile.
    If the profile is not found, defaults to 'moderate'.
    """
    normalized_profile = risk_profile.lower().strip()
    return RISK_PROFILES.get(normalized_profile, RISK_PROFILES["moderate"])
