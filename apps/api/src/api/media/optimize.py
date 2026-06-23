"""Shrink uploaded images before we store them: auto-orient, cap the long edge,
re-encode to WebP, drop metadata. Keeps the library + render fast and small.

SVG and GIF pass through untouched — SVG is already scalable vector text, GIF
may be animated and WebP single-frame save would silently kill the animation.
"""

from io import BytesIO

from PIL import Image, ImageOps

MAX_EDGE = 1600  # px; bigger than any scene needs, small enough to stay light
WEBP_QUALITY = 82
PASSTHROUGH = {".svg", ".gif"}


def optimize_image(data: bytes, filename: str) -> tuple[bytes, str]:
    """Return (bytes, extension) ready to store. On any decode failure or for
    passthrough types, return the input unchanged so an upload never fails here."""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext in PASSTHROUGH:
        return data, ext or ".bin"
    try:
        img = ImageOps.exif_transpose(Image.open(BytesIO(data)))
    except Exception:
        return data, ext or ".bin"  # ponytail: not a decodable raster, store as-is

    img.thumbnail((MAX_EDGE, MAX_EDGE))  # only downscales; no-op if already small
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.mode else "RGB")
    out = BytesIO()
    img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue(), ".webp"


def demo() -> None:
    # 4000px solid image -> capped at MAX_EDGE, re-encoded as webp, smaller bytes
    buf = BytesIO()
    Image.new("RGB", (4000, 3000), (10, 120, 200)).save(buf, format="PNG")
    raw = buf.getvalue()
    out, ext = optimize_image(raw, "big.png")
    assert ext == ".webp", ext
    assert max(Image.open(BytesIO(out)).size) == MAX_EDGE
    assert len(out) < len(raw)
    # svg passes through verbatim
    svg = b"<svg/>"
    assert optimize_image(svg, "logo.svg") == (svg, ".svg")
    # garbage bytes don't blow up
    assert optimize_image(b"nope", "x.png") == (b"nope", ".png")
    print("ok")


if __name__ == "__main__":
    demo()
