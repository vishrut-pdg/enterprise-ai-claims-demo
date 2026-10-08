from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parents[2] / ".env"), ".env"),
        extra="ignore",
    )
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://claims:claims@localhost:5432/claims"
    redis_url: str = "redis://localhost:6379/0"
    arq_queue_name: str = "claims"
    llm_provider: Literal["mock", "ollama", "vertex", "btp"] = "ollama"
    llm_model: str = "gemma4:e4b-it-q4_K_M"
    rag_enabled: bool = False
    embedding_provider: Literal["vertex", "mock"] = "vertex"
    embedding_model: str = "gemini-embedding-001"
    embedding_location: str = "us-central1"
    llm_timeout: float = 60
    ollama_base_url: str = "http://localhost:11434"
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    btp_ai_deployment_id: str = ""
    btp_ai_base_url: str = ""
    btp_token_url: str = ""
    btp_client_id: str = ""
    btp_client_secret: str = ""
    btp_resource_group: str = "default"
    btp_api_version: str = "2024-10-21"
    log_level: str = "INFO"
    otel_service_name: str = "enterprise-ai-claims"
    otel_exporter_otlp_endpoint: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
