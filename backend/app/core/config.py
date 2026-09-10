from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
import urllib.parse
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cohort Marketing Performance Dashboard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Connection Details (Supports MARIADB_*, DB_HOST, DB_USER, DB_PASS, DB_NAME)
    MARIADB_HOST: str = Field(default="localhost", validation_alias=AliasChoices("DB_HOST", "MARIADB_HOST"))
    MARIADB_PORT: int = Field(default=3306, validation_alias=AliasChoices("DB_PORT", "MARIADB_PORT"))
    MARIADB_USER: str = Field(default="root", validation_alias=AliasChoices("DB_USER", "DB_USERNAME", "MARIADB_USER"))
    MARIADB_PASSWORD: str = Field(default="", validation_alias=AliasChoices("DB_PASS", "DB_PASSWORD", "MARIADB_PASSWORD"))
    MARIADB_DATABASE: str = Field(default="production", validation_alias=AliasChoices("DB_NAME", "MARIADB_DATABASE"))
    
    # Read-Only Safety Enforcer
    DB_READ_ONLY: bool = Field(default=True, validation_alias=AliasChoices("DB_READ_ONLY", "READ_ONLY"))
    
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
        escaped_user = urllib.parse.quote_plus(self.MARIADB_USER)
        escaped_pass = urllib.parse.quote_plus(self.MARIADB_PASSWORD)
        return f"mysql+pymysql://{escaped_user}:{escaped_pass}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}?charset=utf8mb4"
    
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

