import os
import re
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# =====================================================
# DATABASE CONFIG
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./boomerang.db")
SQLITE_FALLBACK_URL = os.getenv("SQLITE_FALLBACK_URL", "sqlite:///./boomerang.db")
DB_FALLBACK_TO_SQLITE = os.getenv("DB_FALLBACK_TO_SQLITE", "true").lower() == "true"

_active_database_url = DATABASE_URL


def _engine_options_for(db_url: str):
    options = {
        "pool_pre_ping": True,
        "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    }

    if not db_url.startswith("sqlite"):
        options.update({
            "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 10)),
            "pool_recycle": 1800,
        })
    return options


def _create_engine_for(db_url: str):
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(db_url, connect_args=connect_args, **_engine_options_for(db_url))


def _safe_db_url(db_url: str) -> str:
    if "@" in db_url and "://" in db_url:
        prefix, rest = db_url.split("://", 1)
        if "@" in rest:
            _, tail = rest.split("@", 1)
            return f"{prefix}://***:***@{tail}"
    return db_url

# Lazy engine creation
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_for(_active_database_url)
    return _engine


def get_active_database_url() -> str:
    return _active_database_url


def switch_to_sqlite_fallback(reason: str = ""):
    global _engine, _active_database_url
    if _active_database_url.startswith("sqlite"):
        return

    previous_url = _active_database_url
    _active_database_url = SQLITE_FALLBACK_URL

    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = _create_engine_for(_active_database_url)

    logger.warning(
        "Database fallback activated. previous_url=%s fallback_url=%s reason=%s",
        _safe_db_url(previous_url),
        _safe_db_url(_active_database_url),
        reason,
    )

# For backwards compatibility (engine instance)
engine = get_engine()

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
    # Ensure models are imported so metadata is populated
    from backend.database import models  # noqa: F401
    try:
        Base.metadata.create_all(bind=get_engine())
    except SQLAlchemyError as e:
        if DB_FALLBACK_TO_SQLITE and not get_active_database_url().startswith("sqlite"):
            switch_to_sqlite_fallback(reason=f"init_db failed: {e}")
            Base.metadata.create_all(bind=get_engine())
        else:
            raise

def run_init_sql():
    """Run init.sql to create tables that might not be in ORM (like user_profiles)"""
    init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")
    if os.path.exists(init_sql_path):
        print(f"Running init.sql from {init_sql_path}...")
        with open(init_sql_path, "r") as f:
            sql_script = f.read()

        dialect = get_engine().dialect.name.lower()

        def _split_sql_statements(script: str):
            statements = []
            current_statement = []
            in_trigger_block = False

            for line in script.split('\n'):
                stripped = line.strip()
                current_statement.append(line)

                if 'CREATE TRIGGER' in stripped.upper():
                    in_trigger_block = True

                if in_trigger_block and stripped.upper() == 'END;':
                    statements.append('\n'.join(current_statement))
                    current_statement = []
                    in_trigger_block = False
                elif not in_trigger_block and stripped.endswith(';'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []

            if current_statement:
                stmt = '\n'.join(current_statement).strip()
                if stmt:
                    statements.append(stmt)

            return statements

        # Normalize SQLite-only syntax for non-SQLite databases (Render/Postgres).
        if dialect != "sqlite":
            sql_script = re.sub(
                r"CREATE\s+TRIGGER[\s\S]*?END;",
                "",
                sql_script,
                flags=re.IGNORECASE,
            )
            sql_script = re.sub(
                r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
                "BIGSERIAL PRIMARY KEY",
                sql_script,
                flags=re.IGNORECASE,
            )
            sql_script = re.sub(
                r"INSERT\s+OR\s+IGNORE\s+INTO",
                "INSERT INTO",
                sql_script,
                flags=re.IGNORECASE,
            )
            sql_script = re.sub(
                r"\);\s*(?=\s*--\s*SQLite trigger|\s*$)",
                ") ON CONFLICT DO NOTHING;",
                sql_script,
                flags=re.IGNORECASE,
            )

        statements = _split_sql_statements(sql_script)

        with get_engine().connect() as connection:
            for statement in statements:
                statement = statement.strip()
                if not statement or statement.startswith('--'):
                    continue
                try:
                    connection.execute(text(statement))
                    connection.commit()
                except Exception as e:
                    # Critical: reset failed transaction so subsequent statements can run.
                    connection.rollback()
                    print(f"Warning executing statement: {e}")
                    print(f"[SQL: {statement[:200]}]")

        print("init.sql executed successfully.")

# =====================================================
# HEALTH CHECK
# =====================================================

def check_db_connection() -> bool:
    """Verify DB connectivity"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed ({get_active_database_url()}): {e}")
        return False
