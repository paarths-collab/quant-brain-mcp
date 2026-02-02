# Database module
from .connection import get_db, get_engine, SessionLocal, Base
from .models import FredData, FredSeriesMetadata
from .fred_repository import FredRepository

# Backwards compatibility
engine = property(lambda: get_engine()) # type: ignore

__all__ = ['get_db', 'get_engine', 'SessionLocal', 'Base', 'FredData', 'FredSeriesMetadata', 'FredRepository']
