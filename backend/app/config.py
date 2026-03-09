"""DataPilot — Application Configuration"""
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_env: Literal["development", "production"] = "development"
    secret_key: str = "change-me-in-production"
    api_key_header: str = "X-API-Key"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_model: str = "gpt-4o"

    datapilot_db_user: str = "datapilot"
    datapilot_db_password: str = "datapilot"
    datapilot_db_name: str = "datapilot"
    datapilot_db_host: str = "localhost"
    datapilot_db_port: int = 5433

    @property
    def datapilot_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.datapilot_db_user}:{self.datapilot_db_password}"
            f"@{self.datapilot_db_host}:{self.datapilot_db_port}/{self.datapilot_db_name}"
        )

    @property
    def datapilot_db_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.datapilot_db_user}:{self.datapilot_db_password}"
            f"@{self.datapilot_db_host}:{self.datapilot_db_port}/{self.datapilot_db_name}"
        )

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 30
    sql_query_timeout_seconds: int = 30
    sql_max_rows_returned: int = 1000
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
