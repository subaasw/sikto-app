"""Map a scene's spoken `delivery` to edge-tts prosody (rate + pitch).

Kept here, in one place, so the pipeline and any tests agree on how a delivery
tone translates into voice settings.
"""

# delivery -> (rate, pitch) in edge-tts' percentage / Hz notation.
DELIVERY_PROSODY: dict[str, tuple[str, str]] = {
    "neutral": ("-3%", "+0Hz"),
    "excited": ("+9%", "+4Hz"),
    "calm": ("-8%", "-2Hz"),
    "curious": ("-1%", "+3Hz"),
    "serious": ("-6%", "-3Hz"),
}


def prosody_for(delivery: str) -> tuple[str, str]:
    """Return the (rate, pitch) for a delivery tone, defaulting to neutral."""
    return DELIVERY_PROSODY.get(delivery, DELIVERY_PROSODY["neutral"])
