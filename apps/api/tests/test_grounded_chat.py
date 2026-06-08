from api.agent.types import Passage
from api.chat.engine import GroundedChat


class FakeRetriever:
    def __init__(self, passages: list[Passage]) -> None:
        self._passages = passages
        self.queries: list[tuple[str, int]] = []

    async def retrieve(self, query: str, k: int) -> list[Passage]:
        self.queries.append((query, k))
        return self._passages


class FakeLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.seen: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str) -> str:
        self.seen.append((system, user))
        return self.answer


async def test_answers_grounded_in_passages_with_citations():
    passages = [Passage("Vectors capture meaning", "src-1", 0.9)]
    llm = FakeLLM("Embeddings capture meaning [source src-1].")
    chat = GroundedChat(FakeRetriever(passages), llm, k=3)

    result = await chat.answer("What are embeddings?")

    assert result.answer == "Embeddings capture meaning [source src-1]."
    assert result.citations == passages
    # the source-labeled passage was provided to the model
    assert "[source src-1] Vectors capture meaning" in llm.seen[0][1]


async def test_handles_no_passages():
    llm = FakeLLM("I don't have enough information from the provided sources.")
    chat = GroundedChat(FakeRetriever([]), llm)

    result = await chat.answer("unknown topic")

    assert result.citations == []
    assert "No source passages were found" in llm.seen[0][1]
