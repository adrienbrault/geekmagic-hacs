"""Cairo-based image renderer for GeekMagic displays.

Uses pycairo for high-quality anti-aliased vector graphics.
"""

from __future__ import annotations

import math
from io import BytesIO
from typing import TYPE_CHECKING

import cairo
from PIL import Image, ImageDraw, ImageFont

from .const import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_GRAY,
    COLOR_GRAY,
    COLOR_PANEL,
    COLOR_WHITE,
    DEFAULT_JPEG_QUALITY,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
)

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont


def _load_font(size: int) -> FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font or fall back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/System/Library/Fonts/SFNSText.ttf",  # macOS newer
        "C:/Windows/Fonts/arial.ttf",  # Windows
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    return ImageFont.load_default()


def _rgb_to_cairo(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert RGB (0-255) to Cairo color (0-1)."""
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


class Renderer:
    """Renders widgets and layouts to images using Cairo for high-quality anti-aliasing."""

    def __init__(self) -> None:
        """Initialize the renderer with fonts."""
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT

        # Load fonts at different sizes
        self.font_tiny = _load_font(9)
        self.font_small = _load_font(11)
        self.font_regular = _load_font(13)
        self.font_medium = _load_font(16)
        self.font_large = _load_font(22)
        self.font_xlarge = _load_font(32)
        self.font_huge = _load_font(48)

        # Cairo surface and context (created per render)
        self._surface: cairo.ImageSurface | None = None
        self._ctx: cairo.Context | None = None
        self._pil_image: Image.Image | None = None

    def create_canvas(
        self, background: tuple[int, int, int] = COLOR_BLACK
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a new image canvas.

        Returns PIL Image and ImageDraw for API compatibility.
        Cairo context is stored internally.

        Args:
            background: RGB background color tuple

        Returns:
            Tuple of (Image, ImageDraw) - ImageDraw is a proxy that uses Cairo
        """
        # Create Cairo surface
        self._surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.width, self.height)
        self._ctx = cairo.Context(self._surface)

        # Set best anti-aliasing
        self._ctx.set_antialias(cairo.ANTIALIAS_BEST)

        # Fill background
        self._ctx.set_source_rgb(*_rgb_to_cairo(background))
        self._ctx.paint()

        # Create PIL image for text rendering (Cairo font handling is complex)
        self._pil_image = Image.new("RGB", (self.width, self.height), background)
        pil_draw = ImageDraw.Draw(self._pil_image)

        return self._pil_image, pil_draw

    def _sync_cairo_to_pil(self) -> None:
        """Copy Cairo surface to PIL image."""
        if self._surface is None or self._pil_image is None:
            return

        # Get Cairo surface data and copy to PIL
        data = bytes(self._surface.get_data())
        cairo_img = Image.frombuffer("RGBA", (self.width, self.height), data, "raw", "BGRA", 0, 1)
        # Paste Cairo content onto PIL image (preserving text)
        self._pil_image.paste(cairo_img.convert("RGB"))

    def _sync_pil_to_cairo(self) -> None:
        """Copy PIL image to Cairo surface for compositing."""
        if self._surface is None or self._pil_image is None or self._ctx is None:
            return

        # Convert PIL to BGRA for Cairo
        img_rgba = self._pil_image.convert("RGBA")
        data = img_rgba.tobytes("raw", "BGRA")

        # Create temporary surface and paint onto main surface
        temp_surface = cairo.ImageSurface.create_for_data(
            bytearray(data), cairo.FORMAT_ARGB32, self.width, self.height
        )
        self._ctx.set_source_surface(temp_surface, 0, 0)
        self._ctx.paint()

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font: FreeTypeFont | ImageFont.ImageFont | None = None,
        color: tuple[int, int, int] = COLOR_WHITE,
        anchor: str | None = None,
    ) -> None:
        """Draw text on the canvas using PIL for consistent fonts.

        Args:
            draw: ImageDraw instance
            text: Text to draw
            position: (x, y) position
            font: Font to use (default: regular)
            color: RGB color tuple
            anchor: Text anchor (e.g., "mm" for center)
        """
        if font is None:
            font = self.font_regular
        draw.text(position, text, font=font, fill=color, anchor=anchor)

    def draw_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle using Cairo.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            rect: (x1, y1, x2, y2) coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        if self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        self._ctx.rectangle(x1, y1, x2 - x1, y2 - y1)

        if fill:
            self._ctx.set_source_rgb(*_rgb_to_cairo(fill))
            if outline:
                self._ctx.fill_preserve()
            else:
                self._ctx.fill()

        if outline:
            self._ctx.set_source_rgb(*_rgb_to_cairo(outline))
            self._ctx.set_line_width(width)
            self._ctx.stroke()

    def draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        radius: int = 4,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rounded rectangle with smooth anti-aliased corners.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            rect: (x1, y1, x2, y2) coordinates
            radius: Corner radius
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        if self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        w = x2 - x1
        h = y2 - y1

        # Limit radius
        r = min(radius, w / 2, h / 2)

        # Draw rounded rectangle path
        self._ctx.new_path()
        self._ctx.arc(x1 + r, y1 + r, r, math.pi, 1.5 * math.pi)
        self._ctx.arc(x2 - r, y1 + r, r, 1.5 * math.pi, 2 * math.pi)
        self._ctx.arc(x2 - r, y2 - r, r, 0, 0.5 * math.pi)
        self._ctx.arc(x1 + r, y2 - r, r, 0.5 * math.pi, math.pi)
        self._ctx.close_path()

        if fill:
            self._ctx.set_source_rgb(*_rgb_to_cairo(fill))
            if outline:
                self._ctx.fill_preserve()
            else:
                self._ctx.fill()

        if outline:
            self._ctx.set_source_rgb(*_rgb_to_cairo(outline))
            self._ctx.set_line_width(width)
            self._ctx.stroke()

    def draw_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
    ) -> None:
        """Draw a horizontal progress bar.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            percent: Fill percentage (0-100)
            color: Bar fill color
            background: Background color
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        fill_width = int(width * (percent / 100))

        # Draw background
        self.draw_rounded_rect(draw, rect, radius=2, fill=background)

        # Draw fill
        if fill_width > 0:
            self.draw_rounded_rect(draw, (x1, y1, x1 + fill_width, y2), radius=2, fill=color)

    def _interpolate_catmull_rom(
        self, points: list[tuple[float, float]], num_points: int = 100
    ) -> list[tuple[float, float]]:
        """Interpolate points using Catmull-Rom spline for smooth curves.

        Args:
            points: List of (x, y) control points
            num_points: Number of output points

        Returns:
            Smoothly interpolated points
        """
        if len(points) < 2:
            return points
        if len(points) == 2:
            result = []
            for i in range(num_points):
                t = i / (num_points - 1)
                x = points[0][0] + t * (points[1][0] - points[0][0])
                y = points[0][1] + t * (points[1][1] - points[0][1])
                result.append((x, y))
            return result

        # Add phantom points at start and end for Catmull-Rom
        pts = [points[0], *points, points[-1]]
        result = []

        segments = len(pts) - 3
        points_per_segment = max(1, num_points // segments)

        for i in range(segments):
            p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]

            for j in range(points_per_segment):
                t = j / points_per_segment
                t2 = t * t
                t3 = t2 * t

                x = 0.5 * (
                    (2 * p1[0])
                    + (-p0[0] + p2[0]) * t
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    (2 * p1[1])
                    + (-p0[1] + p2[1]) * t
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                result.append((x, y))

        result.append(pts[-2])
        return result

    def draw_sparkline(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        fill: bool = True,
        smooth: bool = True,
    ) -> None:
        """Draw a smooth anti-aliased sparkline chart using Cairo.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            rect: (x1, y1, x2, y2) bounding box
            data: List of data points
            color: Line color
            fill: Whether to fill area under the line
            smooth: Whether to use spline interpolation for smooth curves
        """
        if not data or len(data) < 2 or self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1

        # Normalize data
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate control points
        control_points: list[tuple[float, float]] = []
        for i, value in enumerate(data):
            x = x1 + (i / (len(data) - 1)) * width
            y = y2 - ((value - min_val) / range_val) * height
            control_points.append((x, y))

        # Interpolate for smooth curves
        if smooth and len(control_points) >= 3:
            num_points = max(50, width // 2)
            points = self._interpolate_catmull_rom(control_points, num_points)
        else:
            points = control_points

        # Draw filled area
        if fill:
            self._ctx.new_path()
            self._ctx.move_to(x1, y2)
            for p in points:
                self._ctx.line_to(p[0], p[1])
            self._ctx.line_to(x2, y2)
            self._ctx.close_path()

            fill_color = _rgb_to_cairo((color[0] // 4, color[1] // 4, color[2] // 4))
            self._ctx.set_source_rgb(*fill_color)
            self._ctx.fill()

        # Draw line
        if len(points) >= 2:
            self._ctx.set_source_rgb(*_rgb_to_cairo(color))
            self._ctx.set_line_width(2)
            self._ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            self._ctx.set_line_join(cairo.LINE_JOIN_ROUND)

            self._ctx.move_to(points[0][0], points[0][1])
            for p in points[1:]:
                self._ctx.line_to(p[0], p[1])
            self._ctx.stroke()

    def draw_arc(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
        width: int = 8,
    ) -> None:
        """Draw a circular arc gauge using Cairo for smooth anti-aliasing.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            rect: (x1, y1, x2, y2) bounding box
            percent: Fill percentage (0-100)
            color: Arc color
            background: Background arc color
            width: Arc line width
        """
        if self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        radius = (x2 - x1) / 2

        # Draw background arc (270 degree sweep from bottom-left)
        self._ctx.set_source_rgb(*_rgb_to_cairo(background))
        self._ctx.set_line_width(width)
        self._ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self._ctx.arc(cx, cy, radius, math.radians(135), math.radians(405))
        self._ctx.stroke()

        # Draw progress arc
        if percent > 0:
            self._ctx.set_source_rgb(*_rgb_to_cairo(color))
            end_angle = 135 + (percent / 100) * 270
            self._ctx.arc(cx, cy, radius, math.radians(135), math.radians(end_angle))
            self._ctx.stroke()

    def draw_ring_gauge(
        self,
        draw: ImageDraw.ImageDraw,
        center: tuple[int, int],
        radius: int,
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        width: int = 6,
    ) -> None:
        """Draw a full circular ring gauge (360 degrees) using Cairo.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            center: (x, y) center point
            radius: Ring radius
            percent: Fill percentage (0-100)
            color: Ring color
            background: Background ring color
            width: Ring thickness
        """
        if self._ctx is None:
            return

        x, y = center

        # Draw background ring (full circle)
        self._ctx.set_source_rgb(*_rgb_to_cairo(background))
        self._ctx.set_line_width(width)
        self._ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self._ctx.arc(x, y, radius, 0, 2 * math.pi)
        self._ctx.stroke()

        # Draw progress ring (starting from top, -90 degrees)
        if percent > 0:
            self._ctx.set_source_rgb(*_rgb_to_cairo(color))
            start_angle = -math.pi / 2
            end_angle = start_angle + (percent / 100) * 2 * math.pi
            self._ctx.arc(x, y, radius, start_angle, end_angle)
            self._ctx.stroke()

    def draw_segmented_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        segments: list[tuple[float, tuple[int, int, int]]],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        radius: int = 2,
    ) -> None:
        """Draw a segmented horizontal bar with multiple colored sections.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            segments: List of (percentage, color) tuples, should sum to <= 100
            background: Background color
            radius: Corner radius
        """
        x1, y1, x2, y2 = rect
        total_width = x2 - x1

        # Draw background
        self.draw_rounded_rect(draw, rect, radius=radius, fill=background)

        # Draw segments
        current_x = x1
        for percent, seg_color in segments:
            seg_width = int(total_width * (percent / 100))
            if seg_width > 0 and current_x < x2:
                seg_rect = (current_x, y1, min(current_x + seg_width, x2), y2)
                self.draw_rect(draw, seg_rect, fill=seg_color)
                current_x += seg_width

    def draw_mini_bars(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] | None = None,
        bar_width: int = 3,
        gap: int = 1,
    ) -> None:
        """Draw a mini bar chart (vertical bars) using Cairo.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of values
            color: Bar color
            background: Optional background color for empty space
            bar_width: Width of each bar
            gap: Gap between bars
        """
        if not data or self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        height = y2 - y1

        # Normalize data
        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate how many bars fit
        available_width = x2 - x1
        num_bars = min(len(data), available_width // (bar_width + gap))

        # Use last N data points if we have more data than space
        if len(data) > num_bars:
            data = data[-num_bars:]

        self._ctx.set_source_rgb(*_rgb_to_cairo(color))

        # Draw bars from right to left (most recent on right)
        for i, value in enumerate(reversed(data)):
            bar_x = x2 - (i + 1) * (bar_width + gap)
            if bar_x < x1:
                break

            bar_height = int(((value - min_val) / range_val) * height * 0.9)
            bar_height = max(bar_height, 2)

            bar_y = y2 - bar_height
            self._ctx.rectangle(bar_x, bar_y, bar_width, bar_height)
            self._ctx.fill()

    def draw_panel(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        background: tuple[int, int, int] = COLOR_PANEL,
        border_color: tuple[int, int, int] | None = None,
        radius: int = 4,
    ) -> None:
        """Draw a panel/card background with rounded corners.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            background: Panel background color
            border_color: Optional border color
            radius: Corner radius
        """
        self.draw_rounded_rect(draw, rect, radius=radius, fill=background, outline=border_color)

    def draw_ellipse(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw an anti-aliased ellipse using Cairo.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            rect: (x1, y1, x2, y2) bounding box
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        if self._ctx is None:
            return

        x1, y1, x2, y2 = rect
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = (x2 - x1) / 2
        ry = (y2 - y1) / 2

        self._ctx.save()
        self._ctx.translate(cx, cy)
        self._ctx.scale(rx, ry)
        self._ctx.arc(0, 0, 1, 0, 2 * math.pi)
        self._ctx.restore()

        if fill:
            self._ctx.set_source_rgb(*_rgb_to_cairo(fill))
            if outline:
                self._ctx.fill_preserve()
            else:
                self._ctx.fill()

        if outline:
            self._ctx.set_source_rgb(*_rgb_to_cairo(outline))
            self._ctx.set_line_width(width)
            self._ctx.stroke()

    def draw_line(
        self,
        draw: ImageDraw.ImageDraw,
        xy: list[tuple[int, int]],
        fill: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw anti-aliased lines using Cairo.

        Args:
            draw: ImageDraw instance (unused, for API compatibility)
            xy: List of (x, y) points
            fill: Line color
            width: Line width
        """
        if self._ctx is None or not xy or len(xy) < 2:
            return

        if fill:
            self._ctx.set_source_rgb(*_rgb_to_cairo(fill))
        self._ctx.set_line_width(width)
        self._ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self._ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        self._ctx.move_to(xy[0][0], xy[0][1])
        for p in xy[1:]:
            self._ctx.line_to(p[0], p[1])
        self._ctx.stroke()

    def draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        icon: str,
        position: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = COLOR_WHITE,
    ) -> None:
        """Draw a simple geometric icon using Cairo.

        Args:
            draw: ImageDraw instance
            icon: Icon name (cpu, memory, disk, temp, power, network, home, sun, drop, bolt)
            position: (x, y) top-left corner
            size: Icon size
            color: Icon color
        """
        if self._ctx is None:
            return

        x, y = position
        s = size
        half = s // 2
        quarter = s // 4

        self._ctx.set_source_rgb(*_rgb_to_cairo(color))
        self._ctx.set_line_width(1)

        if icon == "cpu":
            # CPU chip icon
            self._ctx.rectangle(x + quarter, y + quarter, s - 2 * quarter, s - 2 * quarter)
            self._ctx.stroke()
            for i in range(3):
                px = x + quarter + (i * quarter)
                self._ctx.move_to(px, y)
                self._ctx.line_to(px, y + quarter)
                self._ctx.move_to(px, y + s - quarter)
                self._ctx.line_to(px, y + s)
            self._ctx.stroke()

        elif icon == "memory":
            self._ctx.rectangle(x + 2, y + quarter, s - 4, s - 2 * quarter)
            self._ctx.stroke()
            for i in range(3):
                cx = x + 4 + i * (quarter + 1)
                self._ctx.rectangle(cx, y + quarter + 2, 2, s - 2 * quarter - 4)
                self._ctx.fill()

        elif icon == "disk":
            self.draw_rounded_rect(
                draw, (x + 1, y + quarter, x + s - 1, y + s - quarter), radius=2, outline=color
            )
            self.draw_ellipse(
                draw,
                (x + s - quarter - 2, y + half - 2, x + s - quarter + 2, y + half + 2),
                fill=color,
            )

        elif icon == "temp":
            cx = x + half
            self.draw_ellipse(draw, (cx - 3, y + s - 7, cx + 3, y + s - 1), outline=color)
            self._ctx.rectangle(cx - 2, y + 2, 4, s - 7)
            self._ctx.stroke()
            self._ctx.rectangle(cx - 1, y + half, 2, s - half - 4)
            self._ctx.fill()

        elif icon in {"power", "bolt"}:
            points = [
                (x + half + 1, y),
                (x + 2, y + half),
                (x + half - 1, y + half),
                (x + half - 3, y + s),
                (x + s - 2, y + half - 2),
                (x + half + 1, y + half - 2),
            ]
            self._ctx.move_to(points[0][0], points[0][1])
            for p in points[1:]:
                self._ctx.line_to(p[0], p[1])
            self._ctx.close_path()
            self._ctx.fill()

        elif icon == "network":
            cx = x + half
            for i, r in enumerate([6, 4, 2]):
                self._ctx.arc(cx, y + 2 + i * 2 + r, r, math.radians(220), math.radians(320))
                self._ctx.stroke()
            self.draw_ellipse(draw, (cx - 1, y + s - 4, cx + 1, y + s - 2), fill=color)

        elif icon == "home":
            cx = x + half
            self._ctx.move_to(cx, y + 1)
            self._ctx.line_to(x + 1, y + half)
            self._ctx.line_to(x + s - 1, y + half)
            self._ctx.close_path()
            self._ctx.stroke()
            self._ctx.rectangle(x + 3, y + half, s - 6, s - half - 1)
            self._ctx.stroke()

        elif icon == "sun":
            cx, cy = x + half, y + half
            r = quarter
            self._ctx.arc(cx, cy, r, 0, 2 * math.pi)
            self._ctx.stroke()
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = cx + int((r + 2) * math.cos(rad))
                y1 = cy + int((r + 2) * math.sin(rad))
                x2 = cx + int((r + 4) * math.cos(rad))
                y2 = cy + int((r + 4) * math.sin(rad))
                self._ctx.move_to(x1, y1)
                self._ctx.line_to(x2, y2)
            self._ctx.stroke()

        elif icon == "drop":
            cx = x + half
            self._ctx.move_to(cx, y + 1)
            self._ctx.line_to(x + 2, y + s - 4)
            self._ctx.line_to(x + s - 2, y + s - 4)
            self._ctx.close_path()
            self._ctx.stroke()
            self._ctx.arc(cx, y + s - 4, (s - 4) / 2, 0, math.pi)
            self._ctx.stroke()

    def dim_color(self, color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
        """Dim a color by a factor.

        Args:
            color: RGB color tuple
            factor: Dimming factor (0-1, lower = dimmer)

        Returns:
            Dimmed RGB color
        """
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor),
        )

    def blend_color(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        factor: float = 0.5,
    ) -> tuple[int, int, int]:
        """Blend two colors.

        Args:
            color1: First RGB color
            color2: Second RGB color
            factor: Blend factor (0 = color1, 1 = color2)

        Returns:
            Blended RGB color
        """
        return (
            int(color1[0] + (color2[0] - color1[0]) * factor),
            int(color1[1] + (color2[1] - color1[1]) * factor),
            int(color1[2] + (color2[2] - color1[2]) * factor),
        )

    def get_text_size(
        self,
        text: str,
        font: FreeTypeFont | ImageFont.ImageFont | None = None,
    ) -> tuple[int, int]:
        """Get the size of rendered text.

        Args:
            text: Text to measure
            font: Font to use

        Returns:
            (width, height) tuple
        """
        if font is None:
            font = self.font_regular

        bbox = font.getbbox(text)
        if bbox:
            return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
        return 0, 0

    def finalize(self, img: Image.Image) -> Image.Image:
        """Finalize rendering by compositing Cairo and PIL layers.

        Args:
            img: PIL Image (with text)

        Returns:
            Final composited image
        """
        if self._surface is None or self._ctx is None:
            return img

        # Get Cairo surface as PIL
        data = bytes(self._surface.get_data())
        cairo_img = Image.frombuffer(
            "RGBA", (self.width, self.height), data, "raw", "BGRA", 0, 1
        ).convert("RGB")

        # Composite: Cairo graphics with PIL text on top
        # For areas where PIL has content (text), use PIL; otherwise use Cairo
        # Simple approach: blend Cairo under PIL
        result = cairo_img.copy()

        # Overlay text from PIL image
        # We use the original PIL image which has text on black background
        # Only copy non-black pixels (text)
        pil_data = img.load()
        result_data = result.load()
        if pil_data is not None and result_data is not None:
            for y_px in range(self.height):
                for x_px in range(self.width):
                    pil_pixel = pil_data[x_px, y_px]
                    # If PIL pixel is not black, it's likely text - use it
                    if pil_pixel != (0, 0, 0):
                        result_data[x_px, y_px] = pil_pixel

        return result

    def to_jpeg(
        self,
        img: Image.Image,
        quality: int = DEFAULT_JPEG_QUALITY,
        max_size: int | None = None,
    ) -> bytes:
        """Convert image to JPEG bytes with optional size cap.

        Args:
            img: PIL Image
            quality: JPEG quality (0-100)
            max_size: Maximum size in bytes (reduces quality if exceeded)

        Returns:
            JPEG image bytes
        """
        from .const import MAX_IMAGE_SIZE

        if max_size is None:
            max_size = MAX_IMAGE_SIZE

        # Finalize compositing before export
        final_img = self.finalize(img)

        # Try at requested quality first
        buffer = BytesIO()
        final_img.save(buffer, format="JPEG", quality=quality)
        result = buffer.getvalue()

        # Reduce quality if size exceeds max
        current_quality = quality
        while len(result) > max_size and current_quality > 20:
            current_quality -= 10
            buffer = BytesIO()
            final_img.save(buffer, format="JPEG", quality=current_quality)
            result = buffer.getvalue()

        return result

    def to_png(self, img: Image.Image) -> bytes:
        """Convert image to PNG bytes.

        Args:
            img: PIL Image

        Returns:
            PNG image bytes
        """
        # Finalize compositing before export
        final_img = self.finalize(img)
        buffer = BytesIO()
        final_img.save(buffer, format="PNG")
        return buffer.getvalue()
