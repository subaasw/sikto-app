"""Render lesson artifacts to Markdown for download/archival.

Keeps the extracted source (e.g. a YouTube transcript) and the generated
narration script in a human-readable text format alongside the video/audio.
"""

from api.engines.protocols import Document
from api.scenes.schema import SceneDocument


def source_markdown(document: Document) -> str:
    """The extracted source text as Markdown."""
    title = (document.title or "Source").strip()
    lines = [f"# {title}", ""]
    if document.meta.get("url"):
        lines += [f"Source: {document.meta['url']}", ""]
    lines.append(document.text.strip())
    return "\n".join(lines).rstrip() + "\n"


def script_markdown(doc: SceneDocument) -> str:
    """The lesson's narration script (title, summary, per-scene narration)."""
    lines = [f"# {doc.title}", "", f"_{doc.summary}_", ""]
    for i, scene in enumerate(doc.scenes, start=1):
        lines.append(f"## Scene {i}")
        narration = (scene.narration.text or "").strip()
        if narration:
            lines += ["", narration]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
