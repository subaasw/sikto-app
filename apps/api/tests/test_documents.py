import pytest

from api.ingestion.documents import (
    ConvertedDocument,
    DocumentLoader,
    document_type,
    is_document,
)


async def test_document_loader_uses_injected_converter():
    async def fake_convert(source: str) -> ConvertedDocument:
        assert source == "https://example.com/paper.pdf"
        return ConvertedDocument(markdown="# Title\n\nBody text", title="Title")

    doc = await DocumentLoader(convert=fake_convert).load("https://example.com/paper.pdf")

    assert doc.type == "pdf"
    assert doc.title == "Title"
    assert "Body text" in doc.text
    assert doc.meta["source"] == "https://example.com/paper.pdf"


async def test_document_loader_handles_local_epub_path():
    async def fake_convert(source: str) -> ConvertedDocument:
        return ConvertedDocument(markdown="chapter one", title=None)

    doc = await DocumentLoader(convert=fake_convert).load("/books/novel.epub")
    assert doc.type == "epub"
    assert doc.text == "chapter one"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://example.com/a.pdf", True),
        ("/tmp/report.epub", True),
        ("/docs/slides.pptx", True),
        ("https://example.com/article", False),
        ("plain text", False),
        ("https://youtu.be/abc", False),
    ],
)
def test_is_document(value, expected):
    assert is_document(value) is expected


def test_document_type():
    assert document_type("https://example.com/a.pdf") == "pdf"
    assert document_type("/tmp/x.epub") == "epub"
