from api.agent.retrieval import EmbeddingRetriever
from api.engines.mocks import MockEmbeddingsClient, MockVectorStore


async def test_embedding_retriever_returns_source_attributed_passages():
    store = MockVectorStore()
    await store.upsert([("src-1:0", "alpha", [0.0] * 8), ("src-2:0", "beta", [0.0] * 8)])

    retriever = EmbeddingRetriever(MockEmbeddingsClient(), store)
    passages = await retriever.retrieve("anything", k=2)

    assert [p.content for p in passages] == ["alpha", "beta"]
    assert passages[0].source_id == "src-1"
    assert passages[1].source_id == "src-2"


async def test_retriever_scopes_to_source_ids():
    store = MockVectorStore()
    await store.upsert([("src-1:0", "alpha", [0.0] * 8), ("src-2:0", "beta", [0.0] * 8)])

    retriever = EmbeddingRetriever(MockEmbeddingsClient(), store, source_ids=["src-2"])
    passages = await retriever.retrieve("anything", k=5)

    assert [p.source_id for p in passages] == ["src-2"]
    assert passages[0].content == "beta"
