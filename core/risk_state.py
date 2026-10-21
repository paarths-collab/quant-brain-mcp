"""Explicit state for risk metrics that could not be computed.

A metric that is missing, undefined or failed must never be reported as 0, as a
neutral score, or as "low risk". Producers return ``unavailable(reason)``;
consumers test ``is_unavailable`` and carry the state forward instead of
substituting a number.
"""
from __future__ import annotations

import math
from typing import Any

UNAVAILABLE = "unavailable"


def unavailable(reason: str) -> dict[str, str]:
    """Marker for a metric that could not be computed.

    ``error`` mirrors ``reason`` so existing consumers that test for an
    ``error`` key (including the research runtime's tool-failure detection)
    keep treating the payload as a failure.
    """
    reason = str(reason)
    return {"status": UNAVAILABLE, "reason": reason, "error": reason}


def is_unavailable(value: Any) -> bool:
    return isinstance(value, dict) and (value.get("status") == UNAVAILABLE or bool(value.get("error")))


def finite(value: Any) -> bool:
    """True for a real, finite number (bool and NaN/inf are not)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def count_unavailable(payload: Any) -> int:
    """Count nested unavailable (or partially unavailable) risk markers in a tool payload."""
    if isinstance(payload, dict):
        own = 1 if payload.get("status") == UNAVAILABLE or payload.get("risk_status") in {"partial", UNAVAILABLE} else 0
        return own + sum(count_unavailable(v) for v in payload.values())
    if isinstance(payload, list):
        return sum(count_unavailable(v) for v in payload)
    return 0
