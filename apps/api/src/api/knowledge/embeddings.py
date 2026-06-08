import httpx

from api.config import get_settings


class GatewayEmbeddingsClient:
    """Provider-agnostic embeddings via an OpenAI-compatible endpoint (the Vercel AI
    Gateway). An httpx client can be injected for testing; otherwise one is created
    per call."""

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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"{self._base_url}/embeddings"
        payload = {"model": self._model, "input": texts}
        headers = {"Authorization": f"Bearer {self._api_key}"}

        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]


def embeddings_client_from_settings() -> GatewayEmbeddingsClient:
    settings = get_settings()
    return GatewayEmbeddingsClient(
        base_url=settings.ai_gateway_base_url,
        api_key=settings.ai_gateway_api_key,
        model=settings.embedding_model,
    )
