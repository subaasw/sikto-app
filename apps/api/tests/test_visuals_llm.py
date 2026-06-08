import json

import httpx

from api.visuals.llm import GatewayChatLLM


async def test_returns_message_content():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "m"
        assert payload["messages"][0]["role"] == "system"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "class MainScene: pass"}}]}
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw")
    llm = GatewayChatLLM(base_url="http://gw", api_key="k", model="m", client=http)
    try:
        out = await llm.complete("system prompt", "user prompt")
    finally:
        await http.aclose()

    assert out == "class MainScene: pass"
