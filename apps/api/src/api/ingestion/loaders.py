import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from api.engines.protocols import Document


@dataclass
class CrawlResult:
    text: str
    title: str | None


Crawler = Callable[[str], Awaitable[CrawlResult]]
TranscriptFetcher = Callable[[str], Awaitable[str]]


def is_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_youtube_url(value: str) -> bool:
    host = (urlparse(value.strip()).hostname or "").lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def youtube_video_id(value: str) -> str:
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        return parsed.path.lstrip("/")
    if "youtube.com" in host:
        ids = parse_qs(parsed.query).get("v")
        if ids:
            return ids[0]
    return value.strip()


class TextLoader:
    """Loads pasted text directly, or scrapes an article URL via Crawl4AI."""

    def __init__(self, crawl: Crawler | None = None) -> None:
        self._crawl = crawl or _crawl4ai_fetch

    async def load(self, raw_input: str) -> Document:
        stripped = raw_input.strip()
        if is_url(stripped):
            result = await self._crawl(stripped)
            return Document(
                text=result.text, title=result.title, type="url", meta={"url": stripped}
            )
        return Document(text=raw_input, title=None, type="text", meta={})


class YouTubeLoader:
    """Loads a YouTube video's transcript as text."""

    def __init__(self, fetch_transcript: TranscriptFetcher | None = None) -> None:
        self._fetch_transcript = fetch_transcript or _youtube_transcript

    async def load(self, raw_input: str) -> Document:
        video_id = youtube_video_id(raw_input)
        text = await self._fetch_transcript(video_id)
        return Document(
            text=text,
            title=None,
            type="youtube",
            meta={"video_id": video_id, "url": raw_input.strip()},
        )


async def _crawl4ai_fetch(url: str) -> CrawlResult:
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    markdown = getattr(result, "markdown", "") or ""
    text = getattr(markdown, "raw_markdown", None) or str(markdown)
    metadata = getattr(result, "metadata", None) or {}
    return CrawlResult(text=text, title=metadata.get("title"))


async def _youtube_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    def _fetch() -> str:
        entries = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(entry["text"] for entry in entries)

    return await asyncio.to_thread(_fetch)
