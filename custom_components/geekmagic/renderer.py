"""PIL-based image renderer for GeekMagic displays.

Uses 2x supersampling for anti-aliased output.
"""

from __future__ import annotations

import math
from io import BytesIO
from typing import TYPE_CHECKING

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


# Supersampling scale for anti-aliasing
SUPERSAMPLE_SCALE = 2


def _load_font(size: int, bold: bool = False) -> FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font or fall back to default.

    Args:
        size: Font size in pixels
        bold: Whether to load bold variant

    Returns:
        Loaded font or default font
    """
    if bold:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            ("/System/Library/Fonts/Helvetica.ttc", 1),  # macOS (index 1 = bold)
            "/System/Library/Fonts/SFNSText-Bold.ttf",  # macOS newer
            "C:/Windows/Fonts/arialbd.ttf",  # Windows
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            ("/System/Library/Fonts/Helvetica.ttc", 0),  # macOS (index 0 = regular)
            "/System/Library/Fonts/SFNSText.ttf",  # macOS newer
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]

    for path_entry in font_paths:
        try:
            if isinstance(path_entry, tuple):
                path, index = path_entry
                return ImageFont.truetype(path, size, index=index)
            return ImageFont.truetype(path_entry, size)
        except OSError:
            continue

    return ImageFont.load_default()


class Renderer:
    """Renders widgets and layouts to images using PIL with supersampling."""

    def __init__(self) -> None:
        """Initialize the renderer with fonts."""
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self._scale = SUPERSAMPLE_SCALE
        self._scaled_width = self.width * self._scale
        self._scaled_height = self.height * self._scale

        # Load fonts at scaled sizes (min 11px for readability on 240x240 display)
        self.font_tiny = _load_font(11 * self._scale)
        self.font_small = _load_font(13 * self._scale)
        self.font_regular = _load_font(15 * self._scale)
        self.font_medium = _load_font(18 * self._scale)
        self.font_large = _load_font(24 * self._scale)
        self.font_xlarge = _load_font(36 * self._scale)
        self.font_huge = _load_font(52 * self._scale)

        # Bold font variants for emphasis
        self.font_small_bold = _load_font(13 * self._scale, bold=True)
        self.font_regular_bold = _load_font(15 * self._scale, bold=True)
        self.font_medium_bold = _load_font(18 * self._scale, bold=True)

    @property
    def scale(self) -> int:
        """Return the supersampling scale factor."""
        return self._scale

    def _s(self, value: float) -> int:
        """Scale a value for supersampling."""
        return int(value * self._scale)

    def get_scaled_font(
        self,
        size_name: str,
        rect_height: int,
        bold: bool = False,
    ) -> FreeTypeFont | ImageFont.ImageFont:
        """Get a font scaled relative to container height.

        This enables widgets to render correctly at any size by scaling
        fonts proportionally to their container.

        Args:
            size_name: Font size category ("tiny", "small", "regular", "medium",
                      "large", "xlarge", "huge")
            rect_height: Height of the container rect (already scaled for supersample)
            bold: Whether to use bold variant

        Returns:
            Font scaled appropriately for the container size
        """
        # Font config: (base_size, min_size) per category
        # Base sizes are for full 240px height at 2x scale = 480px
        # Min sizes ensure readability even in small containers
        font_config = {
            "tiny": (11, 18),
            "small": (13, 20),
            "regular": (15, 24),
            "medium": (18, 28),
            "large": (24, 34),
            "xlarge": (36, 44),
            "huge": (52, 52),
        }

        base_size, min_size = font_config.get(size_name, (15, 24))

        # Calculate scale factor based on container height vs reference
        # Reference is 240px at 2x scale = 480px
        reference_height = self._scaled_height
        scale_factor = rect_height / reference_height

        # Scale font size with category-specific minimum for readability
        scaled_size = max(min_size, int(base_size * self._scale * scale_factor))

        return _load_font(scaled_size, bold=bold)

    def _scale_rect(self, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Scale a rectangle for supersampling."""
        return (self._s(rect[0]), self._s(rect[1]), self._s(rect[2]), self._s(rect[3]))

    def _scale_point(self, point: tuple[int, int]) -> tuple[int, int]:
        """Scale a point for supersampling."""
        return (self._s(point[0]), self._s(point[1]))

    def create_canvas(
        self, background: tuple[int, int, int] = COLOR_BLACK
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a new image canvas at supersampled resolution.

        Args:
            background: RGB background color tuple

        Returns:
            Tuple of (Image, ImageDraw)
        """
        img = Image.new("RGB", (self._scaled_width, self._scaled_height), background)
        draw = ImageDraw.Draw(img)
        return img, draw

    def _downscale(self, img: Image.Image) -> Image.Image:
        """Downscale supersampled image to final resolution with anti-aliasing."""
        return img.resize((self.width, self.height), Image.Resampling.LANCZOS)

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font: FreeTypeFont | ImageFont.ImageFont | None = None,
        color: tuple[int, int, int] = COLOR_WHITE,
        anchor: str | None = None,
    ) -> None:
        """Draw text on the canvas.

        Args:
            draw: ImageDraw instance
            text: Text to draw
            position: (x, y) position (will be scaled)
            font: Font to use (default: regular)
            color: RGB color tuple
            anchor: Text anchor (e.g., "mm" for center)
        """
        if font is None:
            font = self.font_regular
        scaled_pos = self._scale_point(position)
        draw.text(scaled_pos, text, font=font, fill=color, anchor=anchor)

    def draw_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.rectangle(scaled_rect, fill=fill, outline=outline, width=self._s(width))

    def draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        radius: int = 4,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rounded rectangle.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            radius: Corner radius
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.rounded_rectangle(
            scaled_rect,
            radius=self._s(radius),
            fill=fill,
            outline=outline,
            width=self._s(width),
        )

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
        """Draw a sparkline chart with optional smoothing.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of data points
            color: Line color
            fill: Whether to fill area under the line
            smooth: Whether to use spline interpolation for smooth curves
        """
        if not data or len(data) < 2:
            return

        x1, y1, x2, y2 = rect
        # Scale coordinates
        x1, y1, x2, y2 = self._s(x1), self._s(y1), self._s(x2), self._s(y2)
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

        # Convert to integer tuples
        int_points = [(int(p[0]), int(p[1])) for p in points]

        # Draw filled area
        if fill:
            fill_points = [(x1, y2), *int_points, (x2, y2)]
            fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)
            draw.polygon(fill_points, fill=fill_color)

        # Draw line
        if len(int_points) >= 2:
            draw.line(int_points, fill=color, width=self._s(2))

    def draw_arc(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
        width: int = 8,
    ) -> None:
        """Draw a circular arc gauge.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            percent: Fill percentage (0-100)
            color: Arc color
            background: Background arc color
            width: Arc line width
        """
        scaled_rect = self._scale_rect(rect)
        scaled_width = self._s(width)

        # Draw background arc (270 degree sweep from bottom-left)
        draw.arc(scaled_rect, start=135, end=405, fill=background, width=scaled_width)

        # Draw progress arc
        if percent > 0:
            end_angle = 135 + (percent / 100) * 270
            draw.arc(scaled_rect, start=135, end=end_angle, fill=color, width=scaled_width)

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
        """Draw a full circular ring gauge (360 degrees).

        Args:
            draw: ImageDraw instance
            center: (x, y) center point
            radius: Ring radius
            percent: Fill percentage (0-100)
            color: Ring color
            background: Background ring color
            width: Ring thickness
        """
        cx, cy = self._scale_point(center)
        r = self._s(radius)
        w = self._s(width)

        bbox = (cx - r, cy - r, cx + r, cy + r)

        # Draw background ring (full circle)
        draw.arc(bbox, start=0, end=360, fill=background, width=w)

        # Draw progress ring (starting from top, -90 degrees)
        if percent > 0:
            # PIL arc starts at 3 o'clock and goes clockwise
            # We want to start at 12 o'clock (-90 degrees)
            start = -90
            end = start + (percent / 100) * 360
            draw.arc(bbox, start=start, end=end, fill=color, width=w)

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
        for seg_percent, seg_color in segments:
            seg_width = int(total_width * (seg_percent / 100))
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
        """Draw a mini bar chart (vertical bars).

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of values
            color: Bar color
            background: Optional background color for empty space
            bar_width: Width of each bar
            gap: Gap between bars
        """
        if not data:
            return

        x1, y1, x2, y2 = self._scale_rect(rect)
        height = y2 - y1
        bw = self._s(bar_width)
        g = self._s(gap)

        # Normalize data
        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate how many bars fit
        available_width = x2 - x1
        num_bars = min(len(data), available_width // (bw + g))

        # Use last N data points if we have more data than space
        if len(data) > num_bars:
            data = data[-num_bars:]

        # Draw bars from right to left (most recent on right)
        for i, value in enumerate(reversed(data)):
            bar_x = x2 - (i + 1) * (bw + g)
            if bar_x < x1:
                break

            bar_height = int(((value - min_val) / range_val) * height * 0.9)
            bar_height = max(bar_height, self._s(2))

            bar_y = y2 - bar_height
            draw.rectangle((bar_x, bar_y, bar_x + bw, y2), fill=color)

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
        """Draw an ellipse.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.ellipse(scaled_rect, fill=fill, outline=outline, width=self._s(width))

    def draw_line(
        self,
        draw: ImageDraw.ImageDraw,
        xy: list[tuple[int, int]],
        fill: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw lines.

        Args:
            draw: ImageDraw instance
            xy: List of (x, y) points
            fill: Line color
            width: Line width
        """
        if not xy or len(xy) < 2:
            return

        scaled_xy = [self._scale_point(p) for p in xy]
        draw.line(scaled_xy, fill=fill, width=self._s(width))

    def draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        icon: str,
        position: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = COLOR_WHITE,
    ) -> None:
        """Draw a simple geometric icon.

        Args:
            draw: ImageDraw instance
            icon: Icon name. Supported icons:
                - System: cpu, memory, disk, temp, power, bolt, network, home
                - Weather: sun, drop, cloud, rain, moon, wind
                - Media: play, pause, skip_prev, skip_next, music
                - Arrows: arrow_up, arrow_down
                - Status: check, warning, heart, steps, flame
                - Location: location, building
                - Security: lock, unlock, motion, bell
                - Other: battery, lightbulb
            position: (x, y) top-left corner
            size: Icon size
            color: Icon color
        """
        x, y = self._scale_point(position)
        s = self._s(size)
        half = s // 2
        quarter = s // 4

        if icon == "cpu":
            # CPU chip icon
            draw.rectangle(
                (x + quarter, y + quarter, x + s - quarter, y + s - quarter), outline=color
            )
            for i in range(3):
                px = x + quarter + (i * quarter)
                draw.line([(px, y), (px, y + quarter)], fill=color)
                draw.line([(px, y + s - quarter), (px, y + s)], fill=color)

        elif icon == "memory":
            draw.rectangle((x + 2, y + quarter, x + s - 4, y + s - quarter), outline=color)
            for i in range(3):
                cx = x + 4 + i * (quarter + 1)
                draw.rectangle((cx, y + quarter + 2, cx + 2, y + s - quarter - 4), fill=color)

        elif icon == "disk":
            self.draw_rounded_rect(
                draw,
                (
                    position[0] + 1,
                    position[1] + size // 4,
                    position[0] + size - 1,
                    position[1] + size - size // 4,
                ),
                radius=2,
                outline=color,
            )
            self.draw_ellipse(
                draw,
                (
                    position[0] + size - size // 4 - 2,
                    position[1] + size // 2 - 2,
                    position[0] + size - size // 4 + 2,
                    position[1] + size // 2 + 2,
                ),
                fill=color,
            )

        elif icon == "temp":
            cx = x + half
            self.draw_ellipse(
                draw,
                (
                    position[0] + half - 3,
                    position[1] + size - 7,
                    position[0] + half + 3,
                    position[1] + size - 1,
                ),
                outline=color,
            )
            draw.rectangle(
                (cx - self._s(2), y + self._s(2), cx + self._s(2), y + s - self._s(7)),
                outline=color,
            )
            draw.rectangle(
                (cx - self._s(1), y + half, cx + self._s(1), y + s - self._s(4)), fill=color
            )

        elif icon in {"power", "bolt"}:
            points = [
                (x + half + self._s(1), y),
                (x + self._s(2), y + half),
                (x + half - self._s(1), y + half),
                (x + half - self._s(3), y + s),
                (x + s - self._s(2), y + half - self._s(2)),
                (x + half + self._s(1), y + half - self._s(2)),
            ]
            draw.polygon(points, fill=color)

        elif icon == "network":
            cx = x + half
            for i, r in enumerate([6, 4, 2]):
                sr = self._s(r)
                arc_y = y + self._s(2 + i * 2) + sr
                bbox = (cx - sr, arc_y - sr, cx + sr, arc_y + sr)
                draw.arc(bbox, start=220, end=320, fill=color, width=self._s(1))
            self.draw_ellipse(
                draw,
                (
                    position[0] + half - 1,
                    position[1] + size - 4,
                    position[0] + half + 1,
                    position[1] + size - 2,
                ),
                fill=color,
            )

        elif icon == "home":
            cx = x + half
            # Roof
            draw.polygon(
                [(cx, y + self._s(1)), (x + self._s(1), y + half), (x + s - self._s(1), y + half)],
                outline=color,
            )
            # House body
            draw.rectangle(
                (x + self._s(3), y + half, x + s - self._s(3), y + s - self._s(1)), outline=color
            )

        elif icon == "sun":
            cx, cy = x + half, y + half
            r = quarter
            # Circle
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color)
            # Rays
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = cx + int((r + self._s(2)) * math.cos(rad))
                y1 = cy + int((r + self._s(2)) * math.sin(rad))
                x2 = cx + int((r + self._s(4)) * math.cos(rad))
                y2 = cy + int((r + self._s(4)) * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=color)

        elif icon == "drop":
            cx = x + half
            # Water drop shape
            draw.polygon(
                [
                    (cx, y + self._s(1)),
                    (x + self._s(2), y + s - self._s(4)),
                    (x + s - self._s(2), y + s - self._s(4)),
                ],
                outline=color,
            )
            r = (s - self._s(4)) // 2
            draw.arc(
                (cx - r, y + s - self._s(4) - r, cx + r, y + s - self._s(4) + r),
                start=0,
                end=180,
                fill=color,
            )

        # Media controls
        elif icon == "play":
            # Right-pointing triangle
            draw.polygon(
                [
                    (x + self._s(3), y + self._s(2)),
                    (x + s - self._s(2), y + half),
                    (x + self._s(3), y + s - self._s(2)),
                ],
                fill=color,
            )

        elif icon == "pause":
            # Two vertical bars
            bar_w = s // 4
            gap = s // 6
            draw.rectangle(
                (x + gap, y + self._s(2), x + gap + bar_w, y + s - self._s(2)), fill=color
            )
            draw.rectangle(
                (x + s - gap - bar_w, y + self._s(2), x + s - gap, y + s - self._s(2)), fill=color
            )

        elif icon == "skip_prev":
            # |◀◀ - bar + two triangles pointing left
            bar_x = x + self._s(2)
            draw.rectangle(
                (bar_x, y + self._s(3), bar_x + self._s(2), y + s - self._s(3)), fill=color
            )
            # First triangle
            tri_x = x + s // 3
            draw.polygon(
                [
                    (tri_x + quarter, y + self._s(3)),
                    (tri_x, y + half),
                    (tri_x + quarter, y + s - self._s(3)),
                ],
                fill=color,
            )
            # Second triangle
            tri_x2 = x + s // 3 + quarter
            draw.polygon(
                [
                    (tri_x2 + quarter, y + self._s(3)),
                    (tri_x2, y + half),
                    (tri_x2 + quarter, y + s - self._s(3)),
                ],
                fill=color,
            )

        elif icon == "skip_next":
            # ▶▶| - two triangles pointing right + bar
            bar_x = x + s - self._s(4)
            draw.rectangle(
                (bar_x, y + self._s(3), bar_x + self._s(2), y + s - self._s(3)), fill=color
            )
            # First triangle
            tri_x = x + self._s(2)
            draw.polygon(
                [
                    (tri_x, y + self._s(3)),
                    (tri_x + quarter, y + half),
                    (tri_x, y + s - self._s(3)),
                ],
                fill=color,
            )
            # Second triangle
            tri_x2 = x + self._s(2) + quarter
            draw.polygon(
                [
                    (tri_x2, y + self._s(3)),
                    (tri_x2 + quarter, y + half),
                    (tri_x2, y + s - self._s(3)),
                ],
                fill=color,
            )

        elif icon == "music":
            # Music note - quarter note
            note_r = s // 5
            stem_x = x + s - self._s(4)
            # Note head (filled ellipse)
            draw.ellipse(
                (
                    x + self._s(2),
                    y + s - note_r * 2,
                    x + self._s(2) + note_r * 2,
                    y + s - self._s(1),
                ),
                fill=color,
            )
            # Stem
            draw.rectangle(
                (stem_x - self._s(1), y + self._s(2), stem_x + self._s(1), y + s - note_r),
                fill=color,
            )

        # Arrows & indicators
        elif icon == "arrow_up":
            # Upward pointing triangle
            draw.polygon(
                [
                    (x + half, y + self._s(2)),
                    (x + self._s(2), y + s - self._s(2)),
                    (x + s - self._s(2), y + s - self._s(2)),
                ],
                fill=color,
            )

        elif icon == "arrow_down":
            # Downward pointing triangle
            draw.polygon(
                [
                    (x + half, y + s - self._s(2)),
                    (x + self._s(2), y + self._s(2)),
                    (x + s - self._s(2), y + self._s(2)),
                ],
                fill=color,
            )

        elif icon == "check":
            # Checkmark
            draw.line(
                [
                    (x + self._s(2), y + half),
                    (x + half - self._s(1), y + s - self._s(3)),
                    (x + s - self._s(2), y + self._s(3)),
                ],
                fill=color,
                width=self._s(2),
            )

        elif icon == "warning":
            # Triangle with exclamation mark
            draw.polygon(
                [
                    (x + half, y + self._s(1)),
                    (x + self._s(1), y + s - self._s(2)),
                    (x + s - self._s(1), y + s - self._s(2)),
                ],
                outline=color,
            )
            # Exclamation mark
            draw.rectangle(
                (x + half - self._s(1), y + quarter, x + half + self._s(1), y + half + self._s(2)),
                fill=color,
            )
            draw.ellipse(
                (
                    x + half - self._s(1),
                    y + s - self._s(5),
                    x + half + self._s(1),
                    y + s - self._s(3),
                ),
                fill=color,
            )

        # Activity & health
        elif icon == "heart":
            # Heart shape
            cx = x + half
            # Two circles at top
            r = quarter - self._s(1)
            draw.ellipse((cx - r * 2, y + self._s(2), cx, y + self._s(2) + r * 2), fill=color)
            draw.ellipse((cx, y + self._s(2), cx + r * 2, y + self._s(2) + r * 2), fill=color)
            # Triangle at bottom
            draw.polygon(
                [
                    (x + self._s(2), y + quarter + self._s(2)),
                    (cx, y + s - self._s(2)),
                    (x + s - self._s(2), y + quarter + self._s(2)),
                ],
                fill=color,
            )

        elif icon == "steps":
            # Walking figure (simplified)
            cx = x + half
            # Head
            head_r = s // 6
            draw.ellipse(
                (cx - head_r, y + self._s(1), cx + head_r, y + self._s(1) + head_r * 2), fill=color
            )
            # Body
            draw.line(
                [(cx, y + self._s(1) + head_r * 2), (cx, y + half + quarter)],
                fill=color,
                width=self._s(2),
            )
            # Legs (walking pose)
            draw.line(
                [(cx, y + half + quarter), (x + self._s(3), y + s - self._s(1))],
                fill=color,
                width=self._s(2),
            )
            draw.line(
                [(cx, y + half + quarter), (x + s - self._s(3), y + s - self._s(1))],
                fill=color,
                width=self._s(2),
            )
            # Arms
            draw.line(
                [(cx, y + quarter + head_r), (x + self._s(2), y + half)],
                fill=color,
                width=self._s(2),
            )
            draw.line(
                [(cx, y + quarter + head_r), (x + s - self._s(2), y + half)],
                fill=color,
                width=self._s(2),
            )

        elif icon == "flame":
            # Fire/flame shape
            cx = x + half
            draw.polygon(
                [
                    (cx, y + self._s(1)),
                    (x + self._s(2), y + half + quarter),
                    (x + quarter, y + s - self._s(2)),
                    (cx, y + half + self._s(2)),
                    (x + s - quarter, y + s - self._s(2)),
                    (x + s - self._s(2), y + half + quarter),
                ],
                fill=color,
            )

        # Location & buildings
        elif icon == "location":
            # Map pin/marker
            cx = x + half
            r = quarter
            # Circle at top
            draw.ellipse(
                (cx - r, y + self._s(2), cx + r, y + self._s(2) + r * 2),
                outline=color,
                width=self._s(2),
            )
            # Point at bottom
            draw.polygon(
                [
                    (cx - r + self._s(1), y + self._s(2) + r),
                    (cx, y + s - self._s(2)),
                    (cx + r - self._s(1), y + self._s(2) + r),
                ],
                fill=color,
            )

        elif icon == "building":
            # Simple building
            # Main structure
            draw.rectangle(
                (x + self._s(3), y + self._s(3), x + s - self._s(3), y + s - self._s(1)),
                outline=color,
            )
            # Windows (2x2 grid)
            win_size = self._s(2)
            for row in range(2):
                for col in range(2):
                    wx = x + self._s(5) + col * self._s(4)
                    wy = y + self._s(5) + row * self._s(4)
                    draw.rectangle((wx, wy, wx + win_size, wy + win_size), fill=color)

        elif icon == "lock":
            # Padlock (locked)
            cx = x + half
            # Shackle (arc)
            shackle_r = quarter
            draw.arc(
                (cx - shackle_r, y + self._s(2), cx + shackle_r, y + self._s(2) + shackle_r * 2),
                start=180,
                end=0,
                fill=color,
                width=self._s(2),
            )
            # Lock body
            draw.rectangle(
                (x + self._s(3), y + half - self._s(1), x + s - self._s(3), y + s - self._s(2)),
                fill=color,
            )

        elif icon == "unlock":
            # Padlock (unlocked)
            cx = x + half
            # Shackle (open arc)
            shackle_r = quarter
            draw.arc(
                (cx - shackle_r, y + self._s(1), cx + shackle_r, y + self._s(1) + shackle_r * 2),
                start=180,
                end=270,
                fill=color,
                width=self._s(2),
            )
            # Lock body
            draw.rectangle(
                (x + self._s(3), y + half, x + s - self._s(3), y + s - self._s(2)),
                fill=color,
            )

        elif icon == "motion":
            # Motion detection waves
            cx = x + half
            for r in [quarter, half - self._s(1), half + self._s(2)]:
                draw.arc(
                    (cx - r, y + half - r, cx + r, y + half + r),
                    start=300,
                    end=60,
                    fill=color,
                    width=self._s(1),
                )

        # Weather
        elif icon == "cloud":
            # Cloud shape (overlapping circles)
            # Bottom large circle
            r1 = quarter + self._s(1)
            draw.ellipse(
                (
                    x + self._s(2),
                    y + half - self._s(1),
                    x + self._s(2) + r1 * 2,
                    y + s - self._s(2),
                ),
                fill=color,
            )
            # Top circle
            r2 = quarter
            draw.ellipse(
                (x + quarter, y + self._s(3), x + quarter + r2 * 2, y + half + self._s(2)),
                fill=color,
            )
            # Right circle
            draw.ellipse(
                (x + half, y + quarter, x + s - self._s(2), y + s - self._s(3)),
                fill=color,
            )

        elif icon == "rain":
            # Cloud with rain drops
            # Smaller cloud at top
            r = self._s(3)
            draw.ellipse(
                (x + self._s(2), y + self._s(2), x + self._s(2) + r * 2, y + half - self._s(1)),
                fill=color,
            )
            draw.ellipse(
                (x + quarter, y + self._s(1), x + half + self._s(1), y + half - self._s(2)),
                fill=color,
            )
            draw.ellipse(
                (x + half - self._s(2), y + self._s(2), x + s - self._s(2), y + half - self._s(1)),
                fill=color,
            )
            # Rain drops
            for i in range(3):
                dx = x + self._s(4) + i * self._s(4)
                draw.line(
                    [(dx, y + half + self._s(1)), (dx - self._s(1), y + s - self._s(2))],
                    fill=color,
                    width=self._s(1),
                )

        elif icon == "moon":
            # Crescent moon
            cx, cy = x + half, y + half
            r = half - self._s(2)
            # Full circle
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            # Cut out with black circle offset to the right
            cut_r = r - self._s(2)
            draw.ellipse(
                (
                    cx - cut_r + self._s(4),
                    cy - cut_r - self._s(1),
                    cx + cut_r + self._s(4),
                    cy + cut_r - self._s(1),
                ),
                fill=COLOR_BLACK,
            )

        elif icon == "wind":
            # Wind lines (wavy)
            for i, length in enumerate([s - self._s(4), s - self._s(6), s - self._s(8)]):
                ly = y + self._s(4) + i * self._s(4)
                draw.line(
                    [(x + self._s(2), ly), (x + self._s(2) + length, ly)],
                    fill=color,
                    width=self._s(1),
                )
                # Small curve at end
                draw.arc(
                    (
                        x + length - self._s(2),
                        ly - self._s(2),
                        x + length + self._s(2),
                        ly + self._s(2),
                    ),
                    start=270,
                    end=90,
                    fill=color,
                    width=self._s(1),
                )

        elif icon == "battery":
            # Battery icon
            # Main body
            draw.rectangle(
                (x + self._s(1), y + self._s(3), x + s - self._s(3), y + s - self._s(3)),
                outline=color,
            )
            # Positive terminal
            draw.rectangle(
                (
                    x + s - self._s(3),
                    y + half - self._s(2),
                    x + s - self._s(1),
                    y + half + self._s(2),
                ),
                fill=color,
            )

        elif icon == "bell":
            # Bell/notification icon
            cx = x + half
            # Bell body (arc)
            r = half - self._s(2)
            draw.arc(
                (cx - r, y + self._s(2), cx + r, y + self._s(2) + r * 2),
                start=180,
                end=0,
                fill=color,
                width=self._s(2),
            )
            # Bell sides
            draw.line(
                [(cx - r, y + self._s(2) + r), (cx - r - self._s(1), y + s - self._s(4))],
                fill=color,
                width=self._s(2),
            )
            draw.line(
                [(cx + r, y + self._s(2) + r), (cx + r + self._s(1), y + s - self._s(4))],
                fill=color,
                width=self._s(2),
            )
            # Bell bottom
            draw.line(
                [(x + self._s(1), y + s - self._s(4)), (x + s - self._s(1), y + s - self._s(4))],
                fill=color,
                width=self._s(2),
            )
            # Clapper
            draw.ellipse(
                (cx - self._s(1), y + s - self._s(3), cx + self._s(1), y + s - self._s(1)),
                fill=color,
            )

        elif icon == "lightbulb":
            # Light bulb
            cx = x + half
            r = quarter + self._s(1)
            # Bulb (circle)
            draw.ellipse(
                (cx - r, y + self._s(2), cx + r, y + self._s(2) + r * 2),
                outline=color,
                width=self._s(2),
            )
            # Base
            draw.rectangle(
                (cx - self._s(3), y + half + self._s(2), cx + self._s(3), y + s - self._s(2)),
                fill=color,
            )

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
            (width, height) tuple (in final resolution)
        """
        if font is None:
            font = self.font_regular

        bbox = font.getbbox(text)
        if bbox:
            return int((bbox[2] - bbox[0]) / self._scale), int((bbox[3] - bbox[1]) / self._scale)
        return 0, 0

    def finalize(self, img: Image.Image) -> Image.Image:
        """Finalize rendering by downscaling supersampled image.

        Args:
            img: PIL Image at supersampled resolution

        Returns:
            Final anti-aliased image at display resolution
        """
        return self._downscale(img)

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

        # Finalize (downscale) before export
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
        # Finalize (downscale) before export
        final_img = self.finalize(img)
        buffer = BytesIO()
        final_img.save(buffer, format="PNG")
        return buffer.getvalue()
