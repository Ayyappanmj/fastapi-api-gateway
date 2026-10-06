"""
Centralized application configuration.

All environment-driven settings live here so the rest of the codebase
never touches os.environ directly. This keeps configuration testable
and makes it obvious where to look when adding a new setting.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://gateway_user:change_me@localhost:5432/gateway_db"
    direct_url: str | None = None

    # Optional downstream URLs; unset services use the in-process demo handlers.
    echo_service_url: str | None = None
    time_service_url: str | None = None
    users_service_url: str | None = None
    orders_service_url: str | None = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "replace_with_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Rate limiting defaults (token bucket)
    rate_limit_enabled: bool = True
    default_rate_limit_tokens: int = 100
    default_rate_limit_refill_per_sec: float = 1.0

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def service_url_map(self) -> dict[str, str]:
        return {
            name: url
            for name, url in {
                "echo": self.echo_service_url,
                "time": self.time_service_url,
                "users": self.users_service_url,
                "orders": self.orders_service_url,
            }.items()
            if url
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so we parse the environment only once."""
    return Settings()
