"""Art-direction pass: the lesson opens with a stick-figure presenter, then
eligible slides gain a graphic; diagrams are left untouched."""

from api.media.resolver import ResolvedAsset
from api.scenes import art_director
from api.scenes.assemble import diagram_scene, slide_scene
from api.scenes.schema import DiagramDraft, ElementType, SceneDocument, SlideDraft
from api.scenes.templates import get_template


def _doc(*scenes) -> SceneDocument:
    return SceneDocument(title="t", summary="s", scenes=list(scenes))


def _seed():
    # A throwaway first slide that absorbs the presenter promotion, so later
    # scenes exercise the hero / icon_grid paths.
    return slide_scene(9, SlideDraft(heading="Intro", bullets=["a"], narration="n"))


async def test_first_slide_becomes_presenter(monkeypatch):
    async def fake_resolve(session, query, *, color=None, registry=None):
        raise AssertionError("the presenter is procedural — no asset lookup")

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    scene = slide_scene(0, SlideDraft(heading="Welcome", bullets=["one", "two"], narration="hi", delivery="excited"))
    out = await art_director.art_direct(None, _doc(scene), get_template("explainer"))
    chars = [e for e in out.scenes[0].elements if e.type == ElementType.character]
    assert len(chars) == 1 and chars[0].style.get("emotion") == "excited"
    for e in out.scenes[0].elements:
        assert e.frame.x + e.frame.w <= 1.0001 and e.frame.y + e.frame.h <= 1.0001


async def test_hero_for_single_feature_image(monkeypatch):
    captured = {}

    async def fake_resolve(session, query, *, color=None, registry=None):
        captured["query"] = query
        return ResolvedAsset(url="https://img/x.svg", kind="icon", source="iconify")

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    draft = SlideDraft(
        heading="Neural nets",
        bullets=["a fairly long descriptive point that exceeds the grid word limit"],
        narration="n",
        visual="brain neurons",
    )
    out = await art_director.art_direct(None, _doc(_seed(), slide_scene(0, draft)), get_template("explainer"))
    images = [e for e in out.scenes[1].elements if e.type == ElementType.image]
    assert len(images) == 1 and images[0].src == "https://img/x.svg"
    assert captured["query"] == "brain neurons"  # the LLM visual query drives hero


async def test_icon_grid_for_short_bullet_list(monkeypatch):
    async def fake_resolve(session, query, *, color=None, registry=None):
        return ResolvedAsset(url=f"https://icon/{query}.svg", kind="icon", source="iconify")

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    draft = SlideDraft(
        heading="Three pillars", bullets=["Speed", "Safety", "Scale"], narration="n", visual="pillars"
    )
    out = await art_director.art_direct(None, _doc(_seed(), slide_scene(0, draft)), get_template("explainer"))
    images = [e for e in out.scenes[1].elements if e.type == ElementType.image]
    assert len(images) == 3  # one icon per bullet


async def test_unresolved_slide_left_untouched(monkeypatch):
    async def fake_resolve(session, query, *, color=None, registry=None):
        return None

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    scene = slide_scene(0, SlideDraft(heading="X", bullets=["a"], narration="n", visual="something"))
    out = await art_director.art_direct(None, _doc(_seed(), scene), get_template("explainer"))
    assert out.scenes[1] is scene


async def test_marketing_slide_becomes_image_poster(monkeypatch):
    captured = {}

    async def fake_resolve(session, query, *, color=None, registry=None, prefer_photo=False):
        captured["query"] = query
        captured["prefer_photo"] = prefer_photo
        return ResolvedAsset(url="https://img/p.jpg", kind="photo", source="openverse")

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    scene = slide_scene(0, SlideDraft(heading="Ship faster", bullets=["a", "b"], narration="n", visual="rocket"))
    out = await art_director.art_direct(None, _doc(scene), get_template("marketing"))
    types = [e.type for e in out.scenes[0].elements]
    assert ElementType.image in types  # dominant visual
    assert ElementType.bullets not in types  # minimal text — no bullet lists
    assert ElementType.character not in types  # marketing skips the presenter
    assert sum(t == ElementType.heading for t in types) == 1  # one headline
    # queries the concrete visual (not the metaphorical headline) as a real photo
    assert captured == {"query": "rocket", "prefer_photo": True}


async def test_marketing_text_poster_when_no_asset(monkeypatch):
    async def fake_resolve(session, query, *, color=None, registry=None):
        return None

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    scene = slide_scene(0, SlideDraft(heading="Big idea", bullets=["a", "b"], narration="n"))
    out = await art_director.art_direct(None, _doc(scene), get_template("marketing"))
    types = [e.type for e in out.scenes[0].elements]
    assert types == [ElementType.heading]  # one bold headline, no bullets, no image


async def test_diagram_scene_is_skipped(monkeypatch):
    async def fake_resolve(session, query, *, color=None, registry=None):
        raise AssertionError("should not resolve for a diagram scene")

    monkeypatch.setattr(art_director, "resolve_asset", fake_resolve)
    scene = diagram_scene(0, DiagramDraft(heading="H", layout="flow", nodes=["a", "b"], narration="n"))
    out = await art_director.art_direct(None, _doc(_seed(), scene), get_template("explainer"))
    assert out.scenes[1] is scene
