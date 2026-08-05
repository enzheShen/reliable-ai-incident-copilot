from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "Reliable AI Incident Copilot"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://incident:incident@localhost:5432/incident_copilot"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] | str = Field(default_factory=lambda: ["http://localhost:5173"])
    max_incident_body_bytes: int = Field(default=65_536, ge=1_024, le=1_048_576)
    data_dir: Path = Path("../data")
    reports_dir: Path = Path("../reports")

    llm_mode: str = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    llm_timeout_seconds: float = Field(default=12.0, gt=0, le=120)
    mock_llm_url: str = "http://localhost:8080"

    cache_ttl_seconds: int = Field(default=900, ge=1)
    rate_limit_per_minute: int = Field(default=10, ge=1)
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_recovery_seconds: int = Field(default=60, ge=1)
    idempotency_ttl_seconds: int = Field(default=86_400, ge=60)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_production_wildcard(cls, value: list[str] | str) -> list[str] | str:
        return value

    def validated_cors_origins(self) -> list[str]:
        origins = self.cors_origins if isinstance(self.cors_origins, list) else [self.cors_origins]
        if self.app_env == "production" and "*" in origins:
            raise ValueError("Wildcard CORS is not allowed in production")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
