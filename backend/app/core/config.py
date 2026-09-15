from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
import urllib.parse
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cohort Marketing Performance Dashboard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Connection Details (Supports MARIADB_*, DB_HOST, DB_SOCKET, DB_USER, DB_PASS, DB_NAME)
    MARIADB_HOST: str = Field(default="localhost", validation_alias=AliasChoices("DB_HOST", "MARIADB_HOST"))
    MARIADB_PORT: int = Field(default=3306, validation_alias=AliasChoices("DB_PORT", "MARIADB_PORT"))
    MARIADB_USER: str = Field(default="root", validation_alias=AliasChoices("DB_USER", "DB_USERNAME", "MARIADB_USER"))
    MARIADB_PASSWORD: str = Field(default="", validation_alias=AliasChoices("DB_PASS", "DB_PASSWORD", "MARIADB_PASSWORD"))
    MARIADB_DATABASE: str = Field(default="production", validation_alias=AliasChoices("DB_NAME", "MARIADB_DATABASE"))
    DB_SOCKET: Optional[str] = Field(default=None, validation_alias=AliasChoices("DB_SOCKET", "CLOUD_SQL_SOCKET"))
    
    # Read-Only Safety Enforcer
    DB_READ_ONLY: bool = Field(default=True, validation_alias=AliasChoices("DB_READ_ONLY", "READ_ONLY"))
    # Seconds to wait for a single statement's result. The web app keeps the
    # default; the nightly pipeline raises it for the long cache-rebuild CALL.
    DB_READ_TIMEOUT: int = Field(default=120, validation_alias=AliasChoices("DB_READ_TIMEOUT"))
    
    # Direct Meta Marketing Graph API Settings
    META_ACCESS_TOKEN: str = Field(default="", validation_alias=AliasChoices("META_ACCESS_TOKEN", "META_API_KEY", "FB_ACCESS_TOKEN"))
    META_AD_ACCOUNT_IDS: str = Field(default="", validation_alias=AliasChoices("META_AD_ACCOUNT_IDS", "META_ACCOUNTS", "FB_ACCOUNT_IDS"))
    META_API_VERSION: str = Field(default="v20.0")

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = Field(default="bambinos-cohort-secret-jwt-key-2026-production-secure-random", validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"))
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440) # 24 hours
    
    # Dashboard Admin & Growth Credentials
    ADMIN_USERNAME: str = Field(default="admin", validation_alias=AliasChoices("ADMIN_USERNAME", "AUTH_USER"))
    ADMIN_PASSWORD: str = Field(default="admin123", validation_alias=AliasChoices("ADMIN_PASSWORD", "AUTH_PASS"))
    ADMIN_NAME: str = Field(default="Growth Executive", validation_alias=AliasChoices("ADMIN_NAME", "AUTH_NAME"))
    ADMIN_ROLE: str = Field(default="Admin", validation_alias=AliasChoices("ADMIN_ROLE", "AUTH_ROLE"))
    
    # Database URL Constructor with safe URL encoding
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        from sqlalchemy.engine.url import URL
        
        raw_user = (self.MARIADB_USER or "root").strip()
        raw_pass = (self.MARIADB_PASSWORD or "").strip()
        raw_db = (self.MARIADB_DATABASE or "production").strip()
        
        socket_path = self.DB_SOCKET
        if not socket_path:
            # Auto-detect Cloud Run / Cloud SQL unix socket mount
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

        # NOTE: str(URL) masks the password as "***" in SQLAlchemy 2.x, so the
        # URL must be rendered explicitly with hide_password=False.
        if socket_path:
            return URL.create(
                drivername="mysql+pymysql",
                username=raw_user,
                password=raw_pass,
                database=raw_db,
                query={"unix_socket": socket_path.strip(), "charset": "utf8mb4"}
            ).render_as_string(hide_password=False)
            
        return URL.create(
            drivername="mysql+pymysql",
            username=raw_user,
            password=raw_pass,
            host=self.MARIADB_HOST,
            port=self.MARIADB_PORT,
            database=raw_db,
            query={"charset": "utf8mb4"}
        ).render_as_string(hide_password=False)
    
    # Feature flags & Caching
    MOCK_DATA_FALLBACK: bool = True
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600 # 1 hour default TTL
    CACHE_PREWARM_ENABLED: bool = True
    CACHE_PREWARM_INTERVAL_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
            ".env"
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

