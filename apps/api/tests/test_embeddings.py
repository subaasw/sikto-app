import json

import httpx
import pytest

from api.knowledge.embeddings import GatewayEmbeddingsClient


def _client_with_handler(handler) -> tuple[GatewayEmbeddingsClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw")
    client = GatewayEmbeddingsClient(
        base_url="http://gw", api_key="secret", model="test-embed", client=http
    )
    return client, http


async def test_embed_returns_vectors_in_index_order():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "test-embed"
        assert request.headers["Authorization"] == "Bearer secret"
        n = len(payload["input"])
        # return rows out of order to prove the client sorts by index
        data = [{"index": i, "embedding": [float(i)] * 3} for i in reversed(range(n))]
        return httpx.Response(200, json={"data": data})

    client, http = _client_with_handler(handler)
    try:
        vectors = await client.embed(["a", "b"])
    finally:
        await http.aclose()

    assert vectors == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]


async def test_embed_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client, http = _client_with_handler(handler)
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.embed(["a"])
    finally:
        await http.aclose()
