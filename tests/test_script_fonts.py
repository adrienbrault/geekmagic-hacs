"""Scripts Nunito and DejaVu lack draw in the embedded Noto faces (issue #320).

Home Assistant OS ships no fonts for CJK, Thai, Arabic or Devanagari, and
the engine only falls back to fonts a stack names, then to the host's: a
stack without the embedded faces draws those scripts as missing-glyph
boxes there, and measures them at the box's advance. The render checks
compare a theme's stack with the faces named explicitly, so they also
hold on hosts that do have such fonts (macOS), where the bug would show
as the host's face.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import ImageChops

from custom_components.geekmagic import htmldoc
from custom_components.geekmagic.const import SCRIPT_FAMILIES
from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.widgets._textfit import metrics_for
from custom_components.geekmagic.widgets.theme import THEMES

FONTS = Path(htmldoc.__file__).parent / "fonts"
FAMILY_FILES = {
    "Noto Sans JP": "NotoSansJP-JIS.ttf",
    "Noto Sans SC": "NotoSansSC-GB2312.ttf",
    "Noto Sans TC": "NotoSansTC-Big5.ttf",
    "Noto Sans KR": "NotoSansKR-Hangul.ttf",
    "Noto Sans Thai": "NotoSansThai.ttf",
    "Noto Sans Arabic": "NotoSansArabic.ttf",
    "Noto Sans Devanagari": "NotoSansDevanagari.ttf",
}
SAMPLES = {
    "japanese": "夜に駆ける",
    "simplified": "周杰伦晴天",  # 伦 is GB2312-only, the rest shared with JP
    "traditional": "臺灣鄉愁",  # 臺/鄉/愁 come from the Big5 face
    "korean": "아이유",
    "thai": "ภาษาไทย",
    "arabic": "العربية",
    "urdu": "اردو ہے",  # heh goal and yeh barree: letters DejaVu Sans lacks
    "devanagari": "हिन्दी",
}


def _names(data: bytes) -> dict[int, str]:
    """The Windows-platform strings of an sfnt ``name`` table, by name ID."""
    num_tables = struct.unpack_from(">H", data, 4)[0]
    for i in range(num_tables):
        tag, _checksum, offset, _length = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        if tag == b"name":
            break
    else:
        raise AssertionError("no name table")
    _fmt, count, strings = struct.unpack_from(">HHH", data, offset)
    names = {}
    for r in range(count):
        platform, _enc, _lang, name_id, length, str_off = struct.unpack_from(
            ">HHHHHH", data, offset + 6 + 12 * r
        )
        if platform == 3:
            start = offset + strings + str_off
            names[name_id] = data[start : start + length].decode("utf-16-be")
    return names


def test_stack_list_and_embedded_files_agree() -> None:
    assert [f.strip().strip('"') for f in SCRIPT_FAMILIES.split(",")] == list(FAMILY_FILES)
    for name in FAMILY_FILES.values():
        assert name in htmldoc._FONT_FILES


@pytest.mark.parametrize(("family", "file"), FAMILY_FILES.items())
def test_font_registers_as_the_family_the_stacks_name(family, file) -> None:
    """The typographic family (ID 16) when the font has one, else ID 1. The
    CJK faces' ID 1 names their default instance ("Noto Sans JP Thin"):
    losing ID 16 in the subset registers them under that name."""
    names = _names((FONTS / file).read_bytes())
    assert names.get(16, names.get(1)) == family


@pytest.mark.parametrize("theme", list(THEMES.values()), ids=list(THEMES))
def test_every_stack_names_the_script_faces_after_its_own(theme) -> None:
    """Right after the theme's face (it sets the line box), and before
    DejaVu Sans when that is only a fallback."""
    assert theme.font_stack.split(",", 1)[1].lstrip().startswith(SCRIPT_FAMILIES)


def test_html_widgets_get_the_list_as_a_variable() -> None:
    assert f"--script-fonts: {SCRIPT_FAMILIES};" in htmldoc.theme_css_variables(THEMES["watchos"])


@pytest.fixture
def engine():
    engine = get_engine()
    if engine is None:
        pytest.skip(reason="blitz-py is not installed")
    return engine


def _render(theme, text: str, style: str):
    doc = htmldoc.build_cell_document(f'<div class="t-hero" style="{style}">{text}</div>', theme)
    img = htmldoc.render_document(doc, 240, 80)
    assert img is not None
    assert img.getbbox() is not None, "nothing was drawn"
    return img


def _reference_stack(theme) -> str:
    """The theme's own face, then the script faces: what the stack must draw."""
    first = theme.font_stack.split(",")[0]
    return f"{first}, {SCRIPT_FAMILIES}".replace('"', "'")


@pytest.mark.parametrize("theme", ["watchos", "retro"])
@pytest.mark.parametrize("text", SAMPLES.values(), ids=list(SAMPLES))
def test_theme_stack_draws_the_script_in_the_embedded_faces(engine, theme, text) -> None:
    """Nunito and DejaVu themes both reach the faces, pixel for pixel."""
    t = THEMES[theme]
    reference = _render(t, text, f"font-family: {_reference_stack(t)}")
    assert ImageChops.difference(_render(t, text, ""), reference).getbbox() is None


def test_weight_axis_survives_the_subset(engine) -> None:
    t = THEMES["watchos"]
    regular = _render(t, SAMPLES["korean"], "font-weight: 400")
    bold = _render(t, SAMPLES["korean"], "font-weight: 800")
    assert ImageChops.difference(regular, bold).getbbox() is not None


@pytest.mark.parametrize("theme", ["watchos", "retro"])
@pytest.mark.parametrize("text", SAMPLES.values(), ids=list(SAMPLES))
def test_measurement_uses_the_embedded_faces(engine, theme, text) -> None:
    """Fitting measures the advance the document draws."""
    t = THEMES[theme]
    width = metrics_for(t).width(text, 20, "bold")
    expected, _h = engine.measure_text(
        text, font_size=20.0, font_family=_reference_stack(t).replace("'", '"'), font_weight=700.0
    )
    assert width == pytest.approx(expected, abs=0.5)


@pytest.mark.parametrize("text", [SAMPLES[k] for k in ("japanese", "simplified", "traditional")])
def test_han_and_kana_measure_one_em_per_glyph(engine, text) -> None:
    """Not the missing-glyph box's half em. (Noto's Hangul is 0.92 em.)"""
    assert metrics_for(THEMES["watchos"]).width(text, 20, "bold") == pytest.approx(
        20 * len(text), abs=0.5
    )
