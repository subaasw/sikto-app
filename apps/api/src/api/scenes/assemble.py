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
    Narration,
    Scene,
    SceneKind,
    SlideDraft,
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


def hero_layout(
    sid: str,
    heading: str,
    bullets: list[str],
    image_src: str,
    *,
    narration: str,
    caption: str | None = None,
    delivery: str = "neutral",
    emphasis: list[str] | None = None,
) -> Scene:
    """Archetype: heading + up to ~3 bullets in a left column, a graphic on the
    right. The graphic is the visible upgrade over a plain text slide."""
    left_specs: list[tuple[Element, float]] = [
        (Element(id=f"{sid}-h", type=ElementType.heading, text=heading, emphasis=emphasis or None), _W_HEADING)
    ]
    left_specs.extend(
        (Element(id=f"{sid}-b{i}", type=ElementType.bullets, items=[b], emphasis=emphasis or None), _W_BULLET)
        for i, b in enumerate(bullets)
    )
    elements = _layout_block(left_specs, x=0.06, width=0.50)
    elements.append(
        Element(
            id=f"{sid}-img",
            type=ElementType.image,
            src=image_src,
            frame=Frame(x=0.60, y=0.30, w=0.34, h=0.40),
        )
    )
    animations = [
        Animation(
            target_id=el.id,
            type=AnimationType.fade_in if i == 0 else AnimationType.reveal,
            at_ms=i * 280,
        )
        for i, el in enumerate(elements)
    ]
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=narration, caption=caption, delivery=delivery),
        elements=elements,
        animations=animations,
    )


def poster_layout(
    sid: str,
    heading: str,
    image_src: str,
    *,
    narration: str,
    caption: str | None = None,
    delivery: str = "neutral",
    emphasis: list[str] | None = None,
) -> Scene:
    """Marketing archetype: a dominant image fills the frame with a single punchy
    headline below it — minimal text, visual-first. No bullets."""
    image = Element(
        id=f"{sid}-img",
        type=ElementType.image,
        src=image_src,
        frame=Frame(x=0.16, y=0.08, w=0.68, h=0.56),
    )
    head = Element(
        id=f"{sid}-h",
        type=ElementType.heading,
        text=heading,
        emphasis=emphasis or None,
        frame=Frame(x=0.08, y=0.66, w=0.84, h=0.14),
    )
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=narration, caption=caption, delivery=delivery),
        elements=[image, head],
        animations=[
            Animation(target_id=image.id, type=AnimationType.fade_in, at_ms=0),
            Animation(target_id=head.id, type=AnimationType.reveal, at_ms=260),
        ],
    )


def poster_text_layout(
    sid: str,
    heading: str,
    *,
    narration: str,
    caption: str | None = None,
    delivery: str = "neutral",
    emphasis: list[str] | None = None,
) -> Scene:
    """Marketing fallback when no image resolves: one big bold headline, centred.
    The animated texture + motion carry the frame; the narration carries detail."""
    head = Element(
        id=f"{sid}-h",
        type=ElementType.heading,
        text=heading,
        emphasis=emphasis or None,
        frame=Frame(x=0.1, y=0.34, w=0.8, h=0.32),
    )
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=narration, caption=caption, delivery=delivery),
        elements=[head],
        animations=[Animation(target_id=head.id, type=AnimationType.fade_in, at_ms=0)],
    )


def icon_grid_layout(
    sid: str,
    heading: str,
    items: list[tuple[str, str]],
    *,
    narration: str,
    caption: str | None = None,
    delivery: str = "neutral",
    emphasis: list[str] | None = None,
) -> Scene:
    """Archetype: a heading over 2-4 columns, each an icon above a short label —
    turns a plain bullet list into a visual grid. `items` is (label, icon_src)."""
    n = len(items)
    gap = 0.04
    col_w = (_W - gap * (n - 1)) / n
    top, icon_h = 0.34, 0.26
    label_y, label_h = top + icon_h + 0.02, 0.14
    heading_el = Element(
        id=f"{sid}-h", type=ElementType.heading, text=heading, emphasis=emphasis or None,
        frame=Frame(x=_X, y=0.12, w=_W, h=0.16),
    )
    elements: list[Element] = [heading_el]
    animations: list[Animation] = [Animation(target_id=heading_el.id, type=AnimationType.fade_in, at_ms=0)]
    for i, (label, icon_src) in enumerate(items):
        col_x = _X + i * (col_w + gap)
        icon = Element(
            id=f"{sid}-i{i}", type=ElementType.image, src=icon_src,
            frame=Frame(x=round(col_x + col_w * 0.18, 4), y=top, w=round(col_w * 0.64, 4), h=icon_h),
        )
        text = Element(
            id=f"{sid}-l{i}", type=ElementType.text, text=label,
            frame=Frame(x=round(col_x, 4), y=round(label_y, 4), w=round(col_w, 4), h=label_h),
        )
        elements += [icon, text]
        at = (i + 1) * 260
        animations.append(Animation(target_id=icon.id, type=AnimationType.fade_in, at_ms=at))
        animations.append(Animation(target_id=text.id, type=AnimationType.reveal, at_ms=at))
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=narration, caption=caption, delivery=delivery),
        elements=elements,
        animations=animations,
    )


def presenter_layout(
    sid: str,
    heading: str,
    bullets: list[str],
    *,
    narration: str,
    emotion: str = "neutral",
    caption: str | None = None,
    delivery: str = "neutral",
    emphasis: list[str] | None = None,
) -> Scene:
    """Archetype: a procedural stick-figure presenter on the left lip-syncing the
    narration, with heading + bullets in the right column."""
    figure = Element(
        id=f"{sid}-fig",
        type=ElementType.character,
        frame=Frame(x=0.05, y=0.16, w=0.30, h=0.66),
        style={"emotion": emotion},
    )
    right_specs: list[tuple[Element, float]] = [
        (Element(id=f"{sid}-h", type=ElementType.heading, text=heading, emphasis=emphasis or None), _W_HEADING)
    ]
    right_specs.extend(
        (Element(id=f"{sid}-b{i}", type=ElementType.bullets, items=[b], emphasis=emphasis or None), _W_BULLET)
        for i, b in enumerate(bullets)
    )
    body = _layout_block(right_specs, x=0.40, width=0.54)
    elements = [figure, *body]
    animations = [Animation(target_id=figure.id, type=AnimationType.fade_in, at_ms=0)]
    animations += [
        Animation(
            target_id=el.id,
            type=AnimationType.fade_in if i == 0 else AnimationType.reveal,
            at_ms=(i + 1) * 280,
        )
        for i, el in enumerate(body)
    ]
    return Scene(
        id=sid,
        kind=SceneKind.slide,
        narration=Narration(text=narration, caption=caption, delivery=delivery),
        elements=elements,
        animations=animations,
    )


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
        kind=SceneKind.slide,
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
