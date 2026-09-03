"""Theme system for GeekMagic display.

A theme is a complete design system, not a palette swap: it owns the
color roles, the text-opacity hierarchy, the per-cell chrome, the
fullscreen backdrop, and (rarely) an overlay pass.

Design rules every theme in this file follows:

* **Curated accents.** ``accent_colors`` is a small, harmonised rotation
  (2-5 hues at comparable chroma/lightness), never a grab-bag of
  default-web colors. Slots cycle it, so repetition reads intentional.
* **Derived text hierarchy.** Dark themes composite white over their own
  background at ~95% / ~62% / ~40% for primary / secondary / tertiary;
  light themes do the same with ink. That keeps the three steps evenly
  spaced whatever the backdrop is.
* **Restraint in chrome.** Hairlines over heavy borders, one consistent
  radius per theme, and — for elevated themes — a 1px inner top
  highlight (``inset 0 1px 0 rgba(255,255,255,0.06)``) plus a y-offset
  shadow. That reads as depth; glows read as decoration.
* **Backdrops are atmosphere.** Multi-stop gradients that place a light
  source, kept dark/desaturated enough that cell content stays the
  brightest thing on screen.
* **Overlays only where they are the identity.** Retro (scanlines +
  CRT vignette) and neon (glow band + vignette). Clean themes ship none.

The default theme (``watchos``) is modelled on Apple's watchOS Human
Interface Guidelines: true-black background, system-color tints,
opacity-based text hierarchy, tinted (not gray) gauge tracks, and no
card chrome at all.
"""

from __future__ import annotations

from dataclasses import dataclass
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
        text_primary: Hero values and key content (~95% white over bg)
        text_secondary: Supporting info, labels (~62% white over bg)
        text_tertiary: Captions, hints (~40% white over bg)
        text_on_primary: Text rendered on top of a primary-colored fill

    Light themes derive the same three steps from ink instead of white,
    so ``--chip-bg`` / ``--hairline`` / ``--track`` (built from
    ``text_primary`` in :func:`htmldoc.theme_css_variables`) stay correct
    on both polarities.
    """

    name: str

    # Design system colors
    primary: Color = SYSTEM_CYAN
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
    text_primary: Color = (240, 240, 242)
    text_secondary: Color = (158, 158, 161)
    text_tertiary: Color = (102, 102, 105)
    text_on_primary: Color = (0, 0, 0)

    # Accent color palette for widgets (cycles through for variety).
    # Default = the watchOS Activity rotation: cyan, pink, green, orange.
    accent_colors: tuple[Color, ...] = (
        SYSTEM_CYAN,
        SYSTEM_PINK,
        SYSTEM_GREEN,
        SYSTEM_ORANGE,
    )

    # Shape styling
    corner_radius: int = 10
    border_width: int = 0
    border_style: BorderStyle = "none"

    # Spacing. The panel is 27mm wide and read from arm's length or
    # further, so the outer margin is a hair — the screen is used edge to
    # edge — and the gap between widgets does the visual separation.
    layout_padding: int = 3
    widget_padding: int = 5  # Percentage of width
    gap: int = 8

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

    # ------------------------------------------------------------------
    # CSS-first styling (Blitz pipeline). Themes are full stylesheets,
    # not just palettes: distinct fonts, chrome, backdrops, and effects.
    # ------------------------------------------------------------------

    # font-family stack for all cell documents. Families resolve against
    # the embedded fonts: "Nunito", "DejaVu Sans", "Material Design Icons".
    font_stack: str = '"Nunito", "DejaVu Sans", sans-serif'

    # Per-cell chrome: styles applied inside every cell document.
    # ``.root`` fills the cell — paint cards/borders on it here.
    chrome_css: str = ""

    # Fullscreen backdrop document body CSS. Empty = solid var(--bg).
    backdrop_css: str = ""

    # Fullscreen overlay document body CSS + HTML, composited on top of
    # everything (scanlines, vignettes). Empty = no overlay pass.
    overlay_css: str = ""

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


# =============================================================================
# Pre-defined Themes
# =============================================================================

# 0. watchOS — true-black minimalism (default)
#
# Deference taken literally: no cards, no borders, no gradients. The only
# non-content pixels on screen are the ones the widget draws. Type does
# the hierarchy (95/62/40 white), Activity-style tinted tracks do the
# color, and the accent rotation is Apple's Move/Exercise/Stand trio plus
# orange — four hues, so a 3x3 grid repeats instead of turning into a
# rainbow.
THEME_WATCHOS = Theme(
    name="watchos",
    primary=SYSTEM_CYAN,
    secondary=SYSTEM_INDIGO,
    muted=(110, 110, 114),
    surface=(0, 0, 0),  # No card chrome — widgets float on true black
    surface_variant=(18, 18, 20),
    border=(38, 38, 41),
    text_primary=(240, 240, 242),
    text_secondary=(158, 158, 161),
    text_tertiary=(102, 102, 105),
    accent_colors=(
        SYSTEM_CYAN,
        SYSTEM_PINK,
        SYSTEM_GREEN,
        SYSTEM_ORANGE,
    ),
    corner_radius=12,
    layout_padding=2,
    gap=8,
    tint_track_opacity=0.20,
    chrome_css="",
    backdrop_css="body { background: #000; }",
)

# 0b. StandBy — iOS StandBy / Smart Stack widgets on black
#
# The watchOS system, plus one thing: every cell sits on a translucent
# white card (7% over true black, the tone iOS uses for dark widgets)
# with a large continuous radius. No border, no gradient, no shadow —
# the card is a grouping device, not decoration, so the type stays the
# brightest thing on screen. Widgets are a hair smaller than on watchOS
# (the card padding is real pixels) in exchange for structure that reads
# at a glance from across a room.
THEME_STANDBY = Theme(
    name="standby",
    primary=SYSTEM_CYAN,
    secondary=SYSTEM_INDIGO,
    muted=(110, 110, 114),
    surface=(18, 18, 18),
    surface_variant=(28, 28, 30),
    border=(44, 44, 46),
    text_primary=(240, 240, 242),
    text_secondary=(158, 158, 161),
    text_tertiary=(102, 102, 105),
    accent_colors=(
        SYSTEM_CYAN,
        SYSTEM_PINK,
        SYSTEM_GREEN,
        SYSTEM_ORANGE,
    ),
    corner_radius=18,
    layout_padding=4,
    gap=6,
    surface_chrome=True,
    tint_track_opacity=0.22,
    chrome_css="""
.root { border-radius: var(--radius); padding: 4px;
  background: rgba(255,255,255,0.07); }
""",
    backdrop_css="body { background: #000; }",
)

# 1. Classic — Linear-style dark, elevated cards
#
# Near-black neutral canvas, cards lifted by a 1px inner top highlight
# and a tight y-offset shadow (never a glow), hairline border at 6.5%.
# Palette is a modern product set (violet / cyan / emerald / amber /
# rose) at matched chroma so any two cells sit together comfortably.
THEME_CLASSIC = Theme(
    name="classic",
    primary=(139, 124, 246),
    secondary=(56, 189, 248),
    success=(52, 211, 153),
    warning=(251, 191, 36),
    error=(248, 113, 113),
    info=(56, 189, 248),
    muted=(113, 113, 122),
    background=(8, 9, 12),
    surface=(17, 18, 22),
    surface_variant=(24, 25, 30),
    border=(39, 40, 47),
    text_primary=(246, 247, 249),
    text_secondary=(159, 161, 168),
    text_tertiary=(106, 108, 116),
    accent_colors=(
        (139, 124, 246),
        (56, 189, 248),
        (52, 211, 153),
        (251, 191, 36),
        (251, 113, 133),
    ),
    corner_radius=10,
    layout_padding=7,
    gap=7,
    surface_chrome=True,
    tint_track_opacity=0.20,
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: linear-gradient(180deg, rgba(255,255,255,0.062), rgba(255,255,255,0.026));
  border: 1px solid rgba(255,255,255,0.075);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 3px rgba(0,0,0,0.55); }
.t-label { letter-spacing: 0.06em; }
""",
    backdrop_css="""
body { background: linear-gradient(180deg, #0f1015 0%, #08090c 62%, #050609 100%); }
""",
)

# 2. Minimal — strict Swiss, mono-accent
#
# One accent, one weight, one shape. DejaVu grotesque at regular weight,
# square corners, hairline rules instead of cards, and wide caps
# tracking. Gauge tracks stay neutral gray (tint_track off) so the single
# ice-blue accent is the only color on screen.
THEME_MINIMAL = Theme(
    name="minimal",
    primary=(138, 198, 255),
    secondary=(170, 170, 172),
    success=(138, 198, 255),
    warning=(240, 190, 110),
    error=(255, 110, 100),
    info=(138, 198, 255),
    muted=(86, 86, 88),
    background=(0, 0, 0),
    surface=(0, 0, 0),
    surface_variant=(14, 14, 14),
    border=(56, 56, 58),
    text_primary=(250, 250, 250),
    text_secondary=(156, 156, 157),
    text_tertiary=(100, 100, 101),
    accent_colors=((138, 198, 255),),
    corner_radius=0,
    border_width=1,
    border_style="solid",
    layout_padding=6,
    widget_padding=4,
    gap=6,
    value_bold=False,
    label_weight="light",
    rounded_font=False,
    tint_track=False,
    bar_background=(28, 28, 28),
    font_stack='"DejaVu Sans", sans-serif',
    chrome_css="""
.root { border-top: 1px solid rgba(255,255,255,0.26); padding: 5px 3px 3px; }
.t-hero, .t-value { font-weight: 400; letter-spacing: -0.005em; }
.t-unit { font-weight: 400; }
.t-label { font-weight: 400; letter-spacing: 0.12em; }
.chip { border-radius: 0; background: transparent; border: 1px solid var(--hairline); }
""",
    backdrop_css="body { background: #000; }",
)

# 3. Neon — tasteful cyberpunk, cyan + magenta only
#
# Two hues, full stop. Depth comes from layered box-shadows (hairline
# ring, soft outer bloom, inner haze, top highlight) rather than from
# thick saturated borders, and the backdrop places a violet light source
# above with a magenta bounce below. The overlay adds one faint cyan glow
# band at the top plus a vignette.
_NEON_CYAN = (45, 226, 255)
_NEON_MAGENTA = (255, 79, 216)
THEME_NEON = Theme(
    name="neon",
    primary=_NEON_CYAN,
    secondary=_NEON_MAGENTA,
    success=(54, 255, 190),
    warning=(255, 196, 64),
    error=(255, 64, 120),
    info=_NEON_CYAN,
    muted=(96, 104, 140),
    background=(7, 6, 20),
    surface=(12, 13, 32),
    surface_variant=(18, 20, 44),
    border=(45, 226, 255),
    text_primary=(233, 238, 252),
    text_secondary=(168, 176, 205),
    text_tertiary=(112, 120, 150),
    accent_colors=(_NEON_CYAN, _NEON_MAGENTA),
    corner_radius=6,
    border_width=2,
    border_style="solid",
    widget_padding=3,
    glow_effect=True,
    surface_chrome=True,
    tint_track_opacity=0.22,
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: linear-gradient(180deg, rgba(16,20,48,0.62), rgba(8,10,26,0.46));
  border: 1px solid rgba(45,226,255,0.32);
  box-shadow: 0 0 7px rgba(45,226,255,0.20),
              0 0 20px rgba(45,226,255,0.10),
              inset 0 0 18px rgba(45,226,255,0.06),
              inset 0 1px 0 rgba(190,240,255,0.12); }
.t-label { color: rgb(255,79,216); letter-spacing: 0.08em; }
.chip { background: rgba(45,226,255,0.10); }
""",
    backdrop_css="""
body { background:
  radial-gradient(120% 85% at 50% -25%, #2b1b60 0%, rgba(43,27,96,0) 62%),
  radial-gradient(95% 55% at 50% 118%, rgba(255,45,190,0.16) 0%, rgba(255,45,190,0) 70%),
  linear-gradient(180deg, #0a0820 0%, #05040f 72%); }
""",
    overlay_css="""
body { background:
  linear-gradient(180deg, rgba(45,226,255,0.055) 0%, rgba(45,226,255,0) 15%),
  radial-gradient(125% 95% at 50% 50%, rgba(0,0,0,0) 56%, rgba(6,0,26,0.42) 100%); }
""",
)

# 4. Retro — authentic phosphor CRT
#
# A single P1-green hue rendered as a ramp: bright phosphor for values,
# half-lit for support, dim for captions, and three green accents so
# neighbouring cells vary in tone without leaving the tube. Cells are
# bracketed by a thin green rule with an inner phosphor haze; the overlay
# carries the scanlines and a heavy corner vignette.
_CRT_BRIGHT = (126, 255, 150)
THEME_RETRO = Theme(
    name="retro",
    primary=_CRT_BRIGHT,
    secondary=(60, 230, 120),
    success=_CRT_BRIGHT,
    warning=(178, 255, 110),
    error=(255, 96, 64),
    info=(60, 230, 150),
    muted=(26, 110, 62),
    background=(3, 12, 6),
    surface=(4, 18, 9),
    surface_variant=(7, 28, 14),
    border=(40, 170, 82),
    text_primary=(126, 255, 150),
    text_secondary=(48, 198, 110),
    text_tertiary=(26, 124, 68),
    accent_colors=(_CRT_BRIGHT, (60, 230, 120), (178, 255, 110)),
    corner_radius=0,
    border_width=1,
    border_style="outline",
    layout_padding=8,
    widget_padding=8,
    gap=8,
    rounded_font=False,
    scanlines=True,
    invert_bars=True,
    tint_track_opacity=0.16,
    bar_background=(8, 42, 20),
    font_stack='"DejaVu Sans", monospace',
    chrome_css="""
.root { border: 1px solid rgba(126,255,150,0.28); padding: 5px;
  background: linear-gradient(180deg, rgba(12,48,24,0.40), rgba(4,20,10,0.26));
  box-shadow: inset 0 0 18px rgba(126,255,150,0.06); }
.t-label { text-transform: uppercase; letter-spacing: 0.12em; }
.chip { border-radius: 2px; background: rgba(126,255,150,0.10); }
""",
    backdrop_css="""
body { background:
  radial-gradient(115% 88% at 50% 44%, #0b2a15 0%, #04150a 56%, #010703 100%); }
""",
    overlay_css="""
body { background:
  repeating-linear-gradient(0deg,
    rgba(0,0,0,0.34) 0px, rgba(0,0,0,0.34) 1px,
    rgba(0,0,0,0) 1px, rgba(0,0,0,0) 3px),
  radial-gradient(125% 95% at 50% 50%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.50) 100%); }
""",
)

# 5. Soft — cozy low-contrast dusk
#
# Plum-ink canvas with a light source just off the top edge, dusty
# pastels at matched saturation, and pillowy cards that are barely
# brighter than the backdrop. Semibold type instead of extrabold keeps
# the whole screen quiet.
THEME_SOFT = Theme(
    name="soft",
    primary=(126, 176, 222),
    secondary=(172, 152, 226),
    success=(136, 200, 162),
    warning=(232, 168, 126),
    error=(224, 126, 138),
    info=(126, 176, 222),
    muted=(108, 105, 122),
    background=(20, 19, 28),
    surface=(31, 30, 42),
    surface_variant=(41, 39, 55),
    border=(56, 54, 72),
    text_primary=(238, 236, 246),
    text_secondary=(168, 163, 186),
    text_tertiary=(117, 112, 134),
    text_on_primary=(20, 19, 28),
    accent_colors=(
        (126, 176, 222),
        (172, 152, 226),
        (136, 200, 162),
        (232, 168, 126),
        (222, 146, 168),
    ),
    corner_radius=18,
    layout_padding=8,
    widget_padding=8,
    gap=8,
    value_bold=False,
    surface_chrome=True,
    tint_track_opacity=0.24,
    chrome_css="""
.root { border-radius: var(--radius); padding: 6px;
  background: linear-gradient(180deg, rgba(255,255,255,0.078), rgba(255,255,255,0.032));
  border: 1px solid rgba(255,255,255,0.06);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07); }
.t-hero, .t-value { font-weight: 600; letter-spacing: -0.02em; }
""",
    backdrop_css="""
body { background:
  radial-gradient(120% 85% at 50% -5%, #272438 0%, rgba(39,36,56,0) 62%),
  linear-gradient(180deg, #1a1926 0%, #100f18 82%); }
""",
)

# 6. Light — crisp paper, real shadow physics
#
# Layered paper backdrop (a white highlight from above over a cool gray
# wash) so pure-white cards separate from it. Shadows are y-offset
# two-layer stacks — a tight contact shadow plus a wide soft one — never
# a symmetric halo. Accents are deepened iOS-light system colors so they
# hold contrast against white.
THEME_LIGHT = Theme(
    name="light",
    primary=(10, 110, 235),
    secondary=(139, 80, 220),
    success=(22, 163, 90),
    warning=(222, 132, 10),
    error=(222, 52, 72),
    info=(10, 110, 235),
    muted=(150, 154, 164),
    background=(255, 255, 255),
    surface=(255, 255, 255),
    surface_variant=(245, 247, 250),
    border=(226, 229, 236),
    text_primary=(24, 26, 32),
    text_secondary=(112, 114, 120),
    text_tertiary=(163, 165, 172),
    text_on_primary=(255, 255, 255),
    accent_colors=(
        (10, 110, 235),
        (231, 60, 95),
        (22, 163, 90),
        (222, 132, 10),
        (139, 80, 220),
    ),
    corner_radius=14,
    layout_padding=7,
    widget_padding=6,
    gap=7,
    surface_chrome=True,
    tint_track_opacity=0.16,
    bar_background=(232, 235, 241),
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px; background: #ffffff;
  border: 1px solid rgba(16,24,40,0.05);
  box-shadow: 0 1px 2px rgba(16,24,40,0.07), 0 8px 18px -6px rgba(16,24,40,0.14); }
""",
    backdrop_css="""
body { background:
  radial-gradient(120% 80% at 50% -15%, #ffffff 0%, rgba(255,255,255,0) 58%),
  linear-gradient(180deg, #ecf0f6 0%, #dde3ee 100%); }
""",
)

# 7. Ocean — deep water, all-cool accents
#
# Light filtering down from the surface: a wide cyan pool at the top of
# the backdrop falling into near-black at the bottom. Every accent sits
# in the cool half of the wheel (sky, aqua, periwinkle, ice) so nothing
# breaks the temperature. Cells are aqua glass with a lit top edge.
THEME_OCEAN = Theme(
    name="ocean",
    primary=(56, 203, 240),
    secondary=(0, 214, 190),
    success=(0, 206, 170),
    warning=(255, 190, 92),
    error=(255, 110, 110),
    info=(56, 203, 240),
    muted=(86, 120, 142),
    background=(5, 25, 44),
    surface=(9, 41, 68),
    surface_variant=(13, 52, 84),
    border=(30, 78, 112),
    text_primary=(232, 244, 252),
    text_secondary=(150, 182, 205),
    text_tertiary=(96, 132, 160),
    text_on_primary=(3, 22, 38),
    accent_colors=(
        (56, 203, 240),
        (0, 214, 190),
        (122, 176, 255),
        (0, 152, 214),
    ),
    corner_radius=12,
    layout_padding=7,
    gap=7,
    surface_chrome=True,
    tint_track_opacity=0.22,
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: linear-gradient(180deg, rgba(120,205,255,0.10), rgba(10,70,115,0.05));
  border: 1px solid rgba(130,215,255,0.14);
  box-shadow: inset 0 1px 0 rgba(190,235,255,0.10); }
""",
    backdrop_css="""
body { background:
  radial-gradient(115% 80% at 50% -12%, #12557f 0%, rgba(18,85,127,0) 62%),
  linear-gradient(180deg, #06294a 0%, #03101f 84%); }
""",
)

# 8. Sunset — golden hour
#
# The warmth comes from below: an ember glow anchored off the bottom
# edge under a plum-to-clay vertical wash, which leaves the top of the
# screen calm enough to read. Accents are a single warm run (coral,
# amber, gold, rose); cell chrome is warm glass with a lit top edge and
# no outer glow.
THEME_SUNSET = Theme(
    name="sunset",
    primary=(255, 122, 102),
    secondary=(255, 168, 84),
    success=(140, 196, 120),
    warning=(255, 196, 102),
    error=(255, 86, 96),
    info=(232, 186, 132),
    muted=(142, 108, 106),
    background=(34, 18, 32),
    surface=(52, 30, 42),
    surface_variant=(66, 38, 50),
    border=(96, 58, 62),
    text_primary=(255, 242, 236),
    text_secondary=(198, 166, 164),
    text_tertiary=(142, 108, 110),
    text_on_primary=(42, 20, 26),
    accent_colors=(
        (255, 122, 102),
        (255, 168, 84),
        (255, 205, 112),
        (247, 131, 150),
    ),
    corner_radius=16,
    layout_padding=7,
    gap=7,
    surface_chrome=True,
    tint_track_opacity=0.22,
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: linear-gradient(180deg, rgba(78,38,52,0.42), rgba(46,22,34,0.30));
  border: 1px solid rgba(255,175,120,0.18);
  box-shadow: inset 0 1px 0 rgba(255,220,190,0.12); }
""",
    backdrop_css="""
body { background:
  radial-gradient(95% 62% at 50% 118%, rgba(255,146,74,0.30) 0%, rgba(255,146,74,0) 70%),
  linear-gradient(180deg, #211230 0%, #35172c 48%, #47232e 100%); }
""",
)

# 9. Forest — canopy light
#
# Cool green shade with a break in the canopy at the top. Accents run
# fern → moss → sage with one bark-gold for contrast, all at forest
# temperature. Corners are a single consistent radius (the old
# asymmetric leaf shape read as a gimmick at 2 inches).
THEME_FOREST = Theme(
    name="forest",
    primary=(124, 207, 138),
    secondary=(166, 214, 110),
    success=(124, 207, 138),
    warning=(220, 182, 84),
    error=(214, 102, 78),
    info=(128, 190, 160),
    muted=(96, 112, 94),
    background=(17, 32, 22),
    surface=(27, 45, 32),
    surface_variant=(35, 56, 40),
    border=(58, 82, 60),
    text_primary=(236, 244, 234),
    text_secondary=(158, 182, 160),
    text_tertiary=(104, 128, 108),
    text_on_primary=(17, 32, 22),
    accent_colors=(
        (124, 207, 138),
        (166, 214, 110),
        (140, 196, 168),
        (198, 168, 110),
    ),
    corner_radius=14,
    layout_padding=7,
    gap=7,
    surface_chrome=True,
    tint_track_opacity=0.20,
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: linear-gradient(180deg, rgba(150,220,160,0.09), rgba(30,70,40,0.05));
  border: 1px solid rgba(150,215,160,0.14);
  box-shadow: inset 0 1px 0 rgba(200,240,205,0.08); }
""",
    backdrop_css="""
body { background:
  radial-gradient(110% 78% at 50% -8%, #26492f 0%, rgba(38,73,47,0) 62%),
  linear-gradient(180deg, #14271b 0%, #0a140b 88%); }
""",
)

# 10. Candy — playful, coherent pastels
#
# Pastel sky (blush → lilac → ice) with marshmallow cards. The accents
# are one family sampled around the wheel at the same saturation and
# lightness, so pink next to mint next to sky still reads as one set.
# Shadows are tinted rose rather than gray, and the card rim is a
# hairline — the old 2px pink outline fought the type.
THEME_CANDY = Theme(
    name="candy",
    primary=(255, 111, 175),
    secondary=(96, 186, 255),
    success=(86, 214, 160),
    warning=(255, 186, 84),
    error=(255, 108, 132),
    info=(96, 186, 255),
    muted=(198, 182, 204),
    background=(255, 240, 247),
    surface=(255, 252, 253),
    surface_variant=(255, 236, 244),
    border=(255, 208, 228),
    text_primary=(74, 58, 84),
    text_secondary=(143, 130, 150),
    text_tertiary=(183, 166, 190),
    text_on_primary=(255, 255, 255),
    accent_colors=(
        (255, 111, 175),
        (96, 186, 255),
        (86, 214, 160),
        (255, 158, 92),
        (178, 140, 255),
    ),
    corner_radius=20,
    layout_padding=8,
    widget_padding=8,
    gap=8,
    surface_chrome=True,
    tint_track_opacity=0.22,
    bar_background=(255, 222, 236),
    chrome_css="""
.root { border-radius: var(--radius); padding: 5px;
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,163,205,0.38);
  box-shadow: 0 1px 2px rgba(186,104,150,0.10), 0 9px 18px -7px rgba(186,104,150,0.26); }
.t-hero, .t-value { font-weight: 800; letter-spacing: -0.03em; }
""",
    backdrop_css="""
body { background:
  radial-gradient(105% 72% at 12% -8%, #ffe6f3 0%, rgba(255,230,243,0) 60%),
  linear-gradient(155deg, #ffeaf4 0%, #f0e8ff 55%, #ddf1ff 100%); }
""",
)


# 12. Blueprint — an engineering drawing, not a screen
#
# Prussian-blue drafting paper carrying a two-scale grid (fine 8px lines
# under 40px majors, both from repeating-linear-gradients), cells drawn
# as pure line-work — square corners, 1px strokes, no fill — and DejaVu
# caps annotations. Accents are the four pens on a drafting desk:
# cyanotype white-blue, amber marker, red pen, chalk green. The overlay
# stamps corner register ticks like a plotted sheet.
THEME_BLUEPRINT = Theme(
    name="blueprint",
    primary=(140, 200, 255),
    secondary=(120, 165, 215),
    success=(150, 220, 170),
    warning=(255, 190, 90),
    error=(255, 110, 100),
    info=(140, 200, 255),
    muted=(95, 125, 160),
    background=(11, 42, 80),
    surface=(16, 52, 96),
    surface_variant=(20, 60, 108),
    border=(90, 130, 175),
    text_primary=(235, 244, 255),
    text_secondary=(170, 195, 225),
    text_tertiary=(120, 150, 185),
    text_on_primary=(11, 42, 80),
    accent_colors=(
        (140, 200, 255),
        (255, 190, 90),
        (150, 220, 170),
        (255, 110, 100),
        (200, 215, 240),
    ),
    corner_radius=2,
    layout_padding=8,
    widget_padding=5,
    gap=8,
    rounded_font=False,
    surface_chrome=True,
    tint_track=False,
    font_stack='"DejaVu Sans", sans-serif',
    chrome_css="""
.root { border-radius: 2px; padding: 4px;
  border: 1px solid rgba(200,220,245,0.42); }
.t-label { text-transform: uppercase; letter-spacing: 0.12em; }
.t-hero, .t-value { font-weight: 700; letter-spacing: 0; }
.chip { border-radius: 2px; background: transparent;
        border: 1px solid rgba(200,220,245,0.30); }
""",
    backdrop_css="""
body { background:
  radial-gradient(130% 95% at 50% 0%, rgba(30,75,130,0.55) 0%, rgba(30,75,130,0) 62%),
  repeating-linear-gradient(0deg, rgba(215,232,255,0.085) 0px, rgba(215,232,255,0.085) 1px,
    rgba(0,0,0,0) 1px, rgba(0,0,0,0) 40px),
  repeating-linear-gradient(90deg, rgba(215,232,255,0.085) 0px, rgba(215,232,255,0.085) 1px,
    rgba(0,0,0,0) 1px, rgba(0,0,0,0) 40px),
  repeating-linear-gradient(0deg, rgba(215,232,255,0.035) 0px, rgba(215,232,255,0.035) 1px,
    rgba(0,0,0,0) 1px, rgba(0,0,0,0) 8px),
  repeating-linear-gradient(90deg, rgba(215,232,255,0.035) 0px, rgba(215,232,255,0.035) 1px,
    rgba(0,0,0,0) 1px, rgba(0,0,0,0) 8px),
  linear-gradient(180deg, #0d3161 0%, #0b2a50 100%); }
""",
    # Plotted-sheet register ticks: one 12x1 (or 1x12) white stroke per
    # corner edge, each a solid two-stop gradient placed/sized via
    # background shorthand. Assembled in Python to keep lines readable.
    overlay_css="body { background: "
    + ", ".join(
        f"linear-gradient(rgba(235,244,255,0.55), rgba(235,244,255,0.55)) {pos} / {size} no-repeat"
        for pos, size in (
            ("3px 3px", "12px 1px"),
            ("3px 3px", "1px 12px"),
            ("225px 3px", "12px 1px"),
            ("236px 3px", "1px 12px"),
            ("3px 236px", "12px 1px"),
            ("3px 225px", "1px 12px"),
            ("225px 236px", "12px 1px"),
            ("236px 225px", "1px 12px"),
        )
    )
    + "; }",
)

# 13. Ink — warm newsprint, one pot of red ink
#
# An editorial page, not a display: cream paper, near-black ink, DejaVu
# caps, and cells set as newspaper column blocks — a strong rule above,
# a faint one below, no fill, no radius. Everything is ink-toned except
# a single vermilion spot color (the "red pen"), so a glance reads like
# a well-set broadsheet where only what matters is circled.
THEME_INK = Theme(
    name="ink",
    primary=(196, 62, 42),
    secondary=(70, 90, 130),
    success=(64, 110, 74),
    warning=(168, 120, 42),
    error=(196, 62, 42),
    info=(70, 90, 130),
    muted=(158, 150, 138),
    background=(246, 241, 231),
    surface=(240, 234, 222),
    surface_variant=(233, 226, 212),
    border=(205, 196, 180),
    text_primary=(30, 28, 25),
    text_secondary=(92, 87, 79),
    text_tertiary=(142, 135, 123),
    text_on_primary=(246, 241, 231),
    accent_colors=(
        (196, 62, 42),
        (30, 28, 25),
        (70, 90, 130),
        (168, 120, 42),
        (64, 110, 74),
    ),
    corner_radius=0,
    layout_padding=9,
    widget_padding=5,
    gap=9,
    rounded_font=False,
    surface_chrome=True,
    tint_track=False,
    bar_background=(222, 214, 199),
    font_stack='"DejaVu Sans", sans-serif',
    chrome_css="""
.root { border-radius: 0; padding: 5px 3px 3px;
  border-top: 2px solid rgba(30,28,25,0.78);
  border-bottom: 1px solid rgba(30,28,25,0.22); }
.t-label { text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; }
.t-hero, .t-value { font-weight: 700; letter-spacing: -0.01em; }
.chip { border-radius: 0; background: transparent;
        border: 1px solid rgba(30,28,25,0.28); }
""",
    backdrop_css="""
body { background:
  radial-gradient(120% 70% at 50% -10%, #fbf7ee 0%, rgba(251,247,238,0) 55%),
  linear-gradient(180deg, #f6f1e7 0%, #efe8da 100%); }
""",
)

# 14. Aurora — a luminous mesh-gradient poster
#
# The Linear/Stripe poster look: three vast low-alpha radial washes
# (teal, violet, magenta) drifting over near-black indigo, with cells as
# frosted glass — translucent white with a lit top sheen — so the color
# field glows THROUGH the interface. Accents are iridescent northern
# hues that read as parts of the same light.
THEME_AURORA = Theme(
    name="aurora",
    primary=(110, 255, 210),
    secondary=(170, 130, 255),
    success=(110, 255, 210),
    warning=(255, 210, 130),
    error=(255, 120, 190),
    info=(130, 200, 255),
    muted=(110, 112, 138),
    background=(10, 10, 24),
    surface=(24, 24, 46),
    surface_variant=(32, 32, 58),
    border=(58, 58, 92),
    text_primary=(240, 240, 250),
    text_secondary=(172, 172, 198),
    text_tertiary=(118, 118, 146),
    text_on_primary=(10, 10, 24),
    accent_colors=(
        (110, 255, 210),
        (170, 130, 255),
        (255, 120, 190),
        (130, 200, 255),
        (255, 210, 130),
    ),
    corner_radius=20,
    layout_padding=8,
    widget_padding=7,
    gap=8,
    surface_chrome=True,
    tint_track_opacity=0.22,
    chrome_css="""
.root { border-radius: var(--radius); padding: 6px;
  background: linear-gradient(180deg, rgba(255,255,255,0.085), rgba(255,255,255,0.030));
  border: 1px solid rgba(255,255,255,0.11);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.10); }
.t-hero, .t-value { font-weight: 800; letter-spacing: -0.03em; }
""",
    backdrop_css="""
body { background:
  radial-gradient(85% 65% at 12% 6%, rgba(0,220,182,0.26) 0%, rgba(0,220,182,0) 58%),
  radial-gradient(90% 70% at 88% 22%, rgba(140,92,255,0.24) 0%, rgba(140,92,255,0) 60%),
  radial-gradient(100% 80% at 65% 100%, rgba(255,74,160,0.17) 0%, rgba(255,74,160,0) 55%),
  linear-gradient(180deg, #0d0d20 0%, #07070f 100%); }
""",
)

# 15. Brutal — neo-brutalism at 240px
#
# Flat bone paper, white blocks with thick 2px ink borders and a HARD
# offset shadow (no blur — the whole point), loud primary-school
# accents, and everything set extra-bold. The shadow offset budget
# (3px) plus border (2px) plus padding (2px) matches the chrome inset
# the fit math reserves, so nothing clips at the cell edge.
THEME_BRUTAL = Theme(
    name="brutal",
    primary=(40, 90, 255),
    secondary=(150, 80, 255),
    success=(0, 180, 110),
    warning=(255, 180, 0),
    error=(255, 70, 60),
    info=(40, 90, 255),
    muted=(150, 146, 136),
    background=(240, 235, 220),
    surface=(255, 252, 245),
    surface_variant=(246, 242, 232),
    border=(20, 20, 20),
    text_primary=(20, 20, 20),
    text_secondary=(85, 82, 75),
    text_tertiary=(138, 133, 122),
    text_on_primary=(255, 252, 245),
    accent_colors=(
        (40, 90, 255),
        (255, 70, 60),
        (255, 180, 0),
        (0, 180, 110),
        (150, 80, 255),
    ),
    corner_radius=6,
    layout_padding=8,
    widget_padding=6,
    gap=9,
    surface_chrome=True,
    tint_track_opacity=0.18,
    bar_background=(226, 220, 205),
    chrome_css="""
.root { width: calc(100% - 3px); height: calc(100% - 3px);
  border-radius: var(--radius); padding: 2px;
  background: #fffcf5; border: 2px solid #141414;
  box-shadow: 3px 3px 0 #141414; }
.t-label { font-weight: 800; letter-spacing: 0.04em; }
.t-hero, .t-value { font-weight: 800; letter-spacing: -0.03em; }
.chip { background: #f0ebdc; border: 1px solid #141414; font-weight: 700; }
""",
    backdrop_css="""
body { background: #f0ebdc; }
""",
)

# =============================================================================
# Theme Registry
# =============================================================================

THEMES: dict[str, Theme] = {
    "watchos": THEME_WATCHOS,
    "standby": THEME_STANDBY,
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
    "blueprint": THEME_BLUEPRINT,
    "ink": THEME_INK,
    "aurora": THEME_AURORA,
    "brutal": THEME_BRUTAL,
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
    "THEME_AURORA",
    "THEME_BLUEPRINT",
    "THEME_BRUTAL",
    "THEME_CANDY",
    "THEME_CLASSIC",
    "THEME_FOREST",
    "THEME_INK",
    "THEME_LIGHT",
    "THEME_MINIMAL",
    "THEME_NEON",
    "THEME_OCEAN",
    "THEME_RETRO",
    "THEME_SOFT",
    "THEME_STANDBY",
    "THEME_SUNSET",
    "THEME_WATCHOS",
    "BorderStyle",
    "Color",
    "FontWeight",
    "Theme",
    "get_theme",
]
