from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "sikto-api"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    storage_dir: str = ".storage"

    # database — credentials MUST come from the environment / .env (no defaults are
    # baked in). Set the POSTGRES_* parts (the Makefile reuses them) or override
    # DATABASE_URL directly for a managed/remote database. Host/port keep dev
    # defaults since they are not secrets.
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = ""

    @model_validator(mode="after")
    def _assemble_database_url(self) -> "Settings":
        if not self.database_url:
            if not (self.postgres_user and self.postgres_db):
                raise ValueError(
                    "database is not configured: set DATABASE_URL, or POSTGRES_USER / "
                    "POSTGRES_PASSWORD / POSTGRES_DB in your environment (.env)"
                )
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        # Fail fast rather than sign tokens with an empty/placeholder secret in prod.
        if self.environment == "production" and self.jwt_secret in ("", "dev-insecure-change-me"):
            raise ValueError("JWT_SECRET must be set to a strong value in production")
        return self

    # auth — set JWT_SECRET in the environment (`make secret`); no default is baked in.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 24 * 7  # 7 days
    auth_cookie_name: str = "access_token"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    render_url: str = "http://localhost:8001"
    tts_url: str = "http://localhost:8002"
    # Outbound HTTP timeouts (seconds). Neural TTS and Remotion renders run long
    # — a cold first render (bundle + Chromium) plus a multi-scene lesson with
    # audio can take several minutes. Kept longer than the render service's own
    # worker timeout (see apps/render scene-runner) so the API receives the
    # worker's result/error instead of giving up first.
    tts_timeout_seconds: float = 60.0
    render_timeout_seconds: float = 900.0
    # run the job worker in-process alongside the API. Disable when running a
    # dedicated worker so jobs aren't picked up twice.
    run_worker: bool = True

    # Web research during lesson planning. Uses a free, no-key provider
    # (DuckDuckGo) to gather relevant material so the outline is well-structured.
    web_search_enabled: bool = True
    web_search_provider: Literal["duckduckgo"] = "duckduckgo"
    web_search_results: int = 5  # snippets fetched per query
    web_search_max_chars: int = 2000  # cap on aggregated research fed to the brain

    # logging
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"
    log_dir: str | None = None  # when set, also write rotating file logs here

    # Agent LLM. Both are OpenAI-compatible. NVIDIA (free) is the PRIMARY provider
    # when NVIDIA_API_KEY is set; DeepSeek is the automatic fallback. Just provide
    # whichever keys you have — nothing else to configure.
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "deepseek-ai/deepseek-v4-pro"
    nvidia_rpm: int = 40  # free-tier requests/minute; the brain throttles below it
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # embeddings stay on an OpenAI-compatible gateway (DeepSeek/Anthropic have none).
    ai_gateway_base_url: str = "https://ai-gateway.vercel.sh/v1"
    ai_gateway_api_key: str = ""
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536
    planner_model: str = "deepseek-chat"
    tts_model: str = "qwen3-tts"
    tts_voice: str = "default"
    tts_language: str = "en"


@lru_cache
def get_settings() -> Settings:
    return Settings()
