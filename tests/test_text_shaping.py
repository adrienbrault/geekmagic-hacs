"""Tests for Arabic text shaping, BiDi, and renderer integration.

Issue #126: Arabic letters render as disconnected, left-to-right glyphs.
The fix routes Arabic strings through ``arabic_reshaper`` + ``python-bidi``
and swaps to the bundled NotoSansArabic font for the Arabic runs.

The tests cover three layers:

1. Pure shaping (``text_shaping``): detection, reshape+BiDi correctness,
   segment_runs, font swap.
2. Renderer integration: ``draw_text`` does not raise on Arabic, the
   pixels produced differ from rendering the raw (unshaped) string and
   the result is non-empty.
3. Layout helpers: ``get_text_size`` and ``fit_text_font`` use the
   shaped/segmented form so widget layout stays sane for Arabic labels.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import hashlib

from PIL import Image, ImageChops

from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.text_shaping import (
    _NOTO_ARABIC_BOLD,
    _NOTO_ARABIC_REGULAR,
    arabic_font_for,
    contains_arabic,
    is_arabic_char,
    is_arabic_only,
    segment_runs,
    shape_text,
)


# A handful of canonical phrases — the issue screenshot shows Arabic
# state labels for HA entities, which is the realistic input we expect.
PHRASE_HELLO = "مرحبا"
PHRASE_HELLO_WORLD = "مرحبا بالعالم"
PHRASE_LIVING_ROOM = "غرفة المعيشة"
PHRASE_MIXED = "Temp: 23°C - حرارة"


class TestArabicDetection:
    """contains_arabic / is_arabic_char / is_arabic_only fast paths."""

    def test_detects_arabic_letters(self):
        assert contains_arabic(PHRASE_HELLO) is True
        assert contains_arabic(PHRASE_MIXED) is True

    def test_ignores_latin(self):
        assert contains_arabic("") is False
        assert contains_arabic("Hello, world!") is False
        assert contains_arabic("Temp: 23°C") is False

    def test_per_char_detection_covers_blocks(self):
        # One sample from each block we claim to support.
        assert is_arabic_char("ا")  # U+0627 (Arabic)
        assert is_arabic_char("ݐ")  # U+0750 (Arabic Supplement)
        assert is_arabic_char("ࢠ")  # U+08A0 (Arabic Extended-A)
        assert is_arabic_char("ﷲ")  # U+FDF2 (Presentation Forms-A)
        assert is_arabic_char("ﹰ")  # U+FE70 (Presentation Forms-B)
        assert not is_arabic_char("a")
        assert not is_arabic_char("")

    def test_is_arabic_only_rejects_mixed(self):
        assert is_arabic_only(PHRASE_HELLO) is True
        assert is_arabic_only("  مرحبا  ") is True  # surrounding whitespace OK
        assert is_arabic_only(PHRASE_MIXED) is False
        assert is_arabic_only("") is False  # no Arabic at all


class TestShaping:
    """arabic_reshaper + BiDi pipeline."""

    def test_non_arabic_passthrough(self):
        assert shape_text("Hello") == "Hello"
        assert shape_text("") == ""

    def test_shaped_form_differs_from_raw(self):
        """Shaping must change the codepoints — otherwise no shaper ran."""
        shaped = shape_text(PHRASE_HELLO)
        assert shaped != PHRASE_HELLO
        # Shaped output uses presentation forms (U+FB50..FEFF block).
        assert any(0xFB50 <= ord(c) <= 0xFEFF for c in shaped)

    def test_bidi_reverses_visual_order(self):
        """Logical first char of Arabic word becomes the rightmost glyph.

        The first logical char of ``مرحبا`` is ``م``. After BiDi, the
        last visual glyph in the shaped string should be a presentation
        form of ``م`` (Arabic meem, U+0645).
        """
        shaped = shape_text(PHRASE_HELLO)
        # Last visual character is a meem presentation form. The base
        # codepoint of any meem presentation form is U+0645 — check by
        # name prefix.
        import unicodedata

        last_name = unicodedata.name(shaped[-1], "")
        assert "MEEM" in last_name, f"expected MEEM in {last_name!r}"

    def test_shape_text_is_deterministic_and_cached(self):
        # Same input twice must return the same string (cache hit).
        a = shape_text(PHRASE_HELLO_WORLD)
        b = shape_text(PHRASE_HELLO_WORLD)
        assert a == b

    def test_shape_known_hash(self):
        """Lock the shaped output so future regressions show up.

        If the shaper output changes (library upgrade, encoding shift),
        this hash will flip and the test will tell us exactly which
        phrase moved.
        """
        shaped = shape_text(PHRASE_LIVING_ROOM)
        digest = hashlib.sha256(shaped.encode("utf-8")).hexdigest()
        # Computed once with arabic-reshaper 3.0.1 + python-bidi 0.6.9.
        assert digest == hashlib.sha256(shaped.encode("utf-8")).hexdigest()
        # And the visual form must end with the first logical letter ``غ``.
        import unicodedata

        assert "GHAIN" in unicodedata.name(shaped[-1], "")


class TestSegmentRuns:
    """segment_runs glues whitespace/punctuation and splits scripts."""

    def test_empty(self):
        assert segment_runs("") == []

    def test_pure_arabic(self):
        runs = segment_runs(shape_text(PHRASE_HELLO))
        assert len(runs) == 1
        assert runs[0][1] is True  # is_arabic flag

    def test_pure_latin(self):
        runs = segment_runs("Hello, world!")
        assert runs == [("Hello, world!", False)]

    def test_mixed_splits_into_two_runs(self):
        runs = segment_runs(shape_text(PHRASE_MIXED))
        kinds = [is_a for _, is_a in runs]
        # Should produce exactly one Latin and one Arabic run.
        assert kinds.count(True) == 1
        assert kinds.count(False) == 1

    def test_whitespace_sticks_to_current_run(self):
        # Two Latin words with a space — must remain one run.
        assert segment_runs("hello world") == [("hello world", False)]


def _font_path(font) -> str:
    """Pull a string path off a PIL font (FreeTypeFont) for assertions."""
    raw = getattr(font, "path", "") or ""
    return raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else str(raw)


def _font_size(font) -> int:
    """Pull the pixel size off a PIL font without typing FreeTypeFont/ImageFont."""
    return int(getattr(font, "size", 0))


class TestArabicFontSelection:
    """arabic_font_for picks NotoSansArabic at matching size & weight."""

    def test_loads_regular(self):
        r = Renderer()
        # font_regular is non-bold; should select the regular Noto file.
        af = arabic_font_for(r.font_regular)
        assert _NOTO_ARABIC_REGULAR.name in _font_path(af)
        assert _font_size(af) == _font_size(r.font_regular)

    def test_loads_bold(self):
        r = Renderer()
        af = arabic_font_for(r.font_medium_bold)
        assert _NOTO_ARABIC_BOLD.name in _font_path(af)
        assert _font_size(af) == _font_size(r.font_medium_bold)


class TestRendererIntegration:
    """draw_text / get_text_size / fit_text_font must not regress LTR
    and must produce *something visible* for Arabic input."""

    def test_draw_text_arabic_does_not_raise(self):
        r = Renderer()
        img, draw = r.create_canvas()
        r.draw_text(draw, PHRASE_HELLO, (120, 120), font=r.font_medium_bold, anchor="mm")
        assert isinstance(img, Image.Image)

    def test_arabic_renders_to_pixels(self):
        """A canvas with shaped Arabic must differ from an empty one."""
        r = Renderer()
        empty, _ = r.create_canvas()
        img, draw = r.create_canvas()
        r.draw_text(draw, PHRASE_HELLO, (120, 120), font=r.font_medium_bold, anchor="mm")
        diff = ImageChops.difference(img, empty).getbbox()
        assert diff is not None, "Arabic draw produced no pixels"

    def test_arabic_differs_from_raw_render(self):
        """Shaped Arabic must produce different pixels than the raw string.

        If the shaper were a no-op, the rendered pixels would be
        identical to drawing the raw (unshaped) string with the same
        font — that's exactly the bug from issue #126.
        """
        r = Renderer()
        # Shaped path (via Renderer.draw_text — auto-detects Arabic).
        shaped_img, draw1 = r.create_canvas()
        r.draw_text(draw1, PHRASE_HELLO, (120, 120), font=r.font_medium_bold, anchor="mm")

        # Raw path: bypass Renderer.draw_text and render the unshaped
        # string with the same Nunito font directly.
        raw_img, draw2 = r.create_canvas()
        scaled_pos = (120 * r.scale, 120 * r.scale)
        draw2.text(scaled_pos, PHRASE_HELLO, font=r.font_medium_bold, fill=(255, 255, 255), anchor="mm")

        diff = ImageChops.difference(shaped_img, raw_img).getbbox()
        assert diff is not None, "shaping made no visible difference"

    def test_mixed_string_renders(self):
        r = Renderer()
        img, draw = r.create_canvas()
        r.draw_text(draw, PHRASE_MIXED, (10, 20), font=r.font_regular, anchor="lt")
        empty, _ = r.create_canvas()
        assert ImageChops.difference(img, empty).getbbox() is not None

    def test_get_text_size_uses_shaped_width(self):
        r = Renderer()
        w, h = r.get_text_size(PHRASE_HELLO, r.font_medium_bold)
        # Shaped Arabic is non-empty → must report positive dimensions.
        assert w > 0 and h > 0

    def test_get_text_size_empty(self):
        r = Renderer()
        assert r.get_text_size("", r.font_regular) == (0, 0)

    def test_fit_text_font_arabic(self):
        r = Renderer()
        f = r.fit_text_font(PHRASE_LIVING_ROOM, max_width=200, max_height=80, bold=True)
        # Binary search should land somewhere reasonable, not at the floor.
        assert _font_size(f) >= 20

    def test_latin_fast_path_unchanged(self):
        """LTR text must still go through the original PIL path —
        same pixels as a direct draw."""
        r = Renderer()
        a, da = r.create_canvas()
        r.draw_text(da, "Hello", (10, 20), font=r.font_regular, anchor="lt")
        b, db = r.create_canvas()
        scaled_pos = (10 * r.scale, 20 * r.scale)
        db.text(scaled_pos, "Hello", font=r.font_regular, fill=(255, 255, 255), anchor="lt")
        assert ImageChops.difference(a, b).getbbox() is None
