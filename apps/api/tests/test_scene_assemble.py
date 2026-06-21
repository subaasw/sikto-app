"""Layout invariants: assembled element frames stay on-canvas, and slide content
respects the caption-safe band (so captions never overlap it)."""

from api.scenes import assemble
from api.scenes.assemble import diagram_scene, divide_scenes, slide_scene
from api.scenes.schema import DiagramDraft, SlideDraft

EPS = 1e-6


def _within_canvas(el) -> bool:
    f = el.frame
    return (
        f.x >= -EPS and f.y >= -EPS and f.x + f.w <= 1 + EPS and f.y + f.h <= 1 + EPS
    )


def test_slide_frames_stay_in_caption_safe_band():
    draft = SlideDraft(
        heading="A very long heading that goes on and on about the subject matter at hand here",
        bullets=[f"This is bullet number {i} with a fair amount of explanatory text" for i in range(6)],
        narration="Some narration to split across the parts.",
    )
    scenes = divide_scenes([slide_scene(0, draft)])
    bottom = assemble._BAND_BOTTOM_CAPTION
    assert len(scenes) >= 2  # 6 bullets must split
    for scene in scenes:
        for el in scene.elements:
            assert _within_canvas(el), el
            assert el.frame.y >= assemble._BAND_TOP - EPS, el
            assert el.frame.y + el.frame.h <= bottom + EPS, el


def test_title_slide_within_bounds():
    scene = slide_scene(1, SlideDraft(heading="Just a title", narration="n"))
    assert all(_within_canvas(el) for el in scene.elements)


def test_visual_intent_carries_to_scene():
    scene = slide_scene(
        0, SlideDraft(heading="H", bullets=["a"], narration="n", visual="rocket launch", visual_kind="illustration")
    )
    assert scene.visual_query == "rocket launch" and scene.visual_kind == "illustration"
    # No visual → text-only intent preserved.
    plain = slide_scene(0, SlideDraft(heading="H", bullets=["a"], narration="n"))
    assert plain.visual_query is None


def test_diagram_frames_within_canvas():
    for layout in ("flow", "stack", "compare"):
        draft = DiagramDraft(
            heading="H", layout=layout, nodes=["alpha", "beta", "gamma"], narration="n"
        )
        scene = diagram_scene(2, draft)
        assert all(_within_canvas(el) for el in scene.elements), layout


def test_flow_connectors_draw_in():
    draft = DiagramDraft(heading="H", layout="flow", nodes=["a", "b", "c"], narration="n")
    scene = diagram_scene(3, draft)
    arrows = {e.id for e in scene.elements if e.shape == "arrow"}
    assert arrows  # a flow has connectors
    anim_for = {a.target_id: a.type for a in scene.animations}
    assert all(anim_for[aid] == "draw" for aid in arrows)
    # Non-arrow elements (cards/heading) do not use the draw animation.
    non_arrows = {e.id for e in scene.elements if e.shape != "arrow"}
    assert all(anim_for[eid] != "draw" for eid in non_arrows)
