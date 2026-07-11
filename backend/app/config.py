from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PT_", env_file=_REPO_ROOT / ".env", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://persontrace:persontrace@localhost:5432/persontrace"
    s3_endpoint: str = "http://localhost:8333"
    s3_access_key: str = "persontrace"
    s3_secret_key: str = "persontrace"
    s3_bucket: str = "persontrace"
    jwt_secret: str = "change-me-in-production-minimum-32-bytes!"
    jwt_expires_hours: int = 72
    cookie_name: str = "pt_session"


settings = Settings()
