import base64
import io
import os

import edge_tts
from fastapi import FastAPI, HTTPException
from mutagen.mp3 import MP3
from pydantic import BaseModel

app = FastAPI(title="sikto-tts")

# A warm, conversational narrator voice. Andrew/Emma/Ava/Brian are Microsoft's
# most natural-sounding English voices; override with TTS_VOICE. Browse options
# with `edge-tts --list-voices`. A slightly relaxed rate reads less robotic.
DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewNeural")
DEFAULT_RATE = os.getenv("TTS_RATE", "-3%")
_MAX_TTS_ATTEMPTS = 3


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    rate: str | None = None  # e.g. "+8%" / "-6%"; falls back to the default
    pitch: str | None = None  # e.g. "+4Hz" / "-2Hz"


class WordTiming(BaseModel):
    text: str
    start_ms: int
    end_ms: int


class SynthesizeResponse(BaseModel):
    audio_b64: str  # base64-encoded MP3
    duration_ms: int
    words: list[WordTiming] = []  # per-word timing for synced captions


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(body: SynthesizeRequest) -> SynthesizeResponse:
    """Synthesize narration to MP3 via Microsoft Edge's free neural TTS.

    Returns the audio plus its duration (derived from word-boundary timing) so
    the renderer can size each scene to its narration.
    """
    text = body.text.strip() or " "
    voice = body.voice if body.voice and body.voice != "default" else DEFAULT_VOICE

    audio_bytes, words = await _stream_audio(text, voice, body.rate or DEFAULT_RATE, body.pitch or "+0Hz")
    word_end_ms = words[-1].end_ms if words else 0
    return SynthesizeResponse(
        audio_b64=base64.b64encode(audio_bytes).decode(),
        duration_ms=_duration_ms(audio_bytes, word_end_ms, text),
        words=words,
    )


async def _stream_audio(
    text: str, voice: str, rate: str, pitch: str
) -> tuple[bytes, list[WordTiming]]:
    """Synthesize, retrying transient edge-tts failures. The Microsoft endpoint
    occasionally returns no audio (``NoAudioReceived``); a fresh attempt almost
    always succeeds. `rate`/`pitch` carry the scene's delivery. Also collects
    per-word timings for synced captions."""
    last_exc: Exception | None = None
    for _ in range(_MAX_TTS_ATTEMPTS):
        # boundary="WordBoundary" makes the endpoint emit per-word timings (the
        # default is SentenceBoundary, which gives none) for synced captions.
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, pitch=pitch, boundary="WordBoundary"
        )
        audio = bytearray()
        words: list[WordTiming] = []
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # offset/duration are in 100-nanosecond units.
                    start = chunk["offset"] // 10_000
                    words.append(
                        WordTiming(
                            text=chunk["text"],
                            start_ms=start,
                            end_ms=start + chunk["duration"] // 10_000,
                        )
                    )
        except edge_tts.exceptions.NoAudioReceived as exc:
            last_exc = exc
            continue
        if audio:
            return bytes(audio), words
    raise HTTPException(
        status_code=502, detail=f"tts upstream returned no audio: {last_exc}"
    )


def _duration_ms(audio: bytes, word_end_ms: int, text: str) -> int:
    """Prefer the true MP3 length (so trailing audio is never clipped), falling
    back to word-boundary timing, then a rough text-length estimate."""
    try:
        seconds = MP3(io.BytesIO(audio)).info.length
        if seconds > 0:
            return int(seconds * 1000)
    except Exception:
        pass
    return word_end_ms or max(1, len(text)) * 60
