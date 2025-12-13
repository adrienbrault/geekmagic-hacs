"""Pillow-based image renderer for GeekMagic displays."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from .const import (
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    DEFAULT_JPEG_QUALITY,
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_GRAY,
    COLOR_CYAN,
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

        # Load fonts at different sizes
        self.font_small = _load_font(12)
        self.font_regular = _load_font(14)
        self.font_large = _load_font(24)
        self.font_xlarge = _load_font(36)

    def create_canvas(self, background: tuple[int, int, int] = COLOR_BLACK) -> tuple[Image.Image, ImageDraw.Draw]:
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
        draw: ImageDraw.Draw,
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
        draw: ImageDraw.Draw,
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
        draw: ImageDraw.Draw,
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
        draw: ImageDraw.Draw,
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
            fill_points = [(x1, y2)] + points + [(x2, y2)]
            # Use semi-transparent fill
            fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)
            draw.polygon(fill_points, fill=fill_color)

        # Draw line
        if len(points) >= 2:
            draw.line(points, fill=color, width=2)

    def draw_arc(
        self,
        draw: ImageDraw.Draw,
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
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
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
