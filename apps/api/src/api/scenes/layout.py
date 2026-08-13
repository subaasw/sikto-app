"""Deterministic placement: semantic region + size -> Frame.

The LLM composes layers; this owns pixels (LLMs are bad at coordinates). Pure
and testable.

Approach: bg-texture / full-bleed / size=full fill the stage. Content layers are
placed TOP-DOWN in region order (a `center` image never gets stranded above an
`upper` headline just because of array order), each anchored by its region and
sized by its `size`, then pushed down off whatever sits above it and, if it still
collides at the bottom, shrunk to fit. Result: no overlaps, all in-bounds.
"""

from api.scenes.schema import Frame, Layer

# region -> anchor centre (cx, cy) in the 0..1 square
_ANCHOR = {
    "full-bleed": (0.5, 0.5),
    "center": (0.5, 0.5),
    "left": (0.30, 0.5),
    "right": (0.70, 0.5),
    "upper": (0.5, 0.18),
    "lower": (0.5, 0.82),
    "upper-third": (0.5, 0.13),
    "lower-third": (0.5, 0.87),
}
# top-down placement order (smaller = higher on the stage)
_REGION_RANK = {
    "upper-third": 0,
    "upper": 1,
    "left": 2,
    "right": 2,
    "center": 2,
    "lower": 3,
    "lower-third": 4,
}
# size -> (w, h) fraction of the stage
_SIZE = {
    "sm": (0.40, 0.14),
    "md": (0.56, 0.26),
    "lg": (0.72, 0.40),
    "full": (1.0, 1.0),
}
# text reads in a tight band regardless of `size`; only images want the tall box
_TEXT_KINDS = {"headline", "caption", "sticker"}
_TEXT_MAX_H = 0.22
_MARGIN = 0.04  # keep content off the very edges
_GAP = 0.02


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def solve_layout(layers: list[Layer]) -> list[Layer]:
    backdrops: list[Layer] = []
    content: list[Layer] = []
    for layer in layers:
        l = layer.model_copy()
        if l.kind == "bg-texture" or l.region == "full-bleed" or l.size == "full":
            l.frame = Frame(x=0.0, y=0.0, w=1.0, h=1.0)
            backdrops.append(l)
        else:
            content.append(l)

    # place top-down so each layer only has to avoid what's above it
    content.sort(key=lambda l: _REGION_RANK.get(l.region, 2))
    placed: list[Layer] = []
    for l in content:
        w, h = _SIZE[l.size]
        if l.kind in _TEXT_KINDS:
            h = min(h, _TEXT_MAX_H)
        cx, cy = _ANCHOR[l.region]
        x = _clamp(cx - w / 2, _MARGIN, 1.0 - _MARGIN - w)
        y = _clamp(cy - h / 2, _MARGIN, 1.0 - _MARGIN - h)
        # push below anything already placed that it overlaps
        for p in placed:
            assert p.frame is not None
            overlaps_x = min(x + w, p.frame.x + p.frame.w) - max(x, p.frame.x) > _GAP
            if overlaps_x and (min(y + h, p.frame.y + p.frame.h) - max(y, p.frame.y)) > _GAP:
                y = p.frame.y + p.frame.h + _GAP
        # if it now runs off the bottom, pull up then shrink to fit the gap
        if y + h > 1.0 - _MARGIN:
            y = max(_MARGIN, 1.0 - _MARGIN - h)
            top = max((p.frame.y + p.frame.h for p in placed if p.frame), default=_MARGIN)
            h = min(h, max(0.08, 1.0 - _MARGIN - max(y, top)))
            y = max(y, top + _GAP) if top + _GAP + h <= 1.0 - _MARGIN else y
        l.frame = Frame(x=round(x, 4), y=round(y, 4), w=round(w, 4), h=round(h, 4))
        placed.append(l)
    return backdrops + placed
