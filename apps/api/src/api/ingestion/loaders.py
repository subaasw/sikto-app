import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from api.engines.protocols import Document

logger = logging.getLogger("api.ingestion")

# Preferred caption languages, in order, before falling back to anything available.
_TRANSCRIPT_LANGS = ["en", "en-US", "en-GB"]


@dataclass
class CrawlResult:
    text: str
    title: str | None


Crawler = Callable[[str], Awaitable[CrawlResult]]
TranscriptFetcher = Callable[[str], Awaitable[str]]


# Sources are joined into the single `raw_input` column with this record separator
# (ASCII RS, U+001E) — safe because pasted text never contains it, so a text blob
# with newlines stays one source.
SOURCE_SEP = "\x1e"


def split_sources(raw_input: str) -> list[str]:
    """One create-request may carry several sources (links/videos/text). Split the
    stored blob back into the individual inputs; a single-source blob returns [it]."""
    parts = [p.strip() for p in raw_input.split(SOURCE_SEP)]
    return [p for p in parts if p] or [raw_input]


def combine_documents(docs: list[Document]) -> Document:
    """Merge several loaded sources into one document the brain treats as a single
    body of material. Titles are kept as section headers so provenance survives."""
    if len(docs) == 1:
        return docs[0]
    sections = [
        f"# {d.title}\n\n{d.text}" if d.title else d.text for d in docs if d.text.strip()
    ]
    return Document(
        text="\n\n---\n\n".join(sections),
        title=next((d.title for d in docs if d.title), None),
        type="mixed",
        meta={"sources": [d.meta for d in docs]},
    )


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

    logger.info("crawling url: %s", url)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    if not getattr(result, "success", True):
        raise ValueError(f"crawl failed for {url}: {getattr(result, 'error_message', 'unknown')}")
    markdown = getattr(result, "markdown", "") or ""
    text = getattr(markdown, "raw_markdown", None) or str(markdown)
    metadata = getattr(result, "metadata", None) or {}
    logger.info("crawled %s (%d chars)", url, len(text))
    return CrawlResult(text=text, title=metadata.get("title"))


async def _youtube_transcript(video_id: str) -> str:
    """Fetch a video's captions: prefer a manually-created transcript in a
    preferred language, fall back to an auto-generated one, then to anything
    available (translated to English when possible)."""
    from youtube_transcript_api import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        YouTubeTranscriptApi,
    )

    def _fetch() -> str:
        ytt = YouTubeTranscriptApi()
        try:
            transcripts = ytt.list(video_id)
        except CouldNotRetrieveTranscript as exc:
            raise ValueError(f"no transcript available for video {video_id}: {exc}") from exc

        transcript = None
        for find in (
            transcripts.find_manually_created_transcript,
            transcripts.find_generated_transcript,
        ):
            try:
                transcript = find(_TRANSCRIPT_LANGS)
                break
            except NoTranscriptFound:
                continue

        if transcript is None:
            transcript = next(iter(transcripts), None)
            if transcript is None:
                raise ValueError(f"no transcript available for video {video_id}")
            if transcript.is_translatable and transcript.language_code not in _TRANSCRIPT_LANGS:
                transcript = transcript.translate("en")

        try:
            fetched = transcript.fetch()
        except CouldNotRetrieveTranscript as exc:
            raise ValueError(f"could not fetch transcript for video {video_id}: {exc}") from exc

        snippets = fetched.snippets
        logger.info(
            "fetched youtube transcript %s (%s, %d segments)",
            video_id,
            transcript.language_code,
            len(snippets),
        )
        return " ".join(s.text for s in snippets if s.text.strip())

    return await asyncio.to_thread(_fetch)
