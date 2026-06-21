"""Lesson mode shapes the outline budget: a video stays short, a course runs longer."""

from api.lesson_mode import DEFAULT_MODE, MODES, beat_bounds, mode_guidance


def test_video_is_capped_shorter_than_course():
    v_lo, v_hi = beat_bounds("video")
    c_lo, c_hi = beat_bounds("course")
    assert v_hi < c_hi  # a video can't sprawl into a full course
    assert v_lo <= c_lo


def test_auto_falls_back_to_course_bounds():
    assert beat_bounds("auto") == beat_bounds("course") == beat_bounds(None)


def test_guidance_known_and_default():
    assert DEFAULT_MODE in MODES
    assert "video" in mode_guidance("video").lower()
    assert mode_guidance("nonsense") == mode_guidance(DEFAULT_MODE)
