"""Pillow-based image renderer for GeekMagic displays."""

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
    COLOR_WHITE,
    DEFAULT_JPEG_QUALITY,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
)

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont


# Try to load a good font, fall back to default
def _load_font(size: int) -> FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font or fall back to default."""
    # Common font paths on different systems
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

    # Fall back to default bitmap font
    return ImageFont.load_default()


class Renderer:
    """Renders widgets and layouts to images using Pillow."""

    def __init__(self) -> None:
        """Initialize the renderer with fonts."""
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT

        # Load fonts at different sizes (expanded range for better hierarchy)
        self.font_tiny = _load_font(9)
        self.font_small = _load_font(11)
        self.font_regular = _load_font(13)
        self.font_medium = _load_font(16)
        self.font_large = _load_font(22)
        self.font_xlarge = _load_font(32)
        self.font_huge = _load_font(48)

    def create_canvas(
        self, background: tuple[int, int, int] = COLOR_BLACK
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a new image canvas.

        Args:
            background: RGB background color tuple

        Returns:
            Tuple of (Image, ImageDraw)
        """
        img = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(img)
        return img, draw

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
        """Draw a rectangle.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        draw.rectangle(rect, fill=fill, outline=outline, width=width)

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
        draw.rectangle(rect, fill=background)

        # Draw fill
        if fill_width > 0:
            draw.rectangle((x1, y1, x1 + fill_width, y2), fill=color)

    def draw_sparkline(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        fill: bool = True,
    ) -> None:
        """Draw a sparkline chart.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of data points
            color: Line color
            fill: Whether to fill area under the line
        """
        if not data or len(data) < 2:
            return

        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1

        # Normalize data
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate points
        points = []
        for i, value in enumerate(data):
            x = x1 + (i / (len(data) - 1)) * width
            y = y2 - ((value - min_val) / range_val) * height
            points.append((x, y))

        # Draw filled area if requested
        if fill:
            fill_points = [(x1, y2), *points, (x2, y2)]
            # Use semi-transparent fill
            fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)
            draw.polygon(fill_points, fill=fill_color)

        # Draw line
        if len(points) >= 2:
            draw.line(points, fill=color, width=2)

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
        # Draw background arc (full circle)
        draw.arc(rect, start=135, end=405, fill=background, width=width)

        # Draw progress arc
        if percent > 0:
            end_angle = 135 + (percent / 100) * 270
            draw.arc(rect, start=135, end=int(end_angle), fill=color, width=width)

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

        # Use getbbox for more accurate measurements
        bbox = font.getbbox(text)
        if bbox:
            return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
        return 0, 0

    def to_jpeg(self, img: Image.Image, quality: int = DEFAULT_JPEG_QUALITY) -> bytes:
        """Convert image to JPEG bytes.

        Args:
            img: PIL Image
            quality: JPEG quality (0-100)

        Returns:
            JPEG image bytes
        """
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()

    def to_png(self, img: Image.Image) -> bytes:
        """Convert image to PNG bytes.

        Args:
            img: PIL Image

        Returns:
            PNG image bytes
        """
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    # ========== Advanced Drawing Methods ==========

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
        x, y = center
        rect = (x - radius, y - radius, x + radius, y + radius)

        # Draw background ring (full circle)
        draw.arc(rect, start=0, end=360, fill=background, width=width)

        # Draw progress ring (starting from top, -90 degrees)
        if percent > 0:
            end_angle = -90 + (percent / 100) * 360
            draw.arc(rect, start=-90, end=int(end_angle), fill=color, width=width)

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
        draw.rounded_rectangle(rect, radius=radius, fill=background)

        # Draw segments
        current_x = x1
        for percent, color in segments:
            seg_width = int(total_width * (percent / 100))
            if seg_width > 0 and current_x < x2:
                seg_rect = (current_x, y1, min(current_x + seg_width, x2), y2)
                draw.rectangle(seg_rect, fill=color)
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

        # Draw bars from right to left (most recent on right)
        for i, value in enumerate(reversed(data)):
            bar_x = x2 - (i + 1) * (bar_width + gap)
            if bar_x < x1:
                break

            bar_height = int(((value - min_val) / range_val) * height * 0.9)
            bar_height = max(bar_height, 2)  # Minimum visible height

            bar_y = y2 - bar_height
            draw.rectangle(
                (bar_x, bar_y, bar_x + bar_width, y2),
                fill=color,
            )

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
        draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)

    def draw_panel(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        background: tuple[int, int, int] = (20, 20, 20),
        border_color: tuple[int, int, int] | None = None,
        radius: int = 4,
    ) -> None:
        """Draw a panel/card background.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            background: Panel background color
            border_color: Optional border color
            radius: Corner radius
        """
        draw.rounded_rectangle(rect, radius=radius, fill=background, outline=border_color)

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
            icon: Icon name (cpu, memory, disk, temp, power, network, home, sun, drop, bolt)
            position: (x, y) top-left corner
            size: Icon size
            color: Icon color
        """
        x, y = position
        s = size
        half = s // 2
        quarter = s // 4

        if icon == "cpu":
            # CPU chip icon
            draw.rectangle(
                (x + quarter, y + quarter, x + s - quarter, y + s - quarter), outline=color, width=1
            )
            # Pins
            for i in range(3):
                px = x + quarter + (i * quarter)
                draw.line([(px, y), (px, y + quarter)], fill=color, width=1)
                draw.line([(px, y + s - quarter), (px, y + s)], fill=color, width=1)

        elif icon == "memory":
            # RAM stick icon
            draw.rectangle((x + 2, y + quarter, x + s - 2, y + s - quarter), outline=color, width=1)
            # Chips
            for i in range(3):
                cx = x + 4 + i * (quarter + 1)
                draw.rectangle((cx, y + quarter + 2, cx + 2, y + s - quarter - 2), fill=color)

        elif icon == "disk":
            # Hard drive icon
            draw.rounded_rectangle(
                (x + 1, y + quarter, x + s - 1, y + s - quarter), radius=2, outline=color, width=1
            )
            draw.ellipse(
                (x + s - quarter - 2, y + half - 2, x + s - quarter + 2, y + half + 2), fill=color
            )

        elif icon == "temp":
            # Thermometer icon
            cx = x + half
            draw.ellipse((cx - 3, y + s - 7, cx + 3, y + s - 1), outline=color, width=1)
            draw.rectangle((cx - 2, y + 2, cx + 2, y + s - 5), outline=color, width=1)
            draw.rectangle((cx - 1, y + half, cx + 1, y + s - 4), fill=color)

        elif icon == "power":
            # Power/lightning bolt
            points = [
                (x + half + 2, y),
                (x + quarter, y + half),
                (x + half, y + half),
                (x + half - 2, y + s),
                (x + s - quarter, y + half),
                (x + half, y + half),
            ]
            draw.polygon(points, fill=color)

        elif icon == "network":
            # Network/wifi icon
            cx = x + half
            for i, r in enumerate([6, 4, 2]):
                draw.arc(
                    (cx - r, y + 2 + i * 2, cx + r, y + 2 + r * 2),
                    start=220,
                    end=320,
                    fill=color,
                    width=1,
                )
            draw.ellipse((cx - 1, y + s - 4, cx + 1, y + s - 2), fill=color)

        elif icon == "home":
            # House icon
            cx = x + half
            # Roof
            draw.polygon(
                [(cx, y + 1), (x + 1, y + half), (x + s - 1, y + half)], outline=color, width=1
            )
            # Body
            draw.rectangle((x + 3, y + half, x + s - 3, y + s - 1), outline=color, width=1)

        elif icon == "sun":
            # Sun icon
            cx, cy = x + half, y + half
            r = quarter
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=1)
            # Rays
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = cx + int((r + 2) * math.cos(rad))
                y1 = cy + int((r + 2) * math.sin(rad))
                x2 = cx + int((r + 4) * math.cos(rad))
                y2 = cy + int((r + 4) * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

        elif icon == "drop":
            # Water drop icon
            cx = x + half
            # Drop shape
            draw.polygon(
                [(cx, y + 1), (x + 2, y + s - 4), (x + s - 2, y + s - 4)], outline=color, width=1
            )
            draw.arc((x + 2, y + half, x + s - 2, y + s), start=0, end=180, fill=color, width=1)

        elif icon == "bolt":
            # Lightning bolt
            points = [
                (x + half + 1, y),
                (x + 2, y + half),
                (x + half - 1, y + half),
                (x + half - 3, y + s),
                (x + s - 2, y + half - 2),
                (x + half + 1, y + half - 2),
            ]
            draw.polygon(points, fill=color)

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
