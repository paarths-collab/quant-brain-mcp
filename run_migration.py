import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Correctly locate backend/.env
# This script is at the root: c:\Users\Paarth\Github\Boomerang - agentic\run_migration.py
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / "backend" / ".env"
SQL_PATH = BASE_DIR / "backend" / "init.sql"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    logger.info(f"Loaded .env from {ENV_PATH}")
else:
    logger.error(f".env not found at {ENV_PATH}")
    # try fallback
    load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment variables")
    # For debugging, print cwd
    logger.info(f"CWD: {os.getcwd()}")
    exit(1)

def run_migration():
    try:
        logger.info(f"Connecting to database...")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Read init.sql
            if not SQL_PATH.exists():
                logger.error(f"init.sql not found at {SQL_PATH}")
                return
                
            with open(SQL_PATH, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            # Extract the user_profiles section
            marker = '-- USER PROFILES'
            if marker in sql_content:
                # Get everything after marker
                migration_sql = sql_content.split(marker)[-1]
                logger.info("Found USER PROFILES section in init.sql")
                
                # Execute the SQL
                logger.info("Executing migration...")
                connection.execute(text(migration_sql))
                connection.commit()
                logger.info("Migration successful: user_profiles table created/updated.")
            else:
                logger.warning(f"Could not find '{marker}' section in init.sql")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        exit(1)

if __name__ == "__main__":
    run_migration()
