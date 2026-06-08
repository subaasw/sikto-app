import pytest
from pydantic import ValidationError

from api.planning.schema import ProductionPlan, VisualType


def _valid_plan_dict() -> dict:
    return {
        "lesson": {
            "title": "Intro to Vectors",
            "summary": "A short lesson on vectors.",
            "difficulty": "intro",
            "key_points": ["point one", "point two", "point three"],
            "quiz": [
                {"question": "Q1?", "answer": "A1", "explanation": "because"},
                {
                    "question": "Q2?",
                    "choices": ["a", "b"],
                    "answer": "a",
                    "explanation": "because a",
                },
            ],
        },
        "voice": {"id": "default", "language": "en"},
        "segments": [
            {
                "id": "s0",
                "order": 0,
                "narration": "Welcome to the lesson.",
                "caption": "Welcome",
                "visual_type": "title",
            }
        ],
        "retrieval": {"strategy": "direct", "store": "pgvector"},
        "meta": {
            "source_ids": ["src-1"],
            "planner_model": "openai/gpt",
            "embedding_model": "openai/embed",
            "tts_model": "qwen3-tts",
            "engine_version": "0.1.0",
        },
    }


def test_valid_plan_parses():
    plan = ProductionPlan.model_validate(_valid_plan_dict())
    assert plan.lesson.title == "Intro to Vectors"
    assert plan.segments[0].visual_type is VisualType.title
    assert plan.segments[0].render_hints == {}
    assert plan.segments[0].estimated_duration_ms is None
    assert plan.retrieval.k is None


def test_too_few_key_points_rejected():
    data = _valid_plan_dict()
    data["lesson"]["key_points"] = ["only one"]
    with pytest.raises(ValidationError):
        ProductionPlan.model_validate(data)


def test_too_few_quiz_items_rejected():
    data = _valid_plan_dict()
    data["lesson"]["quiz"] = [data["lesson"]["quiz"][0]]
    with pytest.raises(ValidationError):
        ProductionPlan.model_validate(data)


def test_empty_segments_rejected():
    data = _valid_plan_dict()
    data["segments"] = []
    with pytest.raises(ValidationError):
        ProductionPlan.model_validate(data)


def test_unknown_visual_type_rejected():
    data = _valid_plan_dict()
    data["segments"][0]["visual_type"] = "hologram"
    with pytest.raises(ValidationError):
        ProductionPlan.model_validate(data)
