"""Structured-output LLM for the brain.

Each node asks the model to fill a pydantic schema. The production implementation
first tries LangChain's `with_structured_output` (function calling). Some
providers — notably DeepSeek — occasionally answer with prose and no tool call,
so we fall back to JSON mode (ask for raw JSON matching the schema and validate
it). Tests inject a fake that returns canned objects — no network required.
"""

import json
import logging
import re
from typing import Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

from api.agent.providers import agent_llm_chain, provider_label
from api.config import get_settings
from api.logger import short_error

logger = logging.getLogger("api.brain")

T = TypeVar("T", bound=BaseModel)

# Function-calling models occasionally answer with plain prose and no tool call,
# in which case LangChain hands back ``None``. We retry, then fall back to JSON.
_MAX_ATTEMPTS = 3
_NUDGE = (
    "\n\nIMPORTANT: You MUST respond by calling the provided function with all "
    "required fields filled in. Do not reply with plain text."
)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _hard_provider_error(exc: BaseException) -> bool:
    """True for errors where retrying the same provider is pointless (rate limit,
    auth, connection) — fail over to the next provider instead."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    return status in (429, 401, 403) or any(
        k in name for k in ("RateLimit", "Authentication", "Connection")
    )


def _extract_json(content: str) -> str:
    """Pull the JSON object out of a model reply, tolerating code fences and
    surrounding prose."""
    text = _FENCE.sub("", content.strip())
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class StructuredLLM(Protocol):
    async def generate(self, system: str, user: str, schema: type[T]) -> T: ...


class BrainError(RuntimeError):
    pass


class FallbackStructuredLLM:
    """Tries each provider in order; on any error, falls back to the next. Used to
    put a free (rate-limited) provider in front of a paid one."""

    def __init__(
        self,
        providers: list[StructuredLLM],
        labels: list[str] | None = None,
        models: list[str] | None = None,
    ) -> None:
        if not providers:
            raise BrainError("FallbackStructuredLLM needs at least one provider")
        self._providers = providers
        self._labels = labels or [f"provider {i + 1}" for i in range(len(providers))]
        self._models = models  # model ids parallel to providers, for cooldown on failure

    async def generate(self, system: str, user: str, schema: type[T]) -> T:
        last_exc: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                return await provider.generate(system, user, schema)
            except Exception as exc:  # provider down / rate-limited / bad key → next
                last_exc = exc
                if self._models and i < len(self._models):
                    from api.agent.model_switch import note_failure

                    note_failure(self._models[i])  # next request skips this model
                nxt = self._labels[i + 1] if i + 1 < len(self._labels) else None
                tail = f" → trying {nxt}" if nxt else ""
                logger.warning("%s %s for %s%s", self._labels[i], short_error(exc), schema.__name__, tail)
        raise BrainError("all LLM providers failed") from last_exc


class LangChainStructuredLLM:
    """Wraps a LangChain chat model and coerces each call into a pydantic schema."""

    def __init__(self, model: object) -> None:
        self._model = model

    async def generate(self, system: str, user: str, schema: type[T]) -> T:
        result = await self._try_function_calling(system, user, schema)
        if result is not None:
            return result
        logger.info("falling back to JSON mode for %s", schema.__name__)
        return await self._generate_json(system, user, schema)

    async def _try_function_calling(self, system: str, user: str, schema: type[T]) -> T | None:
        structured = self._model.with_structured_output(  # type: ignore[attr-defined]
            schema, method="function_calling"
        )
        for attempt in range(_MAX_ATTEMPTS):
            sys_prompt = system if attempt == 0 else system + _NUDGE
            try:
                result = await structured.ainvoke([("system", sys_prompt), ("human", user)])
            except Exception as exc:
                if _hard_provider_error(exc):  # 429/auth → fall back now, don't retry
                    raise
                logger.debug("function-calling retry for %s: %s", schema.__name__, short_error(exc))
                result = None
            if result is not None:
                return cast(T, result)
        return None

    async def _generate_json(self, system: str, user: str, schema: type[T]) -> T:
        schema_json = json.dumps(schema.model_json_schema())
        sys_prompt = (
            f"{system}\n\nRespond with ONLY a single JSON object that conforms to this "
            f"JSON Schema. No markdown, no code fences, no commentary.\n\nSchema:\n{schema_json}"
        )
        json_model = self._model.bind(response_format={"type": "json_object"})  # type: ignore[attr-defined]
        last_exc: Exception | None = None
        for _ in range(_MAX_ATTEMPTS):
            try:
                message = await json_model.ainvoke([("system", sys_prompt), ("human", user)])
                content = message.content
                text = content if isinstance(content, str) else str(content)
                return schema.model_validate_json(_extract_json(text))
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_exc = exc
                logger.debug("JSON-mode retry for %s: %s", schema.__name__, short_error(exc))
        raise BrainError(
            f"model returned no valid structured output for {schema.__name__} "
            f"after function-calling and JSON-mode retries"
        ) from last_exc


def structured_llm_from_settings(*, temperature: float = 0.4) -> StructuredLLM:
    """Build the brain's LLM: NVIDIA (free, throttled to its RPM) when keyed, with
    DeepSeek as the automatic fallback. Whichever keys are set, NVIDIA goes first."""
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    chain = agent_llm_chain(settings)
    if not chain:
        raise BrainError("no agent LLM configured: set NVIDIA_API_KEY or DEEPSEEK_API_KEY")

    providers: list[StructuredLLM] = []
    labels: list[str] = []
    models: list[str] = []
    for config in chain:
        params: dict[str, object] = {
            "model": config.model,
            "base_url": config.base_url,
            "api_key": config.api_key,
            "temperature": temperature,
            # Cap per-request time so a stuck provider fails over instead of hanging.
            "request_timeout": settings.llm_timeout_seconds,
            # Without this the SDK retries timeouts twice, turning the cap into ~3x.
            "max_retries": 0,
        }
        if config.rate_limiter is not None:  # shared NVIDIA throttle
            params["rate_limiter"] = config.rate_limiter
        if config.extra_body:
            params["extra_body"] = config.extra_body
        providers.append(LangChainStructuredLLM(ChatOpenAI(**params)))
        labels.append(f"{provider_label(config.base_url)}:{config.model}")
        models.append(config.model)

    if len(providers) == 1:
        return providers[0]
    return FallbackStructuredLLM(providers, labels, models)
