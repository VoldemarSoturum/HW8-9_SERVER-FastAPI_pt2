from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_name: str = "Advertisements Service"
    debug: bool = False

    # либо DATABASE_URL напрямую, либо собираем из POSTGRES_*
    database_url: str = Field(..., validation_alias="DATABASE_URL")

    # Для реализации JWT(JSON Web Token) в FastAPI

    jwt_secret: str = Field("CHANGE_ME", validation_alias="JWT_SECRET")  # в .env!
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    jwt_exp_hours: int = Field(48, validation_alias="JWT_EXP_HOURS")

    # “первый админ” через env (bootstrap)
    # ВАЖНО:
    # - если переменные не заданы — root НЕ создаём
    # - root — отдельная роль (group="root"), обычные админы остаются group="admin"
    bootstrap_root_username: str | None = Field(default=None, validation_alias="BOOTSTRAP_ROOT_USERNAME")
    bootstrap_root_password: str | None = Field(default=None, validation_alias="BOOTSTRAP_ROOT_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ВАЖНО: оставляем ради совместимости со строками вида:
# from app.config import settings
settings = get_settings()
