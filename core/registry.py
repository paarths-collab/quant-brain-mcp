"""Legacy flat tool registry, now backed by the explicit allowlist.

Previously this walked the entire tools/ tree and auto-registered every
compatible get_*/compute function (~133 tools). It now reads the curated
38-indicator allowlist in core.indicator_registry so the stdio server
(main.py) exposes the same curated surface as the FastMCP server.
"""

import importlib

from core.indicator_registry import _resolve, iter_all_indicators


def register_all_tools():
    """Return {tool_name: {func, description, parameters}} for the 38 core indicators."""
    tools = {}
    for key, module_path, func_name, group in iter_all_indicators():
        try:
            func = _resolve(module_path, func_name)
        except Exception:
            # Skip indicators whose module cannot import in this environment.
            continue

        module_doc = (importlib.import_module(module_path).__doc__ or "").strip()
        func_doc = (func.__doc__ or "").strip()
        description = module_doc or func_doc or (
            f"Technical analysis tool for {key.upper()} ({group}). "
            f"Use this when the user asks for {key} on a ticker."
        )

        tools[func_name] = {
            "func": func,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker (e.g., AAPL or RELIANCE.NS)",
                    }
                },
                "required": ["ticker"],
            },
        }

    return tools
