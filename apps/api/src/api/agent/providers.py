"""Agent LLM provider resolution.

Two OpenAI-compatible providers: NVIDIA (free) as the primary and DeepSeek as the
fallback. Callers that want resilience use ``agent_llm_chain`` (try each in
order); single-client callers use ``resolve_agent_llm`` (the primary).
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from api.config import Settings

if TYPE_CHECKING:
    from langchain_core.rate_limiters import BaseRateLimiter


@lru_cache(maxsize=1)
def _nvidia_limiter(rpm: int) -> "BaseRateLimiter":
    """One process-wide throttle every NVIDIA caller shares, so their combined
    rate stays under the free-tier limit. 10% headroom, strict spacing (no bursts)."""
    from langchain_core.rate_limiters import InMemoryRateLimiter

    return InMemoryRateLimiter(
        requests_per_second=max(rpm, 1) * 0.9 / 60.0,
        check_every_n_seconds=0.1,
        max_bucket_size=1,
    )


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    # NVIDIA needs this in the request body to disable its reasoning trace.
    extra_body: dict[str, object] | None = None
    # Shared NVIDIA throttle; None for providers with no client-side limit.
    rate_limiter: "BaseRateLimiter | None" = None


def _deepseek(settings: Settings) -> LLMConfig | None:
    if not settings.deepseek_api_key:
        return None
    return LLMConfig(
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
    )


def provider_label(base_url: str) -> str:
    """Short human name for logs, derived from the endpoint."""
    if "nvidia" in base_url:
        return "nvidia"
    if "deepseek" in base_url:
        return "deepseek"
    return base_url


def agent_llm_chain(settings: Settings) -> list[LLMConfig]:
    """Configs to try in order: the NVIDIA free-model cascade (advanced → light,
    see api.agent.model_switch) followed by DeepSeek's own API as a last resort.
    Imported lazily to avoid a circular import with model_switch."""
    from api.agent.model_switch import nvidia_cascade

    chain = list(nvidia_cascade(settings))
    deepseek = _deepseek(settings)
    if deepseek is not None:
        chain.append(deepseek)
    return chain


def resolve_agent_llm(settings: Settings) -> LLMConfig:
    """The primary provider (NVIDIA when keyed, else DeepSeek) for single-client
    callers that don't do their own fallback."""
    chain = agent_llm_chain(settings)
    if not chain:
        raise RuntimeError("no agent LLM configured: set NVIDIA_API_KEY or DEEPSEEK_API_KEY")
    return chain[0]
