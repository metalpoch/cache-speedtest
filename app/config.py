from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_url: str = "redis://valkey:6379/0"
    database_url: str = "postgresql://bench:bench@postgres:5432/bench"

    memory_max_size: int = 4096
    memory_ttl_seconds: int = 3600
    pg_pool_min_size: int = 1
    pg_pool_max_size: int = 10

    default_key: str = "theta"
    default_value: str = "42"
    benchmark_iterations: int = 500
    benchmark_warmup: int = 50
    benchmark_concurrency: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
