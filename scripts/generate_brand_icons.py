#!/usr/bin/env python3
"""Generate Home Assistant brand icons from a rendered dashboard sample."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = PROJECT_ROOT / "samples" / "layouts" / "layout_grid_2x2.png"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "custom_components" / "geekmagic" / "brand"
ICON_SIZES = {"icon.png": 256, "icon@2x.png": 512}
SUPERSAMPLE = 4


def _scaled_box(size: int, inset: float) -> tuple[int, int, int, int]:
    """Return a square box inset by a fraction of its size."""
    offset = round(size * inset)
    return offset, offset, size - offset, size - offset


def render_brand_icon(sample: Image.Image, size: int) -> Image.Image:
    """Wrap a dashboard sample in a stand-free display bezel.

    The icon is rendered at higher resolution and downsampled so the rounded
    transparent edge remains smooth at Home Assistant's normal 256 px size.
    """
    if size <= 0:
        msg = "Icon size must be positive"
        raise ValueError(msg)

    work_size = size * SUPERSAMPLE
    canvas = Image.new("RGBA", (work_size, work_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    shell_box = _scaled_box(work_size, 0.025)
    screen_box = _scaled_box(work_size, 0.072)
    screen_radius = round(work_size * 0.1)

    # Keep the two corner arcs concentric so the bezel has uniform thickness.
    shell_radius = screen_radius + (screen_box[0] - shell_box[0])
    draw.rounded_rectangle(shell_box, radius=shell_radius, fill=(248, 243, 234, 255))

    screen_width = screen_box[2] - screen_box[0]
    screen_height = screen_box[3] - screen_box[1]
    screen = ImageOps.fit(
        sample.convert("RGB"),
        (screen_width, screen_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    screen_mask = Image.new("L", (screen_width, screen_height), 0)
    mask_draw = ImageDraw.Draw(screen_mask)
    mask_draw.rounded_rectangle(
        (0, 0, screen_width - 1, screen_height - 1),
        radius=screen_radius,
        fill=255,
    )
    canvas.paste(screen, screen_box[:2], screen_mask)

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate_brand_icons(sample_path: Path, output_dir: Path) -> list[Path]:
    """Generate the normal and high-DPI Home Assistant brand icons."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(sample_path) as source:
        sample = source.copy()

    generated: list[Path] = []
    for filename, size in ICON_SIZES.items():
        output_path = output_dir / filename
        render_brand_icon(sample, size).save(output_path, format="PNG", optimize=True)
        generated.append(output_path)
        print(f"Generated: {output_path}")
    return generated


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Generate Home Assistant brand icons from a dashboard sample."
    )
    parser.add_argument(
        "--sample",
        type=Path,
        default=DEFAULT_SAMPLE,
        help=f"Dashboard image to use (default: {DEFAULT_SAMPLE.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for icon.png and icon@2x.png",
    )
    return parser


def main() -> None:
    """Generate brand icons from command-line arguments."""
    args = create_parser().parse_args()
    generate_brand_icons(args.sample, args.output_dir)


if __name__ == "__main__":
    main()
