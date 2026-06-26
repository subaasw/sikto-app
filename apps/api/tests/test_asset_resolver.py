"""Asset resolver: keyword extraction, illustration-first, icon fallback, reuse."""

from api.media import resolver
from api.media.providers import MediaResult


class _Asset:
    def __init__(self, url: str) -> None:
        self.url = url
        self.storage_key = None


def _ill(name: str) -> MediaResult:
    url = f"https://api.iconify.design/noto/{name}.svg"
    return MediaResult(name, url, url, "iconify-color", "illustration")


def _icon(name: str) -> MediaResult:
    url = f"https://api.iconify.design/mdi/{name}.svg"
    return MediaResult(name, url, url, "iconify", "icon")


def _photo(title: str) -> MediaResult:
    url = f"https://openverse/{title.replace(' ', '-')}.jpg"
    return MediaResult(title, url, url, "openverse", "image")


def _patch(monkeypatch, *, uploads=None, illustrations=None, icons=None, images=None):
    async def fake_media(session, *, tags, kind=None, limit=1):
        return uploads or []

    async def fake_ill(query, k):
        return illustrations or []

    async def fake_icons(query, k):
        return icons or []

    async def fake_images(query, k):
        return images or []

    monkeypatch.setattr(resolver, "search_media_assets", fake_media)
    monkeypatch.setattr(resolver, "search_illustrations", fake_ill)
    monkeypatch.setattr(resolver, "search_icons", fake_icons)
    monkeypatch.setattr(resolver, "search_images", fake_images)


def test_keywords_strip_stopwords():
    assert resolver._keywords("How the brain learns things") == ["brain", "learns", "things"]


def test_recolor_icon():
    assert resolver._recolor_icon("https://x/a.svg", "#84cc16") == "https://x/a.svg?color=%2384cc16"
    assert resolver._recolor_icon("https://x/a.svg", None) == "https://x/a.svg"


def test_relevance_rejects_fuzzy_mismatches():
    # The whole point of "no mistakes": a router is not a planet.
    assert not resolver._relevant("wifi router", ["outer", "planets", "gas", "giants"])
    assert not resolver._relevant("japanese symbol for beginner", ["inner", "rocky", "planets"])
    # Equal or shared-stem (plural) passes.
    assert resolver._relevant("earth 1", ["earth", "supports", "life"])
    assert resolver._relevant("ringed planet", ["planets", "gas"])  # planet ~ planets


async def test_irrelevant_results_are_skipped(monkeypatch):
    # Search returns only an irrelevant match → resolver yields nothing, not junk.
    _patch(monkeypatch, illustrations=[_ill("wifi-router")], icons=[_icon("wifi-router")])
    assert await resolver.resolve_asset(None, "gas giants", color=None) is None


async def test_illustration_is_preferred_and_not_recolored(monkeypatch):
    _patch(monkeypatch, illustrations=[_ill("brain")], icons=[_icon("brain")])
    got = await resolver.resolve_asset(None, "the brain", color="#84cc16")
    assert got is not None and got.kind == "illustration"
    assert "color=" not in got.url  # full-colour illustration is never tinted


async def test_uploads_win_over_everything(monkeypatch):
    _patch(monkeypatch, uploads=[_Asset("https://uploads/mine.png")], illustrations=[_ill("x")])
    got = await resolver.resolve_asset(object(), "neural networks", color="#fff")
    assert got is not None and got.kind == "upload"


async def test_icon_fallback_when_no_illustration(monkeypatch):
    _patch(monkeypatch, illustrations=[], icons=[_icon("brain")])
    got = await resolver.resolve_asset(None, "the brain works", color="#84cc16")
    assert got is not None and got.kind == "icon" and "color=%2384cc16" in got.url


async def test_none_when_nothing_matches(monkeypatch):
    _patch(monkeypatch)
    assert await resolver.resolve_asset(None, "the of to", color=None) is None  # all stopwords
    assert await resolver.resolve_asset(None, "quantum entanglement", color=None) is None


async def test_prefer_photo_returns_relevant_openverse_photo(monkeypatch):
    # Marketing: the top photo whose title shares a word-stem with the query wins.
    _patch(monkeypatch, images=[_photo("a rocket at dawn")], icons=[_icon("rocket")])
    got = await resolver.resolve_asset(None, "rocket launch", prefer_photo=True)
    assert got is not None and got.kind == "photo" and got.source == "openverse"


async def test_prefer_photo_rejects_irrelevant_photo(monkeypatch):
    # A top hit unrelated to the query (noisy Openverse search) is rejected →
    # caller falls back to a typographic poster rather than showing a random image.
    _patch(monkeypatch, images=[_photo("vintage kitchen sink")], illustrations=[], icons=[])
    assert await resolver.resolve_asset(None, "rocket launch", prefer_photo=True) is None


async def test_prefer_photo_never_falls_back_to_mono_icon(monkeypatch):
    # No photo, no illustration → marketing gets nothing rather than a cheap icon.
    _patch(monkeypatch, images=[], illustrations=[], icons=[_icon("rocket")])
    assert await resolver.resolve_asset(None, "rocket launch", prefer_photo=True) is None


async def test_registry_reuses_the_same_asset(monkeypatch):
    calls = {"n": 0}

    async def fake_ill(query, k):
        calls["n"] += 1
        return [_ill("brain")]

    monkeypatch.setattr(resolver, "search_illustrations", fake_ill)
    reg: dict = {}
    a = await resolver.resolve_asset(None, "the brain", registry=reg)  # session None → no uploads
    b = await resolver.resolve_asset(None, "a brain!", registry=reg)  # same keyword → cache hit
    assert a is b and calls["n"] == 1  # resolved once, reused
