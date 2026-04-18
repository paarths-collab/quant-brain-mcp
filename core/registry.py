import os
import importlib.util


def _resolve_callable(module, module_name: str):
    """Resolve a callable tool entrypoint from a module.

    Supported patterns:
    - compute(df, ...)
    - get_<name>(df, ...)
    """
    if hasattr(module, "compute") and callable(module.compute):
        return f"get_{module_name}", module.compute

    preferred_name = f"get_{module_name}"
    if hasattr(module, preferred_name) and callable(getattr(module, preferred_name)):
        return preferred_name, getattr(module, preferred_name)

    for attr_name in dir(module):
        if not attr_name.startswith("get_"):
            continue
        candidate = getattr(module, attr_name)
        if callable(candidate):
            return attr_name, candidate

    return None, None

def register_all_tools():
    """
    Dynamically discovers all indicators and strategies.
    Returns a dictionary mapping tool names to their metadata and functions.
    """
    tools = {}
    base_path = os.path.join(os.path.dirname(__file__), "..", "tools")

    if not os.path.exists(base_path):
        return tools

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                file_path = os.path.join(root, file)

                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    # Skip modules that are not import-safe in registry scan.
                    continue

                tool_name, tool_func = _resolve_callable(module, module_name)
                if tool_func is None:
                    continue

                description = getattr(module, "__doc__", None)
                if not description or not str(description).strip():
                    description = (
                        f"Technical analysis tool for {module_name.upper()}. "
                        f"Use this when the user asks for {module_name} on a ticker."
                    )
                tools[tool_name] = {
                    "func": tool_func,
                    "description": (description or "").strip(),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Stock ticker (e.g., AAPL or RELIANCE.NS)"}
                        },
                        "required": ["ticker"]
                    }
                }
                
    return tools
