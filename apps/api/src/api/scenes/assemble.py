"""Turn LLM-produced drafts into laid-out, valid `Scene`s.

Each draft is placed by a small template chosen from its content (title /
bullets / equation / diagram). Templates size every element to its content and
centre the whole block in the canvas, so scenes are balanced (no dead space)
and stay inside the frame — the model never reasons about coordinates.
"""

import re

from api.scenes.schema import (
    Animation,
    AnimationType,
    DiagramDraft,
    Element,
    ElementType,
    Frame,
    ManimDraft,
    Mark,
    Narration,
    Scene,
    SceneKind,
    SlideDraft,
    WhiteboardDraft,
)

# Content band (the usable area, leaving margins top/bottom and sides). The
# bottom is pulled up so the caption pill never overlaps slide content.
_X = 0.08
_W = 0.84
_BAND_TOP = 0.14
_BAND_BOTTOM_CAPTION = 0.80  # reserve the lower ~20% for captions
_BAND_BOTTOM_PLAIN = 0.90
_GAP = 0.03

# Relative vertical weights per role. The renderer fits text to its box (see
# scene-kit fit.ts), so exact heights no longer matter — only sensible
# proportions. This replaces the old, fragile char-count height estimation.
_W_HEADING = 1.5
_W_BULLET = 1.0
_W_TEXT = 0.9
_W_LATEX = 1.8
_W_TITLE = 2.2
_W_SUBTITLE = 0.9


def _bullet_specs(sid: str, bullets: list[str]) -> list[tuple[Element, float]]:
    """One element per bullet so they can reveal individually as the narrator
    reaches each point."""
    return [
        (Element(id=f"{sid}-b{i}", type=ElementType.bullets, items=[b]), _W_BULLET)
        for i, b in enumerate(bullets)
    ]


def _layout_block(
    specs: list[tuple[Element, float]],
    *,
    captioned: bool = True,
    gap: float = _GAP,
    x: float = _X,
    width: float = _W,
) -> list[Element]:
    """Stack elements top-to-bottom in the column `[x, x+width]`, dividing the
    content band by their relative weights. Fills the band proportionally; the
    renderer fits + centres text within each frame, so content reads balanced
    and never overflows."""
    band_bottom = _BAND_BOTTOM_CAPTION if captioned else _BAND_BOTTOM_PLAIN
    band = band_bottom - _BAND_TOP
    total_gap = gap * max(0, len(specs) - 1)
    total_weight = sum(w for _, w in specs) or 1.0
    avail = max(0.0, band - total_gap)
    y = _BAND_TOP
    out: list[Element] = []
    for el, weight in specs:
        h = avail * (weight / total_weight)
        el.frame = Frame(x=x, y=round(y, 4), w=width, h=round(h, 4))
        out.append(el)
        y += h + gap
    return out


_EMPHASISABLE = {ElementType.heading, ElementType.bullets, ElementType.text}


def _slide(sid: str, draft: SlideDraft, specs: list[tuple[Element, float]]) -> Scene:
    elements = _layout_block(specs)
    # Mark key terms so the renderer can highlight them (hybrid: LLM-suggested).
    emphasis = draft.emphasis or None
    if emphasis:
        for el in elements:
            if el.type in _EMPHASISABLE:
                el.emphasis = emphasis
    # Heading fades in; body elements rise in for a touch of motion.
    animations = [
        Animation(
            target_id=el.id,
            type=AnimationType.fade_in if i == 0 else AnimationType.reveal,
            at_ms=i * 300,
        )
        for i, el in enumerate(elements)
    ]
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=draft.narration, caption=draft.caption, delivery=draft.delivery),
        visual_query=draft.visual,
        visual_kind=draft.visual_kind,
        elements=elements,
        animations=animations,
    )


def slide_scene(index: int, draft: SlideDraft) -> Scene:
    """Pick a template from the draft's content and lay it out."""
    sid = f"s{index}"
    has_bullets = bool(draft.bullets)
    # Guard against the model emitting the literal string "None"/"null" as latex,
    # which otherwise renders a bogus equation and blocks art direction.
    has_latex = bool(draft.latex and draft.latex.strip().lower() not in ("none", "null"))

    if has_latex:  # equation template: heading + big formula (+ supporting bullets)
        specs: list[tuple[Element, float]] = [
            (Element(id=f"{sid}-h", type=ElementType.heading, text=draft.heading), _W_HEADING),
            (Element(id=f"{sid}-l", type=ElementType.latex, latex=draft.latex), _W_LATEX),
        ]
        specs.extend(_bullet_specs(sid, draft.bullets[:3]))
        return _slide(sid, draft, specs)

    if not has_bullets:  # title template: large heading (+ optional subtitle)
        specs = [(Element(id=f"{sid}-h", type=ElementType.heading, text=draft.heading), _W_TITLE)]
        if draft.caption:
            specs.append(
                (Element(id=f"{sid}-sub", type=ElementType.text, text=draft.caption), _W_SUBTITLE)
            )
        return _slide(sid, draft, specs)

    # bullets template: heading + one element per bullet (build one at a time).
    specs = [(Element(id=f"{sid}-h", type=ElementType.heading, text=draft.heading), _W_HEADING)]
    specs.extend(_bullet_specs(sid, draft.bullets))
    return _slide(sid, draft, specs)


def _card(eid: str, label: str, frame: Frame) -> Element:
    return Element(id=eid, type=ElementType.card, text=label, frame=frame)


def _arrow(eid: str, direction: str, label: str | None, frame: Frame) -> Element:
    return Element(
        id=eid,
        type=ElementType.shape,
        shape="arrow",
        text=label or None,
        frame=frame,
        style={"dir": direction},
    )


def _flow_elements(sid: str, nodes: list[str], connectors: list[str]) -> list[Element]:
    """Boxes left-to-right joined by right-pointing arrows. Arrows get a wide
    gap so connector labels never spill onto the cards."""
    n = len(nodes)
    arrow_w = 0.09
    card_w = (_W - (n - 1) * arrow_w) / n
    card_h, card_y = 0.32, 0.4
    arrow_h = 0.12
    arrow_y = card_y + (card_h - arrow_h) / 2
    out: list[Element] = []
    x = _X
    for i, label in enumerate(nodes):
        out.append(_card(f"{sid}-c{i}", label, Frame(x=round(x, 4), y=card_y, w=round(card_w, 4), h=card_h)))
        x += card_w
        if i < n - 1:
            conn = connectors[i] if i < len(connectors) else None
            out.append(
                _arrow(f"{sid}-a{i}", "right", conn, Frame(x=round(x, 4), y=round(arrow_y, 4), w=arrow_w, h=arrow_h))
            )
            x += arrow_w
    return out


def _stack_elements(sid: str, nodes: list[str], connectors: list[str]) -> list[Element]:
    """Boxes top-to-bottom joined by down-pointing arrows, centred in the band."""
    n = len(nodes)
    top, bottom = 0.3, 0.88
    arrow_h = 0.05
    card_h = (bottom - top - (n - 1) * arrow_h) / n
    card_x, card_w = 0.28, 0.44
    out: list[Element] = []
    y = top
    for i, label in enumerate(nodes):
        out.append(_card(f"{sid}-c{i}", label, Frame(x=card_x, y=round(y, 4), w=card_w, h=round(card_h, 4))))
        y += card_h
        if i < n - 1:
            conn = connectors[i] if i < len(connectors) else None
            out.append(
                _arrow(f"{sid}-a{i}", "down", conn, Frame(x=0.46, y=round(y, 4), w=0.08, h=arrow_h))
            )
            y += arrow_h
    return out


def _compare_elements(sid: str, nodes: list[str]) -> list[Element]:
    """A two-column grid of boxes (no arrows) for side-by-side comparison."""
    top, bottom, gap = 0.32, 0.88, 0.04
    rows = (len(nodes) + 1) // 2
    row_h = (bottom - top - (rows - 1) * gap) / rows
    cols = [(0.08, 0.4), (0.52, 0.4)]
    out: list[Element] = []
    for i, label in enumerate(nodes):
        cx, cw = cols[i % 2]
        y = top + (i // 2) * (row_h + gap)
        out.append(_card(f"{sid}-c{i}", label, Frame(x=cx, y=round(y, 4), w=cw, h=round(row_h, 4))))
    return out


def diagram_scene(index: int, draft: DiagramDraft) -> Scene:
    sid = f"s{index}"
    heading = Element(
        id=f"{sid}-h",
        type=ElementType.heading,
        text=draft.heading,
        frame=Frame(x=_X, y=0.1, w=_W, h=0.14),
    )
    if draft.layout == "stack":
        body = _stack_elements(sid, draft.nodes, draft.connectors)
    elif draft.layout == "compare":
        body = _compare_elements(sid, draft.nodes)
    else:
        body = _flow_elements(sid, draft.nodes, draft.connectors)

    elements = [heading, *body]
    # Connectors draw themselves in (sketch/whiteboard feel); boxes & heading fade.
    animations = [
        Animation(
            target_id=el.id,
            type=AnimationType.draw if el.shape == "arrow" else AnimationType.fade_in,
            at_ms=i * 280,
        )
        for i, el in enumerate(elements)
    ]
    return Scene(
        id=sid,
        kind=SceneKind.diagram,  # keeps `elements` (cards/arrows); plan_layers skips non-slide
        narration=Narration(text=draft.narration, caption=draft.caption, delivery=draft.delivery),
        elements=elements,
        animations=animations,
    )


def manim_scene(index: int, draft: ManimDraft) -> Scene:
    sid = f"s{index}"
    return Scene(
        id=sid,
        kind=SceneKind.manim,
        narration=Narration(text=draft.narration, caption=draft.caption),
        manim_code=draft.manim_code,
        manim_entry="MainScene",
    )


def _clamp01(v: float) -> float:
    return max(0.0, min(float(v), 1.0))


# Per-kind height hint (0..1). Text marks are short; boxes/sketches enclose more.
# The renderer auto-sizes text, so this is only a placement hint, not a hard box.
_MARK_HEIGHT = {"title": 0.16, "box": 0.2, "sketch": 0.24}


def whiteboard_scene(index: int, draft: WhiteboardDraft) -> Scene:
    """Build a whiteboard scene from the director's marks. The model owns layout
    and timing; we only clamp positions into the board and resolve arrow endpoints
    (referenced by list index) to mark ids. No layout solver, no fallback — a beat
    that can't be directed is rendered as a slide by the caller."""
    sid = f"s{index}"
    marks: list[Mark] = []
    for i, m in enumerate(draft.marks[:12]):
        x = _clamp01(m.x)
        y = _clamp01(m.y)
        w = max(0.05, min(_clamp01(m.w), 1.0 - x))
        h = min(_MARK_HEIGHT.get(m.kind, 0.1), 1.0 - y)
        marks.append(
            Mark(
                id=f"{sid}m{i}",
                kind=m.kind,
                text=m.text.strip(),
                frame=Frame(x=round(x, 4), y=round(y, 4), w=round(w, 4), h=round(h, 4)),
                accent=m.accent,
                emphasis=m.emphasis,
                at=_clamp01(m.at),
                draw=max(0.2, min(float(m.draw), 3.0)),
            )
        )
    # Resolve arrows: the model references source/target by index in its own list.
    for mark, m in zip(marks, draft.marks[:12]):
        if m.kind == "arrow":
            mark.ref = marks[m.from_index].id if _in_range(m.from_index, marks) else None
            mark.to = marks[m.to_index].id if _in_range(m.to_index, marks) else None
    return Scene(
        id=sid,
        kind=SceneKind.whiteboard,
        narration=Narration(text=draft.narration, caption=draft.caption, delivery=draft.delivery),
        marks=marks,
    )


def _in_range(i: int | None, marks: list[Mark]) -> bool:
    return i is not None and 0 <= i < len(marks)


# --- scene division --------------------------------------------------------

_MAX_BULLETS_PER_SCENE = 5
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str, parts: int) -> list[str]:
    """Distribute a narration into `parts` chunks along sentence boundaries."""
    sentences = [s for s in _SENTENCE_RE.split(text.strip()) if s]
    if parts <= 1 or len(sentences) <= 1:
        return [text.strip()] + [""] * (parts - 1)
    per = max(1, round(len(sentences) / parts))
    chunks = [" ".join(sentences[i : i + per]) for i in range(0, len(sentences), per)]
    # Fold any overflow chunks into the last one so we return exactly `parts`.
    if len(chunks) > parts:
        chunks[parts - 1 :] = [" ".join(chunks[parts - 1 :])]
    while len(chunks) < parts:
        chunks.append("")
    return chunks


def _split_bullets_scene(scene: Scene) -> list[Scene]:
    """Split a slide carrying too many bullets into a few sequential scenes so
    nothing is cramped; narration is divided along sentence boundaries."""
    heading = next((e for e in scene.elements if e.type == ElementType.heading), None)
    bullets = [e for e in scene.elements if e.type == ElementType.bullets]
    if heading is None or len(bullets) <= _MAX_BULLETS_PER_SCENE:
        return [scene]

    n_parts = -(-len(bullets) // _MAX_BULLETS_PER_SCENE)  # ceil
    per = -(-len(bullets) // n_parts)  # balance across parts
    groups = [bullets[i : i + per] for i in range(0, len(bullets), per)]
    narrations = _split_sentences(scene.narration.text, len(groups))

    out: list[Scene] = []
    for gi, group in enumerate(groups):
        sid = f"{scene.id}p{gi}"
        head_text = heading.text if gi == 0 else f"{heading.text} (cont.)"
        specs: list[tuple[Element, float]] = [
            (Element(id=f"{sid}-h", type=ElementType.heading, text=head_text, emphasis=heading.emphasis), _W_HEADING)
        ]
        for bi, b in enumerate(group):
            specs.append(
                (Element(id=f"{sid}-b{bi}", type=ElementType.bullets, items=b.items, emphasis=b.emphasis), _W_BULLET)
            )
        elements = _layout_block(specs)
        animations = [
            Animation(
                target_id=el.id,
                type=AnimationType.fade_in if i == 0 else AnimationType.reveal,
                at_ms=i * 300,
            )
            for i, el in enumerate(elements)
        ]
        out.append(
            Scene(
                id=sid,
                kind=SceneKind.slide,
                narration=Narration(
                    text=narrations[gi] or scene.narration.text,
                    caption=scene.narration.caption,
                    delivery=scene.narration.delivery,
                ),
                elements=elements,
                animations=animations,
            )
        )
    return out


def divide_scenes(scenes: list[Scene]) -> list[Scene]:
    """Post-process pass: split any over-crowded scene into sequential scenes."""
    out: list[Scene] = []
    for scene in scenes:
        out.extend(_split_bullets_scene(scene) if scene.kind == SceneKind.slide else [scene])
    return out
