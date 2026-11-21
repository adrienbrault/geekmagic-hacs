"""Rebuild the embedded Noto script fonts in custom_components/geekmagic/fonts/.

Home Assistant OS ships no fonts beyond what an integration brings, so any
script Nunito and DejaVu Sans lack drew as missing-glyph boxes (issue
#320). Each face below is a subset of a Noto Sans variable font, weight
axis intact (the kit draws 400-800), cut to the script it is in the stack
for:

* JP: kana, CJK punctuation, half/fullwidth forms, the 6,355 JIS X 0208 kanji
* SC: the GB2312 hanzi JP lacks
* TC: the Big5 level-1 (everyday) hanzi JP and SC lack
* KR: every Hangul syllable and jamo
* Thai, Arabic (Urdu and Persian letters included), Devanagari: their blocks

Shared Han characters come from the first face that has them, so Chinese
text draws those in the Japanese face's forms.

Usage (fontTools is not a project dependency; sources are fetched from a
pinned google/fonts commit):

    uv run --with fonttools python scripts/subset_fonts.py

Every source is SIL Open Font License 1.1; its OFL.txt is written next to
the subset as OFL-<file stem without the suffix>.txt.
"""

from __future__ import annotations

import tempfile
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from fontTools import subset  # ty: ignore[import-not-found]
from fontTools.ttLib import TTFont  # ty: ignore[import-not-found]

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

FONTS_DIR = Path(__file__).parent.parent / "custom_components/geekmagic/fonts"
GOOGLE_FONTS = (
    "https://raw.githubusercontent.com/google/fonts/06bfe0d62a98375cb09c942fa18e68bd32cff057/ofl"
)

HAN = (range(0x3400, 0x4DC0), range(0x4E00, 0xA000), range(0xF900, 0xFB00))
# Joiners, bidi marks and the dotted circle the shaper draws for a lone mark.
SHAPING = (range(0x200B, 0x2010), range(0x25CC, 0x25CD))


def encodes(codec: str) -> Callable[[int], bool]:
    def check(cp: int) -> bool:
        try:
            chr(cp).encode(codec)
        except UnicodeEncodeError:
            return False
        return True

    return check


def big5_level1() -> set[int]:
    """The 5,401 everyday hanzi of Big5 (lead bytes 0xA4-0xC6)."""
    chars = set()
    for lead in range(0xA4, 0xC7):
        for trail in (*range(0x40, 0x7F), *range(0xA1, 0xFF)):
            try:
                chars.add(ord(bytes((lead, trail)).decode("big5")))
            except UnicodeDecodeError:
                continue
    return {cp for cp in chars if any(cp in block for block in HAN)}


def blocks(*ranges: range) -> set[int]:
    return {cp for block in ranges for cp in block}


in_jis = encodes("iso2022_jp")  # ASCII + JIS X 0208
in_gb2312 = encodes("gb2312")
JP_CODEPOINTS = blocks(range(0x3000, 0x3100), range(0x31F0, 0x3200), range(0xFF00, 0xFFF0)) | {
    cp for cp in blocks(*HAN) if in_jis(cp)
}
SC_CODEPOINTS = {cp for cp in blocks(*HAN) if in_gb2312(cp) and cp not in JP_CODEPOINTS}
TC_CODEPOINTS = big5_level1() - JP_CODEPOINTS - SC_CODEPOINTS

# (google/fonts directory, source file, output file, code points wanted)
FONTS: tuple[tuple[str, str, str, Iterable[int]], ...] = (
    ("notosansjp", "NotoSansJP[wght].ttf", "NotoSansJP-JIS.ttf", JP_CODEPOINTS),
    ("notosanssc", "NotoSansSC[wght].ttf", "NotoSansSC-GB2312.ttf", SC_CODEPOINTS),
    ("notosanstc", "NotoSansTC[wght].ttf", "NotoSansTC-Big5.ttf", TC_CODEPOINTS),
    (
        "notosanskr",
        "NotoSansKR[wght].ttf",
        "NotoSansKR-Hangul.ttf",
        blocks(
            range(0xAC00, 0xD7A4),
            range(0x1100, 0x1200),
            range(0x3130, 0x3190),
            range(0xA960, 0xA980),
        ),
    ),
    (
        "notosansthai",
        "NotoSansThai[wdth,wght].ttf",
        "NotoSansThai.ttf",
        blocks(range(0x0E00, 0x0E80), *SHAPING),
    ),
    (
        "notosansarabic",
        "NotoSansArabic[wdth,wght].ttf",
        "NotoSansArabic.ttf",
        blocks(
            range(0x0600, 0x0700),
            range(0x0750, 0x0780),
            range(0x08A0, 0x0900),
            range(0xFB50, 0xFE00),
            range(0xFE70, 0xFF00),
            *SHAPING,
        ),
    ),
    (
        "notosansdevanagari",
        "NotoSansDevanagari[wdth,wght].ttf",
        "NotoSansDevanagari.ttf",
        blocks(range(0x0900, 0x0980), range(0xA8E0, 0xA900), range(0x1CD0, 0x1D00), *SHAPING),
    ),
)


def fetch(url: str, dest: Path) -> Path:
    with urllib.request.urlopen(url.replace("[", "%5B").replace("]", "%5D")) as response:  # noqa: S310
        dest.write_bytes(response.read())
    return dest


def build(source: Path, out: Path, wanted: Iterable[int]) -> int:
    font = TTFont(source)
    cmap = font.getBestCmap()
    keep = {cp for cp in wanted if cp in cmap}
    options = subset.Options()
    options.hinting = False
    options.desubroutinize = True
    # Keep every name: by default the subsetter drops the typographic
    # family (ID 16), and a variable font then registers under its
    # default instance's name ("Noto Sans JP Thin").
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)
    font.recalcTimestamp = False  # same source, same bytes
    font.save(out)
    return len(keep)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for directory, source, output, wanted in FONTS:
            src = fetch(f"{GOOGLE_FONTS}/{directory}/{source}", Path(tmp) / source)
            out = FONTS_DIR / output
            kept = build(src, out, wanted)
            license_name = f"OFL-{output.split('-')[0].removesuffix('.ttf')}.txt"
            fetch(f"{GOOGLE_FONTS}/{directory}/OFL.txt", FONTS_DIR / license_name)
            print(f"{output}: {kept} code points, {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
