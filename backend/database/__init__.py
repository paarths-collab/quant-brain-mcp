# Database module
from .connection import get_db, get_engine, SessionLocal, Base
from .models import FredData, FredSeriesMetadata, SectorNewsItem, SectorSnapshot, SectorScore

try:
    from .fred_repository import FredRepository
except Exception as _exc:
    _fred_repository_import_error = _exc

    class FredRepository:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "FredRepository requires optional dependency 'pandas'. "
                "Install it (e.g. `pip install -r backend/requirements.txt`) to use FRED features."
            ) from _fred_repository_import_error

# Backwards compatibility
engine = property(lambda: get_engine()) # type: ignore

__all__ = [
    'get_db',
    'get_engine',
    'SessionLocal',
    'Base',
    'FredData',
    'FredSeriesMetadata',
    'SectorNewsItem',
    'SectorSnapshot',
    'SectorScore',
    'FredRepository',
]
