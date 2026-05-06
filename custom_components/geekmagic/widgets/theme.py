"""Theme system for GeekMagic display.

Themes provide a complete design system affecting colors, typography,
spacing, shapes, borders, and visual effects.

The default theme (`watchos`) is inspired by Apple's watchOS Human Interface
Guidelines: true-black backgrounds, system-color tints, opacity-based text
hierarchy, and tinted (not gray) gauge tracks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Type aliases
Color = tuple[int, int, int]
BorderStyle = Literal["none", "solid", "outline", "double"]
FontWeight = Literal["light", "regular"]


# =============================================================================
# watchOS-inspired system color palette
# =============================================================================
# Sourced from Apple's system color set used across watchOS / iOS dark mode.
# Each tint pairs with a meaningful semantic role; widgets should pick a tint
# based on what the data *means*, not just to add color.

SYSTEM_RED = (255, 69, 58)
SYSTEM_ORANGE = (255, 159, 10)
SYSTEM_YELLOW = (255, 214, 10)
SYSTEM_GREEN = (50, 215, 75)
SYSTEM_MINT = (102, 212, 207)
SYSTEM_TEAL = (90, 200, 245)
SYSTEM_CYAN = (100, 210, 255)
SYSTEM_BLUE = (10, 132, 255)
SYSTEM_INDIGO = (94, 92, 230)
SYSTEM_PURPLE = (191, 90, 242)
SYSTEM_PINK = (255, 55, 95)


@dataclass(frozen=True)
class Theme:
    """Theme configuration affecting all visual aspects.

    Design System Colors:
        primary: Main accent color for key elements, values, highlights
        secondary: Supporting accent for less prominent elements
        success: Positive states (on, connected, complete)
        warning: Caution states (low battery, pending)
        error: Negative states (off, disconnected, failed)
        muted: Subtle elements, disabled states

    Surface Colors:
        background: Screen/canvas background
        surface: Widget/panel background — only painted when surface_chrome=True
        surface_variant: Alternate surface (cards, elevated elements)
        border: Border/divider color

    Text Colors (opacity hierarchy):
        text_primary: Hero values and key content (~100% white)
        text_secondary: Supporting info, labels (~60% white)
        text_tertiary: Captions, hints (~40% white)
        text_on_primary: Text rendered on top of a primary-colored fill
    """

    name: str

    # Design system colors
    primary: Color = SYSTEM_TEAL
    secondary: Color = SYSTEM_INDIGO
    success: Color = SYSTEM_GREEN
    warning: Color = SYSTEM_ORANGE
    error: Color = SYSTEM_RED
    info: Color = SYSTEM_BLUE  # Cool / cold / data / water / rain
    muted: Color = (100, 100, 100)

    # Surface colors
    background: Color = (0, 0, 0)
    surface: Color = (14, 14, 14)
    surface_variant: Color = (24, 24, 24)
    border: Color = (38, 38, 38)

    # Text colors
    text_primary: Color = (235, 235, 235)
    text_secondary: Color = (150, 150, 150)
    text_tertiary: Color = (105, 105, 105)
    text_on_primary: Color = (0, 0, 0)

    # Accent color palette for widgets (cycles through for variety).
    # Default = watchOS system colors in a pleasant rotation.
    accent_colors: tuple[Color, ...] = field(
        default_factory=lambda: (
            SYSTEM_TEAL,
            SYSTEM_ORANGE,
            SYSTEM_GREEN,
            SYSTEM_PURPLE,
            SYSTEM_PINK,
            SYSTEM_YELLOW,
        )
    )

    # Shape styling
    corner_radius: int = 10
    border_width: int = 0
    border_style: BorderStyle = "none"

    # Spacing
    layout_padding: int = 6
    widget_padding: int = 5  # Percentage of width
    gap: int = 6

    # Typography
    value_bold: bool = True
    label_weight: FontWeight = "regular"
    # Whether the theme prefers the rounded font family (Nunito).
    # When False, the renderer falls back to DejaVu Sans.
    rounded_font: bool = True

    # Visual effects
    glow_effect: bool = False
    scanlines: bool = False
    invert_bars: bool = False

    # Whether widgets render with a card/panel chrome behind them.
    # watchOS-style themes set this to False so widgets float on the
    # background (deference principle).
    surface_chrome: bool = False

    # Track styling for bars/rings/arcs.
    # When `tint_track`, the track is the accent color blended toward black
    # at `tint_track_opacity`. When False, `bar_background` is used.
    tint_track: bool = True
    tint_track_opacity: float = 0.18  # 18% — soft tinted track

    # Fallback bar/ring track color when tint_track is False
    bar_background: Color = (38, 38, 38)

    def get_accent_color(self, index: int) -> Color:
        """Get accent color for a slot index, cycling through available colors."""
        return self.accent_colors[index % len(self.accent_colors)]

    def track_color(self, tint: Color) -> Color:
        """Compute the track color for a tinted bar/ring/arc.

        When `tint_track` is True, returns the tint blended toward black
        at `tint_track_opacity`. Otherwise returns `bar_background`.
        """
        if not self.tint_track:
            return self.bar_background
        op = self.tint_track_opacity
        return (
            int(tint[0] * op),
            int(tint[1] * op),
            int(tint[2] * op),
        )


# =============================================================================
# Pre-defined Themes
# =============================================================================

# 0. watchOS — true-black, system colors, no chrome (new default)
THEME_WATCHOS = Theme(
    name="watchos",
    primary=SYSTEM_TEAL,
    secondary=SYSTEM_INDIGO,
    success=SYSTEM_GREEN,
    warning=SYSTEM_ORANGE,
    error=SYSTEM_RED,
    info=SYSTEM_BLUE,
    muted=(105, 105, 105),
    background=(0, 0, 0),
    surface=(0, 0, 0),  # No card chrome — widgets float on true black
    surface_variant=(20, 20, 20),
    border=(40, 40, 40),
    text_primary=(235, 235, 235),
    text_secondary=(150, 150, 150),
    text_tertiary=(105, 105, 105),
    text_on_primary=(0, 0, 0),
    accent_colors=(
        SYSTEM_TEAL,
        SYSTEM_ORANGE,
        SYSTEM_GREEN,
        SYSTEM_PURPLE,
        SYSTEM_PINK,
        SYSTEM_YELLOW,
    ),
    corner_radius=12,
    border_width=0,
    border_style="none",
    layout_padding=6,
    widget_padding=5,
    gap=6,
    rounded_font=True,
    surface_chrome=False,
    tint_track=True,
    tint_track_opacity=0.20,
)

# 1. Classic — like watchOS but with a subtle card chrome for users who
#    prefer separation between widgets.
THEME_CLASSIC = Theme(
    name="classic",
    primary=SYSTEM_TEAL,
    secondary=SYSTEM_INDIGO,
    success=SYSTEM_GREEN,
    warning=SYSTEM_ORANGE,
    error=SYSTEM_RED,
    info=SYSTEM_BLUE,
    muted=(105, 105, 105),
    background=(0, 0, 0),
    surface=(14, 14, 14),
    surface_variant=(24, 24, 24),
    border=(45, 45, 45),
    text_primary=(235, 235, 235),
    text_secondary=(150, 150, 150),
    text_tertiary=(105, 105, 105),
    text_on_primary=(0, 0, 0),
    accent_colors=(
        SYSTEM_TEAL,
        SYSTEM_ORANGE,
        SYSTEM_PURPLE,
        SYSTEM_PINK,
        SYSTEM_GREEN,
        SYSTEM_YELLOW,
    ),
    corner_radius=10,
    border_width=0,
    border_style="none",
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.18,
)

# 2. Minimal — sharp, mono, ice blue
THEME_MINIMAL = Theme(
    name="minimal",
    primary=(140, 210, 255),
    secondary=(180, 180, 180),
    success=(140, 210, 255),
    warning=(255, 200, 100),
    error=(255, 100, 100),
    info=(140, 210, 255),
    muted=(70, 70, 70),
    background=(0, 0, 0),
    surface=(0, 0, 0),
    surface_variant=(15, 15, 15),
    border=(80, 80, 80),
    text_primary=(235, 235, 235),
    text_secondary=(140, 140, 140),
    text_tertiary=(90, 90, 90),
    text_on_primary=(0, 0, 0),
    accent_colors=((140, 210, 255),),
    corner_radius=0,
    border_width=1,
    border_style="solid",
    layout_padding=4,
    widget_padding=4,
    gap=4,
    value_bold=False,
    label_weight="light",
    rounded_font=False,
    surface_chrome=False,
    tint_track=False,
    bar_background=(30, 30, 30),
)

# 3. Neon — cyberpunk
THEME_NEON = Theme(
    name="neon",
    primary=(0, 255, 255),
    secondary=(255, 0, 255),
    success=(0, 255, 128),
    warning=(255, 255, 0),
    error=(255, 50, 50),
    info=(0, 255, 255),
    muted=(80, 80, 100),
    background=(5, 5, 15),
    surface=(10, 10, 20),
    surface_variant=(15, 15, 30),
    border=(0, 200, 200),
    text_primary=(235, 235, 245),
    text_secondary=(200, 200, 220),
    text_tertiary=(120, 120, 160),
    text_on_primary=(0, 0, 0),
    accent_colors=(
        (0, 255, 255),
        (255, 0, 255),
        (0, 255, 128),
        (255, 100, 200),
        (100, 200, 255),
        (255, 255, 0),
    ),
    corner_radius=4,
    border_width=2,
    border_style="solid",
    # Neon ships card chrome with a 2-px outline, so default layout
    # padding (6) is fine; pull widget_padding lower so rings/arcs
    # have more cell space to breathe inside the chrome.
    layout_padding=6,
    widget_padding=3,
    gap=6,
    rounded_font=True,
    glow_effect=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.22,
)

# 4. Retro — terminal/CRT
THEME_RETRO = Theme(
    name="retro",
    primary=(0, 255, 0),
    secondary=(255, 180, 0),
    success=(0, 255, 0),
    warning=(255, 180, 0),
    error=(255, 50, 0),
    info=(0, 220, 140),
    muted=(0, 100, 0),
    background=(0, 8, 0),
    surface=(0, 0, 0),
    surface_variant=(0, 15, 0),
    border=(0, 180, 0),
    text_primary=(0, 255, 0),
    text_secondary=(0, 180, 0),
    text_tertiary=(0, 110, 0),
    text_on_primary=(0, 0, 0),
    accent_colors=((0, 255, 0), (255, 180, 0)),
    corner_radius=0,
    border_width=1,
    border_style="outline",
    layout_padding=8,
    widget_padding=8,
    gap=8,
    rounded_font=False,
    scanlines=True,
    invert_bars=True,
    surface_chrome=False,
    tint_track=True,
    tint_track_opacity=0.18,
    bar_background=(0, 40, 0),
)

# 5. Soft — muted, cozy
THEME_SOFT = Theme(
    name="soft",
    primary=(120, 180, 220),
    secondary=(180, 140, 200),
    success=(140, 200, 160),
    warning=(220, 180, 140),
    error=(220, 140, 140),
    info=(120, 180, 220),
    muted=(100, 100, 115),
    background=(15, 15, 20),
    surface=(30, 30, 40),
    surface_variant=(40, 40, 55),
    border=(50, 50, 65),
    text_primary=(240, 240, 245),
    text_secondary=(155, 155, 170),
    text_tertiary=(110, 110, 125),
    text_on_primary=(20, 20, 30),
    accent_colors=(
        (120, 180, 220),
        (180, 140, 200),
        (140, 200, 160),
        (220, 180, 140),
        (200, 150, 180),
        (180, 200, 140),
    ),
    corner_radius=14,
    border_width=0,
    border_style="none",
    layout_padding=8,
    widget_padding=8,
    gap=8,
    value_bold=False,
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.22,
)

# 6. Light — clean light theme
THEME_LIGHT = Theme(
    name="light",
    primary=(0, 122, 204),
    secondary=(102, 45, 145),
    success=(40, 167, 69),
    warning=(255, 140, 0),
    error=(220, 53, 69),
    info=(0, 122, 204),
    muted=(190, 190, 195),
    background=(255, 255, 255),
    surface=(255, 255, 255),
    surface_variant=(248, 248, 250),
    border=(230, 230, 235),
    text_primary=(28, 28, 32),
    text_secondary=(110, 110, 118),
    text_tertiary=(165, 165, 172),
    text_on_primary=(255, 255, 255),
    accent_colors=(
        (0, 122, 204),
        (255, 140, 0),
        (40, 167, 69),
        (102, 45, 145),
        (220, 53, 69),
        (23, 162, 184),
    ),
    corner_radius=12,
    border_width=0,
    border_style="none",
    layout_padding=6,
    widget_padding=6,
    gap=6,
    rounded_font=True,
    surface_chrome=False,
    tint_track=True,
    tint_track_opacity=0.16,
    bar_background=(232, 232, 238),
)

# 7. Ocean — deep blue
THEME_OCEAN = Theme(
    name="ocean",
    primary=(0, 200, 240),
    secondary=(72, 202, 228),
    success=(0, 220, 170),
    warning=(255, 200, 87),
    error=(255, 107, 107),
    info=(0, 200, 240),
    muted=(80, 110, 130),
    background=(3, 28, 50),
    surface=(8, 42, 70),
    surface_variant=(12, 52, 85),
    border=(30, 80, 115),
    text_primary=(240, 248, 255),
    text_secondary=(155, 195, 215),
    text_tertiary=(95, 135, 165),
    text_on_primary=(0, 30, 50),
    accent_colors=(
        (0, 200, 240),
        (72, 202, 228),
        (144, 224, 239),
        (0, 220, 170),
        (255, 200, 87),
        (120, 170, 220),
    ),
    corner_radius=10,
    border_width=0,
    border_style="none",
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.22,
)

# 8. Sunset — warm
THEME_SUNSET = Theme(
    name="sunset",
    primary=(255, 107, 107),
    secondary=(255, 159, 67),
    success=(106, 196, 96),
    warning=(255, 200, 87),
    error=(255, 71, 87),
    info=(220, 190, 130),
    muted=(140, 105, 105),
    background=(28, 18, 22),
    surface=(42, 28, 33),
    surface_variant=(54, 36, 42),
    border=(80, 55, 60),
    text_primary=(255, 245, 238),
    text_secondary=(195, 160, 160),
    text_tertiary=(135, 105, 105),
    text_on_primary=(40, 20, 25),
    accent_colors=(
        (255, 107, 107),
        (255, 159, 67),
        (255, 200, 87),
        (255, 140, 140),
        (200, 120, 180),
        (255, 180, 120),
    ),
    corner_radius=14,
    border_width=0,
    border_style="none",
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.22,
)

# 9. Forest — natural
THEME_FOREST = Theme(
    name="forest",
    primary=(116, 205, 130),
    secondary=(180, 220, 100),
    success=(116, 205, 130),
    warning=(220, 185, 70),
    error=(210, 95, 70),
    info=(110, 180, 145),
    muted=(95, 110, 90),
    background=(18, 28, 20),
    surface=(28, 42, 30),
    surface_variant=(36, 52, 38),
    border=(60, 80, 60),
    text_primary=(240, 245, 235),
    text_secondary=(170, 185, 165),
    text_tertiary=(110, 130, 110),
    text_on_primary=(20, 30, 20),
    accent_colors=(
        (116, 205, 130),
        (180, 220, 100),
        (220, 185, 70),
        (180, 145, 105),
        (110, 180, 145),
        (200, 215, 115),
    ),
    corner_radius=8,
    border_width=0,
    border_style="none",
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.20,
)

# 10. Candy — playful pastel (light variant)
THEME_CANDY = Theme(
    name="candy",
    primary=(255, 105, 180),
    secondary=(138, 207, 255),
    success=(120, 215, 130),
    warning=(255, 195, 90),
    error=(255, 110, 130),
    info=(138, 207, 255),
    muted=(200, 180, 200),
    background=(255, 240, 245),
    surface=(255, 250, 252),
    surface_variant=(255, 235, 242),
    border=(255, 200, 220),
    text_primary=(80, 60, 80),
    text_secondary=(150, 120, 150),
    text_tertiary=(195, 165, 195),
    text_on_primary=(255, 255, 255),
    accent_colors=(
        (255, 105, 180),
        (138, 207, 255),
        (255, 175, 105),
        (130, 215, 145),
        (255, 195, 90),
        (200, 130, 220),
    ),
    corner_radius=18,
    border_width=0,
    border_style="none",
    layout_padding=8,
    widget_padding=8,
    gap=8,
    rounded_font=True,
    surface_chrome=True,
    tint_track=True,
    tint_track_opacity=0.20,
    bar_background=(255, 220, 235),
)


# =============================================================================
# Theme Registry
# =============================================================================

THEMES: dict[str, Theme] = {
    "watchos": THEME_WATCHOS,
    "classic": THEME_CLASSIC,
    "minimal": THEME_MINIMAL,
    "neon": THEME_NEON,
    "retro": THEME_RETRO,
    "soft": THEME_SOFT,
    "light": THEME_LIGHT,
    "ocean": THEME_OCEAN,
    "sunset": THEME_SUNSET,
    "forest": THEME_FOREST,
    "candy": THEME_CANDY,
}

DEFAULT_THEME = THEME_WATCHOS


def get_theme(name: str) -> Theme:
    """Get a theme by name, defaulting to watchOS if not found."""
    return THEMES.get(name, DEFAULT_THEME)


__all__ = [
    "DEFAULT_THEME",
    "SYSTEM_BLUE",
    "SYSTEM_CYAN",
    "SYSTEM_GREEN",
    "SYSTEM_INDIGO",
    "SYSTEM_MINT",
    "SYSTEM_ORANGE",
    "SYSTEM_PINK",
    "SYSTEM_PURPLE",
    "SYSTEM_RED",
    "SYSTEM_TEAL",
    "SYSTEM_YELLOW",
    "THEMES",
    "THEME_CANDY",
    "THEME_CLASSIC",
    "THEME_FOREST",
    "THEME_LIGHT",
    "THEME_MINIMAL",
    "THEME_NEON",
    "THEME_OCEAN",
    "THEME_RETRO",
    "THEME_SOFT",
    "THEME_SUNSET",
    "THEME_WATCHOS",
    "BorderStyle",
    "Color",
    "FontWeight",
    "Theme",
    "get_theme",
]
