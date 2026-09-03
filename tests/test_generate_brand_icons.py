"""Tests for deterministic Home Assistant brand icon generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PIL import Image, ImageDraw

from scripts.generate_brand_icons import ICON_SIZES, generate_brand_icons, render_brand_icon

if TYPE_CHECKING:
    from pathlib import Path


def _sample() -> Image.Image:
    """Create a sample with recognizable center and corner colors."""
    sample = Image.new("RGB", (240, 240), "black")
    draw = ImageDraw.Draw(sample)
    draw.rectangle((20, 20, 110, 110), fill=(0, 200, 220))
    draw.rectangle((130, 20, 220, 110), fill=(255, 80, 60))
    draw.rectangle((20, 130, 110, 220), fill=(0, 220, 140))
    draw.rectangle((130, 130, 220, 220), fill=(245, 240, 225))
    return sample


def _rgba_pixel(image: Image.Image, position: tuple[int, int]) -> tuple[int, int, int, int]:
    """Return a pixel from an RGBA test image with a precise type."""
    return cast("tuple[int, int, int, int]", image.getpixel(position))


def test_render_brand_icon_is_square_and_transparent() -> None:
    """The bezel must be stand-free with transparent exterior corners."""
    icon = render_brand_icon(_sample(), 256)

    assert icon.mode == "RGBA"
    assert icon.size == (256, 256)
    assert _rgba_pixel(icon, (0, 0))[3] == 0
    assert _rgba_pixel(icon, (128, 128))[3] == 255
    bounding_box = icon.getbbox()
    assert bounding_box is not None
    assert bounding_box[1] == bounding_box[0]
    assert bounding_box[3] == bounding_box[2]


def test_render_brand_icon_reuses_sample_pixels() -> None:
    """The generated screen should contain the source dashboard colors."""
    icon = render_brand_icon(_sample(), 256)

    assert _rgba_pixel(icon, (72, 72))[:3] == (0, 200, 220)
    assert _rgba_pixel(icon, (184, 72))[:3] == (255, 80, 60)
    assert _rgba_pixel(icon, (72, 184))[:3] == (0, 220, 140)
    assert _rgba_pixel(icon, (184, 184))[:3] == (245, 240, 225)


def test_generate_brand_icons_writes_required_sizes(tmp_path: Path) -> None:
    """Both Home Assistant icon resolutions should be emitted."""
    sample_path = tmp_path / "sample.png"
    output_dir = tmp_path / "brand"
    _sample().save(sample_path)

    generated = generate_brand_icons(sample_path, output_dir)

    assert generated == [output_dir / filename for filename in ICON_SIZES]
    for filename, size in ICON_SIZES.items():
        with Image.open(output_dir / filename) as icon:
            assert icon.mode == "RGBA"
            assert icon.size == (size, size)
            assert _rgba_pixel(icon, (0, 0))[3] == 0
