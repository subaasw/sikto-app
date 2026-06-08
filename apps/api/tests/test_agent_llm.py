import json

import httpx
import pytest

from api.agent.llm import GatewayToolCallingLLM
from api.agent.types import Message, ToolSpec


async def test_parses_first_tool_call():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "planner-m"
        assert payload["tool_choice"] == "required"
        assert payload["tools"][0]["function"]["name"] == "retrieve"
        message = {
            "tool_calls": [
                {
                    "function": {
                        "name": "retrieve",
                        "arguments": json.dumps({"query": "vectors", "k": 3}),
                    }
                }
            ]
        }
        return httpx.Response(200, json={"choices": [{"message": message}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw")
    llm = GatewayToolCallingLLM(base_url="http://gw", api_key="k", model="planner-m", client=http)
    try:
        call = await llm.next_action(
            [Message("user", "hi")],
            [ToolSpec("retrieve", "search", {"type": "object"})],
        )
    finally:
        await http.aclose()

    assert call.name == "retrieve"
    assert call.arguments == {"query": "vectors", "k": 3}


async def test_raises_when_no_tool_call():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "no tools"}}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw")
    llm = GatewayToolCallingLLM(base_url="http://gw", api_key="k", model="m", client=http)
    try:
        with pytest.raises(ValueError):
            await llm.next_action([Message("user", "hi")], [])
    finally:
        await http.aclose()
