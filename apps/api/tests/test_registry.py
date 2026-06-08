from api.ingestion.documents import DocumentLoader
from api.ingestion.loaders import TextLoader, YouTubeLoader
from api.ingestion.registry import select_loader


def test_youtube_url_selects_youtube_loader():
    assert isinstance(select_loader("https://www.youtube.com/watch?v=abc"), YouTubeLoader)
    assert isinstance(select_loader("https://youtu.be/abc"), YouTubeLoader)


def test_document_files_select_document_loader():
    assert isinstance(select_loader("https://example.com/paper.pdf"), DocumentLoader)
    assert isinstance(select_loader("/tmp/book.epub"), DocumentLoader)


def test_article_url_selects_text_loader():
    assert isinstance(select_loader("https://example.com/post"), TextLoader)


def test_plain_text_selects_text_loader():
    assert isinstance(select_loader("some pasted notes"), TextLoader)
