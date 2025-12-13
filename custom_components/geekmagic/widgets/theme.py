"""Theme system for GeekMagic display.

Themes go beyond colors to affect typography, spacing, shapes, borders,
and visual effects for a distinctive look per screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Type aliases
Color = tuple[int, int, int]
BorderStyle = Literal["none", "solid", "outline"]
FontWeight = Literal["light", "regular"]


@dataclass(frozen=True)
class Theme:
    """Theme configuration affecting all visual aspects.

    Attributes:
        name: Unique theme identifier
        corner_radius: Corner rounding (0=sharp, 8=rounded, 16=very rounded)
        border_width: Border thickness (0=none, 1=thin, 2-3=thick)
        border_style: How borders are drawn (none, solid, outline-only)
        layout_padding: Padding around entire layout in pixels
        widget_padding: Padding inside widgets as percentage of width (e.g., 6 = 6%)
        gap: Gap between elements in pixels
        background: Screen/canvas background color
        panel_fill: Widget background fill color
        panel_border: Widget border color
        text_primary: Primary text color (values, main content)
        text_secondary: Secondary text color (labels, muted content)
        accent_colors: List of accent colors to cycle through for widgets
        value_bold: Whether primary values use bold font
        label_weight: Font weight for labels
        glow_effect: Enable glow effect around panels (Neon theme)
        scanlines: Enable retro scanline overlay (Retro theme)
        invert_bars: Use outline-only bars/gauges (Retro theme)
    """

    name: str

    # Shape styling
    corner_radius: int = 8
    border_width: int = 0
    border_style: BorderStyle = "none"

    # Spacing
    layout_padding: int = 8
    widget_padding: int = 6  # Percentage of width
    gap: int = 6

    # Colors
    background: Color = (0, 0, 0)
    panel_fill: Color = (18, 18, 18)
    panel_border: Color = (60, 60, 60)
    text_primary: Color = (255, 255, 255)
    text_secondary: Color = (150, 150, 150)
    accent_colors: tuple[Color, ...] = field(
        default_factory=lambda: (
            (27, 158, 119),  # Cyan/Teal
            (217, 95, 2),  # Orange
            (117, 112, 179),  # Lavender
            (231, 41, 138),  # Magenta
            (102, 166, 30),  # Lime
            (230, 171, 2),  # Gold
        )
    )

    # Typography
    value_bold: bool = True
    label_weight: FontWeight = "regular"

    # Visual effects
    glow_effect: bool = False
    scanlines: bool = False
    invert_bars: bool = False

    def get_accent_color(self, index: int) -> Color:
        """Get accent color for a slot index, cycling through available colors.

        Args:
            index: Slot or widget index

        Returns:
            RGB color tuple
        """
        return self.accent_colors[index % len(self.accent_colors)]


# =============================================================================
# Pre-defined Themes
# =============================================================================

THEME_CLASSIC = Theme(
    name="classic",
    corner_radius=8,
    border_width=0,
    border_style="none",
    layout_padding=8,
    widget_padding=6,
    gap=6,
    background=(0, 0, 0),
    panel_fill=(18, 18, 18),
    panel_border=(60, 60, 60),
    text_primary=(255, 255, 255),
    text_secondary=(150, 150, 150),
    accent_colors=(
        (27, 158, 119),  # Cyan/Teal
        (217, 95, 2),  # Orange
        (117, 112, 179),  # Lavender
        (231, 41, 138),  # Magenta
        (102, 166, 30),  # Lime
        (230, 171, 2),  # Gold
    ),
    value_bold=True,
    label_weight="regular",
    glow_effect=False,
    scanlines=False,
    invert_bars=False,
)

THEME_MINIMAL = Theme(
    name="minimal",
    corner_radius=0,
    border_width=1,
    border_style="solid",
    layout_padding=4,
    widget_padding=4,
    gap=4,
    background=(0, 0, 0),
    panel_fill=(0, 0, 0),  # No fill - just borders
    panel_border=(80, 80, 80),
    text_primary=(255, 255, 255),
    text_secondary=(120, 120, 120),
    accent_colors=(
        (100, 200, 255),  # Single cool blue accent
    ),
    value_bold=False,
    label_weight="light",
    glow_effect=False,
    scanlines=False,
    invert_bars=False,
)

THEME_NEON = Theme(
    name="neon",
    corner_radius=4,
    border_width=3,
    border_style="solid",
    layout_padding=8,
    widget_padding=6,
    gap=6,
    background=(0, 0, 0),
    panel_fill=(10, 10, 15),
    panel_border=(0, 255, 255),  # Neon cyan
    text_primary=(255, 255, 255),
    text_secondary=(200, 200, 200),  # Brighter than usual
    accent_colors=(
        (0, 255, 255),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 128),  # Neon green
        (255, 100, 200),  # Pink
        (100, 200, 255),  # Light blue
    ),
    value_bold=True,
    label_weight="regular",
    glow_effect=True,
    scanlines=False,
    invert_bars=False,
)

THEME_RETRO = Theme(
    name="retro",
    corner_radius=0,
    border_width=1,
    border_style="outline",
    layout_padding=10,
    widget_padding=8,
    gap=8,
    background=(0, 5, 0),  # Slight green tint
    panel_fill=(0, 0, 0),  # No fill - outline only
    panel_border=(0, 180, 0),  # Terminal green
    text_primary=(0, 255, 0),  # Bright green
    text_secondary=(0, 150, 0),  # Dim green
    accent_colors=(
        (0, 255, 0),  # Green
        (255, 180, 0),  # Amber
    ),
    value_bold=False,
    label_weight="regular",
    glow_effect=False,
    scanlines=True,
    invert_bars=True,
)

THEME_SOFT = Theme(
    name="soft",
    corner_radius=16,
    border_width=1,
    border_style="solid",
    layout_padding=12,
    widget_padding=8,
    gap=10,
    background=(15, 15, 20),
    panel_fill=(30, 30, 40),
    panel_border=(50, 50, 65),
    text_primary=(240, 240, 245),
    text_secondary=(140, 140, 155),
    accent_colors=(
        (120, 180, 220),  # Soft blue
        (180, 140, 200),  # Soft purple
        (140, 200, 160),  # Soft green
        (220, 180, 140),  # Soft orange
        (200, 150, 180),  # Soft pink
    ),
    value_bold=False,
    label_weight="regular",
    glow_effect=False,
    scanlines=False,
    invert_bars=False,
)


# =============================================================================
# Theme Registry
# =============================================================================

THEMES: dict[str, Theme] = {
    "classic": THEME_CLASSIC,
    "minimal": THEME_MINIMAL,
    "neon": THEME_NEON,
    "retro": THEME_RETRO,
    "soft": THEME_SOFT,
}

DEFAULT_THEME = THEME_CLASSIC


def get_theme(name: str) -> Theme:
    """Get a theme by name.

    Args:
        name: Theme name (classic, minimal, neon, retro, soft)

    Returns:
        Theme instance, defaults to classic if name not found
    """
    return THEMES.get(name, DEFAULT_THEME)


__all__ = [
    "DEFAULT_THEME",
    "THEMES",
    "THEME_CLASSIC",
    "THEME_MINIMAL",
    "THEME_NEON",
    "THEME_RETRO",
    "THEME_SOFT",
    "BorderStyle",
    "Color",
    "FontWeight",
    "Theme",
    "get_theme",
]
