import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from api.engines.protocols import Document

DOCUMENT_EXTENSIONS = {".pdf", ".epub", ".docx", ".pptx", ".xlsx"}


@dataclass
class ConvertedDocument:
    markdown: str
    title: str | None


Converter = Callable[[str], Awaitable[ConvertedDocument]]


def _extension(value: str) -> str:
    path = urlparse(value.strip()).path or value.strip()
    return os.path.splitext(path)[1].lower()


def is_document(value: str) -> bool:
    return _extension(value) in DOCUMENT_EXTENSIONS


def document_type(value: str) -> str:
    return _extension(value).lstrip(".") or "document"


class DocumentLoader:
    """Loads documents (PDF, EPUB, DOCX, ...) as Markdown via MarkItDown. Accepts a
    local path or a URL. A converter can be injected for testing."""

    def __init__(self, convert: Converter | None = None) -> None:
        self._convert = convert or _markitdown_convert

    async def load(self, raw_input: str) -> Document:
        source = raw_input.strip()
        result = await self._convert(source)
        return Document(
            text=result.markdown,
            title=result.title,
            type=document_type(source),
            meta={"source": source},
        )


async def _markitdown_convert(source: str) -> ConvertedDocument:
    from markitdown import MarkItDown

    def _run() -> ConvertedDocument:
        result = MarkItDown().convert(source)
        return ConvertedDocument(markdown=result.text_content, title=result.title)

    return await asyncio.to_thread(_run)
