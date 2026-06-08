import httpx

from api.config import get_settings


class GatewayChatLLM:
    """Plain chat completion via an OpenAI-compatible endpoint (the Vercel AI Gateway),
    returning the message content. Used for code generation. Injectable httpx for tests."""

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

    async def complete(self, system: str, user: str) -> str:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"])


def chat_llm_from_settings() -> GatewayChatLLM:
    settings = get_settings()
    return GatewayChatLLM(
        base_url=settings.ai_gateway_base_url,
        api_key=settings.ai_gateway_api_key,
        model=settings.planner_model,
    )
