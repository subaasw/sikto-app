"""Creative direction: per-video voice + theme. Pure logic, no DB/LLM."""

import pytest

from api.scenes.planner import _light_or, _safe_hex, direct_creative
from api.scenes.schema import SceneDocument, Scene, Narration
from api.tts_delivery import prosody_for
from api.voices import voice_for


def test_prosody_combines_delivery_and_energy_and_clamps():
    # excited beat in a hype video is faster/higher than a calm one...
    assert prosody_for("excited", "hype") == ("+22%", "+10Hz")  # 9+13 rate; 4+6 pitch
    assert prosody_for("calm", "calm") == ("-13%", "-4Hz")
    # ...and a plain neutral/balanced is gentle
    assert prosody_for("neutral", "balanced") == ("-3%", "+0Hz")


def test_voice_for_respects_gender_then_tone():
    assert voice_for("female", "authoritative") == "en-US-AriaNeural"
    assert voice_for("male", "playful") == "en-US-BrianNeural"
    # unknown tone falls back to warm, unknown gender to default (male)
    assert voice_for("female", "bogus") == "en-US-AvaNeural"
    assert voice_for(None, "warm") == "en-US-AndrewNeural"


def test_theme_guards_keep_light_board_and_valid_hex():
    assert _safe_hex("#1122ff", "#fallback") == "#1122ff"
    assert _safe_hex("not-a-hex", "#f6f7f9") == "#f6f7f9"
    assert _light_or("#000000", "#f6f7f9") == "#f6f7f9"  # too dark -> fallback
    assert _light_or("#fbfbf9", "#f6f7f9") == "#fbfbf9"  # light -> kept


@pytest.mark.asyncio
async def test_direct_creative_without_llm_is_light_and_gender_voiced():
    doc = SceneDocument(
        title="t", summary="s", scenes=[Scene(id="s0", narration=Narration(text="hi"))]
    )
    await direct_creative(doc, llm=None, gender="female")
    assert _light_or(doc.theme.background, "#fff") == doc.theme.background  # light
    assert doc.voice.voice == "en-US-AvaNeural"  # female warm fallback
    assert doc.voice.energy == "balanced"
