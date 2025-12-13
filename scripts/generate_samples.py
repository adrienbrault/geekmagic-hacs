#!/usr/bin/env python3
"""Generate sample renders showcasing GeekMagic display layouts and widgets.

Usage:
    uv run python scripts/generate_samples.py

Outputs PNG images to the samples/ directory.

Uses 2x supersampling for anti-aliased output.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Add the custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_GRAY,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
)
from custom_components.geekmagic.renderer import Renderer, _load_font

# Additional colors for richer UI
COLOR_PURPLE = (168, 85, 247)
COLOR_ORANGE = (251, 146, 60)
COLOR_BLUE = (96, 165, 250)
COLOR_PINK = (244, 114, 182)
COLOR_PANEL = (18, 18, 18)
COLOR_PANEL_BORDER = (40, 40, 40)

# Supersampling scale for anti-aliasing
SCALE = 2


def s(value: float) -> int:
    """Scale a value for supersampling."""
    return int(value * SCALE)


class HighQualityRenderer(Renderer):
    """Renderer that uses supersampling for anti-aliased output.

    All drawing methods automatically scale coordinates by the scale factor.
    """

    def __init__(self, scale: int = 2) -> None:
        """Initialize with scale factor for supersampling."""
        self.scale = scale
        self.width = 240 * scale
        self.height = 240 * scale

        # Load fonts at scaled sizes
        self.font_tiny = _load_font(9 * scale)
        self.font_small = _load_font(11 * scale)
        self.font_regular = _load_font(13 * scale)
        self.font_medium = _load_font(16 * scale)
        self.font_large = _load_font(22 * scale)
        self.font_xlarge = _load_font(32 * scale)
        self.font_huge = _load_font(48 * scale)

    def _s(self, value: float) -> int:
        """Scale a single value."""
        return int(value * self.scale)

    def _scale_rect(self, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Scale a rectangle tuple."""
        return (self._s(rect[0]), self._s(rect[1]), self._s(rect[2]), self._s(rect[3]))

    def _scale_point(self, point: tuple[int, int]) -> tuple[int, int]:
        """Scale a point tuple."""
        return (self._s(point[0]), self._s(point[1]))

    def create_canvas(
        self, background: tuple[int, int, int] = COLOR_BLACK
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a scaled canvas."""
        img = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(img)
        return img, draw

    def downscale(self, img: Image.Image) -> Image.Image:
        """Downscale image to target size with high-quality resampling."""
        return img.resize((240, 240), Image.Resampling.LANCZOS)

    # Override all drawing methods to auto-scale coordinates

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font=None,
        color: tuple[int, int, int] = COLOR_WHITE,
        anchor: str | None = None,
    ) -> None:
        """Draw text with scaled position."""
        super().draw_text(draw, text, self._scale_point(position), font, color, anchor)

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
        """Draw ring gauge with scaled dimensions."""
        super().draw_ring_gauge(
            draw,
            self._scale_point(center),
            self._s(radius),
            percent,
            color,
            background,
            self._s(width),
        )

    def draw_segmented_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        segments: list[tuple[float, tuple[int, int, int]]],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        radius: int = 2,
    ) -> None:
        """Draw segmented bar with scaled dimensions."""
        super().draw_segmented_bar(
            draw, self._scale_rect(rect), segments, background, self._s(radius)
        )

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
        """Draw mini bars with scaled dimensions."""
        super().draw_mini_bars(
            draw, self._scale_rect(rect), data, color, background, self._s(bar_width), self._s(gap)
        )

    def draw_panel(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        background: tuple[int, int, int] = (20, 20, 20),
        border_color: tuple[int, int, int] | None = None,
        radius: int = 4,
    ) -> None:
        """Draw panel with scaled dimensions."""
        super().draw_panel(draw, self._scale_rect(rect), background, border_color, self._s(radius))

    def draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        icon: str,
        position: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = COLOR_WHITE,
    ) -> None:
        """Draw icon with scaled dimensions."""
        super().draw_icon(draw, icon, self._scale_point(position), self._s(size), color)

    def draw_sparkline(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        fill: bool = True,
    ) -> None:
        """Draw sparkline with scaled dimensions."""
        super().draw_sparkline(draw, self._scale_rect(rect), data, color, fill)

    def draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        radius: int = 4,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw rounded rect with scaled dimensions."""
        super().draw_rounded_rect(
            draw, self._scale_rect(rect), self._s(radius), fill, outline, self._s(width)
        )

    def draw_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw rect with scaled dimensions."""
        super().draw_rect(draw, self._scale_rect(rect), fill, outline, self._s(width))

    def draw_arc(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
        width: int = 8,
    ) -> None:
        """Draw arc with scaled dimensions."""
        super().draw_arc(draw, self._scale_rect(rect), percent, color, background, self._s(width))

    def draw_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
    ) -> None:
        """Draw bar with scaled dimensions."""
        super().draw_bar(draw, self._scale_rect(rect), percent, color, background)

    def draw_ellipse(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
    ) -> None:
        """Draw ellipse with scaled dimensions."""
        draw.ellipse(self._scale_rect(rect), fill=fill, outline=outline)

    def draw_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
    ) -> None:
        """Draw rectangle with scaled dimensions."""
        draw.rectangle(self._scale_rect(rect), fill=fill, outline=outline)

    def draw_line(
        self,
        draw: ImageDraw.ImageDraw,
        xy: list[tuple[int, int]],
        fill: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw line with scaled dimensions."""
        scaled_xy = [self._scale_point(p) for p in xy]
        draw.line(scaled_xy, fill=fill, width=self._s(width))


def save_image(
    renderer: HighQualityRenderer, img: Image.Image, name: str, output_dir: Path
) -> None:
    """Save image as PNG with downscaling for anti-aliasing."""
    # Downscale for anti-aliasing
    final_img = renderer.downscale(img)
    output_path = output_dir / f"{name}.png"
    final_img.save(output_path, format="PNG")
    print(f"  ✓ {output_path}")


def generate_system_monitor(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a system monitor dashboard with ring gauges."""
    img, draw = renderer.create_canvas()

    # Title bar
    renderer.draw_text(
        draw, "SYSTEM", (120, 12), font=renderer.font_small, color=COLOR_GRAY, anchor="mm"
    )

    # Top section: CPU and Memory ring gauges
    # CPU Ring (left)
    cpu_center = (60, 70)
    cpu_percent = 42
    renderer.draw_ring_gauge(
        draw, cpu_center, 35, cpu_percent, COLOR_CYAN, COLOR_DARK_GRAY, width=5
    )
    renderer.draw_text(
        draw,
        f"{cpu_percent}%",
        cpu_center,
        font=renderer.font_large,
        color=COLOR_WHITE,
        anchor="mm",
    )
    renderer.draw_text(
        draw, "CPU", (60, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Memory Ring (right)
    mem_center = (180, 70)
    mem_percent = 68
    renderer.draw_ring_gauge(
        draw, mem_center, 35, mem_percent, COLOR_PURPLE, COLOR_DARK_GRAY, width=5
    )
    renderer.draw_text(
        draw,
        f"{mem_percent}%",
        mem_center,
        font=renderer.font_large,
        color=COLOR_WHITE,
        anchor="mm",
    )
    renderer.draw_text(
        draw, "MEM", (180, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Middle section: Disk and Network bars
    y_start = 135

    # Disk usage bar
    renderer.draw_icon(draw, "disk", (12, y_start), size=14, color=COLOR_ORANGE)
    renderer.draw_text(
        draw, "DISK", (32, y_start + 7), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_segmented_bar(
        draw,
        (75, y_start + 2, 190, y_start + 12),
        [(45, COLOR_ORANGE), (20, COLOR_YELLOW)],
        COLOR_DARK_GRAY,
    )
    renderer.draw_text(
        draw, "65%", (200, y_start + 7), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )

    # Network bar
    y_start += 22
    renderer.draw_icon(draw, "network", (12, y_start), size=14, color=COLOR_GREEN)
    renderer.draw_text(
        draw, "NET", (32, y_start + 7), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    net_data = [20, 35, 45, 30, 55, 70, 65, 80, 75, 60, 45, 55]
    renderer.draw_mini_bars(
        draw, (75, y_start, 190, y_start + 14), net_data, COLOR_GREEN, bar_width=4, gap=2
    )
    renderer.draw_text(
        draw, "48Mb", (200, y_start + 7), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )

    # Bottom section: Process list
    y_start = 185

    # Panel background
    renderer.draw_panel(draw, (8, y_start, 232, 232), COLOR_PANEL, radius=4)

    # Process header
    renderer.draw_text(
        draw,
        "TOP PROCESSES",
        (16, y_start + 10),
        font=renderer.font_tiny,
        color=COLOR_GRAY,
        anchor="lm",
    )

    # Process rows
    processes = [
        ("node", 12.4, COLOR_CYAN),
        ("python", 8.2, COLOR_PURPLE),
        ("chrome", 5.1, COLOR_GREEN),
    ]

    for i, (name, cpu, color) in enumerate(processes):
        row_y = y_start + 22 + i * 14
        renderer.draw_text(
            draw, name, (16, row_y), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
        )
        bar_width = int(cpu * 8)
        renderer.draw_rounded_rect(
            draw, (80, row_y - 4, 80 + bar_width, row_y + 4), radius=2, fill=color
        )
        renderer.draw_text(
            draw, f"{cpu}%", (200, row_y), font=renderer.font_tiny, color=color, anchor="lm"
        )

    save_image(renderer, img, "01_system_monitor", output_dir)


def generate_smart_home(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a smart home dashboard."""
    img, draw = renderer.create_canvas()

    # Title
    renderer.draw_icon(draw, "home", (10, 8), size=16, color=COLOR_CYAN)
    renderer.draw_text(
        draw, "HOME", (32, 16), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
    )

    # Temperature panel (top left)
    renderer.draw_panel(draw, (8, 32, 116, 100), COLOR_PANEL, radius=4)
    renderer.draw_icon(draw, "temp", (16, 40), size=14, color=COLOR_ORANGE)
    renderer.draw_text(
        draw, "LIVING ROOM", (36, 47), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "21.5°", (62, 75), font=renderer.font_xlarge, color=COLOR_WHITE, anchor="mm"
    )
    temp_data = [20.5, 20.8, 21.0, 21.2, 21.5, 21.3, 21.5]
    renderer.draw_sparkline(draw, (16, 85, 108, 95), temp_data, COLOR_ORANGE, fill=True)

    # Humidity panel (top right)
    renderer.draw_panel(draw, (124, 32, 232, 100), COLOR_PANEL, radius=4)
    renderer.draw_icon(draw, "drop", (132, 40), size=14, color=COLOR_BLUE)
    renderer.draw_text(
        draw, "HUMIDITY", (152, 47), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "58%", (178, 75), font=renderer.font_xlarge, color=COLOR_WHITE, anchor="mm"
    )
    humidity_data = [55, 56, 57, 58, 57, 58, 58]
    renderer.draw_sparkline(draw, (132, 85, 224, 95), humidity_data, COLOR_BLUE, fill=True)

    # Devices section
    renderer.draw_text(
        draw, "DEVICES", (16, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    devices = [
        ("Lights", True, COLOR_YELLOW),
        ("AC", True, COLOR_CYAN),
        ("TV", False, COLOR_GRAY),
        ("Music", True, COLOR_GREEN),
    ]

    for i, (name, on, color) in enumerate(devices):
        x = 16 + (i % 2) * 112
        y = 130 + (i // 2) * 50
        renderer.draw_panel(draw, (x, y, x + 104, y + 42), COLOR_PANEL, radius=4)

        # Status indicator
        status_color = color if on else COLOR_DARK_GRAY
        renderer.draw_ellipse(draw, (x + 10, y + 16, x + 18, y + 24), fill=status_color)

        renderer.draw_text(
            draw, name, (x + 28, y + 13), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
        )
        status_text = "ON" if on else "OFF"
        renderer.draw_text(
            draw,
            status_text,
            (x + 28, y + 28),
            font=renderer.font_tiny,
            color=status_color,
            anchor="lm",
        )

    save_image(renderer, img, "02_smart_home", output_dir)


def generate_weather(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a weather dashboard."""
    img, draw = renderer.create_canvas()

    # Current weather - large display
    renderer.draw_icon(draw, "sun", (100, 20), size=24, color=COLOR_YELLOW)

    renderer.draw_text(
        draw, "24°", (120, 75), font=renderer.font_huge, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "Sunny", (120, 105), font=renderer.font_regular, color=COLOR_GRAY, anchor="mm"
    )
    renderer.draw_text(
        draw, "San Francisco", (120, 122), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Weather details row
    y_row = 145
    details = [
        ("H: 28°", COLOR_RED),
        ("L: 18°", COLOR_BLUE),
        ("💧 45%", COLOR_CYAN),
        ("💨 12km", COLOR_WHITE),
    ]

    for i, (text, color) in enumerate(details):
        x = 25 + i * 55
        renderer.draw_text(
            draw, text, (x, y_row), font=renderer.font_tiny, color=color, anchor="lm"
        )

    # Forecast section
    renderer.draw_panel(draw, (8, 165, 232, 232), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "5-DAY FORECAST", (16, 177), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    forecast = [
        ("Mon", 26, 19, COLOR_YELLOW),
        ("Tue", 24, 18, COLOR_YELLOW),
        ("Wed", 22, 17, COLOR_GRAY),
        ("Thu", 20, 15, COLOR_BLUE),
        ("Fri", 23, 17, COLOR_YELLOW),
    ]

    for i, (day, high, _low, color) in enumerate(forecast):
        x = 24 + i * 44
        renderer.draw_text(
            draw, day, (x, 195), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
        )
        renderer.draw_ellipse(draw, (x - 4, 203, x + 4, 211), fill=color)
        renderer.draw_text(
            draw, f"{high}°", (x, 222), font=renderer.font_tiny, color=COLOR_WHITE, anchor="mm"
        )

    save_image(renderer, img, "03_weather", output_dir)


def generate_server_stats(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a server statistics dashboard."""
    img, draw = renderer.create_canvas()

    # Header
    renderer.draw_text(
        draw, "SERVER DASHBOARD", (120, 12), font=renderer.font_small, color=COLOR_CYAN, anchor="mm"
    )

    # Large CPU metric with ring
    cpu_center = (60, 65)
    cpu = 73
    renderer.draw_ring_gauge(draw, cpu_center, 32, cpu, COLOR_CYAN, COLOR_DARK_GRAY, width=6)
    renderer.draw_text(
        draw, f"{cpu}", cpu_center, font=renderer.font_large, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "CPU %", (60, 105), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Side metrics
    metrics = [
        ("LOAD", "2.4", COLOR_GREEN),
        ("TEMP", "58°C", COLOR_ORANGE),
        ("UPTIME", "14d", COLOR_PURPLE),
    ]

    for i, (label, value, color) in enumerate(metrics):
        y = 35 + i * 28
        renderer.draw_text(
            draw, label, (130, y), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_text(
            draw, value, (130, y + 12), font=renderer.font_medium, color=color, anchor="lm"
        )

    # Sparkline for history
    cpu_history = [45, 52, 48, 65, 72, 68, 75, 82, 78, 73]
    renderer.draw_panel(draw, (125, 100, 230, 115), COLOR_PANEL, radius=2)
    renderer.draw_sparkline(draw, (128, 102, 227, 113), cpu_history, COLOR_CYAN, fill=True)

    # Resource bars section
    y_section = 125
    renderer.draw_text(
        draw, "RESOURCES", (16, y_section), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    resources = [
        ("MEM", 68, COLOR_PURPLE, "5.4/8 GB"),
        ("DISK", 45, COLOR_ORANGE, "180/400 GB"),
        ("SWAP", 12, COLOR_BLUE, "0.5/4 GB"),
    ]

    for i, (name, percent, color, _detail) in enumerate(resources):
        y = y_section + 18 + i * 24
        renderer.draw_text(
            draw, name, (16, y + 5), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_rounded_rect(draw, (50, y, 180, y + 10), radius=2, fill=COLOR_DARK_GRAY)
        bar_width = int(130 * percent / 100)
        renderer.draw_rounded_rect(draw, (50, y, 50 + bar_width, y + 10), radius=2, fill=color)
        renderer.draw_text(
            draw, f"{percent}%", (188, y + 5), font=renderer.font_tiny, color=color, anchor="lm"
        )

    # Network I/O
    y_net = 210
    renderer.draw_text(
        draw, "▲", (16, y_net), font=renderer.font_tiny, color=COLOR_GREEN, anchor="lm"
    )
    renderer.draw_text(
        draw, "125 MB/s", (28, y_net), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )
    renderer.draw_text(
        draw, "▼", (100, y_net), font=renderer.font_tiny, color=COLOR_RED, anchor="lm"
    )
    renderer.draw_text(
        draw, "48 MB/s", (112, y_net), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )

    # Connections
    renderer.draw_text(
        draw, "CONN: 1,247", (180, y_net), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    save_image(renderer, img, "04_server_stats", output_dir)


def generate_media_player(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a media player display."""
    img, draw = renderer.create_canvas()

    # Album art placeholder (gradient square)
    for i in range(80):
        grad_color = renderer.blend_color(COLOR_PURPLE, COLOR_CYAN, i / 80)
        renderer.draw_line(draw, [(80 + i, 20), (80 + i, 100)], fill=grad_color)

    # Track info
    renderer.draw_text(
        draw, "NOW PLAYING", (120, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )
    renderer.draw_text(
        draw, "Bohemian", (120, 135), font=renderer.font_medium, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "Rhapsody", (120, 152), font=renderer.font_medium, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "Queen", (120, 172), font=renderer.font_small, color=COLOR_CYAN, anchor="mm"
    )

    # Progress bar
    progress = 65
    renderer.draw_rounded_rect(draw, (20, 192, 220, 198), radius=3, fill=COLOR_DARK_GRAY)
    bar_width = int(200 * progress / 100)
    renderer.draw_rounded_rect(draw, (20, 192, 20 + bar_width, 198), radius=3, fill=COLOR_CYAN)

    # Time labels
    renderer.draw_text(
        draw, "2:45", (20, 208), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )
    renderer.draw_text(
        draw, "5:54", (220, 208), font=renderer.font_tiny, color=COLOR_GRAY, anchor="rm"
    )

    # Controls
    controls_y = 225
    renderer.draw_text(
        draw, "⏮", (70, controls_y), font=renderer.font_regular, color=COLOR_GRAY, anchor="mm"
    )
    renderer.draw_text(
        draw, "⏸", (120, controls_y), font=renderer.font_large, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "⏭", (170, controls_y), font=renderer.font_regular, color=COLOR_GRAY, anchor="mm"
    )

    save_image(renderer, img, "05_media_player", output_dir)


def generate_energy_monitor(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate an energy monitoring dashboard."""
    img, draw = renderer.create_canvas()

    # Header
    renderer.draw_icon(draw, "bolt", (10, 8), size=16, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "ENERGY", (32, 16), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
    )

    # Main power display
    renderer.draw_panel(draw, (8, 32, 232, 95), COLOR_PANEL, radius=4)

    # Current power with large display
    renderer.draw_text(
        draw, "2.4", (70, 55), font=renderer.font_huge, color=COLOR_GREEN, anchor="mm"
    )
    renderer.draw_text(
        draw, "kW", (70, 82), font=renderer.font_small, color=COLOR_GRAY, anchor="mm"
    )

    # Solar generation
    renderer.draw_icon(draw, "sun", (130, 40), size=14, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "SOLAR", (150, 47), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "3.8 kW", (150, 62), font=renderer.font_medium, color=COLOR_YELLOW, anchor="lm"
    )

    # Grid
    renderer.draw_text(
        draw, "GRID", (150, 78), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "-1.4 kW", (150, 88), font=renderer.font_small, color=COLOR_GREEN, anchor="lm"
    )

    # Today's usage section
    renderer.draw_text(
        draw, "TODAY", (16, 108), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    usage_data = [1.2, 0.8, 0.5, 0.4, 0.6, 1.5, 2.8, 3.2, 2.4, 2.0, 1.8, 2.4]
    renderer.draw_panel(draw, (8, 118, 232, 165), COLOR_PANEL, radius=4)
    renderer.draw_sparkline(draw, (16, 125, 224, 158), usage_data, COLOR_CYAN, fill=True)

    # Stats row
    stats = [
        ("USED", "18.4 kWh", COLOR_ORANGE),
        ("SOLAR", "24.2 kWh", COLOR_YELLOW),
        ("EXPORT", "8.1 kWh", COLOR_GREEN),
    ]

    for i, (label, value, color) in enumerate(stats):
        x = 16 + i * 75
        y = 175
        renderer.draw_text(
            draw, label, (x, y), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_text(
            draw, value, (x, y + 14), font=renderer.font_small, color=color, anchor="lm"
        )

    # Cost
    renderer.draw_panel(draw, (8, 205, 232, 232), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "TODAY COST", (16, 215), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "$2.45", (100, 218), font=renderer.font_medium, color=COLOR_WHITE, anchor="lm"
    )
    renderer.draw_text(
        draw, "SAVED", (155, 215), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "$4.80", (190, 218), font=renderer.font_medium, color=COLOR_GREEN, anchor="lm"
    )

    save_image(renderer, img, "06_energy_monitor", output_dir)


def generate_fitness(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a fitness tracking dashboard."""
    img, draw = renderer.create_canvas()

    # Activity rings (stacked)
    center = (70, 80)

    # Move ring (outer)
    renderer.draw_ring_gauge(
        draw, center, 50, 85, COLOR_RED, renderer.dim_color(COLOR_RED), width=8
    )
    # Exercise ring (middle)
    renderer.draw_ring_gauge(
        draw, center, 38, 60, COLOR_GREEN, renderer.dim_color(COLOR_GREEN), width=8
    )
    # Stand ring (inner)
    renderer.draw_ring_gauge(
        draw, center, 26, 100, COLOR_CYAN, renderer.dim_color(COLOR_CYAN), width=8
    )

    # Center icon
    renderer.draw_text(draw, "♥", center, font=renderer.font_large, color=COLOR_RED, anchor="mm")

    # Ring labels
    labels = [
        ("MOVE", "680/800 CAL", COLOR_RED),
        ("EXERCISE", "24/40 MIN", COLOR_GREEN),
        ("STAND", "12/12 HR", COLOR_CYAN),
    ]

    for i, (label, value, color) in enumerate(labels):
        y = 25 + i * 36
        renderer.draw_text(draw, label, (140, y), font=renderer.font_tiny, color=color, anchor="lm")
        renderer.draw_text(
            draw, value, (140, y + 12), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
        )

    # Stats section
    y_stats = 145
    renderer.draw_panel(draw, (8, y_stats, 232, 232), COLOR_PANEL, radius=4)

    stats = [
        ("STEPS", "8,542", "🚶"),
        ("DIST", "5.2 km", "📍"),
        ("FLOORS", "14", "🏢"),
        ("HR", "72 bpm", "♥"),
    ]

    for i, (label, value, icon) in enumerate(stats):
        x = 16 + (i % 2) * 110
        y = y_stats + 12 + (i // 2) * 38
        renderer.draw_text(
            draw, icon, (x, y + 8), font=renderer.font_regular, color=COLOR_WHITE, anchor="lm"
        )
        renderer.draw_text(
            draw, label, (x + 25, y), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_text(
            draw, value, (x + 25, y + 14), font=renderer.font_medium, color=COLOR_WHITE, anchor="lm"
        )

    save_image(renderer, img, "07_fitness", output_dir)


def generate_clock_dashboard(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate an advanced clock dashboard."""
    img, draw = renderer.create_canvas()

    # Large time display
    renderer.draw_text(
        draw, "14:32", (120, 60), font=renderer.font_huge, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, ":48", (185, 55), font=renderer.font_medium, color=COLOR_GRAY, anchor="lm"
    )

    # Date
    renderer.draw_text(
        draw,
        "Saturday, December 14",
        (120, 95),
        font=renderer.font_small,
        color=COLOR_GRAY,
        anchor="mm",
    )

    # Weather inline
    renderer.draw_icon(draw, "sun", (70, 115), size=16, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "24°C  Sunny", (92, 123), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
    )

    # Calendar events panel
    renderer.draw_panel(draw, (8, 145, 232, 232), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "UPCOMING", (16, 157), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    events = [
        ("15:00", "Team Meeting", COLOR_CYAN),
        ("17:30", "Gym Session", COLOR_GREEN),
        ("19:00", "Dinner with Alex", COLOR_ORANGE),
    ]

    for i, (time, event, color) in enumerate(events):
        y = 172 + i * 20
        renderer.draw_rectangle(draw, (16, y, 20, y + 14), fill=color)
        renderer.draw_text(
            draw, time, (28, y + 7), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_text(
            draw, event, (70, y + 7), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
        )

    save_image(renderer, img, "08_clock_dashboard", output_dir)


def generate_network_monitor(renderer: HighQualityRenderer, output_dir: Path) -> None:
    """Generate a network monitoring dashboard."""
    img, draw = renderer.create_canvas()

    # Header
    renderer.draw_icon(draw, "network", (10, 8), size=16, color=COLOR_GREEN)
    renderer.draw_text(
        draw, "NETWORK", (32, 16), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
    )

    # Status indicator
    renderer.draw_ellipse(draw, (200, 10, 210, 20), fill=COLOR_GREEN)
    renderer.draw_text(
        draw, "OK", (215, 15), font=renderer.font_tiny, color=COLOR_GREEN, anchor="lm"
    )

    # Speed test results
    renderer.draw_panel(draw, (8, 32, 116, 100), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "DOWNLOAD", (62, 45), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )
    renderer.draw_text(
        draw, "245", (62, 70), font=renderer.font_xlarge, color=COLOR_CYAN, anchor="mm"
    )
    renderer.draw_text(
        draw, "Mbps", (62, 90), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    renderer.draw_panel(draw, (124, 32, 232, 100), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "UPLOAD", (178, 45), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )
    renderer.draw_text(
        draw, "48", (178, 70), font=renderer.font_xlarge, color=COLOR_PURPLE, anchor="mm"
    )
    renderer.draw_text(
        draw, "Mbps", (178, 90), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Traffic graph
    renderer.draw_text(
        draw, "TRAFFIC (24H)", (16, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    traffic = [
        45,
        52,
        38,
        65,
        72,
        55,
        48,
        82,
        90,
        75,
        68,
        55,
        42,
        38,
        45,
        52,
        65,
        78,
        85,
        72,
        58,
        45,
        38,
        42,
    ]
    renderer.draw_panel(draw, (8, 125, 232, 175), COLOR_PANEL, radius=4)
    renderer.draw_sparkline(draw, (16, 132, 224, 168), traffic, COLOR_CYAN, fill=True)

    # Connected devices
    renderer.draw_text(
        draw, "DEVICES", (16, 185), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    devices = [
        ("iPhone", "192.168.1.42", COLOR_GREEN),
        ("MacBook", "192.168.1.15", COLOR_GREEN),
        ("Smart TV", "192.168.1.80", COLOR_YELLOW),
    ]

    for i, (name, ip, color) in enumerate(devices):
        y = 198 + i * 12
        renderer.draw_ellipse(draw, (16, y, 20, y + 4), fill=color)
        renderer.draw_text(
            draw, name, (28, y + 2), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
        )
        renderer.draw_text(
            draw, ip, (140, y + 2), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )

    save_image(renderer, img, "09_network_monitor", output_dir)


def main() -> None:
    """Generate all sample renders."""
    output_dir = Path(__file__).parent.parent / "samples"
    output_dir.mkdir(exist_ok=True)

    # Remove old samples
    for old_file in output_dir.glob("*.png"):
        old_file.unlink()

    print("Generating advanced sample renders (2x supersampled)...")
    print(f"Output directory: {output_dir}\n")

    renderer = HighQualityRenderer(scale=2)

    # Generate all samples
    generate_system_monitor(renderer, output_dir)
    generate_smart_home(renderer, output_dir)
    generate_weather(renderer, output_dir)
    generate_server_stats(renderer, output_dir)
    generate_media_player(renderer, output_dir)
    generate_energy_monitor(renderer, output_dir)
    generate_fitness(renderer, output_dir)
    generate_clock_dashboard(renderer, output_dir)
    generate_network_monitor(renderer, output_dir)

    print(f"\n✓ Generated 9 advanced sample images in {output_dir}/")


if __name__ == "__main__":
    main()
