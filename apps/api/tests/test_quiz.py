import pytest

from api.planning.schema import QuizItem
from api.scenes.quiz import _QuizDraft, build_quiz
from api.scenes.schema import Narration, Scene, SceneDocument


def _doc(narration: str = "x" * 200) -> SceneDocument:
    scene = Scene(id="s0", narration=Narration(text=narration))
    return SceneDocument(title="T", summary="S", scenes=[scene])


class _FakeLLM:
    def __init__(self, draft: _QuizDraft | None = None, boom: bool = False):
        self.draft = draft
        self.boom = boom
        self.calls = 0

    async def generate(self, system, user, schema):
        self.calls += 1
        if self.boom:
            raise RuntimeError("model down")
        return self.draft


@pytest.mark.asyncio
async def test_no_llm_returns_empty():
    assert await build_quiz(_doc(), None) == []


@pytest.mark.asyncio
async def test_thin_content_skips_llm():
    llm = _FakeLLM()
    assert await build_quiz(_doc(narration="too short"), llm) == []
    assert llm.calls == 0  # never bothered the model


@pytest.mark.asyncio
async def test_llm_failure_is_swallowed():
    assert await build_quiz(_doc(), _FakeLLM(boom=True)) == []


@pytest.mark.asyncio
async def test_caps_at_five_and_dumps_dicts():
    items = [QuizItem(question=f"q{i}", choices=["a", "b"], answer="a", explanation="e") for i in range(7)]
    out = await build_quiz(_doc(), _FakeLLM(draft=_QuizDraft(items=items)))
    assert len(out) == 5
    assert out[0] == {"question": "q0", "choices": ["a", "b"], "answer": "a", "explanation": "e"}
