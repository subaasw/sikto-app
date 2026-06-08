from api.engines.mocks import (
    MockEmbeddingsClient,
    MockRenderClient,
    MockSourceLoader,
    MockTTSClient,
    MockVectorStore,
)
from api.engines.protocols import Document, TTSResult


async def test_mock_source_loader_returns_document():
    doc = await MockSourceLoader().load("anything")
    assert isinstance(doc, Document)
    assert doc.text


async def test_mock_embeddings_returns_vector_per_chunk():
    vecs = await MockEmbeddingsClient().embed(["a", "b"])
    assert len(vecs) == 2
    assert all(len(v) == 8 for v in vecs)


async def test_mock_vector_store_upsert_then_query():
    store = MockVectorStore()
    await store.upsert([("c1", "content", [0.0] * 8)])
    hits = await store.query([0.0] * 8, k=1)
    assert hits[0][0] == "c1"


async def test_mock_vector_store_filters_by_source_ids():
    store = MockVectorStore()
    await store.upsert([("src-1:0", "a", [0.0] * 8), ("src-2:0", "b", [0.0] * 8)])
    hits = await store.query([0.0] * 8, k=5, source_ids=["src-2"])
    assert [hit[0] for hit in hits] == ["src-2:0"]


async def test_mock_tts_returns_audio_and_duration():
    result = await MockTTSClient().synthesize("hello")
    assert isinstance(result, TTSResult)
    assert result.audio
    assert result.duration_ms > 0


async def test_mock_render_returns_ref():
    ref = await MockRenderClient().render({"lesson": {"title": "t"}})
    assert ref.endswith(".mp4")
