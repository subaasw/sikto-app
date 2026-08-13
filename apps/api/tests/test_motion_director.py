import asyncio

import pytest
from pydantic import ValidationError

from api.scenes.motion import fallback_motion, plan_motion
from api.scenes.schema import (
    Element,
    ElementType,
    MotionCamera,
    MotionPlane,
    MotionScene,
    Narration,
    Scene,
    SceneDocument,
    SceneKind,
)


def _slide(sid: str, heading: str, bullet: str | None = None) -> Scene:
    els = [Element(id=f"{sid}h", type=ElementType.heading, text=heading)]
    if bullet:
        els.append(Element(id=f"{sid}b", type=ElementType.bullets, items=[bullet]))
    return Scene(id=sid, kind=SceneKind.slide, narration=Narration(text="n"), elements=els)


def test_fallback_assigns_distinct_beats_and_never_empty():
    first = fallback_motion({"heading": "Meet sikto", "bullets": [], "body": ""}, 0, 3)
    mid = fallback_motion({"heading": "Save 5 hours", "bullets": ["less busywork"], "body": ""}, 1, 3)
    last = fallback_motion({"heading": "Try it", "bullets": ["Start free"], "body": ""}, 2, 3)
    assert first.beat == "hook" and last.beat == "cta"
    assert mid.beat == "stat"  # heading has a digit
    assert last.accent == "confetti" and any(p.role == "cta" for p in last.props)
    # every scene opens with a beat chip and carries a title, capped at three lines
    for m in (first, mid, last):
        assert m.props[0].role == "chip" and m.props[0].content
        assert any(p.role == "title" and p.content for p in m.props)
        assert len(m.props) <= 3
    # no line repeats another (chip/title/sub are all distinct text)
    for m in (first, mid, last):
        texts = [p.content.strip().lower() for p in m.props]
        assert len(texts) == len(set(texts))


def test_plan_motion_converts_slides_and_passes_through_manim():
    doc = SceneDocument(
        title="t",
        summary="s",
        scenes=[
            _slide("s0", "Meet sikto"),
            _slide("s1", "Ship faster", "automate the boring parts"),
            Scene(id="m0", kind=SceneKind.manim, narration=Narration(text="n"), manim_code="x"),
            _slide("s2", "Get started", "Sign up today"),
        ],
    )
    asyncio.run(plan_motion(doc))
    kinds = [s.kind for s in doc.scenes]
    assert kinds == [SceneKind.motion, SceneKind.motion, SceneKind.manim, SceneKind.motion]
    motion_scenes = [s for s in doc.scenes if s.kind == SceneKind.motion]
    assert all(s.motion and s.motion.props and not s.elements for s in motion_scenes)
    assert motion_scenes[0].motion.beat == "hook"  # first slide
    assert motion_scenes[-1].motion.beat == "cta"  # last slide


def test_motion_scene_v2_defaults_and_clamps():
    m = MotionScene(beat="hook", mood="bold", props=[])
    # style defaults are valid enum members so an undirected scene still renders
    assert m.palette == "midnight" and m.text_style == "fade_up"
    assert m.background == "mesh" and m.outro == "none"
    assert m.camera.drift == "right" and m.camera.zoom == "in" and m.camera.tilt_deg == 0.0
    assert m.planes == []
    # tilt is clamped to +/-2 degrees; planes capped at 2
    with pytest.raises(ValidationError):
        MotionCamera(tilt_deg=3.5)
    with pytest.raises(ValidationError):
        MotionScene(beat="hook", mood="bold", props=[], planes=[MotionPlane()] * 3)


def test_fallback_fills_v2_style_deterministically():
    a = fallback_motion({"heading": "Meet sikto", "bullets": [], "body": ""}, 0, 3)
    b = fallback_motion({"heading": "Meet sikto", "bullets": [], "body": ""}, 0, 3)
    assert a == b  # deterministic
    mid = fallback_motion({"heading": "Ship faster", "bullets": ["less busywork"], "body": ""}, 1, 3)
    # camera varies by index and chips are sentence case (no ALL-CAPS)
    assert a.camera != mid.camera
    assert not a.props[0].content.isupper()
    # closing scene holds (no outro), inner scenes exit
    last = fallback_motion({"heading": "Try it", "bullets": ["Start free"], "body": ""}, 2, 3)
    assert last.outro == "none" and mid.outro != "none"


class _FakeLLM:
    async def generate(self, system, user, model):
        from api.scenes.motion import _MotionDirectionList

        assert model is _MotionDirectionList
        return _MotionDirectionList.model_validate(
            {
                "scenes": [
                    {
                        "beat": "hook",
                        "mood": "bold",
                        "palette": "royal",
                        "text_style": "spring_in",
                        "background": "grid",
                        "outro": "push",
                        "camera": {"drift": "left", "zoom": "out", "tilt_deg": 1.5},
                        "image_query": "team collaborating",
                        "image_depth": "near",
                        "props": [
                            {"content": "Why it matters", "role": "chip", "emphasis": 1, "entrance": "rise"},
                            {"content": "Meet sikto", "role": "title", "emphasis": 2, "entrance": "pop"},
                        ],
                    }
                ]
            }
        )


def test_plan_motion_applies_llm_direction_and_falls_back_for_missing_scenes():
    doc = SceneDocument(
        title="t",
        summary="s",
        scenes=[_slide("s0", "Meet sikto"), _slide("s1", "Ship faster", "less busywork")],
    )
    asyncio.run(plan_motion(doc, llm=_FakeLLM()))
    m0, m1 = doc.scenes[0].motion, doc.scenes[1].motion
    # scene 0 takes the LLM's direction, including the image plane from image_query
    assert m0.palette == "royal" and m0.camera.drift == "left"
    assert m0.planes and m0.planes[0].query == "team collaborating" and m0.planes[0].depth == "near"
    # the LLM only directed one scene; scene 1 must still be filled by fallback
    assert m1 is not None and m1.props


def test_plan_motion_survives_llm_failure():
    class _Boom:
        async def generate(self, *a):
            raise RuntimeError("no model")

    doc = SceneDocument(title="t", summary="s", scenes=[_slide("s0", "Meet sikto")])
    asyncio.run(plan_motion(doc, llm=_Boom()))
    assert doc.scenes[0].motion is not None  # fallback ran
