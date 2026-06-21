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

from api.agent.providers import resolve_agent_llm
from api.config import get_settings

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
            except Exception as exc:  # transient provider/parse errors → retry
                logger.warning(
                    "function-calling for %s failed (attempt %d/%d): %s",
                    schema.__name__,
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    exc,
                )
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
        for attempt in range(_MAX_ATTEMPTS):
            try:
                message = await json_model.ainvoke([("system", sys_prompt), ("human", user)])
                content = message.content
                text = content if isinstance(content, str) else str(content)
                return schema.model_validate_json(_extract_json(text))
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_exc = exc
                logger.warning(
                    "JSON-mode parse for %s failed (attempt %d/%d): %s",
                    schema.__name__,
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    exc,
                )
        raise BrainError(
            f"model returned no valid structured output for {schema.__name__} "
            f"after function-calling and JSON-mode retries"
        ) from last_exc


def structured_llm_from_settings(*, temperature: float = 0.4) -> LangChainStructuredLLM:
    from langchain_openai import ChatOpenAI

    config = resolve_agent_llm(get_settings())
    model = ChatOpenAI(
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=temperature,
    )
    return LangChainStructuredLLM(model)
