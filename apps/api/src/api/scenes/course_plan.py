"""Course planning: break a source into a sequenced set of modules.

For `course`-mode sources the pipeline doesn't build one lesson — it plans a
short curriculum. Each module is later generated into its own lesson (a normal
video job) on demand. Best-effort, like quiz/narration: no model or a thin
source yields a single "whole topic" module rather than failing the job.
"""

import logging

from pydantic import BaseModel, Field

from api.agent_engine.llm import StructuredLLM

logger = logging.getLogger("api.course")

_SYSTEM = (
    "You are a course designer. Break the source material into a sequenced "
    "microlearning COURSE of 3-7 modules that build on each other, from "
    "foundations to more advanced ideas. Each module gets a short title and a "
    "one-to-two sentence summary of what it teaches. Also give the whole course "
    "a title and a one-sentence summary. Use only the material provided."
)

_MIN_CONTENT = 80


class CoursePlanModule(BaseModel):
    title: str
    summary: str = Field(description="1-2 sentences on what this module teaches.")


class CoursePlanDraft(BaseModel):
    title: str
    summary: str
    modules: list[CoursePlanModule] = Field(min_length=1, max_length=8)


def _single_module(title: str, summary: str) -> CoursePlanDraft:
    """Fallback when no model is available or the source is too thin."""
    name = title.strip() or "Full lesson"
    return CoursePlanDraft(
        title=name,
        summary=summary.strip() or f"A lesson on {name}.",
        modules=[CoursePlanModule(title=name, summary="The complete topic in one lesson.")],
    )


async def plan_course(
    text: str, title: str, summary: str, llm: StructuredLLM | None
) -> CoursePlanDraft:
    """Plan a course from source text. Falls back to a single-module course when
    no model is configured, the content is thin, or the model call fails."""
    if llm is None or len(text.strip()) < _MIN_CONTENT:
        return _single_module(title, summary)
    try:
        draft = await llm.generate(_SYSTEM, text, CoursePlanDraft)
    except Exception:
        logger.warning("course planning failed, using a single-module course", exc_info=True)
        return _single_module(title, summary)
    draft.modules = draft.modules[:7]
    return draft


if __name__ == "__main__":
    # ponytail: self-check the fallback (the only branch with logic worth breaking).
    d = _single_module("  ", "")
    assert d.title == "Full lesson" and len(d.modules) == 1
    d2 = _single_module("Neural Nets", "How networks learn.")
    assert d2.title == "Neural Nets" and d2.summary == "How networks learn."
    print("ok")
