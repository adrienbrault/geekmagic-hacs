"""Tailwind-syntax utility classes for HTML widget templates.

An HTML widget with its **Tailwind utility classes** option on can be
written as ``<div class="h-full flex items-center text-[64px] font-bold
text-warning">``, no ``<style>`` block needed. After Jinja renders the
template, :func:`with_utilities` collects every ``class="..."`` token and
prepends a ``<style>`` holding CSS for the ones it recognises, so classes
built in Jinja (``{{ 'text-success' if on else 'text-muted' }}``) work
too, which a real Tailwind build (a static file scan) can't do.

The names, values and CSS shapes follow Tailwind CSS v4 (spacing scale,
type scale with its line heights, palette, ``--tw-*`` variable stacks
for shadows, rings, gradients and transforms, ``@property`` so they don't
inherit). What differs, because a cell is 76-240px and themed:

- **Colours** are the theme's roles first: ``text-warning``,
  ``bg-surface``, ``ring-accent``, and ``fg`` / ``fg-2`` / ``fg-3`` for
  the primary / secondary / tertiary text tones (``text-secondary`` is
  the secondary *accent*). The Tailwind palette (``sky-400``) and
  arbitrary colours work too; on a monochrome theme (Night) they map onto
  the theme's ramp, keeping their lightness, as colour options do on the
  built-in widgets. Every colour is resolved to a concrete value, so they
  paint SVG ``fill``/``stroke`` too.
- **Cell-size variants** mirror the fluid kit: ``short:`` (under 100px
  tall), ``narrow:`` (under 100px wide), ``small:`` (either under 130px),
  and ``not-short:`` / ``not-narrow:`` / ``not-small:``. ``sm:`` ... ``2xl:``
  keep their real breakpoints, so like in a browser at this size they
  never match.
- **Interaction variants** (``hover:``, ``focus:``, ``group-*``, ...) never
  match a display, so their classes are dropped; ``dark:`` applies on
  dark themes only.
- Utilities Blitz can't paint (``blur``, ``drop-shadow``,
  ``backdrop-*``, ``text-shadow``, ``bg-clip-text``, ``outline-offset``)
  are not generated: they are reported as unknown instead.

The reset is deliberately light (border-box sizing and no default
margins on headings, paragraphs and lists), so the built-in drawing
helpers' markup lays out exactly as it does without the option.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from ..htmldoc import css_rgb, css_rgba
from ._tailwind_palette import PALETTE, SHADES

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..htmldoc import CellContext

_LOGGER = logging.getLogger(__name__)

Decls = tuple[tuple[str, str], ...]
RGB = tuple[int, int, int]

SPACING_PX = 4.0  # Tailwind's --spacing: 0.25rem at a 16px root

PREFLIGHT_CSS = (
    "*, ::before, ::after { box-sizing: border-box; }\n"
    "h1, h2, h3, h4, h5, h6, p, figure, blockquote, dl, dd, ul, ol, pre, hr { margin: 0; }\n"
    "h1, h2, h3, h4, h5, h6 { font-size: inherit; font-weight: inherit; }\n"
    "ul, ol { list-style: none; padding: 0; }\n"
)

# ---------------------------------------------------------------------------
# Theme scales (tailwindcss@4.1.11 theme.css, rem at 16px)
# ---------------------------------------------------------------------------

_TEXT_SIZES = {
    "xs": ("12px", "16px"),
    "sm": ("14px", "20px"),
    "base": ("16px", "24px"),
    "lg": ("18px", "28px"),
    "xl": ("20px", "28px"),
    "2xl": ("24px", "32px"),
    "3xl": ("30px", "36px"),
    "4xl": ("36px", "40px"),
    "5xl": ("48px", "1"),
    "6xl": ("60px", "1"),
    "7xl": ("72px", "1"),
    "8xl": ("96px", "1"),
    "9xl": ("128px", "1"),
}
_FONT_WEIGHTS = {
    "thin": "100",
    "extralight": "200",
    "light": "300",
    "normal": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
    "extrabold": "800",
    "black": "900",
}
_FONT_FAMILIES = {
    "sans": '"Nunito", "DejaVu Sans", sans-serif',
    "serif": "serif",
    "mono": "monospace",
}
_TRACKING = {
    "tighter": "-0.05em",
    "tight": "-0.025em",
    "normal": "0em",
    "wide": "0.025em",
    "wider": "0.05em",
    "widest": "0.1em",
}
_LEADING = {
    "none": "1",
    "tight": "1.25",
    "snug": "1.375",
    "normal": "1.5",
    "relaxed": "1.625",
    "loose": "2",
}
_RADII = {
    "": "4px",
    "none": "0",
    "xs": "2px",
    "sm": "4px",
    "md": "6px",
    "lg": "8px",
    "xl": "12px",
    "2xl": "16px",
    "3xl": "24px",
    "4xl": "32px",
    "full": "calc(infinity * 1px)",
}
_CONTAINERS = {
    "3xs": "256px",
    "2xs": "288px",
    "xs": "320px",
    "sm": "384px",
    "md": "448px",
    "lg": "512px",
    "xl": "576px",
    "2xl": "672px",
    "3xl": "768px",
    "4xl": "896px",
    "5xl": "1024px",
    "6xl": "1152px",
    "7xl": "1280px",
    "prose": "65ch",
}
_SHADOWS = {
    "2xs": "0 1px rgb(0 0 0 / 0.05)",
    "xs": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    "sm": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
    "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
    "xl": "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
    "2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
}
_INSET_SHADOWS = {
    "2xs": "inset 0 1px rgb(0 0 0 / 0.05)",
    "xs": "inset 0 1px 1px rgb(0 0 0 / 0.05)",
    "sm": "inset 0 2px 4px rgb(0 0 0 / 0.05)",
}
_KEYFRAMES = {
    "spin": "@keyframes spin { to { transform: rotate(360deg); } }",
    "ping": "@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }",
    "pulse": "@keyframes pulse { 50% { opacity: 0.5; } }",
    "bounce": (
        "@keyframes bounce { 0%, 100% { transform: translateY(-25%); "
        "animation-timing-function: cubic-bezier(0.8, 0, 1, 1); } "
        "50% { transform: none; animation-timing-function: cubic-bezier(0, 0, 0.2, 1); } }"
    ),
}
_ANIMATIONS = {
    "spin": "spin 1s linear infinite",
    "ping": "ping 1s cubic-bezier(0, 0, 0.2, 1) infinite",
    "pulse": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
    "bounce": "bounce 1s infinite",
    "none": "none",
}

# The --tw-* variables a family of utilities composes, registered so they
# don't inherit (a child's ring must not repeat its parent's).
_PROPERTIES = {
    "shadow": (
        ("--tw-shadow", "0 0 #0000"),
        ("--tw-shadow-color", None),
        ("--tw-inset-shadow", "0 0 #0000"),
        ("--tw-inset-shadow-color", None),
        ("--tw-ring-color", None),
        ("--tw-ring-shadow", "0 0 #0000"),
        ("--tw-inset-ring-color", None),
        ("--tw-inset-ring-shadow", "0 0 #0000"),
        ("--tw-ring-inset", None),
        ("--tw-ring-offset-shadow", "0 0 #0000"),
    ),
    "gradient": (
        ("--tw-gradient-position", None),
        ("--tw-gradient-from", "#0000"),
        ("--tw-gradient-via", "#0000"),
        ("--tw-gradient-to", "#0000"),
        ("--tw-gradient-stops", None),
        ("--tw-gradient-via-stops", None),
        ("--tw-gradient-from-position", "0%"),
        ("--tw-gradient-via-position", "50%"),
        ("--tw-gradient-to-position", "100%"),
    ),
    "translate": (("--tw-translate-x", "0"), ("--tw-translate-y", "0")),
    "scale": (("--tw-scale-x", "1"), ("--tw-scale-y", "1")),
    "border": (("--tw-border-style", "solid"),),
    "leading": (("--tw-leading", None),),
    "content": (("--tw-content", '""'),),
}
_BOX_SHADOW = (
    "var(--tw-inset-shadow), var(--tw-inset-ring-shadow), "
    "var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow)"
)
_GRADIENT_STOPS = (
    "var(--tw-gradient-via-stops, var(--tw-gradient-position), "
    "var(--tw-gradient-from) var(--tw-gradient-from-position), "
    "var(--tw-gradient-to) var(--tw-gradient-to-position))"
)
_GRADIENT_VIA_STOPS = (
    "var(--tw-gradient-position), var(--tw-gradient-from) var(--tw-gradient-from-position), "
    "var(--tw-gradient-via) var(--tw-gradient-via-position), "
    "var(--tw-gradient-to) var(--tw-gradient-to-position)"
)
_DIRECTIONS = {
    "t": "to top",
    "tr": "to top right",
    "r": "to right",
    "br": "to bottom right",
    "b": "to bottom",
    "bl": "to bottom left",
    "l": "to left",
    "tl": "to top left",
}

# ---------------------------------------------------------------------------
# Static utilities: exact class name -> declarations
# ---------------------------------------------------------------------------


def _static() -> dict[str, Decls]:
    table: dict[str, Decls] = {}

    def add(name: str, *decls: tuple[str, str]) -> None:
        table[name] = decls

    for name in ("block", "inline-block", "inline", "flex", "inline-flex", "grid"):
        add(name, ("display", name))
    for name in ("inline-grid", "contents", "flow-root", "table", "list-item"):
        add(name, ("display", name))
    add("hidden", ("display", "none"))
    for name in ("static", "fixed", "absolute", "relative", "sticky"):
        add(name, ("position", name))
    add("visible", ("visibility", "visible"))
    add("invisible", ("visibility", "hidden"))
    add("collapse", ("visibility", "collapse"))
    add("isolate", ("isolation", "isolate"))
    add("isolation-auto", ("isolation", "auto"))
    add("box-border", ("box-sizing", "border-box"))
    add("box-content", ("box-sizing", "content-box"))
    for value in ("auto", "hidden", "clip", "visible", "scroll"):
        add(f"overflow-{value}", ("overflow", value))
        add(f"overflow-x-{value}", ("overflow-x", value))
        add(f"overflow-y-{value}", ("overflow-y", value))
    for value in ("contain", "cover", "fill", "none", "scale-down"):
        add(f"object-{value}", ("object-fit", value))
    for value in ("bottom", "center", "left", "right", "top"):
        add(f"object-{value}", ("object-position", value))
    for value in ("left-bottom", "left-top", "right-bottom", "right-top"):
        add(f"object-{value}", ("object-position", value.replace("-", " ")))
    add("aspect-square", ("aspect-ratio", "1 / 1"))
    add("aspect-video", ("aspect-ratio", "16 / 9"))
    add("aspect-auto", ("aspect-ratio", "auto"))
    # Flexbox & grid
    add("flex-row", ("flex-direction", "row"))
    add("flex-row-reverse", ("flex-direction", "row-reverse"))
    add("flex-col", ("flex-direction", "column"))
    add("flex-col-reverse", ("flex-direction", "column-reverse"))
    add("flex-wrap", ("flex-wrap", "wrap"))
    add("flex-wrap-reverse", ("flex-wrap", "wrap-reverse"))
    add("flex-nowrap", ("flex-wrap", "nowrap"))
    add("flex-auto", ("flex", "auto"))
    add("flex-initial", ("flex", "0 auto"))
    add("flex-none", ("flex", "none"))
    add("grow", ("flex-grow", "1"))
    add("shrink", ("flex-shrink", "1"))
    add("order-first", ("order", "-9999"))
    add("order-last", ("order", "9999"))
    add("order-none", ("order", "0"))
    flex_align = {
        "start": "flex-start",
        "end": "flex-end",
        "center": "center",
        "baseline": "baseline",
        "stretch": "stretch",
    }
    distribute = {
        "between": "space-between",
        "around": "space-around",
        "evenly": "space-evenly",
        "normal": "normal",
    }
    for key, value in {**flex_align, **distribute}.items():
        if key != "baseline":
            add(f"justify-{key}", ("justify-content", value))
            add(f"content-{key}", ("align-content", value))
            add(f"place-content-{key}", ("place-content", value))
    for key, value in flex_align.items():
        add(f"items-{key}", ("align-items", value))
        add(f"self-{key}", ("align-self", value))
    add("self-auto", ("align-self", "auto"))
    for value in ("start", "end", "center", "stretch", "normal"):
        add(f"justify-items-{value}", ("justify-items", value))
        add(f"place-items-{value}", ("place-items", value))
    for value in ("auto", "start", "end", "center", "stretch"):
        add(f"justify-self-{value}", ("justify-self", value))
        add(f"place-self-{value}", ("place-self", value))
    add("grid-flow-row", ("grid-auto-flow", "row"))
    add("grid-flow-col", ("grid-auto-flow", "column"))
    add("grid-flow-dense", ("grid-auto-flow", "dense"))
    add("grid-flow-row-dense", ("grid-auto-flow", "row dense"))
    add("grid-flow-col-dense", ("grid-auto-flow", "column dense"))
    add("grid-cols-none", ("grid-template-columns", "none"))
    add("grid-rows-none", ("grid-template-rows", "none"))
    add("col-span-full", ("grid-column", "1 / -1"))
    add("row-span-full", ("grid-row", "1 / -1"))
    add("col-auto", ("grid-column", "auto"))
    add("row-auto", ("grid-row", "auto"))
    # Typography
    for value in ("left", "center", "right", "justify", "start", "end"):
        add(f"text-{value}", ("text-align", value))
    for value in ("uppercase", "lowercase", "capitalize"):
        add(value, ("text-transform", value))
    add("normal-case", ("text-transform", "none"))
    add("italic", ("font-style", "italic"))
    add("not-italic", ("font-style", "normal"))
    for value in ("underline", "overline", "line-through"):
        add(value, ("text-decoration-line", value))
    add("no-underline", ("text-decoration-line", "none"))
    for value in ("tabular", "proportional", "lining", "oldstyle"):
        add(f"{value}-nums", ("font-variant-numeric", f"{value}-nums"))
    add("normal-nums", ("font-variant-numeric", "normal"))
    add("slashed-zero", ("font-variant-numeric", "slashed-zero"))
    add("ordinal", ("font-variant-numeric", "ordinal"))
    for value in ("normal", "nowrap", "pre", "pre-line", "pre-wrap", "break-spaces"):
        add(f"whitespace-{value}", ("white-space", value))
    for value in ("wrap", "nowrap", "balance", "pretty"):
        add(f"text-{value}", ("text-wrap", value))
    add("break-normal", ("overflow-wrap", "normal"), ("word-break", "normal"))
    add("break-words", ("overflow-wrap", "break-word"))
    add("break-all", ("word-break", "break-all"))
    add("break-keep", ("word-break", "keep-all"))
    add("wrap-break-word", ("overflow-wrap", "break-word"))
    add("wrap-anywhere", ("overflow-wrap", "anywhere"))
    add("wrap-normal", ("overflow-wrap", "normal"))
    add(
        "truncate",
        ("overflow", "hidden"),
        ("text-overflow", "ellipsis"),
        ("white-space", "nowrap"),
    )
    add("text-ellipsis", ("text-overflow", "ellipsis"))
    add("text-clip", ("text-overflow", "clip"))
    for value in ("baseline", "top", "middle", "bottom", "text-top", "text-bottom"):
        add(f"align-{value}", ("vertical-align", value))
    add("align-sub", ("vertical-align", "sub"))
    add("align-super", ("vertical-align", "super"))
    add("list-none", ("list-style-type", "none"))
    add("list-disc", ("list-style-type", "disc"))
    add("list-decimal", ("list-style-type", "decimal"))
    add("list-inside", ("list-style-position", "inside"))
    add("list-outside", ("list-style-position", "outside"))
    # Backgrounds
    add("bg-none", ("background-image", "none"))
    for value in ("auto", "cover", "contain"):
        add(f"bg-{value}", ("background-size", value))
    for value in ("bottom", "center", "left", "right", "top"):
        add(f"bg-{value}", ("background-position", value))
    for value in ("left-bottom", "left-top", "right-bottom", "right-top"):
        add(f"bg-{value}", ("background-position", value.replace("-", " ")))
    for value in ("repeat", "no-repeat", "repeat-x", "repeat-y", "repeat-round", "repeat-space"):
        css = value.removeprefix("repeat-") if value.startswith("repeat-") else value
        add(f"bg-{value}", ("background-repeat", "round" if css == "round" else css))
    # Borders
    for value in ("solid", "dashed", "dotted", "double", "hidden", "none"):
        add(f"border-{value}", ("--tw-border-style", value), ("border-style", value))
    add("outline-none", ("outline", "2px solid transparent"))
    for value in ("solid", "dashed", "dotted", "double"):
        add(f"outline-{value}", ("outline-style", value))
    add("ring-inset", ("--tw-ring-inset", "inset"))
    # Transforms
    for key, value in {
        "center": "center",
        "top": "top",
        "top-right": "top right",
        "right": "right",
        "bottom-right": "bottom right",
        "bottom": "bottom",
        "bottom-left": "bottom left",
        "left": "left",
        "top-left": "top left",
    }.items():
        add(f"origin-{key}", ("transform-origin", value))
    add("transform-none", ("transform", "none"))
    # Content
    add("content-none", ("--tw-content", "none"), ("content", "none"))
    add(
        "sr-only",
        ("position", "absolute"),
        ("width", "1px"),
        ("height", "1px"),
        ("padding", "0"),
        ("margin", "-1px"),
        ("overflow", "hidden"),
        ("clip", "rect(0, 0, 0, 0)"),
        ("white-space", "nowrap"),
        ("border-width", "0"),
    )
    return table


_STATIC = _static()

# Valid utilities with nothing to paint on a still frame: accepted silently
_NOOP_PREFIXES = (
    "transition",
    "duration-",
    "ease-",
    "delay-",
    "cursor-",
    "select-",
    "pointer-events-",
    "touch-",
    "will-change-",
    "scroll-",
    "snap-",
    "appearance-",
    "resize",
)
_NOOP = {"antialiased", "subpixel-antialiased", "group", "peer", "container"}

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", re.IGNORECASE)
_RGB_RE = re.compile(
    r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*(?:[,/]\s*([\d.]+%?)\s*)?\)",
    re.IGNORECASE,
)
_ACCENT_N_RE = re.compile(r"accent-(\d+)")
_SHADOW_COLOR_RE = re.compile(
    r"(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color-mix|color|var)\([^()]*(?:\([^()]*\)[^()]*)*\)"
    r"|#[0-9a-fA-F]{3,8}\b|\bcurrentcolor\b|\btransparent\b",
    re.IGNORECASE,
)


def _srgb_to_oklch(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """sRGB (0-255) as OKLCH (L 0-1, C, H degrees)."""

    def linear(channel: float) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in rgb)
    lms = (
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in lms)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, b2), math.degrees(math.atan2(b2, a)) % 360


def _oklch_to_srgb(lightness: float, chroma: float, hue: float) -> RGB:
    """OKLCH as sRGB (0-255), clipped to the sRGB gamut."""
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def encode(channel: float) -> int:
        c = min(1.0, max(0.0, channel))
        return round((12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055) * 255)

    r, g, b2 = (encode(c) for c in linear)
    return (r, g, b2)


def _fmt(number: float, digits: int = 3) -> str:
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _parse_color(text: str) -> tuple[RGB, float] | None:
    """``#hex`` / ``rgb()`` as (RGB, alpha); None for anything else."""
    text = text.strip()
    if match := _HEX_RE.fullmatch(text):
        digits = match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)), alpha
    if match := _RGB_RE.fullmatch(text):
        r, g, b = (min(255, round(float(part))) for part in match.groups()[:3])
        raw = match.group(4)
        alpha = 1.0
        if raw:
            alpha = float(raw[:-1]) / 100 if raw.endswith("%") else float(raw)
        return (r, g, b), alpha
    return None


# Colour names -> Theme attribute; ``fg`` tones are the text roles
_ROLES = {
    "primary": "primary",
    "secondary": "secondary",
    "success": "success",
    "warning": "warning",
    "error": "error",
    "info": "info",
    "muted": "muted",
    "fg": "text_primary",
    "fg-2": "text_secondary",
    "fg-3": "text_tertiary",
    "bg": "background",
    "surface": "surface",
    "surface-variant": "surface_variant",
    "border": "border",
}
# Neutral tones derived from the primary text colour (htmldoc's --chip-bg...)
_DERIVED = {"chip": 0.08, "hairline": 0.10, "track": 0.12}
# Without a theme (a bare CellContext): the cell document's variables
_ROLE_VARS = {
    **{name: f"var(--{name})" for name in _ROLES},
    "fg": "var(--text-primary)",
    "fg-2": "var(--text-secondary)",
    "fg-3": "var(--text-tertiary)",
    "chip": "var(--chip-bg)",
    "hairline": "var(--hairline)",
    "track": "var(--track)",
}


def _is_accent(name: str) -> bool:
    return name == "accent" or bool(_ACCENT_N_RE.fullmatch(name))


@dataclass(frozen=True)
class _Env:
    """What a class compiles against: the cell's theme and slot."""

    theme: Any
    slot_index: int

    def role(self, name: str) -> str | None:
        """A theme colour role (or the cell accent) as a concrete CSS colour."""
        theme = self.theme
        if theme is None:
            return _ROLE_VARS.get(name) or ("var(--primary)" if _is_accent(name) else None)
        if name in _ROLES:
            return css_rgb(getattr(theme, _ROLES[name]))
        if name in _DERIVED:
            return css_rgba(theme.text_primary, _DERIVED[name])
        accent: RGB | None = None
        if name == "accent":
            accent = theme.get_accent_color(self.slot_index)
        elif match := _ACCENT_N_RE.fullmatch(name):
            accent = theme.accent_colors[int(match.group(1)) % len(theme.accent_colors)]
        return None if accent is None else css_rgb(accent)

    @property
    def monochrome(self) -> bool:
        return bool(self.theme is not None and getattr(self.theme, "monochrome", False))

    @property
    def dark(self) -> bool:
        if self.theme is None:
            return True
        return _srgb_to_oklch(self.theme.background)[0] < 0.5

    def ramp(self, lightness: float, alpha: float = 1.0) -> str:
        """A colour on a monochrome theme: its text ramp at ``lightness``.

        The ramp runs from black up to the theme's primary text colour, so
        ``text-white`` reads as the theme's brightest tone and
        ``bg-slate-900`` stays a dark fill.
        """
        top_l, top_c, top_h = _srgb_to_oklch(self.theme.text_primary)
        out_l = min(lightness, top_l)
        rgb = _oklch_to_srgb(out_l, top_c * (out_l / top_l if top_l else 0), top_h)
        return css_rgb(rgb) if alpha >= 1 else css_rgba(rgb, round(alpha, 3))


def _palette(name: str) -> tuple[float, str] | None:
    """``sky-400`` as (OKLCH lightness 0-1, sRGB CSS); None when not in the palette.

    Converted to sRGB here because Blitz paints ``oklch()`` inside
    ``box-shadow`` as red (backgrounds and gradients are fine), and a
    coloured glow is half of what a palette colour is for.
    """
    family, _, shade = name.rpartition("-")
    if family not in PALETTE or not shade.isdigit() or int(shade) not in SHADES:
        return None
    raw_l, chroma, hue = PALETTE[family][SHADES.index(int(shade))].split()
    lightness = float(raw_l.rstrip("%")) / 100
    return lightness, css_rgb(_oklch_to_srgb(lightness, float(chroma), float(hue)))


def _alpha(modifier: str | None) -> str | None:
    """An opacity modifier (``/50``, ``/[0.35]``, ``/[35%]``) as a percentage."""
    if modifier is None:
        return None
    if modifier.startswith("[") and modifier.endswith("]"):
        inner = modifier[1:-1]
        if inner.endswith("%"):
            return inner
        try:
            return f"{_fmt(float(inner) * 100)}%"
        except ValueError:
            return None
    try:
        return f"{_fmt(float(modifier))}%"
    except ValueError:
        return None


def _color(value: str, modifier: str | None, env: _Env) -> str | None:
    """A colour utility value as concrete CSS, with its opacity modifier."""
    css: str | None = None
    if value in ("inherit", "transparent"):
        css = value
    elif value == "current":
        css = "currentcolor"
    elif (role := env.role(value)) is not None:
        css = role
    elif value in ("white", "black"):
        css = env.ramp(1.0 if value == "white" else 0.0) if env.monochrome else value
    elif (shade := _palette(value)) is not None:
        lightness, srgb = shade
        css = env.ramp(lightness) if env.monochrome else srgb
    elif (inner := _arbitrary(value, "color")) is not None:
        css = inner
        if env.monochrome and inner not in ("transparent", "currentcolor", "inherit"):
            parsed = _parse_color(inner)
            if parsed is not None:
                rgb, alpha = parsed
                css = env.ramp(_srgb_to_oklch(rgb)[0], alpha)
            elif not inner.startswith("var("):
                css = env.role("accent")
    elif value.startswith("(--") and value.endswith(")"):
        css = f"var({value[1:-1]})"
    if css is None:
        return None
    if modifier is not None:
        percent = _alpha(modifier)
        if percent is None:
            return None
        css = f"color-mix(in oklab, {css} {percent}, transparent)"
    return css


_COLOR_PREFIXES = (
    "#",
    "rgb",
    "hsl",
    "oklch",
    "oklab",
    "lab(",
    "lch(",
    "hwb(",
    "color-mix(",
    "color(",
    "var(--",
)


def _looks_like_color(value: str) -> bool:
    """Whether an arbitrary ``[...]`` value is a colour (vs a length)."""
    lowered = value.lower()
    return bool(
        _parse_color(value)
        or lowered.startswith(_COLOR_PREFIXES)
        or lowered in ("transparent", "currentcolor", "white", "black", "red", "inherit")
    )


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------

_LENGTH_RE = re.compile(
    r"-?(?:\d+\.?\d*|\.\d+)(?:px|rem|em|%|vw|vh|vmin|vmax|ch|ex|dvh|dvw|svh|svw|lvh|lvw)?$"
)
_HINT_RE = re.compile(r"([a-z-]+):(.*)", re.DOTALL)


def _unescape_arbitrary(inner: str) -> str:
    """Underscores are spaces (``\\_`` a literal one), except inside url()."""
    out = []
    i = 0
    depth_url = 0
    while i < len(inner):
        if inner.startswith("url(", i):
            depth_url += 1
            out.append("url(")
            i += 4
            continue
        ch = inner[i]
        if depth_url:
            if ch == ")":
                depth_url -= 1
            out.append(ch)
        elif ch == "\\" and i + 1 < len(inner) and inner[i + 1] == "_":
            out.append("_")
            i += 1
        elif ch == "_":
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _arbitrary(value: str, kind: str | None = None) -> str | None:
    """The inside of ``[...]`` (type hint stripped), or None.

    ``kind`` filters on the hint (``[color:var(--x)]``) or, unhinted, on
    what the value looks like: ``"color"`` or ``"length"``.
    """
    if not (value.startswith("[") and value.endswith("]")) or len(value) < 3:
        return None
    inner = _unescape_arbitrary(value[1:-1])
    hint = None
    if (match := _HINT_RE.fullmatch(inner)) and not inner.startswith(("var(", "url(")):
        hint, inner = match.group(1), match.group(2)
        if hint in ("length", "size", "percentage", "number"):
            hint = "length"
    if kind is None:
        return inner
    if hint is not None:
        return inner if hint == kind else None
    if kind == "color":
        return inner if _looks_like_color(inner) else None
    if kind == "length":
        return None if _looks_like_color(inner) else inner
    return inner


def _px(number: float) -> str:
    return f"{_fmt(number)}px" if number else "0"


def _spacing(value: str, negative: bool = False) -> str | None:
    """Spacing-scale value: ``4`` -> 16px, ``0.75`` -> 3px, ``px``, ``[..]``."""
    result: str | None = None
    if value == "px":
        result = "1px"
    elif (arb := _arbitrary(value, "length")) is not None:
        result = arb
    elif value.startswith("(--") and value.endswith(")"):
        result = f"var({value[1:-1]})"
    else:
        try:
            number = float(value)
        except ValueError:
            return None
        if number < 0 or not math.isfinite(number) or (number * 4) % 1:
            return None
        result = _px(number * SPACING_PX)
    if negative and result:
        return f"calc({result} * -1)"
    return result


def _fraction(value: str, modifier: str | None) -> str | None:
    if modifier is None or not value.isdigit() or not modifier.isdigit() or modifier == "0":
        return None
    return f"{_fmt(int(value) / int(modifier) * 100, 6)}%"


def _size(
    value: str, modifier: str | None, axis: str, negative: bool = False, containers: bool = False
) -> str | None:
    """Width/height/inset value: spacing, fraction, keyword or arbitrary."""
    if (fraction := _fraction(value, modifier)) is not None:
        return f"calc({fraction} * -1)" if negative else fraction
    if modifier is not None:
        return None
    keywords = {
        "full": "100%",
        "auto": "auto",
        "min": "min-content",
        "max": "max-content",
        "fit": "fit-content",
        "screen": "100vw" if axis == "x" else "100vh",
        "dvw": "100vw",
        "svw": "100vw",
        "lvw": "100vw",
        "dvh": "100vh",
        "svh": "100vh",
        "lvh": "100vh",
        "none": "none",
    }
    if value in keywords:
        keyword = keywords[value]
        return f"calc({keyword} * -1)" if negative and value == "full" else keyword
    if containers and value in _CONTAINERS:
        return _CONTAINERS[value]
    return _spacing(value, negative)


def _split_modifier(value: str) -> tuple[str, str | None]:
    """``warning/50`` -> (``warning``, ``50``); slashes inside [] don't count."""
    depth = 0
    for index in range(len(value) - 1, -1, -1):
        ch = value[index]
        if ch in "])":
            depth += 1
        elif ch in "[(":
            depth -= 1
        elif ch == "/" and depth == 0:
            return value[:index], value[index + 1 :]
    return value, None


# ---------------------------------------------------------------------------
# Functional utilities: root -> handler(value, modifier, negative, env)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Rule:
    """One class's compiled CSS, before its variants wrap it."""

    decls: Decls
    order: int = 0  # shorthands before longhands (p before px before pt)
    child: str = ""  # selector suffix (space-*, divide-*)
    features: frozenset[str] = frozenset()


_HANDLERS: dict[str, Callable[[str, str | None, bool, _Env], _Rule | None]] = {}


def _handler(*roots: str) -> Callable[[Any], Any]:
    def register(func: Any) -> Any:
        for root in roots:
            _HANDLERS[root] = func
        return func

    return register


def _rule(*decls: tuple[str, str], order: int = 0, child: str = "", features: str = "") -> _Rule:
    return _Rule(
        tuple(decls),
        order=order,
        child=child,
        features=frozenset(features.split()) if features else frozenset(),
    )


_SIDES = {
    "": ("",),
    "x": ("-left", "-right"),
    "y": ("-top", "-bottom"),
    "t": ("-top",),
    "r": ("-right",),
    "b": ("-bottom",),
    "l": ("-left",),
    "s": ("-left",),
    "e": ("-right",),
}


def _side_order(side: str) -> int:
    return 0 if side == "" else 1 if side in ("x", "y") else 2


def _register_box(prop: str, short: str, allow_auto: bool) -> None:
    for side, suffixes in _SIDES.items():

        def handle(
            value: str,
            modifier: str | None,
            negative: bool,
            env: _Env,
            suffixes: tuple[str, ...] = suffixes,
            side: str = side,
        ) -> _Rule | None:
            if modifier is not None:
                return None
            if allow_auto and value == "auto":
                css = "auto"
            else:
                css = _spacing(value, negative and allow_auto)
            if css is None:
                return None
            return _rule(*((f"{prop}{s}", css) for s in suffixes), order=_side_order(side))

        _HANDLERS[f"{short}{side}"] = handle


_register_box("padding", "p", allow_auto=False)
_register_box("margin", "m", allow_auto=True)


def _gap_for(prop: str, order: int) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        css = None if modifier or negative else _spacing(value)
        return None if css is None else _rule((prop, css), order=order)

    return handle


_HANDLERS["gap"] = _gap_for("gap", 0)
_HANDLERS["gap-x"] = _gap_for("column-gap", 1)
_HANDLERS["gap-y"] = _gap_for("row-gap", 1)


def _space_for(axis: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    prop = "margin-right" if axis == "x" else "margin-bottom"

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        css = None if modifier else _spacing(value, negative)
        return None if css is None else _rule((prop, css), child=" > :not(:last-child)")

    return handle


_HANDLERS["space-x"] = _space_for("x")
_HANDLERS["space-y"] = _space_for("y")


def _sizing(
    props: tuple[str, ...], axis: str, containers: bool = False
) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative:
            return None
        if value == "none" and not props[0].startswith("max"):
            return None
        css = _size(value, modifier, axis, containers=containers)
        return None if css is None else _rule(*((p, css) for p in props))

    return handle


_HANDLERS["w"] = _sizing(("width",), "x", containers=True)
_HANDLERS["h"] = _sizing(("height",), "y")
_HANDLERS["size"] = _sizing(("width", "height"), "x")
_HANDLERS["min-w"] = _sizing(("min-width",), "x", containers=True)
_HANDLERS["min-h"] = _sizing(("min-height",), "y")
_HANDLERS["max-w"] = _sizing(("max-width",), "x", containers=True)
_HANDLERS["max-h"] = _sizing(("max-height",), "y")


def _inset_for(
    props: tuple[str, ...], order: int
) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        css = _size(value, modifier, "x", negative)
        if css is None or value in ("min", "max", "fit", "screen", "none"):
            return None
        return _rule(*((p, css) for p in props), order=order)

    return handle


_HANDLERS["inset"] = _inset_for(("top", "right", "bottom", "left"), 0)
_HANDLERS["inset-x"] = _inset_for(("left", "right"), 1)
_HANDLERS["inset-y"] = _inset_for(("top", "bottom"), 1)
for _side in ("top", "right", "bottom", "left"):
    _HANDLERS[_side] = _inset_for((_side,), 2)
_HANDLERS["start"] = _inset_for(("left",), 2)
_HANDLERS["end"] = _inset_for(("right",), 2)


def _integer(value: str) -> str | None:
    if value.isdigit():
        return value
    return _arbitrary(value)


@_handler("z")
def _z(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = "auto" if value == "auto" else _integer(value)
    if css is None or modifier:
        return None
    return _rule(("z-index", f"calc({css} * -1)" if negative else css))


@_handler("order")
def _order(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = _integer(value)
    if css is None or modifier:
        return None
    return _rule(("order", f"calc({css} * -1)" if negative else css))


@_handler("opacity")
def _opacity(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative or modifier:
        return None
    if value.isdigit() and int(value) <= 100:
        return _rule(("opacity", f"{value}%"))
    css = _arbitrary(value)
    return None if css is None else _rule(("opacity", css))


@_handler("aspect")
def _aspect(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if value.isdigit() and modifier and modifier.isdigit():
        return _rule(("aspect-ratio", f"{value} / {modifier}"))
    css = None if modifier else _arbitrary(value)
    return None if css is None else _rule(("aspect-ratio", css))


@_handler("flex")
def _flex(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    if value.isdigit() and modifier is None:
        return _rule(("flex", value))
    if (fraction := _fraction(value, modifier)) is not None:
        return _rule(("flex", f"{fraction}"))
    css = None if modifier else _arbitrary(value)
    return None if css is None else _rule(("flex", css))


def _number_prop(prop: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        css = None if modifier or negative else _integer(value)
        return None if css is None else _rule((prop, css))

    return handle


_HANDLERS["grow"] = _number_prop("flex-grow")
_HANDLERS["shrink"] = _number_prop("flex-shrink")


@_handler("basis")
def _basis(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = None if negative else _size(value, modifier, "x", containers=True)
    return None if css is None else _rule(("flex-basis", css))


def _grid_template(prop: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative or modifier:
            return None
        if value.isdigit() and int(value) > 0:
            return _rule((prop, f"repeat({value}, minmax(0, 1fr))"))
        if value == "subgrid":
            return _rule((prop, "subgrid"))
        css = _arbitrary(value)
        return None if css is None else _rule((prop, css))

    return handle


_HANDLERS["grid-cols"] = _grid_template("grid-template-columns")
_HANDLERS["grid-rows"] = _grid_template("grid-template-rows")


def _grid_line(prop: str, kind: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if modifier:
            return None
        if kind == "span":
            css = _integer(value)
            return None if css is None or negative else _rule((prop, f"span {css} / span {css}"))
        css = "auto" if value == "auto" else _integer(value)
        if css is None:
            return None
        return _rule((prop, f"calc({css} * -1)" if negative else css))

    return handle


_HANDLERS["col-span"] = _grid_line("grid-column", "span")
_HANDLERS["row-span"] = _grid_line("grid-row", "span")
_HANDLERS["col-start"] = _grid_line("grid-column-start", "line")
_HANDLERS["col-end"] = _grid_line("grid-column-end", "line")
_HANDLERS["row-start"] = _grid_line("grid-row-start", "line")
_HANDLERS["row-end"] = _grid_line("grid-row-end", "line")
_HANDLERS["col"] = lambda v, m, n, e: (
    None if m or n or (css := _arbitrary(v)) is None else _rule(("grid-column", css))
)
_HANDLERS["row"] = lambda v, m, n, e: (
    None if m or n or (css := _arbitrary(v)) is None else _rule(("grid-row", css))
)


# Typography -----------------------------------------------------------------


def _line_height(modifier: str) -> str | None:
    if modifier in _LEADING:
        return _LEADING[modifier]
    return _spacing(modifier) if not modifier.startswith("[") else _arbitrary(modifier)


@_handler("text")
def _text(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    if value in _TEXT_SIZES:
        size, leading = _TEXT_SIZES[value]
        if modifier is not None:
            line = _line_height(modifier)
            return None if line is None else _rule(("font-size", size), ("line-height", line))
        return _rule(
            ("font-size", size),
            ("line-height", f"var(--tw-leading, {leading})"),
            features="leading",
        )
    if (length := _arbitrary(value, "length")) is not None:
        if modifier is not None:
            line = _line_height(modifier)
            return None if line is None else _rule(("font-size", length), ("line-height", line))
        return _rule(("font-size", length))
    color = _color(value, modifier, env)
    return None if color is None else _rule(("color", color))


@_handler("font")
def _font(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative or modifier:
        return None
    if value in _FONT_WEIGHTS:
        return _rule(("font-weight", _FONT_WEIGHTS[value]))
    if value in _FONT_FAMILIES:
        return _rule(("font-family", _FONT_FAMILIES[value]))
    css = _arbitrary(value)
    if css is None:
        return None
    if css.isdigit():
        return _rule(("font-weight", css))
    return _rule(("font-family", css))


@_handler("tracking")
def _tracking(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = _TRACKING.get(value) or _arbitrary(value)
    if css is None or modifier:
        return None
    return _rule(("letter-spacing", f"calc({css} * -1)" if negative else css))


@_handler("leading")
def _leading(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative or modifier:
        return None
    css = _line_height(value)
    if css is None:
        return None
    return _rule(("--tw-leading", css), ("line-height", css), features="leading")


@_handler("indent")
def _indent(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = None if modifier else _spacing(value, negative)
    return None if css is None else _rule(("text-indent", css))


@_handler("line-clamp")
def _line_clamp(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    return None  # Blitz has no -webkit-line-clamp: truncate in Jinja instead


@_handler("decoration")
def _decoration(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    if value.isdigit() and modifier is None:
        return _rule(("text-decoration-thickness", f"{value}px"))
    color = _color(value, modifier, env)
    return None if color is None else _rule(("text-decoration-color", color))


@_handler("underline-offset")
def _underline_offset(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if modifier:
        return None
    css = f"{value}px" if value.isdigit() else _arbitrary(value)
    return None if css is None else _rule(("text-underline-offset", css))


# Backgrounds & gradients --------------------------------------------------------


def _gradient(kind: str, position: str) -> _Rule:
    return _rule(
        ("--tw-gradient-position", position),
        ("background-image", f"{kind}(var(--tw-gradient-stops))"),
        features="gradient",
    )


@_handler("bg")
def _bg(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    color = _color(value, modifier, env)
    if color is not None:
        return _rule(("background-color", color))
    css = None if modifier else _arbitrary(value)
    if css is None:
        return None
    hint = _HINT_RE.fullmatch(_unescape_arbitrary(value[1:-1]))
    if hint and hint.group(1) in ("size", "length"):
        return _rule(("background-size", css))
    if hint and hint.group(1) == "position":
        return _rule(("background-position", css))
    return _rule(("background-image", css))


def _linear(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if modifier:
        return None
    if value.startswith("to-") and value[3:] in _DIRECTIONS:
        return None if negative else _gradient("linear-gradient", _DIRECTIONS[value[3:]])
    if value.isdigit():
        return _gradient("linear-gradient", f"{'-' if negative else ''}{value}deg")
    css = _arbitrary(value)
    if css is None or negative:
        return None
    if "," in css:
        return _rule(("background-image", f"linear-gradient({css})"))
    return _gradient("linear-gradient", css)


_HANDLERS["bg-linear"] = _linear
_HANDLERS["bg-gradient"] = _linear  # v3 spelling: bg-gradient-to-r


@_handler("bg-radial")
def _radial(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if value == "" and modifier is None and not negative:
        return _gradient("radial-gradient", "ellipse at center")
    css = None if modifier or negative else _arbitrary(value)
    if css is None:
        return None
    if "," in css:
        return _rule(("background-image", f"radial-gradient({css})"))
    return _gradient("radial-gradient", css)


@_handler("bg-conic")
def _conic(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if modifier:
        return None
    if value == "" and not negative:
        return _gradient("conic-gradient", "from 0deg")
    if value.isdigit():
        return _gradient("conic-gradient", f"from {'-' if negative else ''}{value}deg")
    css = None if negative else _arbitrary(value)
    if css is None:
        return None
    if "," in css:
        return _rule(("background-image", f"conic-gradient({css})"))
    return _gradient("conic-gradient", css)


def _stop(which: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative:
            return None
        if value.endswith("%") and value[:-1].isdigit() and modifier is None:
            return _rule((f"--tw-gradient-{which}-position", value), features="gradient")
        position = _arbitrary(value, "length")
        if position is not None and modifier is None:
            return _rule((f"--tw-gradient-{which}-position", position), features="gradient")
        color = _color(value, modifier, env)
        if color is None:
            return None
        if which == "via":
            return _rule(
                ("--tw-gradient-via", color),
                ("--tw-gradient-via-stops", _GRADIENT_VIA_STOPS),
                ("--tw-gradient-stops", "var(--tw-gradient-via-stops)"),
                order=1,
                features="gradient",
            )
        return _rule(
            (f"--tw-gradient-{which}", color),
            ("--tw-gradient-stops", _GRADIENT_STOPS),
            features="gradient",
        )

    return handle


_HANDLERS["from"] = _stop("from")
_HANDLERS["via"] = _stop("via")
_HANDLERS["to"] = _stop("to")


# Borders, outlines, radii ------------------------------------------------------


def _border_for(side: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    suffixes = _SIDES[side]

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative:
            return None
        width = None
        if modifier is None:
            if value == "":
                width = "1px"
            elif value.isdigit():
                width = f"{value}px"
            else:
                width = _arbitrary(value, "length")
        if width is not None:
            return _rule(
                *((f"border{s}-style", "var(--tw-border-style)") for s in suffixes),
                *((f"border{s}-width", width) for s in suffixes),
                order=_side_order(side),
                features="border",
            )
        color = _color(value, modifier, env)
        if color is None:
            return None
        return _rule(*((f"border{s}-color", color) for s in suffixes), order=_side_order(side) + 3)

    return handle


for _border_side in _SIDES:
    _HANDLERS["border" + (f"-{_border_side}" if _border_side else "")] = _border_for(_border_side)


def _divide_for(axis: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    prop = "border-right" if axis == "x" else "border-bottom"

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative or modifier:
            return None
        width = "1px" if value == "" else f"{value}px" if value.isdigit() else None
        if width is None:
            return None
        return _rule(
            (f"{prop}-style", "var(--tw-border-style)"),
            (f"{prop}-width", width),
            child=" > :not(:last-child)",
            features="border",
        )

    return handle


_HANDLERS["divide-x"] = _divide_for("x")
_HANDLERS["divide-y"] = _divide_for("y")


@_handler("divide")
def _divide(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    color = None if negative else _color(value, modifier, env)
    if color is None:
        return None
    return _rule(("border-color", color), child=" > :not(:last-child)")


@_handler("outline")
def _outline(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    if modifier is None and (value == "" or value.isdigit()):
        width = "1px" if value == "" else f"{value}px"
        return _rule(("outline-style", "solid"), ("outline-width", width))
    if modifier is None and (width := _arbitrary(value, "length")) is not None:
        return _rule(("outline-style", "solid"), ("outline-width", width))
    color = _color(value, modifier, env)
    return None if color is None else _rule(("outline-color", color))


_CORNERS = {
    "": ("",),
    "t": ("-top-left", "-top-right"),
    "r": ("-top-right", "-bottom-right"),
    "b": ("-bottom-right", "-bottom-left"),
    "l": ("-top-left", "-bottom-left"),
    "s": ("-top-left", "-bottom-left"),
    "e": ("-top-right", "-bottom-right"),
    "tl": ("-top-left",),
    "tr": ("-top-right",),
    "br": ("-bottom-right",),
    "bl": ("-bottom-left",),
    "ss": ("-top-left",),
    "se": ("-top-right",),
    "ee": ("-bottom-right",),
    "es": ("-bottom-left",),
}


def _rounded_for(corner: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    corners = _CORNERS[corner]
    order = 0 if corner == "" else 1 if len(corner) == 1 else 2

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative or modifier:
            return None
        css = _RADII.get(value) or _arbitrary(value)
        if css is None:
            return None
        if corner == "":
            return _rule(("border-radius", css))
        return _rule(*((f"border{c}-radius", css) for c in corners), order=order)

    return handle


for _corner in _CORNERS:
    _HANDLERS["rounded" + (f"-{_corner}" if _corner else "")] = _rounded_for(_corner)


# Shadows & rings ---------------------------------------------------------------


def _shadow_colors(value: str, variable: str) -> str:
    """Each shadow's colour behind ``var(--tw-*-color, ...)``, so
    ``shadow-warning/50`` can recolour it; a shadow without one gets
    ``currentcolor``."""
    parts = []
    for raw in _split_top_level(value, ","):
        shadow = raw.strip()
        match = _SHADOW_COLOR_RE.search(shadow)
        if shadow in ("none", "0 0 #0000"):
            parts.append(shadow)
        elif match:
            start, end = match.span()
            parts.append(f"{shadow[:start]}var({variable}, {match.group(0)}){shadow[end:]}")
        else:
            parts.append(f"{shadow} var({variable}, currentcolor)")
    return ", ".join(parts)


def _split_top_level(value: str, sep: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for index, ch in enumerate(value):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def _shadow_for(kind: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    variable = "--tw-shadow" if kind == "shadow" else "--tw-inset-shadow"
    sizes = _SHADOWS if kind == "shadow" else _INSET_SHADOWS

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative:
            return None
        shadow = None
        if modifier is None:
            if value == "none":
                shadow = "0 0 #0000"
            elif value in sizes:
                shadow = _shadow_colors(sizes[value], f"{variable}-color")
            elif (css := _arbitrary(value, "length")) is not None:
                if kind == "inset-shadow" and not css.startswith("inset"):
                    css = _split_top_level(css, ",")
                    css = ", ".join(f"inset {part.strip()}" for part in css)
                shadow = _shadow_colors(css, f"{variable}-color")
        if shadow is not None:
            return _rule((variable, shadow), ("box-shadow", _BOX_SHADOW), features="shadow")
        color = _color(value, modifier, env)
        if color is None:
            return None
        return _rule((f"{variable}-color", color), order=1, features="shadow")

    return handle


_HANDLERS["shadow"] = _shadow_for("shadow")
_HANDLERS["inset-shadow"] = _shadow_for("inset-shadow")


def _ring_for(kind: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    variable = "--tw-ring" if kind == "ring" else "--tw-inset-ring"

    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if negative:
            return None
        width = None
        if modifier is None:
            if value == "":
                width = "1px"
            elif value.isdigit():
                width = f"{value}px"
            else:
                width = _arbitrary(value, "length")
        if width is not None:
            prefix = "var(--tw-ring-inset,) " if kind == "ring" else "inset "
            shadow = f"{prefix}0 0 0 {width} var({variable}-color, currentcolor)"
            return _rule(
                (f"{variable}-shadow", shadow), ("box-shadow", _BOX_SHADOW), features="shadow"
            )
        color = _color(value, modifier, env)
        if color is None:
            return None
        return _rule((f"{variable}-color", color), order=1, features="shadow")

    return handle


_HANDLERS["ring"] = _ring_for("ring")
_HANDLERS["inset-ring"] = _ring_for("inset-ring")


# Transforms --------------------------------------------------------------------


def _translate_for(axes: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        css = _size(value, modifier, "x", negative)
        if css is None or value in ("auto", "min", "max", "fit", "none"):
            return None
        return _rule(
            *((f"--tw-translate-{axis}", css) for axis in axes),
            ("translate", "var(--tw-translate-x) var(--tw-translate-y)"),
            features="translate",
        )

    return handle


_HANDLERS["translate"] = _translate_for("xy")
_HANDLERS["translate-x"] = _translate_for("x")
_HANDLERS["translate-y"] = _translate_for("y")


def _scale_for(axes: str) -> Callable[[str, str | None, bool, _Env], _Rule | None]:
    def handle(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
        if modifier:
            return None
        if value.isdigit():
            css = f"{value}%"
        elif (arb := _arbitrary(value)) is not None:
            css = arb
        else:
            return None
        if negative:
            css = f"calc({css} * -1)"
        return _rule(
            *((f"--tw-scale-{axis}", css) for axis in axes),
            ("scale", "var(--tw-scale-x) var(--tw-scale-y)"),
            features="scale",
        )

    return handle


_HANDLERS["scale"] = _scale_for("xy")
_HANDLERS["scale-x"] = _scale_for("x")
_HANDLERS["scale-y"] = _scale_for("y")


@_handler("rotate")
def _rotate(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if modifier:
        return None
    css = f"{value}deg" if value.replace(".", "", 1).isdigit() else _arbitrary(value)
    if css is None:
        return None
    return _rule(("rotate", f"calc({css} * -1)" if negative else css))


@_handler("origin")
def _origin(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = None if modifier or negative else _arbitrary(value)
    return None if css is None else _rule(("transform-origin", css))


# Animation, SVG, content, misc -----------------------------------------------------


@_handler("animate")
def _animate(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative or modifier:
        return None
    css = _ANIMATIONS.get(value) or _arbitrary(value)
    if css is None:
        return None
    keyframes = " ".join(
        f"keyframes:{name}" for name in _KEYFRAMES if re.search(rf"\b{name}\b", css)
    )
    return _rule(("animation", css), features=keyframes)


@_handler("fill")
def _fill(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if value == "none" and modifier is None:
        return _rule(("fill", "none"))
    color = None if negative else _color(value, modifier, env)
    return None if color is None else _rule(("fill", color))


@_handler("stroke")
def _stroke(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if negative:
        return None
    if value == "none" and modifier is None:
        return _rule(("stroke", "none"))
    if value.isdigit() and modifier is None:
        return _rule(("stroke-width", value))
    if modifier is None and (width := _arbitrary(value, "length")) is not None:
        return _rule(("stroke-width", width))
    color = _color(value, modifier, env)
    return None if color is None else _rule(("stroke", color))


@_handler("content")
def _content(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    css = None if modifier or negative else _arbitrary(value)
    if css is None:
        return None
    return _rule(("--tw-content", css), ("content", "var(--tw-content)"), features="content")


@_handler("mask")
def _mask(value: str, modifier: str | None, negative: bool, env: _Env) -> _Rule | None:
    if value == "none" and modifier is None:
        return _rule(("mask-image", "none"))
    css = None if modifier or negative else _arbitrary(value)
    return None if css is None else _rule(("mask-image", css))


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------

_PSEUDO_CLASSES = {
    "first": ":first-child",
    "last": ":last-child",
    "only": ":only-child",
    "odd": ":nth-child(odd)",
    "even": ":nth-child(even)",
    "first-of-type": ":first-of-type",
    "last-of-type": ":last-of-type",
    "only-of-type": ":only-of-type",
    "empty": ":empty",
}
_PSEUDO_ELEMENTS = {
    "before": "::before",
    "after": "::after",
    "first-letter": "::first-letter",
    "first-line": "::first-line",
}
_BREAKPOINTS = {"sm": "640px", "md": "768px", "lg": "1024px", "xl": "1280px", "2xl": "1536px"}
# Cell-size variants, the fluid kit's .hide-* thresholds. Each is a list
# of nested @media levels; a level may be an OR list.
_CELL_MEDIA = {
    "short": ("(max-height: 99px)",),
    "narrow": ("(max-width: 99px)",),
    "small": ("(max-height: 129px), (max-width: 129px)",),
    "not-short": ("not all and (max-height: 99px)",),
    "not-narrow": ("not all and (max-width: 99px)",),
    "not-small": ("not all and (max-height: 129px)", "not all and (max-width: 129px)"),
    "landscape": ("(orientation: landscape)",),
    "portrait": ("(orientation: portrait)",),
}
# Interaction and environment variants that never match a display
_NEVER = {
    "hover",
    "focus",
    "focus-within",
    "focus-visible",
    "active",
    "visited",
    "target",
    "disabled",
    "enabled",
    "checked",
    "indeterminate",
    "required",
    "invalid",
    "valid",
    "placeholder",
    "placeholder-shown",
    "autofill",
    "read-only",
    "open",
    "inert",
    "selection",
    "print",
    "motion-reduce",
    "contrast-more",
    "contrast-less",
    "forced-colors",
    "inverted-colors",
    "pointer-fine",
    "pointer-coarse",
}
_ALWAYS = {"motion-safe", "noscript", "pointer-none"}


@dataclass
class _Variants:
    """The variants applied to one class, in order."""

    selector: str  # "{}" is the class selector
    media: list[str] = field(default_factory=list)
    pseudo_element: bool = False


class _NeverMatchesError(Exception):
    """A variant that can never match on a display: drop the class."""


def _apply_variant(  # noqa: PLR0911 - one exit per kind of variant
    name: str, state: _Variants, env: _Env
) -> bool:
    """Apply ``name`` to ``state``; False when it isn't a known variant."""
    if name in _NEVER or name.startswith(("group-", "peer-", "aria-", "data-", "has-")):
        raise _NeverMatchesError
    if name in _ALWAYS:
        return True
    if name == "dark":
        if not env.dark:
            raise _NeverMatchesError
        return True
    if name in _PSEUDO_CLASSES:
        state.selector += _PSEUDO_CLASSES[name]
        return True
    if name.startswith("not-") and name[4:] in _PSEUDO_CLASSES:
        state.selector += f":not({_PSEUDO_CLASSES[name[4:]]})"
        return True
    if name in _PSEUDO_ELEMENTS:
        state.selector += _PSEUDO_ELEMENTS[name]
        state.pseudo_element = name in ("before", "after")
        return True
    if name == "*":
        state.selector = f":is({state.selector} > *)"
        return True
    if name in _CELL_MEDIA:
        state.media.extend(_CELL_MEDIA[name])
        return True
    if name in _BREAKPOINTS:
        state.media.append(f"(min-width: {_BREAKPOINTS[name]})")
        return True
    if name.startswith("max-") and name[4:] in _BREAKPOINTS:
        state.media.append(f"not all and (min-width: {_BREAKPOINTS[name[4:]]})")
        return True
    for prefix, template in (("min-", "({})"), ("max-", "not all and ({})")):
        if name.startswith(prefix) and (arb := _arbitrary(name[len(prefix) :])) is not None:
            state.media.append(template.format(f"min-width: {arb}"))
            return True
    if (arb := _arbitrary(name)) is not None and "&" in arb:
        state.selector = arb.replace("&", state.selector)
        return True
    return False


# ---------------------------------------------------------------------------
# Compiling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Compiled:
    """One class's finished CSS block and the shared CSS it needs."""

    css: str
    media: tuple[str, ...]
    order: int
    features: frozenset[str]


def _split_variants(token: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for index, ch in enumerate(token):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == ":" and depth == 0:
            parts.append(token[start:index])
            start = index + 1
    parts.append(token[start:])
    return parts


def _escape(token: str) -> str:
    """``token`` as a CSS class selector (CSS.escape)."""
    out = []
    for index, ch in enumerate(token):
        if ch.isascii() and (ch.isalnum() or ch in "-_"):
            if index == 0 and ch.isdigit():
                out.append(f"\\{ord(ch):x} ")
            else:
                out.append(ch)
        else:
            out.append("\\" + ch)
    return "." + "".join(out)


def _utility(name: str, env: _Env) -> _Rule | None:
    """A utility (variants and ``!`` removed) as its rule, or None."""
    if name in _NOOP or name.startswith(_NOOP_PREFIXES):
        return _Rule(())
    if name in _STATIC:
        decls = _STATIC[name]
        features = frozenset("border" for p, _ in decls if p == "--tw-border-style")
        return _Rule(decls, features=features)
    if name.startswith("[") and name.endswith("]") and ":" in name:
        prop, _, value = name[1:-1].partition(":")
        if re.fullmatch(r"(?:--)?[a-zA-Z][a-zA-Z0-9-]*", prop) and value:
            return _rule((prop, _unescape_arbitrary(value)))
        return None
    negative = name.startswith("-")
    if negative:
        name = name[1:]
    # Longest root first: border-t-2 is border-t + 2, not border + t-2
    candidates = [(name, "")] + [
        (name[:index], name[index + 1 :])
        for index in range(len(name) - 1, 0, -1)
        if name[index] == "-"
    ]
    for root, value in candidates:
        handler = _HANDLERS.get(root)
        if handler is None:
            continue
        raw, modifier = _split_modifier(value)
        rule = handler(raw, modifier, negative, env)
        if rule is not None:
            return rule
    return None


# A class that is valid but paints nothing here (hover:..., transition)
_DROPPED = _Compiled("", (), 0, frozenset())


@lru_cache(maxsize=4096)
def _compile(token: str, env: _Env) -> _Compiled | None:
    """``token`` compiled; None when unknown, ``_DROPPED`` when it paints nothing."""
    *variants, name = _split_variants(token)
    important = False
    if name.endswith("!"):
        name, important = name[:-1], True
    elif name.startswith("!"):
        name, important = name[1:], True
    state = _Variants("{}")
    try:
        for variant in variants:
            if not _apply_variant(variant, state, env):
                return None
    except _NeverMatchesError:
        return _DROPPED
    rule = _utility(name, env)
    if rule is None:
        return None
    if not rule.decls:
        return _DROPPED
    decls = list(rule.decls)
    if state.pseudo_element and not any(p == "content" for p, _ in decls):
        decls.insert(0, ("content", "var(--tw-content)"))
    features = rule.features | ({"content"} if state.pseudo_element else frozenset())
    bang = " !important" if important else ""
    body = "; ".join(f"{prop}: {value}{bang}" for prop, value in decls)
    selector = state.selector.replace("{}", _escape(token)) + rule.child
    return _Compiled(f"{selector} {{ {body}; }}", tuple(state.media), rule.order, features)


@lru_cache(maxsize=1)
def _kit_classes() -> frozenset[str]:
    """The fluid kit's and card primitives' own classes (``icon``, ``t-hero``, ...).

    The drawing helpers emit them, and templates may use them alongside
    utilities: they are not unknown utilities.
    """
    from ..htmldoc import FLUID_KIT_CSS  # noqa: PLC0415
    from ._card import CARD_CSS  # noqa: PLC0415

    # .root: the cell document's own wrapper (build_cell_document)
    kit = re.findall(r"\.([a-zA-Z][\w-]*)", FLUID_KIT_CSS + CARD_CSS)
    return frozenset([*kit, "root"])


_CLASS_ATTR_RE = re.compile(r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)


def class_tokens(html: str) -> list[str]:
    """Every class token in ``html``, in first-seen order."""
    seen: dict[str, None] = {}
    for double, single in _CLASS_ATTR_RE.findall(html):
        for token in (double or single).split():
            seen.setdefault(token, None)
    return list(seen)


def _property_css(features: set[str]) -> str:
    lines = []
    for feature in sorted(features):
        if feature.startswith("keyframes:"):
            lines.append(_KEYFRAMES[feature.split(":", 1)[1]])
            continue
        for name, initial in _PROPERTIES[feature]:
            init = f" initial-value: {initial};" if initial is not None else ""
            lines.append(f'@property {name} {{ syntax: "*"; inherits: false;{init} }}')
    return "\n".join(lines)


_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_CSS_CLASS_RE = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


def _style_classes(html: str) -> set[str]:
    """Class names the document's own ``<style>`` blocks define (``.big``)."""
    return {
        name for block in _STYLE_BLOCK_RE.findall(html) for name in _CSS_CLASS_RE.findall(block)
    }


def compile_utilities(html: str, ctx: CellContext) -> tuple[str, list[str]]:
    """CSS for the utility classes ``html`` uses, and the classes it doesn't know.

    A class the template styles itself (``<style>.big {...}</style>``) is
    not unknown, even though no utility has that name.

    Rules come out in a stable order (shorthands before their longhands,
    media rules last), whatever order the template lists its classes in.
    """
    env = _Env(ctx.theme, ctx.slot_index)
    compiled: list[tuple[int, _Compiled]] = []
    unknown: list[str] = []
    features: set[str] = set()
    kit = _kit_classes() | _style_classes(html)
    for index, token in enumerate(class_tokens(html)):
        if token in kit:
            continue
        result = _compile(token, env)
        if result is None:
            unknown.append(token)
        elif result is not _DROPPED:
            compiled.append((index, result))
            features |= result.features
    compiled.sort(key=lambda item: (bool(item[1].media), item[1].media, item[1].order, item[0]))
    lines = []
    for _, item in compiled:
        css = item.css
        for query in reversed(item.media):
            css = f"@media {query} {{ {css} }}"
        lines.append(css)
    return "\n".join(filter(None, [_property_css(features), *lines])), unknown


def with_utilities(fragment: str, ctx: CellContext) -> str:
    """``fragment`` with the light reset and its utility classes' CSS prepended.

    The ``<style>`` comes first, so a template's own ``<style>`` rules
    still win over a utility of the same specificity.
    """
    css, unknown = compile_utilities(fragment, ctx)
    if unknown:
        _LOGGER.debug("HTML widget: no utility for class(es) %s", ", ".join(unknown))
    return f"<style>\n{PREFLIGHT_CSS}{css}\n</style>{fragment}"
