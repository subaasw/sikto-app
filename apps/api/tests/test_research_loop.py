"""Iterative (ReAct) research node: search → read → refine, bounded by rounds."""

from api.agent_engine.nodes import BrainNodes
from api.agent_engine.research import SearchResult
from api.scenes.schema import ResearchPlan


class _FakeSearch:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str, *, k: int) -> list[SearchResult]:
        self.queries.append(query)
        return [SearchResult(title=query, snippet=f"about {query}", url="u")]


class _FakeLLM:
    def __init__(self, plans: list[ResearchPlan]) -> None:
        self._plans = plans
        self._n = 0

    async def generate(self, system, user, schema):
        plan = self._plans[min(self._n, len(self._plans) - 1)]
        self._n += 1
        return plan


def _state():
    return {
        "source_title": "T",
        "source_text": "some source",
        "research": "",
        "outline": None,
        "document": None,
        "issues": [],
        "repairs": 0,
    }


async def test_research_runs_a_second_round_informed_by_the_first():
    search = _FakeSearch()
    llm = _FakeLLM([ResearchPlan(queries=["q1"]), ResearchPlan(queries=["q2"])])
    out = await BrainNodes(llm, search=search).research(_state())
    assert search.queries == ["q1", "q2"]  # default web_search_rounds=2
    assert "q1" in out["research"] and "q2" in out["research"]


async def test_research_stops_early_when_material_is_sufficient():
    search = _FakeSearch()
    llm = _FakeLLM([ResearchPlan(queries=["q1"]), ResearchPlan(queries=[])])
    out = await BrainNodes(llm, search=search).research(_state())
    assert search.queries == ["q1"]  # follow-up returned no new queries → stop
    assert "q1" in out["research"]
