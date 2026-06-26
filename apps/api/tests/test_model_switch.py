"""NVIDIA model switcher: cascade order, dedup, cooldown skip, deepseek flag."""

import time

from api.agent import model_switch
from api.config import Settings


def _settings(**kw) -> Settings:
    base = dict(
        nvidia_api_key="k",
        nvidia_model="deepseek-ai/deepseek-v4-pro",
        nvidia_fallback_models=["deepseek-ai/deepseek-v4-flash", "deepseek-ai/deepseek-v4-pro", "meta/llama-3.1-8b-instruct"],
    )
    base.update(kw)
    return Settings(**base)


def setup_function(_):
    model_switch._cooldown_until.clear()


def test_cascade_is_ordered_and_deduped():
    models = [c.model for c in model_switch.nvidia_cascade(_settings())]
    assert models == [
        "deepseek-ai/deepseek-v4-pro",
        "deepseek-ai/deepseek-v4-flash",
        "meta/llama-3.1-8b-instruct",
    ]


def test_empty_without_key():
    assert model_switch.nvidia_cascade(_settings(nvidia_api_key="")) == []


def test_deepseek_gets_thinking_off_others_dont():
    by_model = {c.model: c.extra_body for c in model_switch.nvidia_cascade(_settings())}
    assert by_model["deepseek-ai/deepseek-v4-pro"] == {"chat_template_kwargs": {"thinking": False}}
    assert by_model["meta/llama-3.1-8b-instruct"] is None


def test_failed_model_is_skipped_during_cooldown():
    model_switch.note_failure("deepseek-ai/deepseek-v4-pro")
    models = [c.model for c in model_switch.nvidia_cascade(_settings())]
    assert "deepseek-ai/deepseek-v4-pro" not in models
    assert models[0] == "deepseek-ai/deepseek-v4-flash"


def test_all_in_cooldown_still_returns_full_cascade():
    for m in ["deepseek-ai/deepseek-v4-pro", "deepseek-ai/deepseek-v4-flash", "meta/llama-3.1-8b-instruct"]:
        model_switch.note_failure(m)
    assert len(model_switch.nvidia_cascade(_settings())) == 3  # never hard-fail


def test_cooldown_expires():
    model_switch.note_failure("deepseek-ai/deepseek-v4-pro")
    model_switch._cooldown_until["deepseek-ai/deepseek-v4-pro"] = time.monotonic() - 1
    models = [c.model for c in model_switch.nvidia_cascade(_settings())]
    assert models[0] == "deepseek-ai/deepseek-v4-pro"
