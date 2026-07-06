# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Build a labeled contact sheet from sample PNGs for LLM visual review.

Tiles the given images onto one canvas with their filename above each tile,
so a single Read covers many 240x240 device renders without losing
per-file traceability.

Usage:
    uv run .claude/skills/sample-review/contact_sheet.py OUT.png \
        --cols 3 --scale 1.5 samples/0*.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABEL_H = 22
PAD = 4


def build_sheet(files: list[Path], out: Path, cols: int, scale: float) -> None:
    imgs = [Image.open(f).convert("RGB") for f in files]
    tile_w = int(max(i.width for i in imgs) * scale)
    tile_h = int(max(i.height for i in imgs) * scale)
    rows = (len(imgs) + cols - 1) // cols
    canvas = Image.new(
        "RGB",
        (cols * (tile_w + PAD) + PAD, rows * (tile_h + LABEL_H + PAD) + PAD),
        (40, 40, 40),
    )
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except OSError:
        font = ImageFont.load_default()
    for idx, (f, src) in enumerate(zip(files, imgs, strict=True)):
        im = src.resize((int(src.width * scale), int(src.height * scale)), Image.Resampling.NEAREST)
        row, col = divmod(idx, cols)
        x = PAD + col * (tile_w + PAD)
        y = PAD + row * (tile_h + LABEL_H + PAD)
        draw.text((x, y + 3), f.stem, fill=(220, 220, 220), font=font)
        canvas.paste(im, (x, y + LABEL_H))
        draw.rectangle(
            [x - 1, y + LABEL_H - 1, x + tile_w, y + LABEL_H + tile_h],
            outline=(90, 90, 90),
        )
    canvas.save(out)
    print(f"{out} {canvas.size[0]}x{canvas.size[1]} ({len(files)} tiles)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="Output sheet PNG")
    parser.add_argument("images", nargs="+", type=Path, help="Input PNGs, in tile order")
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--scale", type=float, default=1.5)
    args = parser.parse_args()
    build_sheet(args.images, args.out, args.cols, args.scale)


if __name__ == "__main__":
    main()
