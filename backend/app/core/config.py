"""Application configuration via environment variables."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./orbit.db"

    # Security
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32",
        description="JWT signing secret — must be changed in production",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7   # 7 days
    pairing_code_expire_seconds: int = 120

    # CORS — comma-separated in env
    cors_origins_raw: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    # Heartbeat
    heartbeat_interval_seconds: int = 15
    heartbeat_timeout_seconds: int = 45

    # Rate limiting (simple in-process)
    pairing_rate_limit_per_minute: int = 10
    auth_rate_limit_per_minute: int = 30


settings = Settings()
