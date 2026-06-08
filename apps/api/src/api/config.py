from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "sikto-api"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql+asyncpg://sikto:sikto@localhost:5432/sikto"
    storage_dir: str = ".storage"
    render_url: str = "http://localhost:8001"
    tts_url: str = "http://localhost:8002"
    ai_gateway_base_url: str = "https://ai-gateway.vercel.sh/v1"
    ai_gateway_api_key: str = ""
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536
    planner_model: str = "anthropic/claude-sonnet-4-5"
    tts_model: str = "qwen3-tts"
    tts_voice: str = "default"
    tts_language: str = "en"


@lru_cache
def get_settings() -> Settings:
    return Settings()
