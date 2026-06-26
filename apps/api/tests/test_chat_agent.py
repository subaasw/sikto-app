"""Chat agent failure handling: 429 detection and graceful (visible) errors."""

import pytest

from api.chat import agent
from api.chat.stream import ChatMessage


class _Err(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"status {status}")
        self.status_code = status


def test_is_rate_limit_by_status():
    assert agent._is_rate_limit(_Err(429))
    assert not agent._is_rate_limit(_Err(500))


def test_is_rate_limit_by_name():
    class RateLimitError(Exception):
        pass

    assert agent._is_rate_limit(RateLimitError())
    assert not agent._is_rate_limit(ValueError("nope"))


@pytest.mark.asyncio
async def test_no_provider_yields_visible_message(monkeypatch):
    # No configured provider must not die silently mid-stream — it must yield text.
    monkeypatch.setattr(agent, "agent_llm_chain", lambda _s: [])
    chunks = [c async for c in agent.stream_agent_chat([ChatMessage(role="user", content="hi")], None)]
    assert chunks and "configured" in "".join(chunks).lower()
