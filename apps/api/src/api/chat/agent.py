"""Agentic chat: a tool-using assistant that can actually act on the platform.

Unlike the plain ``stream_chat``, this runs a bounded tool-calling loop over the
OpenAI-compatible provider so the model can: create a lesson/video from a source,
list the user's lessons, check a job's status, and ground answers in the user's
own material (a keyword search over stored sources + lessons — no embedding index
needed; upgrade to vector retrieval if the corpus grows). The final text reply is
streamed back; tool decisions are resolved server-side first.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agent.catalog import lead_with_choice
from api.agent.model_switch import note_failure
from api.agent.providers import agent_llm_chain, provider_label
from api.chat.stream import ChatMessage
from api.config import get_settings
from api.jobs.repository import create_source_and_job, get_job, list_lessons
from api.lesson_mode import DEFAULT_MODE, MODES
from api.logger import short_error
from api.models import Lesson, Source
from api.scenes.templates import DEFAULT_TEMPLATE, TEMPLATES
from api.voices import DEFAULT_VOICE

logger = logging.getLogger("api.chat.agent")

_MAX_STEPS = 5  # tool rounds before we force a plain answer (guards runaway loops)
_RETRY_429 = 3  # free-tier 429s are usually transient — back off and retry before failing over


def _is_rate_limit(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    return status == 429 or "RateLimit" in type(exc).__name__


SYSTEM_PROMPT = (
    "You are Sikto, an assistant for a microlearning and video-automation platform. "
    "You can ACT, not just chat — use the tools when they help:\n"
    "- create_lesson: turn a URL, YouTube link, or pasted text into a narrated lesson/video. "
    "When you create one, give the user its link as /lessons/<job_id>.\n"
    "- list_lessons: see the user's recent lessons.\n"
    "- lesson_status: check how a lesson's job is progressing.\n"
    "- search_material: search the user's own sources and lessons. ALWAYS call this before "
    "answering a question about their material, and cite what you found.\n"
    "Be concise and friendly. If a request is ambiguous, ask one short clarifying question."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_lesson",
            "description": "Create a narrated microlearning lesson/video from a source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "A URL, a YouTube link, or pasted text to build the lesson from.",
                    },
                    "template": {"type": "string", "enum": list(TEMPLATES)},
                    "mode": {"type": "string", "enum": list(MODES)},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lessons",
            "description": "List the user's most recent lessons.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lesson_status",
            "description": "Get the status of a lesson's generation job by its job id.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_material",
            "description": "Keyword-search the user's sources and lessons for relevant passages.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


async def _create_lesson(session: AsyncSession, args: dict) -> dict:
    text = str(args.get("input") or "").strip()
    if not text:
        return {"error": "no input provided"}
    template = args.get("template") if args.get("template") in TEMPLATES else DEFAULT_TEMPLATE
    mode = args.get("mode") if args.get("mode") in MODES else DEFAULT_MODE
    job = await create_source_and_job(
        session,
        source_type="mixed",
        raw_input=text,
        template=template,
        mode=mode,
        voice=DEFAULT_VOICE,
    )
    return {"job_id": str(job.id), "url": f"/lessons/{job.id}", "status": "queued"}


async def _list_lessons(session: AsyncSession, _args: dict) -> list[dict]:
    lessons = await list_lessons(session, limit=10)
    return [
        {"job_id": str(les.job_id), "title": les.title, "has_video": bool(les.video_url)}
        for les in lessons
    ]


async def _lesson_status(session: AsyncSession, args: dict) -> dict:
    import uuid

    try:
        job = await get_job(session, uuid.UUID(str(args.get("job_id"))))
    except (ValueError, TypeError):
        return {"error": "invalid job_id"}
    if job is None:
        return {"error": "job not found"}
    return {"status": job.status, "step": job.step, "error": job.error}


async def _search_material(session: AsyncSession, args: dict) -> list[dict]:
    query = str(args.get("query") or "").strip()
    if not query:
        return []
    like = f"%{query}%"
    src = (
        await session.execute(
            select(Source.title, Source.text)
            .where(or_(Source.title.ilike(like), Source.text.ilike(like)))
            .limit(5)
        )
    ).all()
    les = (
        await session.execute(
            select(Lesson.title, Lesson.summary)
            .where(or_(Lesson.title.ilike(like), Lesson.summary.ilike(like)))
            .limit(5)
        )
    ).all()
    out = [{"title": t, "content": (txt or "")[:400]} for t, txt in src if txt]
    out += [{"title": t, "content": s} for t, s in les]
    return out


_DISPATCH = {
    "create_lesson": _create_lesson,
    "list_lessons": _list_lessons,
    "lesson_status": _lesson_status,
    "search_material": _search_material,
}


async def _run_tool(name: str, raw_args: str, session: AsyncSession) -> str:
    fn = _DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool {name}"})
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        args = {}
    try:
        return json.dumps(await fn(session, args), default=str)
    except Exception as exc:
        logger.warning("tool %s failed", name, exc_info=True)
        return json.dumps({"error": str(exc)})


async def stream_agent_chat(
    messages: Sequence[ChatMessage], session: AsyncSession, model: str | None = None
) -> AsyncIterator[str]:
    """Run the tool loop and stream the assistant's final text reply. A validated
    `model` choice leads the chain; the rest stay as fallbacks."""
    settings = get_settings()
    chain = lead_with_choice(agent_llm_chain(settings), settings, model)
    if not chain:
        # Surface config errors in the reply itself — the StreamingResponse has
        # already sent 200, so a raise here would just look like an empty answer.
        yield "⚠️ No chat model is configured. Set NVIDIA_API_KEY or DEEPSEEK_API_KEY and restart the API."
        return

    base = [{"role": "system", "content": SYSTEM_PROMPT}]
    base += [{"role": m.role, "content": m.content} for m in messages if m.content.strip()]

    last_exc: Exception | None = None
    for config in chain:
        client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=settings.llm_timeout_seconds,
            # The SDK retries timeouts twice by default, turning a 30s cap into ~90s.
            # We do our own retry + model fallback, so disable the SDK's.
            max_retries=0,
        )
        convo = list(base)
        try:
            for _ in range(_MAX_STEPS):
                resp = None
                for attempt in range(_RETRY_429):
                    if config.rate_limiter is not None:
                        await config.rate_limiter.aacquire(blocking=True)
                    try:
                        resp = await client.chat.completions.create(
                            model=config.model,
                            messages=convo,
                            tools=TOOLS,  # type: ignore[arg-type]
                            stream=False,
                            extra_body=config.extra_body,
                        )
                        break
                    except Exception as exc:
                        if _is_rate_limit(exc) and attempt < _RETRY_429 - 1:
                            await asyncio.sleep(2**attempt)  # 1s, 2s before retrying
                            continue
                        raise
                msg = resp.choices[0].message
                calls = msg.tool_calls or []
                if not calls:
                    if msg.content:
                        yield msg.content
                    return
                convo.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {
                                    "name": c.function.name,
                                    "arguments": c.function.arguments,
                                },
                            }
                            for c in calls
                        ],
                    }
                )
                for c in calls:
                    result = await _run_tool(c.function.name, c.function.arguments, session)
                    convo.append({"role": "tool", "tool_call_id": c.id, "content": result})
            yield "I've taken a few steps but couldn't wrap up — could you rephrase what you need?"
            return
        except Exception as exc:  # provider down / no tool support → try the next
            logger.warning(
                "agent chat model %s (%s) failed",
                config.model,
                provider_label(config.base_url),
                exc_info=True,
            )
            note_failure(config.model)  # cooldown so the next request skips it
            last_exc = exc
    # Every provider failed. Don't die silently mid-stream — tell the user what
    # broke (the full traceback is in the API logs).
    detail = short_error(last_exc) if last_exc else "unknown error"
    yield f"⚠️ Sorry, the assistant is unavailable right now ({detail}). Please try again in a moment."
