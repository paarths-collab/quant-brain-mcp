import json

REQUIRED_KEYS = [
    "intent",
    "selected_agents",
    "execution_order",
    "parallelizable",
    "risk_flags",
    "search_queries"
]


def validate_schema(json_str: str):
    try:
        data = json.loads(json_str)

        for key in REQUIRED_KEYS:
            if key not in data:
                raise ValueError(f"Missing key: {key}")

        return True, data

    except Exception as e:
        return False, str(e)
