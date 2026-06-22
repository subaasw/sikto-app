from typing import TYPE_CHECKING

import httpx

from api.agent.providers import resolve_agent_llm
from api.config import get_settings

if TYPE_CHECKING:
    from langchain_core.rate_limiters import BaseRateLimiter


class GatewayChatLLM:
    """Plain chat completion via an OpenAI-compatible endpoint (the Vercel AI Gateway),
    returning the message content. Used for code generation. Injectable httpx for tests."""

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

    async def complete(self, system: str, user: str) -> str:
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._extra_body:
            payload.update(self._extra_body)
        if self._rate_limiter is not None:
            await self._rate_limiter.aacquire(blocking=True)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"])


def chat_llm_from_settings() -> GatewayChatLLM:
    config = resolve_agent_llm(get_settings())
    return GatewayChatLLM(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        extra_body=config.extra_body,
        rate_limiter=config.rate_limiter,
    )
