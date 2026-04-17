import numpy as np
import pandas as pd
from collections import OrderedDict

def serialize_output(obj):
    """
    Brutally converts any nested structure containing NumPy/Pandas types
    into standard Python types for JSON serialization.
    """
    # Handle Dictionaries and OrderedDicts
    if isinstance(obj, (dict, OrderedDict)):
        return {str(k): serialize_output(v) for k, v in obj.items()}

    # Handle Lists and Sets
    elif isinstance(obj, (list, tuple, set, pd.Index)):
        return [serialize_output(i) for i in obj]

    # Handle Pandas Series/DataFrames
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return serialize_output(obj.to_dict())

    # Handle NumPy Arrays
    elif isinstance(obj, np.ndarray):
        return serialize_output(obj.tolist())

    # Handle NumPy Scalars
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)

    # Handle everything else
    return obj
