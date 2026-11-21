"""Rebuild the embedded Japanese face, custom_components/geekmagic/fonts/NotoSansJP-JIS.ttf.

Home Assistant OS ships no Japanese fonts, so without an embedded face
Japanese text renders as missing-glyph boxes (issue #320). The full
Noto Sans JP variable font is 9.6 MB; this keeps what everyday Japanese
needs, with the weight axis intact (the kit draws 400-800):

* CJK symbols and punctuation, hiragana, katakana (U+3000-30FF, U+31F0-31FF)
* half- and fullwidth forms (U+FF00-FFEF)
* the 6,355 kanji of JIS X 0208 (levels 1 and 2)

Usage (fontTools is not a project dependency):

    curl -LO 'https://raw.githubusercontent.com/google/fonts/06bfe0d62a98375cb09c942fa18e68bd32cff057/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf'
    uv run --with fonttools python scripts/subset_japanese_font.py 'NotoSansJP[wght].ttf'

The source is SIL Open Font License 1.1 (fonts/OFL-NotoSansJP.txt).
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools import subset  # ty: ignore[import-not-found]
from fontTools.ttLib import TTFont  # ty: ignore[import-not-found]

OUT = Path(__file__).parent.parent / "custom_components/geekmagic/fonts/NotoSansJP-JIS.ttf"

KANA_AND_FORMS = (range(0x3000, 0x3100), range(0x31F0, 0x3200), range(0xFF00, 0xFFF0))
CJK_IDEOGRAPHS = (range(0x3400, 0x4DC0), range(0x4E00, 0xA000), range(0xF900, 0xFB00))


def in_jis_x_0208(cp: int) -> bool:
    """True for a kanji JIS X 0208 encodes (ISO-2022-JP is ASCII + JIS X 0208)."""
    try:
        chr(cp).encode("iso2022_jp")
    except UnicodeEncodeError:
        return False
    return True


def main(source: str) -> None:
    font = TTFont(source)
    cmap = font.getBestCmap()
    keep = {cp for block in KANA_AND_FORMS for cp in block if cp in cmap}
    keep |= {cp for block in CJK_IDEOGRAPHS for cp in block if cp in cmap and in_jis_x_0208(cp)}

    options = subset.Options()
    options.hinting = False
    options.desubroutinize = True
    # Keep every name: by default the subsetter drops the typographic
    # family (ID 16), and the variable font then registers under its
    # default instance's name, "Noto Sans JP Thin".
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)
    font.save(OUT)
    print(f"{len(keep)} code points -> {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
