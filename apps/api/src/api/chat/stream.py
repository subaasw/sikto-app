"""Streaming chat over DeepSeek (or whichever provider AGENT_PROVIDER selects).

A thin async wrapper over the provider's OpenAI-compatible Chat Completions API.
The router turns the yielded token deltas into an HTTP stream; the web client
appends them to the assistant message as they arrive. No retrieval/RAG — this is
a plain assistant grounded only in the conversation.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from openai import AsyncOpenAI

from api.agent.providers import agent_llm_chain
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
    """Yield assistant token deltas, trying NVIDIA first then DeepSeek on error."""
    chain = agent_llm_chain(get_settings())
    if not chain:
        raise RuntimeError("no agent LLM configured: set NVIDIA_API_KEY or DEEPSEEK_API_KEY")

    payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    payload += [{"role": m.role, "content": m.content} for m in messages if m.content.strip()]

    last_exc: Exception | None = None
    for config in chain:
        client = AsyncOpenAI(base_url=config.base_url, api_key=config.api_key)
        try:
            if config.rate_limiter is not None:  # share NVIDIA's throttle
                await config.rate_limiter.aacquire(blocking=True)
            stream = await client.chat.completions.create(
                model=config.model,
                messages=payload,  # type: ignore[arg-type]
                stream=True,
                extra_body=config.extra_body,
            )
            async for chunk in stream:  # type: ignore[union-attr]
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return
        except Exception as exc:  # provider down / rate-limited → try the next
            last_exc = exc
    raise RuntimeError("all chat providers failed") from last_exc
