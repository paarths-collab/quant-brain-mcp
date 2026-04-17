import os
import importlib.util
from utils.serializer import serialize_output

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
                spec.loader.exec_module(module)

                # Identify tools by their 'compute' function (standard for this project)
                if hasattr(module, "compute"):
                    description = getattr(module, "__doc__", f"Calculates {module_name} for the provided ticker.")
                    tools[f"get_{module_name}"] = {
                        "func": module.compute,
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
