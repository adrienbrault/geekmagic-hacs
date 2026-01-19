"""Tests for Pillow-based renderer with supersampling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw

from custom_components.geekmagic.const import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_WHITE,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
)
from custom_components.geekmagic.renderer import SUPERSAMPLE_SCALE, Renderer


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

    def test_draw_text(self):
        """Test drawing text on canvas."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw some text
        renderer.draw_text(draw, "Hello", (10, 10), color=COLOR_WHITE)

        # Verify finalized image is correct size
        final = renderer.finalize(img)
        assert final.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_text_with_font(self):
        """Test drawing text with specific font."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_text(draw, "Big Text", (10, 10), font=renderer.font_large, color=COLOR_CYAN)

        final = renderer.finalize(img)
        assert final.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_rect(self):
        """Test drawing rectangles."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw a filled rectangle
        renderer.draw_rect(draw, (10, 10, 50, 50), fill=COLOR_WHITE)

        # Finalize and check
        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

        # Check that the rectangle was drawn (center of rect)
        assert final_img.getpixel((30, 30)) == COLOR_WHITE

    def test_draw_rect_outline(self):
        """Test drawing rectangle with outline."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_rect(draw, (10, 10, 50, 50), outline=COLOR_CYAN, width=2)

        final_img = renderer.finalize(img)

        # Outline should be at edge (check a few pixels inside the outline)
        pixel = final_img.getpixel((11, 30))
        # With supersampling, the exact color may vary slightly due to anti-aliasing
        # Just verify it's not black (something was drawn)
        assert pixel != COLOR_BLACK

    def test_draw_bar(self):
        """Test drawing progress bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw a 50% filled bar
        renderer.draw_bar(
            draw, rect=(10, 10, 110, 20), percent=50, color=COLOR_CYAN, background=(50, 50, 50)
        )

        final_img = renderer.finalize(img)

        # Check left side (filled part) - should have cyan component
        left_pixel: tuple[int, ...] = final_img.getpixel((30, 15))  # type: ignore[assignment]
        # Check right side (background part) - should be grayish
        right_pixel: tuple[int, ...] = final_img.getpixel((90, 15))  # type: ignore[assignment]

        # Left should have more cyan than right
        assert left_pixel[1] > right_pixel[1]  # Green channel (cyan has high green)

    def test_draw_bar_zero_percent(self):
        """Test drawing 0% bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        background = (50, 50, 50)
        renderer.draw_bar(
            draw, rect=(10, 10, 110, 20), percent=0, color=COLOR_CYAN, background=background
        )

        final_img = renderer.finalize(img)

        # All should be background color (grayish)
        pixel: tuple[int, ...] = final_img.getpixel((60, 15))  # type: ignore[assignment]
        # Should be close to background (allowing for anti-aliasing)
        assert abs(pixel[0] - background[0]) < 20

    def test_draw_bar_hundred_percent(self):
        """Test drawing 100% bar."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_bar(
            draw, rect=(10, 10, 110, 20), percent=100, color=COLOR_CYAN, background=(50, 50, 50)
        )

        final_img = renderer.finalize(img)

        # All should be filled with cyan
        left_pixel: tuple[int, ...] = final_img.getpixel((30, 15))  # type: ignore[assignment]
        right_pixel: tuple[int, ...] = final_img.getpixel((90, 15))  # type: ignore[assignment]

        # Both should have high green (cyan component)
        assert left_pixel[1] > 100
        assert right_pixel[1] > 100

    def test_draw_sparkline(self):
        """Test drawing sparkline."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        data = [10, 20, 15, 30, 25, 35]
        renderer.draw_sparkline(draw, rect=(10, 10, 110, 50), data=data, color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_sparkline_empty_data(self):
        """Test that sparkline handles empty data gracefully."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Should not raise
        renderer.draw_sparkline(draw, rect=(10, 10, 110, 50), data=[], color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_sparkline_single_point(self):
        """Test that sparkline handles single point gracefully."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Should not raise
        renderer.draw_sparkline(draw, rect=(10, 10, 110, 50), data=[5], color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_sparkline_no_fill(self):
        """Test sparkline without fill."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        data = [10, 20, 15, 30, 25, 35]
        renderer.draw_sparkline(
            draw, rect=(10, 10, 110, 50), data=data, color=COLOR_CYAN, fill=False
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_arc(self):
        """Test drawing arc gauge."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_arc(
            draw, rect=(10, 10, 100, 100), percent=50, color=COLOR_CYAN, background=(50, 50, 50)
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_arc_zero(self):
        """Test drawing 0% arc."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_arc(
            draw, rect=(10, 10, 100, 100), percent=0, color=COLOR_CYAN, background=(50, 50, 50)
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_arc_full(self):
        """Test drawing 100% arc."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_arc(
            draw, rect=(10, 10, 100, 100), percent=100, color=COLOR_CYAN, background=(50, 50, 50)
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

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

        jpeg_bytes = renderer.to_jpeg(img, quality=50, max_size=None)

        # JPEG should start with FF D8 FF
        assert jpeg_bytes[:3] == b"\xff\xd8\xff"
        assert len(jpeg_bytes) > 0

    def test_to_jpeg_quality_affects_size(self):
        """Test that quality affects file size."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw complex content to make quality difference visible
        # Gradient-like effect with many colors
        for i in range(0, 480, 2):
            for j in range(0, 480, 20):
                color = ((i + j) % 256, (i * 2) % 256, (j * 3) % 256)
                draw.point((i, j), fill=color)

        # Also draw text and shapes
        renderer.draw_text(draw, "Quality Test", (120, 120), anchor="mm")
        renderer.draw_bar(draw, (10, 200, 230, 220), percent=75)

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

        # Draw content
        renderer.draw_ring_gauge(draw, (120, 120), 80, 75, COLOR_CYAN, (40, 40, 40), width=10)
        renderer.draw_text(draw, "SIZE TEST", (120, 120), anchor="mm")

        # Get size at high quality without cap
        uncapped = renderer.to_jpeg(img, quality=95, max_size=None)

        # Cap at a very small size to force quality reduction
        small_cap = 3000  # 3KB cap
        capped = renderer.to_jpeg(img, quality=95, max_size=small_cap)

        # Capped version should be smaller or equal to cap
        assert len(capped) <= small_cap

        # Capped should be smaller than uncapped (quality was reduced)
        assert len(capped) < len(uncapped)

    def test_to_jpeg_uses_default_max_size(self):
        """Test that to_jpeg uses MAX_IMAGE_SIZE by default."""
        from custom_components.geekmagic.const import MAX_IMAGE_SIZE

        # MAX_IMAGE_SIZE should be 400KB
        assert MAX_IMAGE_SIZE == 400 * 1024

        renderer = Renderer()
        img, _ = renderer.create_canvas()

        # Normal image should be well under 400KB
        jpeg = renderer.to_jpeg(img)
        assert len(jpeg) < MAX_IMAGE_SIZE

    def test_to_png(self):
        """Test converting to PNG."""
        renderer = Renderer()
        img, _ = renderer.create_canvas()

        png_bytes = renderer.to_png(img)

        # PNG should start with signature
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(png_bytes) > 0

    def test_to_jpeg_rotation(self):
        """Test JPEG rotation parameter."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw asymmetric content so rotation is visible
        draw.rectangle((0, 0, 100, 50), fill=(255, 0, 0))  # Red rectangle top-left

        # Get output at different rotations
        rot_0 = renderer.to_jpeg(img, quality=90, rotation=0)
        rot_90 = renderer.to_jpeg(img, quality=90, rotation=90)
        rot_180 = renderer.to_jpeg(img, quality=90, rotation=180)
        rot_270 = renderer.to_jpeg(img, quality=90, rotation=270)

        # All should be valid JPEGs
        for data in [rot_0, rot_90, rot_180, rot_270]:
            assert data[:3] == b"\xff\xd8\xff"

        # Different rotations should produce different output
        assert rot_0 != rot_90
        assert rot_0 != rot_180
        assert rot_0 != rot_270
        assert rot_90 != rot_180

    def test_to_png_rotation(self):
        """Test PNG rotation parameter."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw asymmetric content so rotation is visible
        draw.rectangle((0, 0, 100, 50), fill=(255, 0, 0))  # Red rectangle top-left

        # Get output at different rotations
        rot_0 = renderer.to_png(img, rotation=0)
        rot_90 = renderer.to_png(img, rotation=90)
        rot_180 = renderer.to_png(img, rotation=180)
        rot_270 = renderer.to_png(img, rotation=270)

        # All should be valid PNGs
        for data in [rot_0, rot_90, rot_180, rot_270]:
            assert data[:8] == b"\x89PNG\r\n\x1a\n"

        # Different rotations should produce different output
        assert rot_0 != rot_90
        assert rot_0 != rot_180
        assert rot_0 != rot_270
        assert rot_90 != rot_180

    def test_dim_color(self):
        """Test color dimming."""
        renderer = Renderer()

        white = (255, 255, 255)
        dimmed = renderer.dim_color(white, factor=0.5)

        assert dimmed == (127, 127, 127)

    def test_blend_color(self):
        """Test color blending."""
        renderer = Renderer()

        color1 = (0, 0, 0)
        color2 = (255, 255, 255)
        blended = renderer.blend_color(color1, color2, factor=0.5)

        assert blended == (127, 127, 127)

    def test_draw_ring_gauge(self):
        """Test drawing ring gauge."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_ring_gauge(draw, center=(120, 120), radius=50, percent=75, color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_panel(self):
        """Test drawing panel."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_panel(draw, rect=(10, 10, 100, 100))

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_ellipse(self):
        """Test drawing ellipse."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_ellipse(draw, rect=(10, 10, 50, 50), fill=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_icon(self):
        """Test drawing MDI icons."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw an MDI icon
        renderer.draw_icon(draw, "home", position=(10, 10), size=24, color=COLOR_WHITE)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)


class TestEmojiRendering:
    """Tests for emoji rendering support."""

    def test_is_emoji_detection(self):
        """Test that emoji characters are correctly detected."""
        from custom_components.geekmagic.renderer import _is_emoji

        # Common emoji should be detected
        assert _is_emoji("\U0001f600")  # Grinning face
        assert _is_emoji("\U0001f4a1")  # Light bulb
        assert _is_emoji("\U0001f50b")  # Battery
        assert _is_emoji("\U00002600")  # Sun (weather)
        assert _is_emoji("\U00002714")  # Check mark
        assert _is_emoji("\U0001f7e2")  # Green circle

        # Regular characters should not be detected as emoji
        assert not _is_emoji("A")
        assert not _is_emoji("1")
        assert not _is_emoji(" ")
        assert not _is_emoji("%")

    def test_segment_text_by_font(self):
        """Test text segmentation into regular and emoji parts."""
        renderer = Renderer()

        # Text with emoji
        segments = renderer._segment_text_by_font("\U0001f50b 76%")
        assert len(segments) == 2
        assert segments[0] == ("\U0001f50b", True)  # Battery emoji
        assert segments[1] == (" 76%", False)  # Space and percentage

        # Multiple emoji with text
        segments = renderer._segment_text_by_font("\U0001f50b 76% \U0001f7e2")
        assert len(segments) == 3
        assert segments[0][1] is True  # First is emoji
        assert segments[1][1] is False  # Middle is text
        assert segments[2][1] is True  # Last is emoji

        # No emoji
        segments = renderer._segment_text_by_font("Hello World")
        assert len(segments) == 1
        assert segments[0] == ("Hello World", False)

        # Only emoji
        segments = renderer._segment_text_by_font("\U0001f600\U0001f600")
        assert len(segments) == 1
        assert segments[0][1] is True

        # Empty text
        segments = renderer._segment_text_by_font("")
        assert len(segments) == 0

    def test_has_emoji(self):
        """Test emoji presence detection."""
        renderer = Renderer()

        assert renderer._has_emoji("\U0001f50b 76%")
        assert renderer._has_emoji("Status: \U0001f7e2")
        assert not renderer._has_emoji("Hello World")
        assert not renderer._has_emoji("12345")
        assert not renderer._has_emoji("")

    def test_draw_text_with_emoji(self):
        """Test drawing text containing emoji."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw text with emoji
        renderer.draw_text(draw, "\U0001f50b 76%", (120, 120), color=COLOR_WHITE, anchor="mm")

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

        # Check that something was drawn (not all black)
        pixels = list(final_img.getdata())
        non_black = [p for p in pixels if p != COLOR_BLACK]
        assert len(non_black) > 0

    def test_draw_text_multiple_emoji(self):
        """Test drawing text with multiple emoji."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Draw text with multiple emoji (like the user's use case)
        renderer.draw_text(
            draw, "\U0001f50b 76% \U0001f7e2", (120, 120), color=COLOR_WHITE, anchor="mm"
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_text_emoji_only(self):
        """Test drawing text that is only emoji."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        renderer.draw_text(draw, "\U0001f600\U0001f4a1", (120, 120), color=COLOR_CYAN, anchor="mm")

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_text_without_emoji_unchanged(self):
        """Test that regular text rendering is unchanged."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Regular text should still work
        renderer.draw_text(draw, "Hello World", (120, 120), color=COLOR_WHITE, anchor="mm")

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_get_text_size_with_emoji(self):
        """Test measuring text size with emoji."""
        renderer = Renderer()

        # Text with emoji
        width, height = renderer.get_text_size("\U0001f50b 76%")
        assert width > 0
        assert height > 0

        # Should be wider than just the text part
        text_only_width, _ = renderer.get_text_size(" 76%")
        assert width > text_only_width

    def test_get_text_size_emoji_only(self):
        """Test measuring emoji-only text."""
        renderer = Renderer()

        width, height = renderer.get_text_size("\U0001f600")
        assert width > 0
        assert height > 0

    def test_fit_text_font_with_emoji(self):
        """Test fitting text with emoji into bounds."""
        renderer = Renderer()

        # Fit text with emoji
        font = renderer.fit_text_font(
            "\U0001f50b 76%", max_width=200, max_height=50, min_size=10, max_size=100
        )

        assert font is not None

    def test_get_emoji_font(self):
        """Test getting cached emoji font."""
        renderer = Renderer()

        # Get emoji font at a size
        font1 = renderer.get_emoji_font(24)
        font2 = renderer.get_emoji_font(24)

        # Should return same cached instance
        assert font1 is font2

        # Different size should be different
        font3 = renderer.get_emoji_font(36)
        assert font3 is not font1

    def test_draw_text_anchors_with_emoji(self):
        """Test that text anchors work correctly with emoji."""
        renderer = Renderer()

        anchors = ["lt", "mm", "rm", "lb", "mb", "rb"]

        for anchor in anchors:
            img, draw = renderer.create_canvas()
            # Should not raise
            renderer.draw_text(draw, "\U0001f50b 76%", (120, 120), color=COLOR_WHITE, anchor=anchor)
            final_img = renderer.finalize(img)
            assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)
