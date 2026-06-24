"""Конфигурация приложения через переменные окружения (pydantic-settings)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Общее ---
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = True
    project_name: str = "Созвон"
    api_v1_prefix: str = "/api/v1"

    # Базовый публичный URL фронтенда (для ссылок в письмах, publik-страницы вида domain.ru/имя)
    public_base_url: str = "http://localhost:3000"

    # --- Безопасность / JWT ---
    secret_key: str = Field(
        default="dev-insecure-change-me",
        description="Секрет для подписи JWT. В production задаётся через окружение.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 часа

    # --- База данных ---
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://app:app@localhost:5432/scheduling",  # type: ignore[arg-type]
        description="Async DSN PostgreSQL (драйвер asyncpg).",
    )

    # --- Redis / Celery ---
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",  # type: ignore[arg-type]
    )
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        """Разрешаем задавать CORS_ORIGINS как строку через запятую."""
        if isinstance(v, str) and not v.startswith("["):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or str(self.redis_url)

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or str(self.redis_url)

    @property
    def sync_database_url(self) -> str:
        """Синхронный DSN (например, для некоторых утилит). Заменяем драйвер."""
        return str(self.database_url).replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
