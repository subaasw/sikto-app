import json
from typing import TYPE_CHECKING

import httpx

from api.agent.providers import resolve_agent_llm
from api.agent.types import Message, ToolCall, ToolSpec
from api.config import get_settings

if TYPE_CHECKING:
    from langchain_core.rate_limiters import BaseRateLimiter


class GatewayToolCallingLLM:
    """Tool-calling via an OpenAI-compatible chat-completions endpoint (the Vercel AI
    Gateway). Forces a tool call each turn (tool_choice=required) and returns the first
    one. An httpx client can be injected for testing."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        extra_body: dict[str, object] | None = None,
        rate_limiter: "BaseRateLimiter | None" = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._extra_body = extra_body
        self._rate_limiter = rate_limiter
        self._client = client

    async def next_action(self, messages: list[Message], tools: list[ToolSpec]) -> ToolCall:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ],
            "tool_choice": "required",
        }
        if self._extra_body:
            payload.update(self._extra_body)
        if self._rate_limiter is not None:
            await self._rate_limiter.aacquire(blocking=True)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base_url}/chat/completions"

        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            raise ValueError("model response contained no tool call")
        function = tool_calls[0]["function"]
        return ToolCall(name=function["name"], arguments=json.loads(function["arguments"]))


def tool_calling_llm_from_settings() -> GatewayToolCallingLLM:
    config = resolve_agent_llm(get_settings())
    return GatewayToolCallingLLM(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        extra_body=config.extra_body,
        rate_limiter=config.rate_limiter,
    )
