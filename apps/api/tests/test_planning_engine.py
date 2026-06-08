import json

import pytest

from api.engines.protocols import Document
from api.planning.engine import PlanningEngine, PlanningError
from api.planning.schema import Retrieval, RetrievalStrategy, VectorStoreName, Voice

_GOOD_DRAFT = json.dumps(
    {
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
            }
        ],
    }
)


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    async def complete_json(self, system: str, user: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return response


def _engine(llm: FakeLLM) -> PlanningEngine:
    return PlanningEngine(
        llm,
        voice=Voice(id="default", language="en"),
        retrieval=Retrieval(strategy=RetrievalStrategy.direct, store=VectorStoreName.pgvector),
        planner_model="planner-m",
        embedding_model="embed-m",
        tts_model="tts-m",
        engine_version="0.1.0",
    )


def _doc() -> Document:
    return Document(text="some source", title="T", type="text", meta={})


async def test_plan_builds_full_production_plan():
    llm = FakeLLM([_GOOD_DRAFT])
    plan = await _engine(llm).plan(_doc(), source_ids=["src-1"])

    assert plan.lesson.title == "Intro to Vectors"
    assert len(plan.segments) == 1
    # engine-supplied fields the LLM never sees:
    assert plan.voice.id == "default"
    assert plan.retrieval.store is VectorStoreName.pgvector
    assert plan.meta.source_ids == ["src-1"]
    assert plan.meta.planner_model == "planner-m"
    assert plan.meta.tts_model == "tts-m"


async def test_retries_once_on_invalid_then_succeeds():
    llm = FakeLLM(["not valid json", _GOOD_DRAFT])
    plan = await _engine(llm).plan(_doc(), source_ids=["src-1"])
    assert llm.calls == 2
    assert plan.lesson.title == "Intro to Vectors"


async def test_strips_code_fences():
    fenced = f"```json\n{_GOOD_DRAFT}\n```"
    llm = FakeLLM([fenced])
    plan = await _engine(llm).plan(_doc(), source_ids=["src-1"])
    assert plan.lesson.difficulty.value == "intro"


async def test_raises_after_two_invalid_responses():
    llm = FakeLLM(["bad", "still bad"])
    with pytest.raises(PlanningError):
        await _engine(llm).plan(_doc(), source_ids=["src-1"])
    assert llm.calls == 2
