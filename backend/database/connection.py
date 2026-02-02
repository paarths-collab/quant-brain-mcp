import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# =====================================================
# DATABASE CONFIG
# =====================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./boomerang.db"  # Default to SQLite for local dev
)

ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
}

# Only add pool options for non-SQLite
if not DATABASE_URL.startswith("sqlite"):
    ENGINE_OPTIONS.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 10)),
        "pool_recycle": 1800,
    })

# Lazy engine creation
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        connect_args = {}
        if DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(DATABASE_URL, connect_args=connect_args, **ENGINE_OPTIONS)
    return _engine

# For backwards compatibility
engine = property(lambda self: get_engine())

# =====================================================
# SESSION
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()

# =====================================================
# FASTAPI DEPENDENCY
# =====================================================

def get_db():
    """
    FastAPI dependency.
    Transaction is controlled at service/repo layer.
    """
    SessionLocal.configure(bind=get_engine())
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# CONTEXT MANAGER (SCRIPT / CRON / INGEST)
# =====================================================

@contextmanager
def get_db_session():
    """
    Context manager with automatic commit/rollback.
    Use for scripts, jobs, batch ingestion.
    """
    SessionLocal.configure(bind=get_engine())
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# =====================================================
# DB INIT
# =====================================================

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

# =====================================================
# HEALTH CHECK
# =====================================================

def check_db_connection() -> bool:
    """Verify DB connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
