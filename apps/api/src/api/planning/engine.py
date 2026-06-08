from typing import Protocol

from pydantic import ValidationError

from api.engines.protocols import Document
from api.planning.schema import (
    PlanDraft,
    PlanMeta,
    ProductionPlan,
    Retrieval,
    Voice,
)


class PlannerLLM(Protocol):
    async def complete_json(self, system: str, user: str) -> str: ...


class Planner(Protocol):
    async def plan(self, document: Document, source_ids: list[str]) -> ProductionPlan: ...


class PlanningError(RuntimeError):
    pass


PLANNER_SYSTEM_PROMPT = (
    "You are Sikto's lesson planner. Given source material, produce a single "
    'microlearning lesson as STRICT JSON with exactly two top-level keys: "lesson" '
    'and "segments". '
    '"lesson" has: title (string), summary (string), difficulty (one of "intro", '
    '"intermediate", "advanced"), key_points (3-5 strings), and quiz (2-3 items, each '
    "with question, answer, explanation, and optional choices). "
    '"segments" is an ordered list; each item has id (string), order (int), narration '
    "(text to be spoken), caption (short on-screen text), and visual_type (one of "
    '"title", "bullet", "talking-point", "equation", "diagram", "code"). '
    "Output ONLY the JSON object: no prose, no code fences."
)

REPAIR_SUFFIX = (
    "\n\nYour previous response was not valid. Return ONLY a valid JSON object with the "
    'exact "lesson" and "segments" structure described above. No code fences, no prose.'
)


class PlanningEngine:
    """Turns a source Document into a typed ProductionPlan via an injected LLM."""

    def __init__(
        self,
        llm: PlannerLLM,
        *,
        voice: Voice,
        retrieval: Retrieval,
        planner_model: str,
        embedding_model: str,
        tts_model: str,
        engine_version: str,
    ) -> None:
        self._llm = llm
        self._voice = voice
        self._retrieval = retrieval
        self._planner_model = planner_model
        self._embedding_model = embedding_model
        self._tts_model = tts_model
        self._engine_version = engine_version

    async def plan(self, document: Document, source_ids: list[str]) -> ProductionPlan:
        base_user = _build_user_prompt(document)
        last_error: Exception | None = None

        for attempt in range(2):
            user = base_user if attempt == 0 else base_user + REPAIR_SUFFIX
            raw = await self._llm.complete_json(PLANNER_SYSTEM_PROMPT, user)
            try:
                draft = PlanDraft.model_validate_json(_strip_fences(raw))
            except ValidationError as exc:
                last_error = exc
                continue
            return self._assemble(draft, source_ids)

        raise PlanningError("planner did not return a valid plan") from last_error

    def _assemble(self, draft: PlanDraft, source_ids: list[str]) -> ProductionPlan:
        return ProductionPlan(
            lesson=draft.lesson,
            segments=draft.segments,
            voice=self._voice,
            retrieval=self._retrieval,
            meta=PlanMeta(
                source_ids=source_ids,
                planner_model=self._planner_model,
                embedding_model=self._embedding_model,
                tts_model=self._tts_model,
                engine_version=self._engine_version,
            ),
        )


def _build_user_prompt(document: Document) -> str:
    title = document.title or "(untitled)"
    return f"Source title: {title}\n\nSource content:\n{document.text}"


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
