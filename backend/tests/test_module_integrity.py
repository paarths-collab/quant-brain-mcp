import pytest
import importlib

# Generic test to ensure the module is importable and functional at a base level

@pytest.mark.parametrize("module_path", [
    "backend.core",
    "backend.data",
    "backend.database",
    "backend.network",
    "backend.news",
    "backend.peers",
    "backend.profile",
    "backend.reports",
    "backend.research",
    "backend.screener",
])
def test_module_importable(module_path):
    """Ensure the module can be imported and doesn't have syntax errors."""
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        pytest.fail(f"Could not import {module_path}: {e}")
    except Exception as e:
        pytest.fail(f"Error during import of {module_path}: {e}")
