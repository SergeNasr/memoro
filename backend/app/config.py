"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # OpenRouter API
    openrouter_api_key: str

    # Google OAuth
    google_client_id: str
    google_client_secret: str

    # Security
    secret_key: str

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000


# Global settings instance
settings = Settings()
