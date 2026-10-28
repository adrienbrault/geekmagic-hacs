"""Tests for the canvas/encoding renderer (drawing happens in Blitz)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw

from custom_components.geekmagic.const import (
    COLOR_BLACK,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    SUPERSAMPLE_SCALE,
)
from custom_components.geekmagic.renderer import Renderer


class TestRenderer:
    """Tests for Renderer class."""

    def test_init(self):
        """Test renderer initialization."""
        renderer = Renderer()
        assert renderer.width == DISPLAY_WIDTH
        assert renderer.height == DISPLAY_HEIGHT
        assert renderer.scale == SUPERSAMPLE_SCALE

    def test_create_canvas_default(self):
        """Test creating canvas with default black background."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        assert isinstance(img, Image.Image)
        assert isinstance(draw, ImageDraw.ImageDraw)
        # Raw image is supersampled
        assert img.size == (DISPLAY_WIDTH * SUPERSAMPLE_SCALE, DISPLAY_HEIGHT * SUPERSAMPLE_SCALE)
        assert img.mode == "RGB"
        # Check that background is black
        assert img.getpixel((0, 0)) == COLOR_BLACK

    def test_create_canvas_custom_background(self):
        """Test creating canvas with custom background color."""
        renderer = Renderer()
        bg_color = (100, 50, 200)
        img, _draw = renderer.create_canvas(background=bg_color)

        assert img.getpixel((0, 0)) == bg_color

    def test_finalize_downscales(self):
        """Test that finalize downscales to display resolution."""
        renderer = Renderer()
        img, _draw = renderer.create_canvas()

        final = renderer.finalize(img)
        assert final.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_to_jpeg(self):
        """Test converting to JPEG."""
        renderer = Renderer()
        img, _ = renderer.create_canvas()

        jpeg_bytes = renderer.to_jpeg(img, quality=50, max_size=None)

        # JPEG should start with FF D8 FF
        assert jpeg_bytes[:3] == b"\xff\xd8\xff"
        assert len(jpeg_bytes) > 0

    def test_to_jpeg_quality_affects_size(self):
        """Test that quality affects file size."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw complex content to make quality difference visible
        for i in range(0, img.width, 2):
            for j in range(0, img.height, 20):
                color = ((i + j) % 256, (i * 2) % 256, (j * 3) % 256)
                draw.point((i, j), fill=color)

        low_quality = renderer.to_jpeg(img, quality=10, max_size=None)
        high_quality = renderer.to_jpeg(img, quality=95, max_size=None)

        # Higher quality should produce larger file for complex images
        assert len(high_quality) > len(low_quality)

    def test_to_jpeg_default_quality_is_high(self):
        """Test that default JPEG quality is high (92)."""
        from custom_components.geekmagic.const import DEFAULT_JPEG_QUALITY

        assert DEFAULT_JPEG_QUALITY == 92

    def test_to_jpeg_respects_max_size(self):
        """Test that JPEG output respects max_size cap."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Noisy content so quality reduction has an effect
        for i in range(0, img.width, 3):
            for j in range(0, img.height, 3):
                draw.point((i, j), fill=((i * 7) % 256, (j * 5) % 256, (i + j) % 256))

        uncapped = renderer.to_jpeg(img, quality=95, max_size=None)
        small_cap = 3000
        capped = renderer.to_jpeg(img, quality=95, max_size=small_cap)

        assert len(capped) <= small_cap
        assert len(capped) < len(uncapped)

    def test_to_jpeg_uses_default_max_size(self):
        """Test that to_jpeg uses MAX_IMAGE_SIZE by default."""
        from custom_components.geekmagic.const import MAX_IMAGE_SIZE

        assert MAX_IMAGE_SIZE == 400 * 1024

        renderer = Renderer()
        img, _ = renderer.create_canvas()

        jpeg = renderer.to_jpeg(img)
        assert len(jpeg) < MAX_IMAGE_SIZE

    def test_to_png(self):
        """Test converting to PNG."""
        renderer = Renderer()
        img, _ = renderer.create_canvas()

        png_bytes = renderer.to_png(img)

        # PNG signature
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        final = Image.open(__import__("io").BytesIO(png_bytes))
        assert final.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_rotation(self):
        """Rotation produces same-size output."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()
        draw.rectangle((0, 0, 50, 50), fill=(255, 0, 0))

        for rotation in (0, 90, 180, 270):
            png = renderer.to_png(img, rotation=rotation)
            out = Image.open(__import__("io").BytesIO(png))
            assert out.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)


class TestGifEncoding:
    """Animated GIF assembly from supersampled canvases."""

    def test_to_gif_loops_and_sizes(self):
        renderer = Renderer()
        frames = []
        for i in range(4):
            img, draw = renderer.create_canvas()
            draw.rectangle((i * 40, 0, i * 40 + 80, 80), fill=(255, 159, 10))
            frames.append(img)
        gif = renderer.to_gif(frames, fps=10)
        assert gif[:6] in (b"GIF87a", b"GIF89a")
        out = Image.open(__import__("io").BytesIO(gif))
        assert out.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)
        assert getattr(out, "n_frames", 1) == 4
        assert out.info.get("loop") == 0

    def test_to_gif_rejects_empty(self):
        import pytest

        renderer = Renderer()
        with pytest.raises(ValueError, match="at least one frame"):
            renderer.to_gif([])
