"""thesvg.org brand-logo provider: client-side filtering over the cached manifest."""

from api.media import providers

_MANIFEST = [
    {"slug": "openai", "title": "OpenAI", "aliases": ["gpt"], "variants": ["default", "white"], "license": "MIT"},
    {"slug": "github", "title": "GitHub", "aliases": []},
]


async def test_brand_search_matches_slug_title_or_alias(monkeypatch):
    monkeypatch.setattr(providers, "_brand_icons", _MANIFEST)

    by_alias = await providers.search_brand_icons("gpt", 5)
    assert len(by_alias) == 1
    hit = by_alias[0]
    assert hit.kind == "logo" and hit.source == "thesvg" and hit.license == "MIT"
    assert hit.url == "https://cdn.jsdelivr.net/gh/glincker/thesvg@main/public/icons/openai/default.svg"

    assert len(await providers.search_brand_icons("hub", 5)) == 1  # 'github' contains 'hub'
    assert await providers.search_brand_icons("nonsuch", 5) == []
    assert await providers.search_brand_icons("", 5) == []


async def test_brand_variant_prefers_default_then_first():
    assert providers._brand_variant({"variants": ["white", "dark"]}) == "white"
    assert providers._brand_variant({"variants": {"default": 1, "mono": 2}}) == "default"
    assert providers._brand_variant({}) == "default"
