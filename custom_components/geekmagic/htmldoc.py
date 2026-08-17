"""HTML document assembly for the Blitz rendering pipeline.

The display is rendered in passes, all through the Blitz engine
(via the ``blitz-py`` package):

1. **Backdrop** — one fullscreen document carrying the theme's
   background treatment (solid, gradient, texture).
2. **Cells** — each widget renders an HTML fragment which is wrapped
   with the theme's CSS and rasterized *at the cell size* with a
   transparent background, then alpha-composited onto the backdrop.
   Because every cell is its own CSS viewport, viewport units and media
   queries respond to the CELL — one fluid template adapts from a 76px
   3x3 cell to 240px fullscreen.
3. **Overlay** — an optional fullscreen transparent document for theme
   effects (scanlines, vignettes) composited on top.

Pillow's remaining role is compositing and JPEG/PNG encoding.
"""

from __future__ import annotations

import base64
import io
import logging
import math
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from .icons import get_mdi_char

if TYPE_CHECKING:
    from .widgets.theme import Theme

try:
    from importlib import import_module

    blitz_py: Any = import_module("blitz_py")
    HAS_BLITZ = True
except ImportError:  # pragma: no cover - depends on environment
    blitz_py = None
    HAS_BLITZ = False

# The pipeline requires blitz-py >= 0.4.2 (layered compositing,
# process-wide font registration that survives font-less systems,
# per-layer animation clocks). An older engine on disk gets the
# install-hint screen instead of a half-working fallback pipeline: the
# legacy per-document + Pillow compositing paths were removed once
# 0.4.2 became the floor. manifest.json installs >= 0.5.0 (a pure
# engine bump: crash fixes, no API change, renders differ only at the
# antialiasing level) — the functional floor stays 0.4.2 so a working
# older install is not turned into an error screen.
_ENGINE_FLOOR = (0, 4, 2)


def _engine_ok() -> bool:
    """True when the installed blitz-py meets the pipeline's floor."""
    if not (HAS_BLITZ and hasattr(blitz_py, "render_layers")):
        return False
    try:
        from importlib.metadata import version  # noqa: PLC0415

        parts = tuple(int(p) for p in version("blitz-py").split(".")[:3])
    except Exception:  # pragma: no cover - source installs without metadata
        return True  # API surface is there — trust it
    return parts >= _ENGINE_FLOOR


HAS_ENGINE = _engine_ok()

_LOGGER = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).parent / "fonts"

# Font files embedded into every Blitz render. Families resolve by the
# font's internal name: "Nunito", "DejaVu Sans", "Material Design Icons".
_FONT_FILES = (
    "Nunito-Regular.ttf",
    "Nunito-SemiBold.ttf",
    "Nunito-Bold.ttf",
    "Nunito-ExtraBold.ttf",
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "materialdesignicons-webfont.ttf",
)


@lru_cache(maxsize=1)
def get_font_bytes() -> tuple[bytes, ...]:
    """Load embedded font files once."""
    fonts = []
    for name in _FONT_FILES:
        path = _FONTS_DIR / name
        try:
            fonts.append(path.read_bytes())
        except OSError:
            _LOGGER.warning("Font file missing: %s", path)
    return tuple(fonts)


class _FontRegistry:
    """One-time process-wide font registration, serialized by a lock.

    The lock matters: no thread may measure or render against a
    half-mutated global font collection — a divergence between measured
    widths and drawn glyphs is exactly how text ends up painted over
    the panel edge.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: bool | None = None

    def registered(self) -> bool:
        """Register the embedded faces exactly once; report the outcome.

        Returns False when the engine has no registry (ancient
        blitz-py) or registration failed — callers then pass font bytes
        per call instead.
        """
        if self._state is None:
            with self._lock:
                if self._state is None:
                    self._state = self._register()
        return self._state

    def _register(self) -> bool:
        if not (HAS_BLITZ and hasattr(blitz_py, "register_fonts")):
            return False
        try:
            blitz_py.register_fonts(list(get_font_bytes()), default_family="Nunito")
        except Exception:  # pragma: no cover - registration is best-effort
            _LOGGER.exception("Font registration failed; falling back to per-call fonts")
            return False
        return True


_FONT_REGISTRY = _FontRegistry()


def _fonts_registered() -> bool:
    """True once the process-wide registry holds the embedded faces."""
    return _FONT_REGISTRY.registered()


def font_param() -> list[bytes] | None:
    """The ``fonts=`` argument for engine calls.

    ``None`` once the process-wide registry holds the embedded faces;
    the explicit byte list on older blitz-py.
    """
    return None if _fonts_registered() else list(get_font_bytes())


def css_rgb(color: tuple[int, int, int]) -> str:
    """Format an RGB tuple as a CSS color."""
    return f"rgb({color[0]}, {color[1]}, {color[2]})"


def css_rgba(color: tuple[int, int, int], alpha: float) -> str:
    """Format an RGB tuple + alpha as a CSS color."""
    return f"rgba({color[0]}, {color[1]}, {color[2]}, {alpha})"


def theme_css_variables(theme: Theme) -> str:
    """Build a :root CSS block exposing the theme palette as variables."""
    variables = {
        "--bg": theme.background,
        "--surface": theme.surface,
        "--surface-variant": theme.surface_variant,
        "--border": theme.border,
        "--text-primary": theme.text_primary,
        "--text-secondary": theme.text_secondary,
        "--text-tertiary": theme.text_tertiary,
        "--primary": theme.primary,
        "--secondary": theme.secondary,
        "--success": theme.success,
        "--warning": theme.warning,
        "--error": theme.error,
        "--info": theme.info,
        "--muted": theme.muted,
    }
    lines = "\n".join(f"  {name}: {css_rgb(value)};" for name, value in variables.items())
    accents = "\n".join(f"  --accent-{i}: {css_rgb(c)};" for i, c in enumerate(theme.accent_colors))
    # Neutral derived tones: chip fills, hairline strokes, and gauge
    # tracks derive from the text color so they read correctly on both
    # dark themes (white-based) and light themes (ink-based).
    tp = theme.text_primary
    derived = (
        f"  --chip-bg: {css_rgba(tp, 0.08)};\n"
        f"  --hairline: {css_rgba(tp, 0.10)};\n"
        f"  --track: {css_rgba(tp, 0.12)};"
    )
    return f":root {{\n{lines}\n{accents}\n{derived}\n  --radius: {theme.corner_radius}px;\n}}"


# Fluid kit: opinionated utility classes available in every cell.
#
# Each cell is its own CSS viewport, so viewport units (vmin/vw/vh) and
# media queries respond to the CELL size, not the display size.
#
# - ``.cell``      flex-column scaffold filling the cell, space-evenly;
#                  add ``.row`` to go horizontal
# - ``.t-hero``    primary value — scales with cell size, capped by width
# - ``.t-value``   secondary emphasized value
# - ``.t-unit``    unit suffix next to a hero
# - ``.t-label``   caps caption / label
# - ``.icon``      Material Design Icons glyph
# - ``.hide-short``  hidden when the cell is under 100px tall
# - ``.hide-narrow`` hidden when the cell is under 100px wide
# - ``.hide-small``  hidden when either dimension is under 130px
#
# Breakpoints follow the real cell sizes: 3x3 grid ~76px, 2x2 ~118px,
# fullscreen 240px.
FLUID_KIT_CSS = """
.cell { height: 100%; display: flex; flex-direction: column; align-items: center;
        justify-content: space-evenly; text-align: center; box-sizing: border-box;
        padding: 3%; }
.cell.row { flex-direction: row; }
.t-hero { font-size: clamp(20px, min(48vmin, 30vw), 124px); font-weight: 800;
          line-height: 0.85; letter-spacing: -0.035em; white-space: nowrap; }
.t-value { font-size: clamp(15px, min(26vmin, 20vw), 64px); font-weight: 700;
           line-height: 1; white-space: nowrap; }
.t-unit { font-size: clamp(13px, min(18vmin, 12vw), 40px); font-weight: 600;
          line-height: 1; color: var(--text-secondary); white-space: nowrap; }
.t-label { font-size: clamp(12px, min(12vmin, 9vw), 18px); font-weight: 700;
           line-height: 1; letter-spacing: 0.06em; color: var(--text-tertiary);
           white-space: nowrap; }
.icon { font-family: "Material Design Icons"; font-weight: 400; line-height: 1; }
.i-lg { font-size: clamp(20px, 34vmin, 84px); }
.i-md { font-size: clamp(14px, 20vmin, 48px); }
.i-sm { font-size: clamp(11px, 12vmin, 24px); }
@media (max-height: 99px) { .hide-short { display: none !important; } }
@media (max-width: 99px) { .hide-narrow { display: none !important; } }
@media (max-height: 129px), (max-width: 129px) { .hide-small { display: none !important; } }
"""


def build_cell_document(fragment: str, theme: Theme) -> str:
    """Wrap a widget fragment into a standalone cell document.

    The body is transparent — the theme backdrop shows through — and
    ``.root`` fills the cell so themes can paint per-cell chrome
    (cards, borders) on it via ``theme.chrome_css``.
    """
    # Deferred: _card imports helpers from this module (mdi_span), so a
    # top-level import here would be circular.
    from .widgets._card import CARD_CSS  # noqa: PLC0415

    return f"""<style>
{theme_css_variables(theme)}
html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: transparent; }}
body {{ color: var(--text-primary); font-family: {theme.font_stack}; }}
{FLUID_KIT_CSS}
{CARD_CSS}
.root {{ width: 100%; height: 100%; box-sizing: border-box; }}
{theme.chrome_css}
</style>
<body><div class="root">{fragment}</div></body>"""


def build_fullscreen_document(theme: Theme, body_css: str, body_html: str = "") -> str:
    """Build a fullscreen (backdrop or overlay) document."""
    return f"""<style>
{theme_css_variables(theme)}
html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
{body_css}
</style>
<body>{body_html}</body>"""


def render_layers_image(
    layers: list[dict[str, Any]],
    width: int,
    height: int,
    background: str = "#000000",
) -> Image.Image | None:
    """Composite documents into one surface engine-side (blitz-py >= 0.4.2).

    ``layers`` follow the ``blitz_py.render_layers`` contract: ``html``
    (+ ``width``/``height`` in CSS px), device-px ``x``/``y``, optional
    ``scale``, ``opacity``, ``blur``, ``tint`` and ``time``. Layers paint
    in list order and are clipped to their rects. ``width``/``height``
    here are the surface size in device px. Returns an RGB image, or
    None when layered rendering is unavailable or fails.
    """
    if not HAS_ENGINE:
        return None
    try:
        # When the process-wide registry is live, layers see the
        # embedded faces automatically. When it is not (registration
        # failed), the fonts MUST ride each layer: measurement used the
        # embedded faces via per-call bytes, and letting the render fall
        # back to different fonts is how fitted text overflows the cell.
        fonts = font_param()
        if fonts is not None:
            layers = [
                {**layer, "fonts": fonts} if "html" in layer and "fonts" not in layer else layer
                for layer in layers
            ]
        w, h, data = blitz_py.render_layers(
            layers, width=width, height=height, background=background
        )
        return Image.frombytes("RGBA", (w, h), data).convert("RGB")
    except Exception:
        _LOGGER.exception("Blitz layered render failed")
        return None


def image_data_uri(image: Image.Image) -> str:
    """Encode a PIL image as a PNG data: URI for use in <img src>."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def mdi_span(icon_name: str, classes: str = "icon i-md", style: str = "") -> str:
    """Render an MDI icon as an HTML span using the embedded MDI font.

    Accepts "mdi:thermometer", "thermometer", or legacy aliases.
    Returns an empty string for unknown icons.
    """
    char = get_mdi_char(icon_name)
    if not char:
        return ""
    style_attr = f' style="{style}"' if style else ""
    return f'<span class="{classes}"{style_attr}>&#x{ord(char):X};</span>'


# ============================================================================
# SVG helpers for gauges and charts
#
# IMPORTANT: Blitz does not resolve ``var(--x)`` inside SVG paint
# attributes — always pass concrete colors (css_rgb/css_rgba of theme
# values). The var() defaults below only apply when a caller forgets,
# and render as no paint.
# ============================================================================


def _smooth_path(pts: list[tuple[float, float]]) -> str:
    """Catmull-Rom → cubic bezier path through the points."""
    if len(pts) < 3:
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    path = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        path.append(f"C {c1[0]:.1f} {c1[1]:.1f}, {c2[0]:.1f} {c2[1]:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(path)


def svg_sparkline(
    values: list[float],
    stroke: str = "var(--primary)",
    fill_opacity: float = 0.50,
    stroke_width: float = 2.6,
    *,
    aspect: float = 2.0,
    smooth: bool = True,
    show_dot: bool = True,
) -> str:
    """Build a responsive SVG sparkline (Apple-Health style).

    Smooth bezier line, vertical gradient area fade, and an endpoint
    dot with a soft halo. ``aspect`` is the expected width/height ratio
    of the box the SVG will fill — the viewBox matches it so the dot
    stays circular under stretching. Pass concrete colors, never
    ``var()`` (SVG paint attributes don't resolve CSS variables).
    """
    if len(values) < 2:
        return ""
    vb_w = 100.0 * max(0.4, aspect)
    vmin, vmax = min(values), max(values)
    spread = vmax - vmin
    n = len(values) - 1
    inset = 7.0  # headroom so the dot/halo and stroke stay inside
    if spread == 0:
        # Flat series: draw the line mid-height instead of pinned to the
        # bottom edge (y would otherwise collapse to vmin's baseline).
        pts = [(inset + i / n * (vb_w - 2 * inset), 50.0) for i in range(len(values))]
    else:
        pts = [
            (
                inset + i / n * (vb_w - 2 * inset),
                (100 - inset) - (v - vmin) / spread * (100 - 2 * inset),
            )
            for i, v in enumerate(values)
        ]
    line = _smooth_path(pts) if smooth else "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    # The area fill extends to the viewBox edges (x=0 / x=vb_w) so the
    # gradient has no hard vertical seam at the line insets; the stroked
    # line itself keeps its inset for dot/stroke headroom. A flat series
    # fills nothing — half a cell of gradient under an unchanging value
    # reads as data that isn't there.
    if spread == 0:
        fill_opacity = 0.0
    area = (
        f"M 0 {pts[0][1]:.1f} {line.replace('M', 'L', 1)} "
        f"L {vb_w:.0f} {pts[-1][1]:.1f} L {vb_w:.0f} 100 L 0 100 Z"
    )
    dot = ""
    if show_dot:
        dx, dy = pts[-1]
        dot = (
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="7" fill="{stroke}" fill-opacity="0.25"/>'
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3.4" fill="{stroke}"/>'
        )
    return (
        f'<svg viewBox="0 0 {vb_w:.0f} 100" preserveAspectRatio="none" '
        'style="width:100%;height:100%;display:block">'
        "<defs>"
        '<linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{stroke}" stop-opacity="{fill_opacity}"/>'
        f'<stop offset="55%" stop-color="{stroke}" stop-opacity="{fill_opacity * 0.38:.2f}"/>'
        f'<stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>'
        "</linearGradient>"
        "</defs>"
        f'<path d="{area}" fill="url(#sparkfill)"/>'
        f'<path d="{line}" fill="none" stroke="{stroke}" '
        f'stroke-width="{stroke_width}" vector-effect="non-scaling-stroke" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        f"{dot}"
        "</svg>"
    )


def svg_ring(
    percent: float,
    stroke: str = "var(--primary)",
    track: str = "rgba(255,255,255,0.12)",
    stroke_width: float = 11.0,
    label_html: str = "",
) -> str:
    """Build an Activity-style ring gauge as SVG (square aspect).

    ``label_html`` is centered inside the ring.
    """
    percent = max(0.0, min(100.0, percent))
    radius = 50 - stroke_width / 2
    circumference = 2 * 3.14159265 * radius
    dash = circumference * percent / 100
    svg = (
        '<svg viewBox="0 0 100 100" style="width:100%;height:100%;display:block">'
        f'<circle cx="50" cy="50" r="{radius:.2f}" fill="none" '
        f'stroke="{track}" stroke-width="{stroke_width}"/>'
        f'<circle cx="50" cy="50" r="{radius:.2f}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circumference:.2f}" '
        'transform="rotate(-90 50 50)"/>'
        "</svg>"
    )
    if label_html:
        # max-width guards non-square parents: without it the square
        # aspect box overflows a tall cell's width (and vice versa).
        return (
            '<div style="position:relative;height:100%;max-width:100%;'
            'aspect-ratio:1;margin:0 auto">'
            f"{svg}"
            '<div style="position:absolute;inset:0;display:flex;flex-direction:column;'
            'align-items:center;justify-content:center">'
            f"{label_html}</div></div>"
        )
    return svg


def svg_arc(
    percent: float,
    stroke: str = "var(--primary)",
    track: str = "rgba(255,255,255,0.12)",
    stroke_width: float = 11.0,
) -> str:
    """Build a 270-degree open arc gauge as SVG (gap at the bottom)."""
    percent = max(0.0, min(100.0, percent))
    r = 50 - stroke_width / 2
    sweep = 270.0
    start_angle = 135.0  # degrees, clockwise from 3 o'clock

    def point(angle_deg: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        return (50 + r * math.cos(a), 50 + r * math.sin(a))

    def arc_path(from_deg: float, to_deg: float) -> str:
        x1, y1 = point(from_deg)
        x2, y2 = point(to_deg)
        large = 1 if (to_deg - from_deg) > 180 else 0
        return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}"

    track_path = arc_path(start_angle, start_angle + sweep)
    value_deg = sweep * percent / 100
    parts = [
        '<svg viewBox="0 0 100 100" style="width:100%;height:100%;display:block">',
        f'<path d="{track_path}" fill="none" stroke="{track}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round"/>',
    ]
    if value_deg > 0.5:
        value_path = arc_path(start_angle, start_angle + value_deg)
        parts.append(
            f'<path d="{value_path}" fill="none" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ============================================================================
# Cell render context
# ============================================================================


@dataclass
class CellContext:
    """Context passed to widgets when rendering their HTML fragment.

    Carries the cell geometry (so widgets *can* branch on size in
    Python), the theme, and the slot index for accent cycling. Prefer
    CSS-side fluidity (kit classes, vmin, media queries) over Python
    branching where possible.
    """

    width: int
    height: int
    slot_index: int = 0
    theme: Any = None  # Theme; Any avoids a circular import at runtime
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_compact(self) -> bool:
        """True for cells too small for secondary content (3x3 grid)."""
        return self.height < 100 or self.width < 100

    def accent(self) -> str:
        """CSS color for this slot's accent (cycles the theme palette)."""
        if self.theme is None:
            return "var(--primary)"
        return css_rgb(self.theme.get_accent_color(self.slot_index))
