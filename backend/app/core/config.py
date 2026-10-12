from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "EvalBench"
    environment: str = "development"
    database_url: str = "sqlite:///./evalbench.db"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "mock-sec-qa-v1"
    eval_concurrency: int = Field(default=8, ge=1, le=100)
    eval_timeout: float = Field(default=45, gt=0, le=600)
    eval_retries: int = Field(default=2, ge=0, le=10)
    regression_threshold: float = Field(default=0.05, ge=0, le=1)
    api_admin_key: str | None = None
    cors_origins: list[str] = ["http://localhost:5173"]
    max_request_bytes: int = Field(default=1_048_576, ge=1024)
    log_level: str = "INFO"
    pricing_path: Path = Path("configs/pricing.yaml")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

