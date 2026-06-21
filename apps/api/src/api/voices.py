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
