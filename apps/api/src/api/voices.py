"""Narration voice selection (male / female), chosen at lesson creation.

Maps a simple choice to a concrete Microsoft Edge neural voice — the TTS service
(apps/tts) accepts the voice name directly. Browse more with
``edge-tts --list-voices``.
"""

from typing import Literal, get_args

VoiceChoice = Literal["male", "female"]
VOICES: frozenset[str] = frozenset(get_args(VoiceChoice))
DEFAULT_VOICE: VoiceChoice = "male"

_VOICE_NAMES: dict[str, str] = {
    "male": "en-US-AndrewNeural",  # warm, conversational male
    "female": "en-US-AvaNeural",  # warm, conversational female
}


def voice_name(choice: str | None) -> str:
    return _VOICE_NAMES.get(choice or DEFAULT_VOICE, _VOICE_NAMES[DEFAULT_VOICE])


# Narrator personality the creative director picks per video, resolved to a
# concrete voice WITHIN the user's male/female choice (we respect that choice).
Tone = Literal["warm", "playful", "energetic", "authoritative"]
_VOICE_BY_TONE: dict[str, dict[str, str]] = {
    "male": {
        "warm": "en-US-AndrewNeural",
        "playful": "en-US-BrianNeural",
        "energetic": "en-US-GuyNeural",
        "authoritative": "en-US-ChristopherNeural",
    },
    "female": {
        "warm": "en-US-AvaNeural",
        "playful": "en-US-EmmaNeural",
        "energetic": "en-US-AvaNeural",
        "authoritative": "en-US-AriaNeural",
    },
}


def voice_for(gender: str | None, tone: str) -> str:
    """Resolve a (gender, tone) pair to a concrete edge-tts voice."""
    table = _VOICE_BY_TONE.get(gender or DEFAULT_VOICE, _VOICE_BY_TONE[DEFAULT_VOICE])
    return table.get(tone, table["warm"])
