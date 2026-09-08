from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://campus_sync:campus_sync@db:5432/campus_sync"
    supabase_url: str = ""
    supabase_jwt_audience: str = "authenticated"
    cors_origins: str = "http://localhost:5173"
    default_timezone: str = "Europe/Brussels"


@lru_cache
def get_settings() -> Settings:
    return Settings()
