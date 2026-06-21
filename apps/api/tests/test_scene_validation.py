from api.scenes.schema import (
    Animation,
    AnimationType,
    Element,
    ElementType,
    Frame,
    Narration,
    Scene,
    SceneDocument,
    SceneKind,
)
from api.scenes.validation import validate_document


def _slide(**overrides) -> Scene:
    base = dict(
        id="s0",
        narration=Narration(text="hello"),
        elements=[Element(id="s0-h", type=ElementType.heading, text="Title")],
    )
    base.update(overrides)
    return Scene(**base)


def _doc(scene: Scene) -> SceneDocument:
    return SceneDocument(title="t", summary="s", scenes=[scene])


def test_valid_slide_has_no_issues():
    assert validate_document(_doc(_slide())) == []


def test_empty_narration_flagged():
    issues = validate_document(_doc(_slide(narration=Narration(text="  "))))
    assert any("narration is empty" in i for i in issues)


def test_overflowing_frame_flagged():
    el = Element(id="s0-x", type=ElementType.text, text="x", frame=Frame(x=0.8, y=0.0, w=0.5, h=0.1))
    issues = validate_document(_doc(_slide(elements=[el])))
    assert any("overflows" in i for i in issues)


def test_missing_required_field_flagged():
    el = Element(id="s0-b", type=ElementType.bullets, items=[])
    issues = validate_document(_doc(_slide(elements=[el])))
    assert any("missing 'items'" in i for i in issues)


def test_dangling_animation_target_flagged():
    issues = validate_document(
        _doc(_slide(animations=[Animation(target_id="nope", type=AnimationType.fade_in)]))
    )
    assert any("unknown element" in i for i in issues)


def test_manim_scene_requires_code():
    scene = Scene(id="s0", kind=SceneKind.manim, narration=Narration(text="x"), manim_code="  ")
    assert any("no code" in i for i in validate_document(_doc(scene)))
