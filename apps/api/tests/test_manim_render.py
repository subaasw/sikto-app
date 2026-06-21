"""The render_manim_clips pass: execute → store → manifest, best-effort."""

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
