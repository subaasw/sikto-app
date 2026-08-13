"""WCAG contrast math + legibility repair for scene themes.

Mirrors packages/scene-kit/src/tokens.ts — keep the two in sync. The pipeline
REPAIRS an illegible theme (never rejects): a lesson must always render.
"""

from __future__ import annotations

from loguru import logger

DARK_INK = "#111827"
LIGHT_INK = "#f8fafc"
MIN_TEXT_CONTRAST = 4.5


def _channels(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(hex_color: str) -> float:
    def lin(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = _channels(hex_color)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colors (1..21)."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def legible_ink(background: str, ink: str) -> str:
    """`ink` if it reads on `background`, else black/white — whichever wins."""
    if contrast_ratio(ink, background) >= MIN_TEXT_CONTRAST:
        return ink
    return DARK_INK if contrast_ratio(DARK_INK, background) >= contrast_ratio(LIGHT_INK, background) else LIGHT_INK


def ensure_legible(theme) -> None:
    """Repair a SceneTheme in place so text always reads (ink/bg >= 4.5).

    Checks the legacy trio and, when present, the palette roles the LLM
    director may have repainted.
    """
    fixed = legible_ink(theme.background, theme.foreground)
    if fixed != theme.foreground:
        logger.warning("theme repaired: foreground {} fails on {} -> {}", theme.foreground, theme.background, fixed)
        theme.foreground = fixed
    palette = getattr(theme, "palette", None)
    if palette is not None:
        fixed = legible_ink(palette.bg, palette.ink)
        if fixed != palette.ink:
            logger.warning("theme repaired: palette ink {} fails on {} -> {}", palette.ink, palette.bg, fixed)
            palette.ink = fixed
            palette.soft = fixed
