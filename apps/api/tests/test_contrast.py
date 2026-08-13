"""The legibility gate: shipped palettes pass, director repaints get repaired."""

from api.scenes.contrast import MIN_TEXT_CONTRAST, contrast_ratio, ensure_legible, legible_ink
from api.scenes.schema import SceneTheme
from api.scenes.templates import TEMPLATES


def test_contrast_ratio_known_values():
    assert round(contrast_ratio("#000000", "#ffffff")) == 21
    assert round(contrast_ratio("#ffffff", "#ffffff")) == 1


def test_shipped_template_palettes_meet_floors():
    for name, tmpl in TEMPLATES.items():
        p = tmpl.theme.palette
        assert p is not None, name
        assert contrast_ratio(p.ink, p.bg) >= 4.5, f"{name}: ink/bg"
        assert contrast_ratio(p.soft, p.bg) >= 3.0, f"{name}: soft/bg"
        assert contrast_ratio(p.accent, p.bg) >= 3.0, f"{name}: accent/bg"
        assert contrast_ratio(p.accent2, p.bg) >= 3.0, f"{name}: accent2/bg"
        # legacy trio stays in sync with the palette (old consumers read it)
        assert tmpl.theme.background == p.bg, name
        assert tmpl.theme.foreground == p.ink, name
        assert tmpl.theme.primary == p.accent, name


def test_legible_ink_keeps_good_pairs_and_repairs_bad_ones():
    assert legible_ink("#ffffff", "#1b2a24") == "#1b2a24"
    fixed = legible_ink("#f4f6f2", "#f0f0e8")  # near-white on near-white
    assert contrast_ratio(fixed, "#f4f6f2") >= MIN_TEXT_CONTRAST


def test_ensure_legible_repairs_theme_and_palette():
    theme = SceneTheme(background="#101010", foreground="#1a1a1a")  # unreadable
    ensure_legible(theme)
    assert contrast_ratio(theme.foreground, theme.background) >= MIN_TEXT_CONTRAST

    bad = TEMPLATES["explainer"].theme.model_copy(deep=True)
    assert bad.palette is not None
    bad.palette.ink = bad.palette.bg  # invisible text
    ensure_legible(bad)
    assert contrast_ratio(bad.palette.ink, bad.palette.bg) >= MIN_TEXT_CONTRAST
