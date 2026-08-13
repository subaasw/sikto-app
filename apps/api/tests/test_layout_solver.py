from api.scenes.layout import solve_layout
from api.scenes.schema import Layer


def _no_overlap(frames, tol=0.02):
    for i, a in enumerate(frames):
        for b in frames[i + 1 :]:
            dx = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            dy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
            if dx > tol and dy > tol:
                return False
    return True


def test_frames_in_bounds_and_non_bg_dont_overlap():
    layers = [
        Layer(kind="bg-texture", region="full-bleed", size="full"),
        Layer(kind="headline", content="Title", region="upper", size="lg"),
        Layer(kind="image", content="x.svg", region="center", size="md", depth=1),
        Layer(kind="caption", content="note", region="lower-third", size="sm"),
    ]
    out = solve_layout(layers)
    assert all(l.frame is not None for l in out)
    for l in out:
        f = l.frame
        assert 0 <= f.x and 0 <= f.y and f.x + f.w <= 1.0001 and f.y + f.h <= 1.0001
    assert out[0].frame.w == 1 and out[0].frame.h == 1  # bg full-bleed
    content_frames = [l.frame for l in out if l.kind != "bg-texture"]
    assert _no_overlap(content_frames)
