"""The render_manim_clips pass: execute → store → manifest, best-effort."""

import base64
import json
import uuid

from api.jobs.manim_render import render_manim_clips
from api.sandbox.types import RenderResult
from api.scenes.schema import Narration, Scene, SceneDocument, SceneKind
from api.storage_keys import manim_manifest_key, scene_manim_key

_SAFE = "from manim import Scene\n\nclass MainScene(Scene):\n    def construct(self):\n        pass\n"


class MemStorage:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    def put(self, key: str, value: bytes) -> str:
        self.data[key] = value
        return key

    def get(self, key: str) -> bytes:
        return self.data[key]

    def exists(self, key: str) -> bool:
        return key in self.data


class FakeRunner:
    def __init__(self, video: bytes = b"MP4", fail: bool = False) -> None:
        self.video = video
        self.fail = fail
        self.calls = 0

    async def run(self, code: str, entry: str = "MainScene") -> RenderResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("manim boom")
        return RenderResult(video=self.video, stdout="", stderr="")


def _doc(*scenes) -> SceneDocument:
    return SceneDocument(title="t", summary="s", scenes=list(scenes))


def _manim(sid: str, code: str | None) -> Scene:
    return Scene(id=sid, kind=SceneKind.manim, narration=Narration(text="n"), manim_code=code)


def _slide(sid: str) -> Scene:
    return Scene(id=sid, kind=SceneKind.slide, narration=Narration(text="n"))


async def test_renders_manim_scene_and_stores_clip_and_manifest():
    job = uuid.uuid4()
    storage = MemStorage()
    runner = FakeRunner(video=b"CLIP")
    clips = await render_manim_clips(storage, job, _doc(_manim("s0", _SAFE), _slide("s1")), runner=runner)
    assert "s0" in clips and clips["s0"].startswith("data:video/mp4;base64,")
    assert "s1" not in clips  # slides aren't manim
    assert storage.data[scene_manim_key(job, "s0")] == b"CLIP"
    manifest = json.loads(storage.get(manim_manifest_key(job)))
    assert manifest == [{"scene_id": "s0"}]


async def test_unsafe_code_is_skipped():
    storage = MemStorage()
    runner = FakeRunner()
    clips = await render_manim_clips(storage, uuid.uuid4(), _doc(_manim("s0", "import os")), runner=runner)
    assert clips == {} and runner.calls == 0  # never executed


async def test_render_failure_is_skipped_not_fatal():
    storage = MemStorage()
    runner = FakeRunner(fail=True)
    clips = await render_manim_clips(storage, uuid.uuid4(), _doc(_manim("s0", _SAFE)), runner=runner)
    assert clips == {}  # failure → no clip, lesson unaffected


class FlakyRunner:
    """Fails on any code except `good` — models a broken scene that a repair fixes."""

    def __init__(self, good: str) -> None:
        self.good = good
        self.calls: list[str] = []

    async def run(self, code: str, entry: str = "MainScene") -> RenderResult:
        self.calls.append(code)
        if code != self.good:
            raise RuntimeError("manim boom")
        return RenderResult(video=b"FIXED", stdout="", stderr="")


async def test_repair_turns_a_failing_scene_into_a_clip():
    storage = MemStorage()
    runner = FlakyRunner(good=_SAFE)
    # safe code that blows up at render (not a syntax error — that's caught earlier)
    bad = "from manim import Scene\n\nclass MainScene(Scene):\n    def construct(self):\n        self.does_not_exist()\n"

    async def repair(code: str, error: str) -> str:
        assert code == bad and error  # gets the broken code + a reason
        return _SAFE

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", bad)), runner=runner, repair=repair
    )
    assert clips["s0"].endswith(base64.b64encode(b"FIXED").decode())  # the repaired clip
    assert runner.calls == [bad, _SAFE]  # original then repaired


async def test_repair_fixes_unsafe_code_too():
    storage = MemStorage()
    runner = FlakyRunner(good=_SAFE)

    async def repair(code: str, error: str) -> str:
        return _SAFE

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", "import os")), runner=runner, repair=repair
    )
    assert "s0" in clips
    assert runner.calls == [_SAFE]  # unsafe original never executed; repaired one is


async def test_repair_returning_none_skips_gracefully():
    storage = MemStorage()
    runner = FakeRunner(fail=True)

    async def repair(code: str, error: str) -> None:
        return None

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", _SAFE)), runner=runner, repair=repair
    )
    assert clips == {}  # unrepairable → still best-effort skip


async def test_short_clip_is_padded_to_narration_length():
    storage = MemStorage()
    runner = FakeRunner(video=b"CLIP")
    calls: list[tuple[bytes, int]] = []

    async def pad(video: bytes, target_ms: int) -> bytes:
        calls.append((video, target_ms))
        return b"PADDED"

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", _SAFE)),
        runner=runner, durations={"s0": 9000}, pad=pad,
    )
    assert calls == [(b"CLIP", 9000)]  # padded to the narration length
    assert clips["s0"].endswith(base64.b64encode(b"PADDED").decode())
    assert b"PADDED" in storage.data.values()


async def test_no_duration_means_no_pad():
    storage = MemStorage()
    called = False

    async def pad(video: bytes, target_ms: int) -> bytes:
        nonlocal called
        called = True
        return video

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", _SAFE)),
        runner=FakeRunner(video=b"CLIP"), durations={}, pad=pad,
    )
    assert called is False  # no narration length → nothing to pad against
    assert clips["s0"].endswith(base64.b64encode(b"CLIP").decode())


async def test_repair_runs_up_to_two_rounds():
    storage = MemStorage()
    runner = FlakyRunner(good=_SAFE)
    bad = "from manim import Scene\n\nclass MainScene(Scene):\n    def construct(self):\n        self.nope()\n"
    still_bad = bad.replace("nope", "still_nope")
    fixes = iter([still_bad, _SAFE])  # first repair still fails, second one works

    async def repair(code: str, error: str) -> str:
        return next(fixes)

    clips = await render_manim_clips(
        storage, uuid.uuid4(), _doc(_manim("s0", bad)), runner=runner, repair=repair
    )
    assert clips["s0"].endswith(base64.b64encode(b"FIXED").decode())
    assert runner.calls == [bad, still_bad, _SAFE]  # original + two repair attempts


def test_manim_system_paints_the_theme():
    from api.agent_engine.nodes import _manim_system
    from api.scenes.schema import SceneTheme

    theme = SceneTheme(background="#101010", primary="#00ff88", foreground="#eeeeee", font="Geist")
    prompt = _manim_system(theme)
    assert "#101010" in prompt and "#00ff88" in prompt and "#eeeeee" in prompt and "Geist" in prompt
    assert "background_color" in prompt
    assert _manim_system(None).count("#") == 0  # no theme → generic prompt


async def test_llm_manim_repair_passes_error_and_returns_fixed_code():
    from api.jobs.manim_render import _ManimFix, llm_manim_repair

    seen = {}

    class FakeLLM:
        async def generate(self, system, user, schema):
            seen["user"] = user
            return _ManimFix(manim_code=_SAFE)

    repair = llm_manim_repair(FakeLLM())
    fixed = await repair("broken code", "NameError: boom")
    assert fixed == _SAFE
    assert "broken code" in seen["user"] and "NameError: boom" in seen["user"]
