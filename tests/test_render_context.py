"""Tests for RenderContext providing widget-local coordinate system."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_WHITE,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
)
from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer


class TestRenderContextInit:
    """Tests for RenderContext initialization."""

    def test_init_calculates_width_and_height(self):
        """Test that width and height are calculated from rect."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (10, 20, 110, 120)  # 100x100 widget
        ctx = RenderContext(draw, rect, renderer)

        assert ctx.width == 100
        assert ctx.height == 100

    def test_init_stores_origin(self):
        """Test that origin position is stored correctly."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 75, 150, 175)
        ctx = RenderContext(draw, rect, renderer)

        # Check internal origin (used for coordinate translation)
        assert ctx._x1 == 50
        assert ctx._y1 == 75

    def test_init_full_canvas_rect(self):
        """Test RenderContext with full canvas rect."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        ctx = RenderContext(draw, rect, renderer)

        assert ctx.width == DISPLAY_WIDTH
        assert ctx.height == DISPLAY_HEIGHT


class TestCoordinateTranslation:
    """Tests for coordinate translation methods."""

    def test_abs_point_translates_origin(self):
        """Test that _abs_point translates local to absolute coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 100, 150, 200)  # Origin at (50, 100)
        ctx = RenderContext(draw, rect, renderer)

        # Local (0, 0) should map to (50, 100)
        abs_point = ctx._abs_point(0, 0)
        assert abs_point == (50, 100)

        # Local (10, 20) should map to (60, 120)
        abs_point = ctx._abs_point(10, 20)
        assert abs_point == (60, 120)

    def test_abs_rect_translates_bounds(self):
        """Test that _abs_rect translates local rect to absolute."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 100, 150, 200)  # Origin at (50, 100)
        ctx = RenderContext(draw, rect, renderer)

        # Local rect (10, 10, 40, 40) should map to (60, 110, 90, 140)
        abs_rect = ctx._abs_rect((10, 10, 40, 40))
        assert abs_rect == (60, 110, 90, 140)


class TestFontMethods:
    """Tests for font-related methods."""

    def test_get_font_returns_font(self):
        """Test that get_font returns a font object."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 120, 80)
        ctx = RenderContext(draw, rect, renderer)

        font = ctx.get_font("regular")
        assert font is not None

    def test_get_font_respects_size_name(self):
        """Test that different size names produce different fonts."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 200, 200)
        ctx = RenderContext(draw, rect, renderer)

        small_font = ctx.get_font("small")
        large_font = ctx.get_font("large")

        # Different sizes should produce fonts with different actual sizes
        # (they should be different objects or have different sizes)
        small_size = ctx.get_text_size("Test", small_font)
        large_size = ctx.get_text_size("Test", large_font)

        assert large_size[0] > small_size[0]
        assert large_size[1] > small_size[1]

    def test_get_font_bold(self):
        """Test that bold parameter is accepted."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 120, 80)
        ctx = RenderContext(draw, rect, renderer)

        # Should not raise
        font = ctx.get_font("regular", bold=True)
        assert font is not None

    def test_get_text_size_with_default_font(self):
        """Test get_text_size with default font."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 120, 80)
        ctx = RenderContext(draw, rect, renderer)

        width, height = ctx.get_text_size("Test")
        assert width > 0
        assert height > 0

    def test_get_text_size_with_custom_font(self):
        """Test get_text_size with specific font."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 120, 80)
        ctx = RenderContext(draw, rect, renderer)

        font = ctx.get_font("large")
        width, height = ctx.get_text_size("Test", font)
        assert width > 0
        assert height > 0


class TestDrawingMethods:
    """Tests for drawing methods using local coordinates."""

    def test_draw_text(self):
        """Test drawing text in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)  # Widget at (50, 50)
        ctx = RenderContext(draw, rect, renderer)

        # Draw text at local (0, 0) which should appear at absolute (50, 50)
        ctx.draw_text("Hello", (0, 0), color=COLOR_WHITE)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_text_centered(self):
        """Test drawing centered text."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 100, 100)
        ctx = RenderContext(draw, rect, renderer)

        # Draw centered text
        ctx.draw_text("Center", (ctx.width // 2, ctx.height // 2), anchor="mm")

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_rect(self):
        """Test drawing rectangle in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (100, 100, 200, 200)  # Widget at (100, 100)
        ctx = RenderContext(draw, rect, renderer)

        # Draw rect at local (10, 10, 40, 40) -> absolute (110, 110, 140, 140)
        ctx.draw_rect((10, 10, 40, 40), fill=COLOR_WHITE)

        final_img = renderer.finalize(img)

        # Check that pixels at expected location are white
        # Absolute center of rect is (125, 125)
        pixel = final_img.getpixel((125, 125))
        assert pixel == COLOR_WHITE

    def test_draw_panel(self):
        """Test drawing panel in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 100, 100)
        ctx = RenderContext(draw, rect, renderer)

        # Draw panel filling the widget
        ctx.draw_panel((0, 0, ctx.width, ctx.height))

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_bar(self):
        """Test drawing progress bar in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 200, 100)  # Widget at (50, 50)
        ctx = RenderContext(draw, rect, renderer)

        # Draw 50% bar at local (10, 20, 140, 30)
        ctx.draw_bar((10, 20, 140, 30), percent=50, color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

        # Left side (filled) should have cyan
        left_pixel: tuple[int, ...] = final_img.getpixel((80, 75))  # type: ignore[assignment]
        # Right side (background) should be darker
        right_pixel: tuple[int, ...] = final_img.getpixel((170, 75))  # type: ignore[assignment]

        # Left should have more green (cyan component) than right
        assert left_pixel[1] > right_pixel[1]

    def test_draw_ring_gauge(self):
        """Test drawing ring gauge in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)  # 100x100 widget at (50, 50)
        ctx = RenderContext(draw, rect, renderer)

        # Draw ring at local center (50, 50) -> absolute (100, 100)
        ctx.draw_ring_gauge(
            center=(50, 50),
            radius=40,
            percent=75,
            color=COLOR_CYAN,
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_arc(self):
        """Test drawing arc gauge in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)
        ctx = RenderContext(draw, rect, renderer)

        # Draw arc in local coordinates
        ctx.draw_arc(
            rect=(10, 10, 90, 90),
            percent=50,
            color=COLOR_CYAN,
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_sparkline(self):
        """Test drawing sparkline in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (20, 20, 220, 100)
        ctx = RenderContext(draw, rect, renderer)

        data = [10, 20, 15, 30, 25, 35, 20]
        ctx.draw_sparkline(
            rect=(10, 10, ctx.width - 10, ctx.height - 10),
            data=data,
            color=COLOR_CYAN,
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_ellipse(self):
        """Test drawing ellipse in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)
        ctx = RenderContext(draw, rect, renderer)

        # Draw ellipse at local (10, 10, 40, 40) -> absolute (60, 60, 90, 90)
        ctx.draw_ellipse((10, 10, 40, 40), fill=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

        # Check center of ellipse (75, 75)
        pixel = final_img.getpixel((75, 75))
        assert pixel == COLOR_CYAN

    def test_draw_icon(self):
        """Test drawing icon in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (100, 100, 200, 200)
        ctx = RenderContext(draw, rect, renderer)

        # Draw icon at local (10, 10)
        ctx.draw_icon("sun", (10, 10), size=16, color=COLOR_CYAN)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_line(self):
        """Test drawing lines in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)  # Origin at (50, 50)
        ctx = RenderContext(draw, rect, renderer)

        # Draw line from local (0, 0) to (50, 50)
        # Absolute: (50, 50) to (100, 100)
        ctx.draw_line([(0, 0), (50, 50)], fill=COLOR_WHITE, width=2)

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def test_draw_rounded_rect(self):
        """Test drawing rounded rectangle in local coordinates."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (50, 50, 150, 150)
        ctx = RenderContext(draw, rect, renderer)

        ctx.draw_rounded_rect(
            (10, 10, 80, 80),
            radius=8,
            fill=COLOR_CYAN,
        )

        final_img = renderer.finalize(img)
        assert final_img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)


class TestColorUtilities:
    """Tests for color utility methods."""

    def test_dim_color(self):
        """Test color dimming."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        white = (255, 255, 255)
        dimmed = ctx.dim_color(white, factor=0.5)

        assert dimmed == (127, 127, 127)

    def test_dim_color_zero(self):
        """Test dimming to zero."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        white = (255, 255, 255)
        dimmed = ctx.dim_color(white, factor=0.0)

        assert dimmed == (0, 0, 0)

    def test_blend_color(self):
        """Test color blending."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        black = (0, 0, 0)
        white = (255, 255, 255)
        blended = ctx.blend_color(black, white, factor=0.5)

        assert blended == (127, 127, 127)

    def test_blend_color_extremes(self):
        """Test blending at extreme factors."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        black = (0, 0, 0)
        white = (255, 255, 255)

        # factor=0 should return first color
        blended0 = ctx.blend_color(black, white, factor=0.0)
        assert blended0 == (0, 0, 0)

        # factor=1 should return second color
        blended1 = ctx.blend_color(black, white, factor=1.0)
        assert blended1 == (255, 255, 255)


class TestRenderContextIntegration:
    """Integration tests for RenderContext with real widget-like scenarios."""

    def test_widget_at_origin_renders_correctly(self):
        """Test that a widget at canvas origin renders correctly."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        rect = (0, 0, 120, 80)
        ctx = RenderContext(draw, rect, renderer)

        # Draw filled content at widget center
        ctx.draw_text("Origin", (60, 40), anchor="mm")
        ctx.draw_rect((10, 10, 40, 40), fill=COLOR_CYAN)

        final_img = renderer.finalize(img)

        # Filled rect should be visible in center of rect area (25, 25)
        pixel = final_img.getpixel((25, 25))
        assert pixel == COLOR_CYAN

    def test_widget_offset_renders_at_correct_position(self):
        """Test that an offset widget renders at correct absolute position."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Widget in bottom-right quadrant
        rect = (120, 120, 220, 220)  # 100x100 at (120, 120)
        ctx = RenderContext(draw, rect, renderer)

        # Fill the widget with cyan
        ctx.draw_rect((0, 0, 100, 100), fill=COLOR_CYAN)

        final_img = renderer.finalize(img)

        # Should be cyan at center of widget area (170, 170)
        assert final_img.getpixel((170, 170)) == COLOR_CYAN

        # Should NOT be cyan at top-left corner (50, 50)
        assert final_img.getpixel((50, 50)) == COLOR_BLACK

    def test_multiple_widgets_render_independently(self):
        """Test that multiple RenderContexts render independently."""
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Two side-by-side widgets
        rect1 = (0, 0, 100, 100)
        rect2 = (140, 0, 240, 100)

        ctx1 = RenderContext(draw, rect1, renderer)
        ctx2 = RenderContext(draw, rect2, renderer)

        # Each draws a rect at local (10, 10)
        ctx1.draw_ellipse((10, 10, 50, 50), fill=COLOR_CYAN)
        ctx2.draw_ellipse((10, 10, 50, 50), fill=COLOR_WHITE)

        final_img = renderer.finalize(img)

        # First widget's ellipse should be at absolute (30, 30)
        pixel1 = final_img.getpixel((30, 30))
        assert pixel1 == COLOR_CYAN

        # Second widget's ellipse should be at absolute (170, 30)
        pixel2 = final_img.getpixel((170, 30))
        assert pixel2 == COLOR_WHITE

    def test_font_scaling_respects_container_height(self):
        """Test that font scaling varies with container height.

        Note: Font scaling has minimum sizes, so we need containers
        large enough to show the difference.
        """
        renderer = Renderer()
        img, draw = renderer.create_canvas()

        # Medium widget - should hit minimum font sizes
        medium_rect = (0, 0, 120, 80)
        ctx_medium = RenderContext(draw, medium_rect, renderer)
        font_medium = ctx_medium.get_font("regular")
        size_medium = ctx_medium.get_text_size("Test", font_medium)

        # Full canvas widget - should get larger fonts
        full_rect = (0, 0, 240, 240)
        ctx_full = RenderContext(draw, full_rect, renderer)
        font_full = ctx_full.get_font("regular")
        size_full = ctx_full.get_text_size("Test", font_full)

        # Full canvas container should produce larger font
        assert size_full[1] >= size_medium[1]

        # Also verify fonts are actually usable (have positive size)
        assert size_medium[0] > 0
        assert size_medium[1] > 0
        assert size_full[0] > 0
        assert size_full[1] > 0
