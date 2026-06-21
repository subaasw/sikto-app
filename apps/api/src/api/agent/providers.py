"""Resolve the agent LLM provider into a concrete endpoint config.

DeepSeek, OpenAI (Codex), and Anthropic (Claude) all expose an
OpenAI-compatible ``/chat/completions`` endpoint, so a single client works for
all of them — only the base URL, key, and default model differ. Switch with
``AGENT_PROVIDER`` and keep an API key for whichever provider you use.
"""

from dataclasses import dataclass

from api.config import Settings

# provider -> (base_url, default model)
_PRESETS: dict[str, tuple[str, str]] = {
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "anthropic": ("https://api.anthropic.com/v1", "claude-sonnet-4-5"),
}


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str


def resolve_agent_llm(settings: Settings) -> LLMConfig:
    provider = settings.agent_provider
    if provider == "custom":
        return LLMConfig(
            base_url=settings.agent_base_url,
            api_key=settings.agent_api_key,
            model=settings.agent_model or "",
        )

    base_url, default_model = _PRESETS[provider]
    keys = {
        "deepseek": settings.deepseek_api_key,
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
    }
    return LLMConfig(
        base_url=base_url,
        api_key=keys[provider],
        model=settings.agent_model or default_model,
    )
