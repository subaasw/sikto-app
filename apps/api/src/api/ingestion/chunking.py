def chunk_text(text: str, max_chars: int = 1000, overlap: int = 100) -> list[str]:
    """Split text into overlapping character windows.

    Returns a single chunk when the text fits within ``max_chars``. Otherwise it
    slides a ``max_chars`` window forward by ``max_chars - overlap`` each step so
    consecutive chunks share ``overlap`` characters of context.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not 0 <= overlap < max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")

    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    step = max_chars - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + max_chars])
        if start + max_chars >= len(text):
            break
        start += step
    return chunks
