"""Semantic validation for a SceneDocument (pydantic already covers structure).

Returns a list of human-readable issues; an empty list means the document is
renderable. The brain feeds these issues back to the repair node.
"""

from api.scenes.schema import Element, SceneDocument, SceneKind

_TOL = 1e-6

_REQUIRED_FIELD = {
    "heading": "text",
    "text": "text",
    "code": "text",
    "bullets": "items",
    "latex": "latex",
    "image": "src",
    "shape": "shape",
    "card": "text",
}


def _frame_issues(scene_id: str, el: Element) -> list[str]:
    f = el.frame
    issues = []
    if f.x < 0 or f.y < 0 or f.w <= 0 or f.h <= 0:
        issues.append(f"scene {scene_id}: element {el.id} has an invalid frame")
    if f.x + f.w > 1 + _TOL or f.y + f.h > 1 + _TOL:
        issues.append(f"scene {scene_id}: element {el.id} overflows the canvas")
    return issues


def _content_issues(scene_id: str, el: Element) -> list[str]:
    field = _REQUIRED_FIELD.get(el.type.value)
    if field and getattr(el, field, None) in (None, "", []):
        return [f"scene {scene_id}: {el.type.value} element {el.id} is missing '{field}'"]
    return []


def validate_document(doc: SceneDocument) -> list[str]:
    issues: list[str] = []
    for scene in doc.scenes:
        if not scene.narration.text.strip():
            issues.append(f"scene {scene.id}: narration is empty")

        if scene.kind == SceneKind.manim:
            if not (scene.manim_code or "").strip():
                issues.append(f"scene {scene.id}: manim scene has no code")
            continue

        if not scene.elements:
            issues.append(f"scene {scene.id}: slide has no elements")
        element_ids = {el.id for el in scene.elements}
        for el in scene.elements:
            issues.extend(_frame_issues(scene.id, el))
            issues.extend(_content_issues(scene.id, el))
        for anim in scene.animations:
            if anim.target_id not in element_ids:
                issues.append(
                    f"scene {scene.id}: animation targets unknown element {anim.target_id!r}"
                )
    return issues
