"""Arabic text shaping and BiDi support for the renderer.

PIL ships glyphs but no shaper — Arabic strings render as disconnected,
left-to-right letters unless we pre-shape them. This module:

1. Detects Arabic codepoints (cheap, runs on every draw call).
2. Reshapes them into their positional presentation forms
   (isolated / initial / medial / final) via ``arabic_reshaper``.
3. Applies the Unicode Bidirectional Algorithm via ``python-bidi`` so
   the result is in visual (left-to-right) order — PIL can then draw it
   straight across.
4. Segments mixed strings so Latin runs keep using the project's regular
   font and Arabic runs switch to NotoSansArabic.

Both shaping libraries are pure Python and lazy-imported so the fast
path (no Arabic in the string) is a single ``any()`` call per draw.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import ImageFont

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont, ImageFont as _ImageFont

    _Font = FreeTypeFont | _ImageFont


_FONTS_DIR = Path(__file__).parent / "fonts"
_NOTO_ARABIC_REGULAR = _FONTS_DIR / "NotoSansArabic-Regular.ttf"
_NOTO_ARABIC_BOLD = _FONTS_DIR / "NotoSansArabic-Bold.ttf"


# Arabic Unicode blocks that need shaping + BiDi:
#   U+0600..06FF  Arabic
#   U+0750..077F  Arabic Supplement
#   U+08A0..08FF  Arabic Extended-A
#   U+FB50..FDFF  Arabic Presentation Forms-A
#   U+FE70..FEFF  Arabic Presentation Forms-B
_ARABIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _is_arabic_codepoint(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in _ARABIC_RANGES)


def is_arabic_char(ch: str) -> bool:
    """Return True when ``ch`` is an Arabic-script codepoint."""
    return bool(ch) and _is_arabic_codepoint(ord(ch))


def contains_arabic(text: str) -> bool:
    """Return True if ``text`` contains any Arabic-script codepoint."""
    if not text:
        return False
    return any(_is_arabic_codepoint(ord(ch)) for ch in text)


@lru_cache(maxsize=512)
def shape_text(text: str) -> str:
    """Reshape Arabic letters and apply BiDi → visual LTR order.

    Non-Arabic strings are returned unchanged. Cached because widget
    labels (e.g. clocks, weather captions) repeat across frames.
    """
    if not contains_arabic(text):
        return text

    import arabic_reshaper
    from bidi.algorithm import get_display

    reshaped = arabic_reshaper.reshape(text)
    result = get_display(reshaped)
    # python-bidi types get_display as str | bytes — we always pass str
    # so the str branch is the only reachable one.
    return result if isinstance(result, str) else result.decode("utf-8")


def segment_runs(shaped_text: str) -> list[tuple[str, bool]]:
    """Split shaped text into ``(substring, is_arabic)`` runs.

    Whitespace and shared punctuation are glued onto the current run so
    mixed strings like ``"حرارة 23°C"`` collapse to two runs instead of
    fragmenting at every space.
    """
    if not shaped_text:
        return []

    runs: list[tuple[str, bool]] = []
    cur_buf: list[str] = []
    cur_is_arabic: bool | None = None

    for ch in shaped_text:
        is_a = is_arabic_char(ch)
        is_glue = ch.isspace() or (not ch.isalnum() and not is_a)
        if cur_is_arabic is None:
            cur_is_arabic = is_a
            cur_buf.append(ch)
        elif is_glue or is_a == cur_is_arabic:
            cur_buf.append(ch)
        else:
            runs.append(("".join(cur_buf), cur_is_arabic))
            cur_buf = [ch]
            cur_is_arabic = is_a

    if cur_buf and cur_is_arabic is not None:
        runs.append(("".join(cur_buf), cur_is_arabic))
    return runs


def _font_is_bold(font: _Font) -> bool:
    """Best-effort weight detection from a loaded font's source path."""
    raw = getattr(font, "path", "") or ""
    path = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else str(raw)
    return "bold" in path.lower()  # matches Bold / SemiBold / ExtraBold


@lru_cache(maxsize=64)
def _load_arabic_font(size: int, bold: bool) -> FreeTypeFont:
    path = _NOTO_ARABIC_BOLD if bold else _NOTO_ARABIC_REGULAR
    return ImageFont.truetype(str(path), size)


def arabic_font_for(font: _Font) -> FreeTypeFont:
    """Return the NotoSansArabic variant matching ``font``'s size & weight."""
    size = int(getattr(font, "size", 16))
    return _load_arabic_font(size, _font_is_bold(font))


def is_arabic_only(text: str) -> bool:
    """All non-whitespace chars are Arabic — useful for RTL alignment hints."""
    has_arabic = False
    for ch in text:
        if ch.isspace():
            continue
        if is_arabic_char(ch):
            has_arabic = True
        else:
            return False
    return has_arabic
