import json

import httpx

from api.agent.types import Message, ToolCall, ToolSpec
from api.config import get_settings


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
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._client = client

    async def next_action(self, messages: list[Message], tools: list[ToolSpec]) -> ToolCall:
        payload = {
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
    settings = get_settings()
    return GatewayToolCallingLLM(
        base_url=settings.ai_gateway_base_url,
        api_key=settings.ai_gateway_api_key,
        model=settings.planner_model,
    )
