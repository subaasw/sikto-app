from typing import TypedDict

from api.scenes.schema import LessonOutline, SceneDocument


class BrainState(TypedDict):
    source_title: str
    source_text: str
    research: str
    outline: LessonOutline | None
    document: SceneDocument | None
    issues: list[str]
    repairs: int
