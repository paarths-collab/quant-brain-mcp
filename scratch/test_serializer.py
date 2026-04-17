import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

import json
import numpy as np
import pandas as pd
from utils.serializer import serialize_output

def test_serialization():
    data = {
        "int64": np.int64(10),
        "float64": np.float64(3.14),
        "array": np.array([1, 2, 3]),
        "series": pd.Series([10, 20], index=["a", "b"]),
        "df": pd.DataFrame({"A": [1, 2]}),
        "nested": {
            "more_int": np.int32(5)
        }
    }
    
    print("Original types:")
    print(f"int64 type: {type(data['int64'])}")
    
    try:
        serialized = serialize_output(data)
        json_str = json.dumps(serialized, indent=2)
        print("\nSerialized successfully!")
        print(json_str)
        
        # Verify types in serialized object
        assert isinstance(serialized["int64"], int)
        assert isinstance(serialized["float64"], float)
        assert isinstance(serialized["nested"]["more_int"], int)
        print("\nValidation passed!")
        
    except Exception as e:
        print(f"\nSerialization FAILED: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_serialization()
