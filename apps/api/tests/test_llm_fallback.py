"""The brain's provider fallback: try the primary (e.g. NVIDIA), drop to the
next (DeepSeek) on any error, raise only when all providers fail."""

import pytest
from pydantic import BaseModel

from api.agent_engine.llm import BrainError, FallbackStructuredLLM


class Out(BaseModel):
    ok: bool


class _Boom:
    async def generate(self, system: str, user: str, schema: type[Out]) -> Out:
        raise RuntimeError("provider down")


class _Good:
    def __init__(self, value: bool) -> None:
        self.value = value

    async def generate(self, system: str, user: str, schema: type[Out]) -> Out:
        return schema(ok=self.value)


async def test_falls_back_to_next_provider_on_error():
    llm = FallbackStructuredLLM([_Boom(), _Good(True)])
    assert (await llm.generate("s", "u", Out)).ok is True


async def test_uses_primary_when_it_succeeds():
    llm = FallbackStructuredLLM([_Good(True), _Good(False)])
    assert (await llm.generate("s", "u", Out)).ok is True  # never reaches the second


async def test_raises_when_all_providers_fail():
    llm = FallbackStructuredLLM([_Boom(), _Boom()])
    with pytest.raises(BrainError):
        await llm.generate("s", "u", Out)


def test_requires_at_least_one_provider():
    with pytest.raises(BrainError):
        FallbackStructuredLLM([])
