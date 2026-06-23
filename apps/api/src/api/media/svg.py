"""Recolor SVGs at use-time so a stored vector icon can be themed to a scene's
palette. We keep the SVG source editable (stored as-is) and bake a concrete
color in only when it's used — the render pipeline consumes images as <img src>,
so currentColor wouldn't apply; the color has to be in the bytes.

ponytail: monochrome-icon recolor. Multi-color logos/illustrations would collapse
to one color, so callers only recolor assets of kind "icon". Upgrade path: detect
distinct fills and remap a palette instead of flattening.
"""

import base64
import re

_CURRENTCOLOR = re.compile(r"currentColor", re.I)
# fill="#abc" / stroke="red" — but never fill="none" (structural) or url(...) (gradient ref)
_ATTR = re.compile(r'\b(fill|stroke)="(?!none\b)(?!url\()[^"]*"', re.I)
# inline style: "fill:#abc;stroke:red" — same exclusions
_STYLE = re.compile(r"\b(fill|stroke)\s*:\s*(?!none\b)(?!url\()[^;\"'}]+", re.I)


def recolor_svg(svg: str, color: str) -> str:
    svg, n_cur = _CURRENTCOLOR.subn(color, svg)
    svg, n_attr = _ATTR.subn(rf'\1="{color}"', svg)
    svg = _STYLE.sub(rf"\1:{color}", svg)
    if n_cur == 0 and n_attr == 0:
        # No explicit color anywhere → paths default to black. Drive it from root.
        svg = re.sub(r"<svg\b", f'<svg fill="{color}"', svg, count=1)
    return svg


def svg_data_uri(svg: str) -> str:
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


def demo() -> None:
    c = "#84cc16"
    # explicit fill recolored, fill="none" preserved
    out = recolor_svg('<svg><path fill="#000" d="z"/><path fill="none"/></svg>', c)
    assert f'fill="{c}"' in out and 'fill="none"' in out
    # currentColor swapped
    assert c in recolor_svg('<svg><path fill="currentColor"/></svg>', c)
    # no color anywhere → root fill injected
    assert f'<svg fill="{c}"' in recolor_svg("<svg><path d=\"z\"/></svg>", c)
    # gradient ref left alone
    assert "url(#g)" in recolor_svg('<svg><rect fill="url(#g)"/></svg>', c)
    # round-trips through a data uri
    assert svg_data_uri("<svg/>").startswith("data:image/svg+xml;base64,")
    print("ok")


if __name__ == "__main__":
    demo()
