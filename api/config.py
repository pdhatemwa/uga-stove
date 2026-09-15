from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "UGA Stove"
    app_base_url: str = "http://localhost:8501"
    api_base_url: str = "http://localhost:8000"

    database_url: str = "sqlite:///./uga_stove.db"

    jwt_secret: str = Field(
        default="development-only-change-me-please-12345",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=480, ge=15, le=1440)

    max_evidence_bytes: int = Field(
        default=8 * 1024 * 1024,
        ge=1024,
        le=20 * 1024 * 1024,
    )
    evidence_storage: str = "local"
    evidence_local_dir: Path = Path("storage/evidence")

    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"

    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.strip().casefold()

        if normalized not in {"development", "test", "production"}:
            raise ValueError(
                "APP_ENV must be development, test, or production"
            )

        return normalized

    @field_validator("jwt_secret")
    @classmethod
    def reject_unsafe_secret_in_production(cls, value: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        normalized_secret = value.strip().casefold()

        unsafe_markers = (
            "change-me",
            "changeme",
            "development",
            "example",
            "replace",
            "secret",
        )

        if app_env == "production" and any(
            marker in normalized_secret for marker in unsafe_markers
        ):
            raise ValueError(
                "JWT_SECRET must be a unique, strong production secret"
            )

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()