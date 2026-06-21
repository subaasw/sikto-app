"""Single source of truth for object-storage keys and media data-URLs.

The pipeline writes these keys and the API reads/serves them, so they must stay
in lock-step — hence one place to build them rather than f-strings scattered
across modules.
"""

import uuid

# Prefix for an inline base64 audio data-URL (edge-tts emits MP3).
AUDIO_DATA_URL_PREFIX = "data:audio/mpeg;base64,"
# Prefix for an inline base64 video data-URL (Manim emits MP4).
MANIM_DATA_URL_PREFIX = "data:video/mp4;base64,"


def scene_audio_key(job_id: uuid.UUID, scene_id: str) -> str:
    """Stored narration clip for one scene."""
    return f"audio/{job_id}/{scene_id}.mp3"


def scene_manim_key(job_id: uuid.UUID, scene_id: str) -> str:
    """Rendered Manim animation clip for one math/explainer scene."""
    return f"manim/{job_id}/{scene_id}.mp4"


def manim_manifest_key(job_id: uuid.UUID) -> str:
    """Per-scene Manim-clip manifest (which scenes have a clip) for the web player."""
    return f"manim/{job_id}/manifest.json"


def audio_manifest_key(job_id: uuid.UUID) -> str:
    """Per-scene narration manifest (scene_id + duration) for the web player."""
    return f"audio/{job_id}/manifest.json"


def lesson_video_key(job_id: uuid.UUID) -> str:
    """Final rendered lesson video."""
    return f"renders/{job_id}/lesson.mp4"


def source_markdown_key(job_id: uuid.UUID) -> str:
    """The extracted source text (YouTube transcript / article / pasted) as Markdown."""
    return f"sources/{job_id}/source.md"


def script_markdown_key(job_id: uuid.UUID) -> str:
    """The lesson's narration script as Markdown."""
    return f"lessons/{job_id}/script.md"
