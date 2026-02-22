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
    Base.metadata.create_all(bind=get_engine())

def run_init_sql():
    """Run init.sql to create tables that might not be in ORM (like user_profiles)"""
    init_sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "init.sql")
    if os.path.exists(init_sql_path):
        print(f"Running init.sql from {init_sql_path}...")
        with open(init_sql_path, "r") as f:
            sql_script = f.read()
        
        with get_engine().connect() as connection:
            try:
                # Smart split that handles BEGIN...END blocks in triggers
                statements = []
                current_statement = []
                in_trigger_block = False
                
                for line in sql_script.split('\n'):
                    stripped = line.strip()
                    current_statement.append(line)
                    
                    # Track if we're inside a trigger BEGIN...END block
                    if 'CREATE TRIGGER' in stripped.upper():
                        in_trigger_block = True
                    
                    if in_trigger_block and stripped.upper() == 'END;':
                        # End of trigger block
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                        in_trigger_block = False
                    elif not in_trigger_block and stripped.endswith(';'):
                        # Regular statement end
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                
                # Add any remaining statement
                if current_statement:
                    stmt = '\n'.join(current_statement).strip()
                    if stmt:
                        statements.append(stmt)
                
                # Execute each statement
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            connection.execute(text(statement))
                        except Exception as e:
                            print(f"Warning executing statement: {e}")
                            print(f"[SQL: {statement[:200]}]")
                
                connection.commit()
                print("init.sql executed successfully.")
            except Exception as e:
                print(f"Error running init.sql: {e}")

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
        print(f"Database connection failed: {e}")
        return False
