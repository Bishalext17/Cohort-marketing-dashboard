from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

import os
import pymysql

def _get_raw_connection():
    raw_user = (settings.MARIADB_USER or "root").strip()
    raw_pass = (settings.MARIADB_PASSWORD or "").strip()
    raw_db = (settings.MARIADB_DATABASE or "production").strip()
    
    socket_path = settings.DB_SOCKET
    if not socket_path:
        default_cloudsql_socket = f"/cloudsql/{os.getenv('CLOUD_SQL_INSTANCE', 'bambinos-411405:asia-south1:production')}"
        if os.path.exists(default_cloudsql_socket):
            socket_path = default_cloudsql_socket
        elif os.path.exists("/cloudsql"):
            try:
                entries = [os.path.join("/cloudsql", e) for e in os.listdir("/cloudsql") if not e.startswith(".")]
                if entries:
                    socket_path = entries[0]
            except Exception:
                pass

    kwargs = {
        "user": raw_user,
        "password": raw_pass,
        "database": raw_db,
        "charset": "utf8mb4",
        "connect_timeout": 15,
        "read_timeout": settings.DB_READ_TIMEOUT,
    }
    if socket_path and socket_path.lower() not in ["none", "false", "disabled", "tcp"]:
        kwargs["unix_socket"] = socket_path.strip()
    else:
        kwargs["host"] = settings.MARIADB_HOST
        kwargs["port"] = settings.MARIADB_PORT

    return pymysql.connect(**kwargs)

try:
    engine = create_engine(
        "mysql+pymysql://",
        creator=_get_raw_connection,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
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
