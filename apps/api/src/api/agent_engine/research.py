"""Free web research for lesson planning.

The brain searches the web for material related to the source so the outline is
better-structured and can cover subtopics the source skims. The provider is free
and needs no API key (DuckDuckGo via the ``ddgs`` library). Everything is
best-effort: a network failure or an empty result never fails lesson generation.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("api.brain.research")


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    url: str


class WebSearch(Protocol):
    async def search(self, query: str, *, k: int) -> list[SearchResult]: ...


class NullSearch:
    """No-op provider — used in tests and when web search is disabled."""

    async def search(self, query: str, *, k: int) -> list[SearchResult]:
        return []


class DuckDuckGoSearch:
    """Free, key-less search via the ``ddgs`` library (a sync lib run off-thread)."""

    async def search(self, query: str, *, k: int) -> list[SearchResult]:
        try:
            return await asyncio.to_thread(self._search_sync, query, k)
        except Exception:  # network/library hiccups must never break planning
            logger.warning("web search failed for %r", query, exc_info=True)
            return []

    @staticmethod
    def _search_sync(query: str, k: int) -> list[SearchResult]:
        from ddgs import DDGS  # imported lazily so the dep is optional at import time

        out: list[SearchResult] = []
        with DDGS() as ddgs:
            for row in ddgs.text(query, max_results=k):
                out.append(
                    SearchResult(
                        title=str(row.get("title", "")).strip(),
                        snippet=str(row.get("body", "")).strip(),
                        url=str(row.get("href", "")).strip(),
                    )
                )
        return out


def web_search_from_settings() -> WebSearch:
    from api.config import get_settings

    settings = get_settings()
    if not settings.web_search_enabled:
        return NullSearch()
    return DuckDuckGoSearch()


def format_research(results: list[SearchResult], *, max_chars: int) -> str:
    """Render search hits into a compact context block for the planning prompts."""
    lines: list[str] = []
    used = 0
    for r in results:
        if not r.snippet:
            continue
        entry = f"- {r.title}: {r.snippet}" if r.title else f"- {r.snippet}"
        if used + len(entry) > max_chars:
            break
        lines.append(entry)
        used += len(entry)
    return "\n".join(lines)
