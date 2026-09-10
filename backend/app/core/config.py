from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import urllib.parse
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cohort Marketing Performance Dashboard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Connection Details (Supports both MARIADB_* and DB_* env vars)
    MARIADB_HOST: str = Field(default="localhost", validation_alias="DB_HOST")
    MARIADB_PORT: int = Field(default=3306, validation_alias="DB_PORT")
    MARIADB_USER: str = Field(default="root", validation_alias="DB_USERNAME")
    MARIADB_PASSWORD: str = Field(default="", validation_alias="DB_PASSWORD")
    MARIADB_DATABASE: str = Field(default="production", validation_alias="DB_NAME")
    
    # Database URL Constructor with safe URL encoding
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        escaped_user = urllib.parse.quote_plus(self.MARIADB_USER)
        escaped_pass = urllib.parse.quote_plus(self.MARIADB_PASSWORD)
        return f"mysql+pymysql://{escaped_user}:{escaped_pass}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}?charset=utf8mb4"
    
    # Feature flags
    MOCK_DATA_FALLBACK: bool = True
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600
    
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
