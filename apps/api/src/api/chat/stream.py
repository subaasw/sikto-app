"""Streaming chat over DeepSeek (or whichever provider AGENT_PROVIDER selects).

A thin async wrapper over the provider's OpenAI-compatible Chat Completions API.
The router turns the yielded token deltas into an HTTP stream; the web client
appends them to the assistant message as they arrive. No retrieval/RAG — this is
a plain assistant grounded only in the conversation.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from openai import AsyncOpenAI

from api.agent.providers import resolve_agent_llm
from api.config import get_settings

SYSTEM_PROMPT = (
    "You are Sikto, a concise and friendly assistant for a microlearning and video "
    "automation platform. Answer clearly and helpfully."
)


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


async def stream_chat(messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
    """Yield assistant token deltas for the given conversation."""
    config = resolve_agent_llm(get_settings())
    client = AsyncOpenAI(base_url=config.base_url, api_key=config.api_key)

    payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    payload += [{"role": m.role, "content": m.content} for m in messages if m.content.strip()]

    stream = await client.chat.completions.create(
        model=config.model,
        messages=payload,  # type: ignore[arg-type]
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
