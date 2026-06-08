import pytest

from api.agent.engine import MicrolearningAgent
from api.agent.types import AgentError, Message, Passage, ToolCall, ToolSpec
from api.engines.protocols import Document
from api.planning.schema import Retrieval, RetrievalStrategy, VectorStoreName, Voice

_GOOD_DRAFT = {
    "lesson": {
        "title": "Intro to Vectors",
        "summary": "A short lesson.",
        "difficulty": "intro",
        "key_points": ["a", "b", "c"],
        "quiz": [
            {"question": "Q1?", "answer": "A1", "explanation": "x"},
            {"question": "Q2?", "answer": "A2", "explanation": "y"},
        ],
    },
    "segments": [
        {
            "id": "s0",
            "order": 0,
            "narration": "Welcome.",
            "caption": "Welcome",
            "visual_type": "title",
        },
    ],
}

_BAD_DRAFT = {
    "lesson": {
        "title": "Too thin",
        "summary": "x",
        "difficulty": "intro",
        "key_points": ["only one"],
        "quiz": [{"question": "Q?", "answer": "A", "explanation": "e"}],
    },
    "segments": [],
}


class FakeLLM:
    def __init__(self, calls: list[ToolCall]) -> None:
        self._calls = calls
        self.index = 0
        self.seen: list[list[str]] = []

    async def next_action(self, messages: list[Message], tools: list[ToolSpec]) -> ToolCall:
        self.seen.append([m.content for m in messages])
        call = self._calls[self.index]
        self.index += 1
        return call


class FakeRetriever:
    def __init__(self, passages: list[Passage]) -> None:
        self._passages = passages
        self.queries: list[tuple[str, int]] = []

    async def retrieve(self, query: str, k: int) -> list[Passage]:
        self.queries.append((query, k))
        return self._passages


def _agent(llm, retriever, **kwargs) -> MicrolearningAgent:
    return MicrolearningAgent(
        llm,
        retriever,
        voice=Voice(id="default", language="en"),
        retrieval=Retrieval(strategy=RetrievalStrategy.vector, store=VectorStoreName.pgvector),
        planner_model="planner-m",
        embedding_model="embed-m",
        tts_model="tts-m",
        engine_version="0.1.0",
        **kwargs,
    )


def _doc() -> Document:
    return Document(text="source about vectors", title="T", type="text", meta={})


async def test_agent_retrieves_then_submits():
    llm = FakeLLM(
        [
            ToolCall("retrieve", {"query": "vectors", "k": 2}),
            ToolCall("submit_lesson", _GOOD_DRAFT),
        ]
    )
    passages = [Passage("passage A", "src-1", 0.9), Passage("passage B", "src-2", 0.8)]
    retriever = FakeRetriever(passages)
    run = await _agent(llm, retriever).run(_doc(), source_ids=["s1"])

    assert run.plan.lesson.title == "Intro to Vectors"
    assert run.plan.meta.source_ids == ["s1"]
    assert run.retrieved == passages
    assert retriever.queries == [("vectors", 2)]
    assert len(run.trace) == 2
    # the retrieved passages were fed back with source labels before the second decision
    assert any("[source src-1] passage A" in msg for msg in llm.seen[1])


async def test_agent_self_corrects_on_invalid_submission():
    llm = FakeLLM(
        [
            ToolCall("submit_lesson", _BAD_DRAFT),
            ToolCall("submit_lesson", _GOOD_DRAFT),
        ]
    )
    run = await _agent(llm, FakeRetriever([])).run(_doc(), source_ids=["s1"])

    assert run.plan.lesson.title == "Intro to Vectors"
    assert len(run.trace) == 2
    assert any("submit_lesson was invalid" in msg for msg in llm.seen[1])


async def test_agent_errors_when_it_never_submits():
    llm = FakeLLM([ToolCall("retrieve", {"query": "a"}), ToolCall("retrieve", {"query": "b"})])
    with pytest.raises(AgentError):
        await _agent(llm, FakeRetriever([]), max_steps=2).run(_doc(), source_ids=["s1"])


async def test_agent_recovers_from_unknown_tool():
    llm = FakeLLM([ToolCall("frobnicate", {}), ToolCall("submit_lesson", _GOOD_DRAFT)])
    run = await _agent(llm, FakeRetriever([])).run(_doc(), source_ids=["s1"])

    assert run.plan.lesson.title == "Intro to Vectors"
    assert any("Unknown tool" in msg for msg in llm.seen[1])
