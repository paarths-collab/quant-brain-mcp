import json
import re


def extract_json_from_output(text: str):
    try:
        # Find first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            return None

        json_str = text[start:end + 1]

        # Remove trailing commas before closing braces
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        return json.loads(json_str)

    except Exception as e:
        print("JSON extraction failed:", e)
        # print("Raw extracted text:\n", json_str) # Uncomment to debug raw output
        return None
