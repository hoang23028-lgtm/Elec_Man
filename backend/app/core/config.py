from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Hệ thống AI quản lý đồng hồ điện"
    app_env: str = Field(default="development", pattern="^(development|test|production)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    database_url: str
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60)
    frontend_origin: str = "http://localhost:3000"
    storage_root: Path = Path("./storage")
    models_root: Path = Path("./models")
    worker_poll_interval_seconds: float = Field(default=2.0, gt=0)
    session_cookie_name: str = "ema_session"
    session_ttl_hours: int = Field(default=8, ge=1, le=168)
    session_secret: str = ""
    allowed_hosts: str = "localhost,127.0.0.1"
    admin_initial_password: str | None = None
    max_image_size_mb: int = Field(default=20, ge=1, le=100)
    max_image_pixels: int = Field(default=40_000_000, ge=1_000_000)
    max_retry_count: int = Field(default=3, ge=1, le=10)
    job_stuck_timeout_seconds: int = Field(default=900, ge=60)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if len(self.session_secret) < 32 or self.session_secret.startswith("replace-with-"):
                raise ValueError(
                    "SESSION_SECRET phải là giá trị duy nhất gồm ít nhất 32 ký tự "
                    "trong môi trường production."
                )
            if "change-me-before-deployment" in self.database_url:
                raise ValueError("Mật khẩu cơ sở dữ liệu mặc định không được dùng ở production.")
            if "*" in self.allowed_host_list:
                raise ValueError("ALLOWED_HOSTS không được chứa ký tự * ở production.")
        return self

    @property
    def allowed_host_list(self) -> list[str]:
        hosts = [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return hosts or ["localhost", "127.0.0.1"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
