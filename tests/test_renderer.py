"""Tests for Pillow-based renderer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from PIL import Image, ImageDraw

from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.const import (
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_CYAN,
)


class TestRenderer:
    """Tests for Renderer class."""

    def test_init(self):
        """Test renderer initialization."""
        renderer = Renderer()
        assert renderer.width == DISPLAY_WIDTH
        assert renderer.height == DISPLAY_HEIGHT
        assert renderer.font_small is not None
        assert renderer.font_regular is not None
        assert renderer.font_large is not None

    def test_create_canvas_default(self):
        """Test creating canvas with default black background."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        assert isinstance(img, Image.Image)
        assert isinstance(draw, ImageDraw.ImageDraw)
        assert img.size == (240, 240)
        assert img.mode == "RGB"
        # Check that background is black
        assert img.getpixel((0, 0)) == COLOR_BLACK

    def test_create_canvas_custom_background(self):
        """Test creating canvas with custom background color."""
        renderer = Renderer()
        bg_color = (100, 50, 200)
        img, draw = renderer.create_canvas(background=bg_color)

        assert img.getpixel((0, 0)) == bg_color

    def test_draw_text(self):
        """Test drawing text on canvas."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw some text
        renderer.draw_text(draw, "Hello", (10, 10), color=COLOR_WHITE)

        # Verify pixels were changed (text was drawn)
        # The exact pixels depend on font, but some should be white
        # We just verify no exception was raised and image is valid
        assert img.size == (240, 240)

    def test_draw_text_with_font(self):
        """Test drawing text with specific font."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_text(
            draw, "Big Text", (10, 10),
            font=renderer.font_large,
            color=COLOR_CYAN
        )

        assert img.size == (240, 240)

    def test_draw_rect(self):
        """Test drawing rectangles."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw a filled rectangle
        renderer.draw_rect(draw, (10, 10, 50, 50), fill=COLOR_WHITE)

        # Check that the rectangle was drawn
        assert img.getpixel((30, 30)) == COLOR_WHITE

    def test_draw_rect_outline(self):
        """Test drawing rectangle with outline."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_rect(
            draw, (10, 10, 50, 50),
            outline=COLOR_CYAN,
            width=2
        )

        # Outline should be at edge
        assert img.getpixel((10, 30)) == COLOR_CYAN

    def test_draw_bar(self):
        """Test drawing progress bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw a 50% filled bar
        renderer.draw_bar(
            draw,
            rect=(10, 10, 110, 20),
            percent=50,
            color=COLOR_CYAN,
            background=(50, 50, 50)
        )

        # Check left side (filled part)
        assert img.getpixel((30, 15)) == COLOR_CYAN
        # Check right side (background part)
        assert img.getpixel((90, 15)) == (50, 50, 50)

    def test_draw_bar_zero_percent(self):
        """Test drawing 0% bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        background = (50, 50, 50)
        renderer.draw_bar(
            draw,
            rect=(10, 10, 110, 20),
            percent=0,
            color=COLOR_CYAN,
            background=background
        )

        # All should be background color
        assert img.getpixel((30, 15)) == background
        assert img.getpixel((90, 15)) == background

    def test_draw_bar_hundred_percent(self):
        """Test drawing 100% bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_bar(
            draw,
            rect=(10, 10, 110, 20),
            percent=100,
            color=COLOR_CYAN,
            background=(50, 50, 50)
        )

        # All should be filled
        assert img.getpixel((30, 15)) == COLOR_CYAN
        assert img.getpixel((90, 15)) == COLOR_CYAN

    def test_draw_sparkline(self):
        """Test drawing sparkline chart."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        data = [10, 20, 30, 25, 35, 40, 30]
        renderer.draw_sparkline(
            draw,
            rect=(10, 10, 100, 50),
            data=data,
            color=COLOR_CYAN,
            fill=True
        )

        # Just verify no exception and image is valid
        assert img.size == (240, 240)

    def test_draw_sparkline_empty_data(self):
        """Test sparkline with empty data."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Should not raise exception
        renderer.draw_sparkline(
            draw,
            rect=(10, 10, 100, 50),
            data=[],
            color=COLOR_CYAN
        )

        assert img.size == (240, 240)

    def test_draw_sparkline_single_point(self):
        """Test sparkline with single data point."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Single point - should not draw
        renderer.draw_sparkline(
            draw,
            rect=(10, 10, 100, 50),
            data=[50],
            color=COLOR_CYAN
        )

        assert img.size == (240, 240)

    def test_draw_sparkline_no_fill(self):
        """Test sparkline without fill."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        data = [10, 20, 30, 25, 35]
        renderer.draw_sparkline(
            draw,
            rect=(10, 10, 100, 50),
            data=data,
            color=COLOR_CYAN,
            fill=False
        )

        assert img.size == (240, 240)

    def test_draw_arc(self):
        """Test drawing arc gauge."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_arc(
            draw,
            rect=(10, 10, 100, 100),
            percent=75,
            color=COLOR_CYAN,
            width=8
        )

        assert img.size == (240, 240)

    def test_draw_arc_zero(self):
        """Test drawing arc at 0%."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_arc(
            draw,
            rect=(10, 10, 100, 100),
            percent=0,
            color=COLOR_CYAN,
            width=8
        )

        assert img.size == (240, 240)

    def test_get_text_size(self):
        """Test measuring text size."""
        renderer = Renderer()

        width, height = renderer.get_text_size("Test")

        assert width > 0
        assert height > 0

    def test_get_text_size_with_font(self):
        """Test measuring text with specific font."""
        renderer = Renderer()

        small_size = renderer.get_text_size("Test", font=renderer.font_small)
        large_size = renderer.get_text_size("Test", font=renderer.font_large)

        # Large font should produce larger size
        assert large_size[0] > small_size[0]
        assert large_size[1] > small_size[1]

    def test_to_jpeg(self):
        """Test converting to JPEG."""
        renderer = Renderer()
        img, _ = renderer.create_canvas()

        jpeg_bytes = renderer.to_jpeg(img, quality=50)

        # JPEG should start with FF D8 FF
        assert jpeg_bytes[:3] == b'\xff\xd8\xff'
        assert len(jpeg_bytes) > 0

    def test_to_jpeg_quality_affects_size(self):
        """Test that quality affects file size."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw complex content to make quality difference visible
        # Gradient-like effect with many colors
        for i in range(240):
            for j in range(0, 240, 10):
                color = ((i + j) % 256, (i * 2) % 256, (j * 3) % 256)
                draw.point((i, j), fill=color)

        # Also draw text and shapes
        renderer.draw_text(draw, "Quality Test", (120, 120), anchor="mm")
        renderer.draw_bar(draw, (10, 200, 230, 220), percent=75)

        low_quality = renderer.to_jpeg(img, quality=10)
        high_quality = renderer.to_jpeg(img, quality=95)

        # Higher quality should produce larger file for complex images
        assert len(high_quality) > len(low_quality)

    def test_to_png(self):
        """Test converting to PNG."""
        renderer = Renderer()
        img, _ = renderer.create_canvas()

        png_bytes = renderer.to_png(img)

        # PNG should start with specific magic bytes
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'
        assert len(png_bytes) > 0


class TestRendererIntegration:
    """Integration tests for renderer."""

    def test_complete_render_workflow(self):
        """Test a complete render workflow."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw a simple dashboard layout
        # Title
        renderer.draw_text(draw, "CPU Usage", (120, 20), anchor="mm")

        # Progress bar
        renderer.draw_bar(draw, (20, 50, 220, 70), percent=65)

        # Arc gauge
        renderer.draw_arc(draw, (70, 100, 170, 200), percent=65)

        # Sparkline
        data = [10, 15, 12, 18, 25, 22, 30, 28]
        renderer.draw_sparkline(draw, (20, 210, 220, 235), data)

        # Convert to JPEG
        jpeg_bytes = renderer.to_jpeg(img)

        assert len(jpeg_bytes) > 0
        assert jpeg_bytes[:3] == b'\xff\xd8\xff'
