"""Application configuration using pydantic-settings."""

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
    # Required for Firebase Auth REST API OAuth flow
    firebase_project_id: str | None = None
    firebase_web_api_key: str | None = None
    # Required for Firebase Admin SDK token verification
    firebase_service_account_path: str | None = None
    # No longer needed - Firebase REST API handles OAuth client ID internally
    firebase_web_client_id: str | None = None


# Global settings instance
settings = Settings()
