from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # App Environment
    env: str = Field("development", env="ENV")
    debug: bool = Field(False, env="DEBUG")
    port: int = Field(8888, env="PORT")
    base_url: Optional[str] = Field("http://localhost:8888", env="BASE_URL")
    
    # Database (PostgreSQL)
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    sync_database_url: str = Field(
        "postgresql+psycopg2://admintrader:securepass@localhost:5432/algo_trader",
        env="SYNC_DATABASE_URL"
    )
    async_database_url: str = Field(
        "postgresql+asyncpg://admintrader:securepass@localhost:5432/algo_trader",
        env="ASYNC_DATABASE_URL"
    )
    
    # Encryption key for broker API keys
    encryption_key: Optional[str] = Field(None, env="ENCRYPTION_KEY")
    
    # Session secret
    session_secret_key: str = Field("change-this-in-production", env="SESSION_SECRET_KEY")
    
    model_config = SettingsConfigDict(
        env_file="/home/myalgo/algo-trader/.env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()

