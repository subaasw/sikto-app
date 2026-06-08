import pytest

from api.ingestion.loaders import (
    CrawlResult,
    TextLoader,
    YouTubeLoader,
    is_url,
    is_youtube_url,
    youtube_video_id,
)


async def test_text_loader_passes_through_pasted_text():
    doc = await TextLoader().load("just some pasted notes")
    assert doc.type == "text"
    assert doc.text == "just some pasted notes"
    assert doc.title is None


async def test_text_loader_uses_injected_crawler_for_urls():
    async def fake_crawl(url: str) -> CrawlResult:
        assert url == "https://example.com/article"
        return CrawlResult(text="# Heading\n\nHello world", title="Heading")

    doc = await TextLoader(crawl=fake_crawl).load("https://example.com/article")
    assert doc.type == "url"
    assert doc.title == "Heading"
    assert "Hello world" in doc.text
    assert doc.meta["url"] == "https://example.com/article"


async def test_youtube_loader_uses_injected_transcript():
    async def fake_transcript(video_id: str) -> str:
        assert video_id == "abc123"
        return "first line second line"

    doc = await YouTubeLoader(fetch_transcript=fake_transcript).load(
        "https://www.youtube.com/watch?v=abc123"
    )
    assert doc.type == "youtube"
    assert doc.text == "first line second line"
    assert doc.meta["video_id"] == "abc123"


def test_youtube_video_id_parsing():
    assert youtube_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert youtube_video_id("https://youtu.be/xyz789") == "xyz789"
    assert youtube_video_id("https://www.youtube.com/watch?v=abc123&t=42s") == "abc123"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://example.com", True),
        ("http://example.com/page", True),
        ("just text", False),
        ("ftp://example.com", False),
    ],
)
def test_is_url(value, expected):
    assert is_url(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc", True),
        ("https://youtu.be/abc", True),
        ("https://example.com", False),
        ("plain text", False),
    ],
)
def test_is_youtube_url(value, expected):
    assert is_youtube_url(value) is expected
