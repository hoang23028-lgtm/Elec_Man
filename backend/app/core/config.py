from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Electricity Meter AI Management System"
    app_env: str = Field(default="development", pattern="^(development|test|production)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    database_url: str
    frontend_origin: str = "http://localhost:3000"
    storage_root: Path = Path("./storage")
    models_root: Path = Path("./models")
    worker_poll_interval_seconds: float = Field(default=2.0, gt=0)
    session_cookie_name: str = "ema_session"
    session_ttl_hours: int = Field(default=8, ge=1, le=168)
    session_secret: str = ""
    admin_initial_password: str | None = None
    max_image_size_mb: int = Field(default=20, ge=1, le=100)
    max_image_pixels: int = Field(default=40_000_000, ge=1_000_000)
    max_retry_count: int = Field(default=3, ge=1, le=10)
    job_stuck_timeout_seconds: int = Field(default=900, ge=60)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production" and (
            len(self.session_secret) < 32 or self.session_secret.startswith("replace-with-")
        ):
            raise ValueError("SESSION_SECRET must be a unique value of at least 32 characters in production.")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
