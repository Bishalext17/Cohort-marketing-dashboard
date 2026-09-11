from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

try:
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        connect_args={"connect_timeout": 5},
        execution_options={"read_only": settings.DB_READ_ONLY}
    )
    
    if settings.DB_READ_ONLY:
        @event.listens_for(engine, "connect")
        def set_session_readonly(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET SESSION TRANSACTION READ ONLY;")
                cursor.close()
            except Exception as ex:
                logger.warning(f"Could not set session to read-only: {ex}")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.warning(f"Could not initialize MariaDB engine: {e}")
    engine = None
    SessionLocal = None


def get_db():
    """FastAPI database session dependency with graceful error handling"""
    if SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> bool:
    """Test connection to MariaDB instance"""
    if not engine:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.warning(f"MariaDB connection check failed: {e}. Fallback to analytical engine.")
        return False

def get_db_status() -> dict:
    """Detailed DB connection status and diagnostics"""
    if not engine:
        return {
            "connected": False,
            "error": "SQLAlchemy engine not initialized (check database configuration / .env)",
            "host": settings.MARIADB_HOST,
            "port": settings.MARIADB_PORT,
            "user": settings.MARIADB_USER,
            "database": settings.MARIADB_DATABASE
        }
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT NOW() as db_time, @@hostname as db_host")).fetchone()
            return {
                "connected": True,
                "host": settings.MARIADB_HOST,
                "port": settings.MARIADB_PORT,
                "user": settings.MARIADB_USER,
                "database": settings.MARIADB_DATABASE,
                "db_server_time": str(res[0]) if res else None
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "host": settings.MARIADB_HOST,
            "port": settings.MARIADB_PORT,
            "user": settings.MARIADB_USER,
            "database": settings.MARIADB_DATABASE
        }
