"""Comprehension quiz generation for a finished lesson.

The live scene pipeline builds a SceneDocument (no quiz). This turns that
document's narration into a short multiple-choice quiz via the brain LLM.
Best-effort, exactly like narration/render: a missing model or a thin source
yields no quiz rather than failing the lesson.
"""

import logging

from pydantic import BaseModel

from api.agent_engine.llm import StructuredLLM
from api.planning.schema import QuizItem
from api.scenes.schema import SceneDocument

logger = logging.getLogger("api.quiz")

_SYSTEM = (
    "You write a short comprehension quiz for a lesson. Produce 3-5 multiple-choice "
    "questions that check understanding of the key ideas, not trivia or exact wording. "
    "Each question has exactly 4 plausible choices, one correct `answer` that matches "
    "one choice verbatim, and a one-sentence `explanation`. Use only the lesson content "
    "provided."
)

_MIN_CONTENT = 80  # below this there's nothing meaningful to quiz on


class _QuizDraft(BaseModel):
    items: list[QuizItem]


def _lesson_text(document: SceneDocument) -> str:
    parts = [document.title or "", document.summary or ""]
    parts += [s.narration.text for s in document.scenes if s.narration.text]
    return "\n\n".join(p.strip() for p in parts if p.strip())


async def build_quiz(document: SceneDocument, llm: StructuredLLM | None) -> list[dict]:
    """Generate a quiz from a lesson's content. Returns [] when no model is
    configured, the content is too thin, or the model call fails."""
    if llm is None:
        return []
    content = _lesson_text(document)
    if len(content) < _MIN_CONTENT:
        return []
    try:
        draft = await llm.generate(_SYSTEM, content, _QuizDraft)
    except Exception:
        logger.warning("quiz generation failed, continuing without quiz", exc_info=True)
        return []
    return [item.model_dump() for item in draft.items[:5]]
