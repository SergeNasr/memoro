"""Application configuration using pydantic-settings."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # OpenAI API
    openai_api_key: str

    # Security
    secret_key: str

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Supabase
    supabase_url: str
    supabase_secret_key: str

    # Firebase
    firebase_project_id: Optional[str] = None
    firebase_web_api_key: Optional[str] = None
    firebase_service_account_path: Optional[str] = None


# Global settings instance
settings = Settings()
