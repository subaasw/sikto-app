from dataclasses import dataclass

from api.agent.model_switch import _extra_body
from api.agent.providers import LLMConfig, _nvidia_limiter
from api.config import Settings


@dataclass(frozen=True)
class ProviderModels:
    id: str
    label: str
    models: list[str]
    default: str


def available_providers(settings: Settings) -> list[ProviderModels]:
    out: list[ProviderModels] = []
    if settings.nvidia_api_key:
        models: list[str] = []
        for model in [settings.nvidia_model, *settings.nvidia_fallback_models]:
            if model not in models:
                models.append(model)
        out.append(
            ProviderModels(
                id="nvidia", label="NVIDIA", models=models, default=settings.nvidia_model
            )
        )
    if settings.deepseek_api_key:
        out.append(
            ProviderModels(
                id="deepseek",
                label="DeepSeek",
                models=[settings.deepseek_model],
                default=settings.deepseek_model,
            )
        )
    if settings.openai_api_key:
        models = list(settings.openai_models)
        if settings.openai_model not in models:
            models.insert(0, settings.openai_model)
        out.append(
            ProviderModels(
                id="openai", label="OpenAI", models=models, default=settings.openai_model
            )
        )
    return out


def model_choices(settings: Settings) -> set[str]:
    return {f"{p.id}:{m}" for p in available_providers(settings) for m in p.models}


def lead_with_choice(
    chain: list[LLMConfig], settings: Settings, choice: str | None
) -> list[LLMConfig]:
    chosen = resolve_model(settings, choice)
    if chosen is None:
        return chain
    return [chosen, *[c for c in chain if c.model != chosen.model]]


def resolve_model(settings: Settings, choice: str | None) -> LLMConfig | None:
    if not choice or choice not in model_choices(settings):
        return None
    provider, _, model = choice.partition(":")
    if provider == "nvidia":
        return LLMConfig(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
            model=model,
            extra_body=_extra_body(model),
            rate_limiter=_nvidia_limiter(settings.nvidia_rpm),
        )
    if provider == "deepseek":
        return LLMConfig(
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=model,
        )
    if provider == "openai":
        return LLMConfig(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=model,
        )
    return None
