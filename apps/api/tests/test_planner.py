import asyncio

from api.scenes.assemble import diagram_scene
from api.scenes.planner import _PlannedLayer, _to_layers, fallback_layers, plan_layers, scene_content
from api.scenes.schema import DiagramDraft, Element, ElementType, Narration, Scene, SceneDocument, SceneKind


def test_plan_layers_preserves_diagram_scenes():
    # Regression: diagram scenes carry drawn cards/arrows in `elements`; plan_layers
    # must NOT wipe them (it once set kind=slide and rebuilt as an icon composition).
    d = DiagramDraft(
        heading="Binary Search", layout="flow", nodes=["lo", "mid", "hi"],
        connectors=["check", "go"], narration="n", caption=None, delivery="neutral",
    )
    doc = SceneDocument(title="t", summary="s", scenes=[diagram_scene(0, d)])
    asyncio.run(plan_layers(None, doc, llm=None))
    out = doc.scenes[0]
    assert out.kind == SceneKind.diagram
    assert [e.type for e in out.elements].count(ElementType.card) == 3  # boxes survived
    assert not out.layers  # not rebuilt as an icon/text layer composition


def test_to_layers_fills_image_and_guarantees_bg_and_headline():
    planned = [
        _PlannedLayer(kind="headline", content="Cells", region="upper", size="lg", depth=5, motion="pop"),
        _PlannedLayer(kind="image", content="", region="center", size="md", depth=1, motion="settle"),
    ]
    out = _to_layers(planned, image_src="cell.svg")
    kinds = [l.kind for l in out]
    assert kinds[0] == "bg-texture"  # prepended (LLM omitted it)
    assert "headline" in kinds and "image" in kinds
    img = next(l for l in out if l.kind == "image")
    assert img.content == "cell.svg"
    head = next(l for l in out if l.kind == "headline")
    assert head.depth == 2  # clamped from 5


def test_to_layers_drops_image_without_asset_and_bails_without_headline():
    planned = [_PlannedLayer(kind="image", content="", region="center", size="md")]
    assert _to_layers(planned, image_src=None) == []  # no headline → caller falls back


def test_fallback_has_headline_and_solved_frames():
    content = {
        "heading": "Cells",
        "bullets": ["nucleus", "membrane"],
        "body": "",
        "latex": "",
        "visual": "a cell",
    }
    layers = fallback_layers(content, image_src="cell.svg")
    kinds = [l.kind for l in layers]
    assert "headline" in kinds and "image" in kinds
    assert all(l.frame is not None for l in layers)  # already solved
    img = next(l for l in layers if l.kind == "image")
    assert img.content == "cell.svg"


def test_fallback_without_image_drops_image_layer():
    content = {"heading": "X", "bullets": [], "body": "", "latex": "", "visual": ""}
    layers = fallback_layers(content, image_src=None)
    assert all(l.kind != "image" for l in layers)


def test_scene_content_reads_elements():
    s = Scene(
        id="s0",
        narration=Narration(text="n"),
        visual_query="a leaf",
        elements=[
            Element(id="h", type=ElementType.heading, text="Leaves"),
            Element(id="b0", type=ElementType.bullets, items=["green"]),
        ],
    )
    c = scene_content(s)
    assert c["heading"] == "Leaves" and c["bullets"] == ["green"] and c["visual"] == "a leaf"
