from api.engines.protocols import SourceLoader
from api.ingestion.documents import DocumentLoader, is_document
from api.ingestion.loaders import TextLoader, YouTubeLoader, is_youtube_url


def select_loader(raw_input: str) -> SourceLoader:
    """Pick the loader for an input: YouTube URLs go to YouTubeLoader, document files
    (PDF/EPUB/DOCX/...) to DocumentLoader, and everything else (article URLs and pasted
    text) to TextLoader."""
    if is_youtube_url(raw_input):
        return YouTubeLoader()
    if is_document(raw_input):
        return DocumentLoader()
    return TextLoader()
