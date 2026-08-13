"""Map a scene's spoken `delivery` + the video's `energy` to edge-tts prosody.

Kept here, in one place, so the pipeline and any tests agree on how a delivery
tone and a video-level energy combine into voice settings. Per-scene `delivery`
shapes one beat; `energy` is a video-wide bias (the creative director's pick) so
two videos on the same topic can sound calm vs. hype.
"""

# delivery / energy -> (rate %, pitch Hz), summed then clamped to a sane range.
_DELIVERY: dict[str, tuple[int, int]] = {
    "neutral": (-3, 0),
    "excited": (9, 4),
    "calm": (-8, -2),
    "curious": (-1, 3),
    "serious": (-6, -3),
}
_ENERGY: dict[str, tuple[int, int]] = {
    "calm": (-5, -2),
    "balanced": (0, 0),
    "energetic": (7, 3),
    "hype": (13, 6),
}


def prosody_for(delivery: str, energy: str = "balanced") -> tuple[str, str]:
    """Return (rate, pitch) strings for a delivery tone plus a video energy bias.

    Clamped so excited + hype can't chipmunk the voice."""
    dr, dp = _DELIVERY.get(delivery, _DELIVERY["neutral"])
    er, ep = _ENERGY.get(energy, _ENERGY["balanced"])
    rate = max(-20, min(30, dr + er))
    pitch = max(-12, min(12, dp + ep))
    return (f"{rate:+d}%", f"{pitch:+d}Hz")
