"""Lesson mode: is this a structured *course* or a short *informative video*?

Chosen at creation time (the create screen offers Auto / Course / Video). The
mode steers the brain's outline — how much lesson-planning structure to impose
and how many beats to aim for — but it deliberately does NOT hard-code what to
drop: within a mode the brain still decides per content whether research,
diagrams, or math are warranted. Keeping the two intents cleanly separated
(no "mixed things") is the whole point.
"""

from typing import Literal, get_args

LessonMode = Literal["auto", "course", "video"]
MODES: frozenset[str] = frozenset(get_args(LessonMode))
DEFAULT_MODE: LessonMode = "auto"


# Guidance woven into the outline system prompt.
MODE_GUIDANCE: dict[str, str] = {
    "auto": (
        "First judge the source: a rich, multi-part topic deserves a structured course with "
        "several beats; a single self-contained idea is better as a short informative video "
        "with just a few beats. Shape the outline to whichever it truly is — don't pad a simple "
        "idea into a course, and don't compress a deep topic into a clip."
    ),
    "course": (
        "Treat this as a structured microlearning COURSE: organise the material into clear, "
        "well-sequenced beats that build on each other and cover the topic thoroughly."
    ),
    "video": (
        "Treat this as a short, informative VIDEO, not a course: skip formal lesson-planning "
        "scaffolding. Keep it tight and flowing — a few beats at most, focused on the core idea. "
        "Decide from the content whether any deeper structure (a diagram, an equation) genuinely "
        "helps; if not, plain narrated slides are perfect. Don't manufacture structure."
    ),
}


def mode_guidance(mode: str | None) -> str:
    return MODE_GUIDANCE.get(mode or DEFAULT_MODE, MODE_GUIDANCE[DEFAULT_MODE])


def beat_bounds(mode: str | None) -> tuple[int, int]:
    """(min, max) beats. A video stays short; a course can run longer."""
    return (2, 5) if mode == "video" else (3, 10)
