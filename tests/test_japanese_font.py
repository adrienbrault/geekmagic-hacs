"""Japanese text draws in the embedded Noto Sans JP on every theme (issue #320).

Home Assistant OS ships no Japanese fonts, and the engine only falls back
to fonts a stack names, then to the host's: a stack without the embedded
face draws Japanese as missing-glyph boxes there, and measures it at the
box's half-width advance. The render checks compare a theme's stack with
the face named explicitly, so they also hold on hosts that do have
Japanese fonts (macOS), where the bug would show as the host's face.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import ImageChops

from custom_components.geekmagic import htmldoc
from custom_components.geekmagic.const import JAPANESE_FAMILY
from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.widgets._textfit import metrics_for
from custom_components.geekmagic.widgets.theme import THEMES

FONT = Path(htmldoc.__file__).parent / "fonts" / "NotoSansJP-JIS.ttf"
TEXT = "夜に駆ける"


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


def test_font_is_embedded() -> None:
    assert FONT.name in htmldoc._FONT_FILES


def test_font_registers_as_the_family_the_stacks_name() -> None:
    """The variable font's family is its typographic name (ID 16); without
    it, it registers as its default instance, "Noto Sans JP Thin"."""
    assert _names(FONT.read_bytes()).get(16) == JAPANESE_FAMILY.strip('"')


@pytest.mark.parametrize("theme", list(THEMES.values()), ids=list(THEMES))
def test_every_stack_names_the_japanese_face_before_its_generic(theme) -> None:
    families = [f.strip() for f in theme.font_stack.split(",")]
    assert JAPANESE_FAMILY in families[:-1]


@pytest.fixture
def engine():
    engine = get_engine()
    if engine is None:
        pytest.skip(reason="blitz-py is not installed")
    return engine


def _render(theme, style: str):
    doc = htmldoc.build_cell_document(f'<div class="t-hero" style="{style}">{TEXT}</div>', theme)
    img = htmldoc.render_document(doc, 240, 80)
    assert img is not None
    assert img.getbbox() is not None, "nothing was drawn"
    return img


@pytest.mark.parametrize("theme", ["watchos", "retro"])
def test_theme_stack_draws_japanese_in_the_embedded_face(engine, theme) -> None:
    """Nunito and DejaVu themes both reach the face, pixel for pixel.

    The reference keeps the stack's first family: it sets the line box.
    """
    t = THEMES[theme]
    first = t.font_stack.split(",")[0].replace('"', "'")
    reference = _render(t, f"font-family: {first}, 'Noto Sans JP'")
    assert ImageChops.difference(_render(t, ""), reference).getbbox() is None


def test_weight_axis_survives_the_subset(engine) -> None:
    t = THEMES["watchos"]
    regular = _render(t, "font-family: 'Noto Sans JP'; font-weight: 400")
    bold = _render(t, "font-family: 'Noto Sans JP'; font-weight: 800")
    assert ImageChops.difference(regular, bold).getbbox() is not None


@pytest.mark.parametrize("theme", ["watchos", "retro"])
def test_measurement_uses_the_embedded_face(engine, theme) -> None:
    """Fitting measures the advance the document draws: one em per glyph."""
    width = metrics_for(THEMES[theme]).width(TEXT, 20, "bold")
    expected, _h = engine.measure_text(
        TEXT, font_size=20.0, font_family="Noto Sans JP", font_weight=700.0
    )
    assert width == pytest.approx(expected, abs=0.5)
    assert width == pytest.approx(20 * len(TEXT), abs=0.5)
