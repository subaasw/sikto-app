"""NVIDIA free-model switcher.

The strongest free-tier models (deepseek-v4-pro) are also the most likely to 429
or hang, so we try them first and fall through to lighter, more-available ones —
all on the same NVIDIA endpoint/key and the same shared rate limiter; only the
model id (and deepseek's reasoning-off flag) changes.

A model that just failed is put on a short cooldown so the *next* request skips
straight past it instead of stalling on it again. Callers already iterate a
provider chain (the brain's FallbackStructuredLLM, the chat agent loop), so they
get the cascade for free — they only need to call ``note_failure`` when a model
errors out.

ponytail: in-process cooldown dict — correct for a single API process; move to
Redis only if you run multiple replicas that must share failure state.
"""

import time

from api.agent.providers import LLMConfig, _nvidia_limiter
from api.config import Settings

_COOLDOWN_SECONDS = 90.0
_cooldown_until: dict[str, float] = {}


def note_failure(model: str) -> None:
    """Mark a model as failed; the cascade will skip it for the cooldown window."""
    _cooldown_until[model] = time.monotonic() + _COOLDOWN_SECONDS


def _available(model: str) -> bool:
    return time.monotonic() >= _cooldown_until.get(model, 0.0)


def _extra_body(model: str) -> dict[str, object] | None:
    # deepseek reasoning models otherwise stream a long hidden <think> trace, which
    # both wastes the response and makes them appear to hang.
    if "deepseek" in model and "coder" not in model:
        return {"chat_template_kwargs": {"thinking": False}}
    return None


def nvidia_cascade(settings: Settings) -> list[LLMConfig]:
    """Ordered NVIDIA configs to try: lead model, then fallbacks (deduped), minus
    any on cooldown — but never empty (if all are cooling down, try them anyway so
    we never hard-fail just because everything failed recently)."""
    if not settings.nvidia_api_key:
        return []
    limiter = _nvidia_limiter(settings.nvidia_rpm)
    ordered: list[str] = []
    for model in [settings.nvidia_model, *settings.nvidia_fallback_models]:
        if model not in ordered:
            ordered.append(model)
    live = [m for m in ordered if _available(m)] or ordered
    return [
        LLMConfig(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
            model=model,
            extra_body=_extra_body(model),
            rate_limiter=limiter,
        )
        for model in live
    ]
