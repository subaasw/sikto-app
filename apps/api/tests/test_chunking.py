import pytest

from api.ingestion.chunking import chunk_text


def test_short_text_returns_single_chunk():
    assert chunk_text("hello world", max_chars=1000) == ["hello world"]


def test_empty_text_returns_empty_list():
    assert chunk_text("   ", max_chars=1000) == []


def test_long_text_is_split_with_overlap():
    text = "a" * 2500
    chunks = chunk_text(text, max_chars=1000, overlap=100)
    assert len(chunks) == 3
    assert len(chunks[0]) == 1000
    assert len(chunks[1]) == 1000
    assert len(chunks[2]) == 700  # 2500 - 2*900


def test_consecutive_chunks_share_overlap():
    text = "".join(str(i % 10) for i in range(2500))
    chunks = chunk_text(text, max_chars=1000, overlap=100)
    # tail of chunk 0 equals head of chunk 1 (the overlap region)
    assert chunks[0][-100:] == chunks[1][:100]


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("abc", max_chars=10, overlap=10)
