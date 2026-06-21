"""The static safety guard for LLM-generated Manim code."""

from api.sandbox.manim_safety import is_safe_manim

_GOOD = """
from manim import Scene, Circle, Create
import numpy as np

class MainScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
"""


def test_clean_manim_scene_is_allowed():
    assert is_safe_manim(_GOOD)


def test_rejects_os_and_file_access():
    assert not is_safe_manim("import os\nos.system('rm -rf /')")
    assert not is_safe_manim("open('/etc/passwd').read()")


def test_rejects_dynamic_exec_and_dunders():
    assert not is_safe_manim("eval('2+2')")
    assert not is_safe_manim("exec('x=1')")
    assert not is_safe_manim("().__class__.__bases__")


def test_rejects_network_and_subprocess_imports():
    assert not is_safe_manim("import subprocess")
    assert not is_safe_manim("from urllib import request")


def test_rejects_syntax_errors():
    assert not is_safe_manim("class MainScene(:\n  pass")
