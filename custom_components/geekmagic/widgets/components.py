"""Declarative component system for widget rendering.

This module provides a React-like component tree system where widgets
declare WHAT to show (component trees) and the layout system figures out
HOW to arrange it.

Example usage:
    def render(self, ctx, state) -> Component:
        return Column(children=[
            Text("75%", font="medium", bold=True),  # Uses THEME_TEXT_PRIMARY by default
            Bar(percent=75, color=COLOR_CYAN),
            Text("CPU", font="tiny", color=THEME_TEXT_SECONDARY),
        ])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Literal

from ._flex import (
    AUTO,
    PCT,
    AlignItems,
    Edge,
    FlexDirection,
    JustifyContent,
    Node,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext

# Type aliases
Color = tuple[int, int, int]

# =============================================================================
# Design system — colour rules for widget authors
# =============================================================================
# Apply these consistently across every widget so themes feel coherent and a
# user moving from one widget to another never sees an unexplained shift.
#
#   1. Caption / label  → THEME_TEXT_SECONDARY (or TEXT_TERTIARY in dense)
#   2. Hero value       → THEME_TEXT_PRIMARY (white) by *default*
#                         Use a role tint instead ONLY when one of these
#                         narrow exceptions applies:
#                           a) Gauge family (Bar / Ring / Arc) where the
#                              value matches the gauge's accent — the value
#                              and the fill read as one visual unit.
#                           b) Status state where the colour IS the meaning
#                              (success=green, error=red, etc.).
#                           c) Mode chip (e.g. climate "HEATING") where the
#                              tint reinforces the hvac-action label.
#                         Weather temp, climate hero temp, entity value,
#                         clock time, multi-progress hero, etc. all use
#                         text_primary — the *icon* carries the semantic
#                         tint instead.
#   3. Icon / accent / ring fill / bar fill → role tint
#                         (THEME_WARNING for hot/heating, THEME_INFO for
#                         cool/cooling/water, THEME_SUCCESS / ERROR / etc.)
#   4. Dim track / soft fill → ctx.track_color(tint) (theme-tinted track)
#
# Sentinel values for theme-aware colors. These are resolved at render time
# to the theme's actual colors via `_resolve_color()` (and a parallel copy
# in render_context.py). Negative-channel tuples are safe sentinels because
# legitimate RGB values are 0..255.
#
# Whenever you find yourself reaching for SYSTEM_BLUE / SYSTEM_ORANGE / etc.
# inside a widget, use the matching role sentinel below instead — themes
# (especially candy/retro/neon) ship their own palette and a hardcoded
# system color will look out of place.
THEME_TEXT_PRIMARY: Color = (-1, -1, -1)
THEME_TEXT_SECONDARY: Color = (-2, -2, -2)
THEME_PRIMARY: Color = (-3, -3, -3)
THEME_SECONDARY: Color = (-4, -4, -4)
THEME_SUCCESS: Color = (-5, -5, -5)
THEME_WARNING: Color = (-6, -6, -6)
THEME_ERROR: Color = (-7, -7, -7)
THEME_INFO: Color = (-8, -8, -8)
THEME_MUTED: Color = (-9, -9, -9)
THEME_TEXT_TERTIARY: Color = (-10, -10, -10)


# Single source of truth: sentinel → Theme attribute name.
# Both render_context.RenderContext._resolve_color and the local helper
# below consult this table so they can never drift apart.
_THEME_COLOR_SENTINELS: dict[Color, str] = {
    THEME_TEXT_PRIMARY: "text_primary",
    THEME_TEXT_SECONDARY: "text_secondary",
    THEME_TEXT_TERTIARY: "text_tertiary",
    THEME_PRIMARY: "primary",
    THEME_SECONDARY: "secondary",
    THEME_SUCCESS: "success",
    THEME_WARNING: "warning",
    THEME_ERROR: "error",
    THEME_INFO: "info",
    THEME_MUTED: "muted",
}


def _resolve_color(color: Color, ctx: RenderContext) -> Color:
    """Resolve theme-aware color sentinels to actual colors at render time."""
    attr = _THEME_COLOR_SENTINELS.get(color)
    if attr is not None:
        return getattr(ctx.theme, attr)
    return color


Align = Literal["start", "center", "end", "stretch"]
Justify = Literal["start", "center", "end", "space-between", "space-around"]


def _to_justify(justify: Justify) -> JustifyContent:
    """Convert justify string to flex enum."""
    mapping = {
        "start": JustifyContent.START,
        "center": JustifyContent.CENTER,
        "end": JustifyContent.END,
        "space-between": JustifyContent.SPACE_BETWEEN,
        "space-around": JustifyContent.SPACE_AROUND,
    }
    return mapping.get(justify, JustifyContent.START)


def _to_align(align: Align) -> AlignItems:
    """Convert align string to flex enum."""
    mapping = {
        "start": AlignItems.START,
        "center": AlignItems.CENTER,
        "end": AlignItems.END,
        "stretch": AlignItems.STRETCH,
    }
    return mapping.get(align, AlignItems.CENTER)


# ============================================================================
# Base Component
# ============================================================================


@dataclass
class Component(ABC):
    """Base class for all renderable components."""

    @abstractmethod
    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render this component at the given position and size.

        Args:
            ctx: RenderContext for drawing
            x: Left edge in local coordinates
            y: Top edge in local coordinates
            width: Available width
            height: Available height
        """

    @abstractmethod
    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        """Return preferred (width, height) given max constraints.

        Args:
            ctx: RenderContext for measuring text/fonts
            max_width: Maximum available width
            max_height: Maximum available height

        Returns:
            Tuple of (preferred_width, preferred_height)
        """


# ============================================================================
# Primitive Components
# ============================================================================


@dataclass
class Text(Component):
    """Text component with font and color options.

    Color can be:
    - A specific RGB tuple like (255, 255, 255)
    - THEME_TEXT_PRIMARY for main text (resolves to theme.text_primary)
    - THEME_TEXT_SECONDARY for labels/secondary text (resolves to theme.text_secondary)

    When truncate=True, text that exceeds available width is truncated with ellipsis.
    """

    text: str
    font: str = "regular"
    bold: bool = False
    color: Color = THEME_TEXT_PRIMARY  # Theme-aware by default
    align: Align = "center"
    truncate: bool = False  # Auto-truncate with ellipsis if text exceeds width
    auto_fit: bool = False  # Shrink font progressively until text fits, then truncate

    _FONT_SHRINK_CHAIN: ClassVar[tuple[str, ...]] = (
        "primary",
        "huge",
        "xlarge",
        "large",
        "medium",
        "regular",
        "secondary",
        "small",
        "tertiary",
        "tiny",
    )

    def _resolved_font_chain(self) -> list[str]:
        """Return the cascade of fonts to try when auto_fit is enabled."""
        if self.font in self._FONT_SHRINK_CHAIN:
            idx = self._FONT_SHRINK_CHAIN.index(self.font)
            return list(self._FONT_SHRINK_CHAIN[idx:])
        return [self.font, "small", "tiny"]

    def _pick_font(self, ctx: RenderContext, max_width: int):
        """Return the largest font in the shrink chain that fits the text."""
        for name in self._resolved_font_chain():
            f = ctx.get_font(name, bold=self.bold)
            w, _ = ctx.get_text_size(self.text, f)
            if w <= max_width:
                return f
        return ctx.get_font(self._resolved_font_chain()[-1], bold=self.bold)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        if self.auto_fit:
            font = self._pick_font(ctx, max_width)
        else:
            font = ctx.get_font(self.font, bold=self.bold)
        return ctx.get_text_size(self.text, font)

    def _truncate_text(self, ctx: RenderContext, text: str, font, max_width: int) -> str:
        """Truncate text with ellipsis to fit within max_width."""
        if max_width <= 0:
            return ""
        text_width, _ = ctx.get_text_size(text, font)
        if text_width <= max_width:
            return text
        ellipsis = "…"
        while len(text) > 1:
            text = text[:-1]
            test_text = text + ellipsis
            text_width, _ = ctx.get_text_size(test_text, font)
            if text_width <= max_width:
                return test_text
        return ellipsis

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if self.auto_fit:
            font = self._pick_font(ctx, width)
        else:
            font = ctx.get_font(self.font, bold=self.bold)
        anchor_map = {"start": "lm", "center": "mm", "end": "rm", "stretch": "mm"}
        anchor = anchor_map.get(self.align, "mm")

        # Apply truncation if enabled
        display_text = self.text
        if self.truncate or self.auto_fit:
            display_text = self._truncate_text(ctx, self.text, font, width)

        if self.align == "start":
            text_x = x
        elif self.align == "end":
            text_x = x + width
        else:
            text_x = x + width // 2

        # Resolve theme-aware colors at render time
        resolved_color = _resolve_color(self.color, ctx)
        ctx.draw_text(display_text, (text_x, y + height // 2), font, resolved_color, anchor)


@dataclass
class Icon(Component):
    """Icon component with optional fixed size.

    Args:
        name: Icon name (e.g., "cpu", "temp", "lock")
        size: Fixed size in pixels, or None for auto-sizing
        color: Icon color (supports THEME_TEXT_PRIMARY/SECONDARY)
        min_size: Minimum size for readability (default 12px)
        max_size: Maximum size to prevent icons dominating layout (default 32px)
    """

    name: str
    size: int | None = None  # None = auto-size to container
    color: Color = THEME_TEXT_PRIMARY  # Theme-aware by default
    min_size: int = 12  # Minimum size for readability
    max_size: int = 32  # Maximum size to prevent oversized icons

    def _calculate_size(self, available: int) -> int:
        """Calculate icon size with min/max bounds."""
        if self.size is not None:
            return self.size
        return max(self.min_size, min(self.max_size, available))

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        size = self._calculate_size(min(max_width, max_height))
        return (size, size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        size = self._calculate_size(min(width, height))
        # Center icon in available space
        ix = x + (width - size) // 2
        iy = y + (height - size) // 2
        # Resolve theme-aware colors at render time
        resolved_color = _resolve_color(self.color, ctx)
        ctx.draw_icon(self.name, (ix, iy), size, resolved_color)


@dataclass
class Bar(Component):
    """Horizontal progress bar component.

    When background is None, the track is tinted (a soft mix of the bar color
    over the theme background) — watchOS Activity-bar style. Themes can opt
    out by setting Theme.tint_track=False.
    """

    percent: float
    color: Color = (0, 255, 255)
    background: Color | None = None  # None = use theme-aware tinted track
    height: int | None = None  # None = use default relative to container

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        h = self.height or max(6, int(max_height * 0.15))
        return (max_width, h)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        bg = self.background if self.background is not None else ctx.track_color(self.color)
        ctx.draw_bar((x, y, x + width, y + height), self.percent, self.color, bg)


@dataclass
class VerticalBar(Component):
    """Vertical progress bar — fills upward from the bottom.

    Mirror of `Bar` on the vertical axis. Useful for tall, narrow cells
    (1x2, 1x3, sidebar slots) where a horizontal bar looks orphaned. The
    track picks up the theme's tinted-track style via `ctx.track_color`,
    matching the rest of the gauge family.
    """

    percent: float
    color: Color = (0, 255, 255)
    background: Color | None = None  # None = theme tinted track
    width: int | None = None  # None = sensible default relative to container

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        # Default thickness: ~30% of available width, clamped to 12..32 so
        # it reads as a substantial column without dominating small cells.
        # (Bumped from 22%/24-cap so vertical gauges feel "a bit larger" —
        # they look orphaned at the previous narrower default.)
        w = self.width or max(12, min(32, int(max_width * 0.30)))
        return (w, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        bg_raw = self.background if self.background is not None else ctx.track_color(self.color)
        # Resolve sentinels — Bar is constructed with a sentinel-aware color
        # passed by widgets; VerticalBar should match that contract.
        fill_color = _resolve_color(self.color, ctx)
        bg_color = _resolve_color(bg_raw, ctx)

        # Match horizontal Bar's radius (small fixed value). A larger radius
        # (e.g. width // 2) makes the fill's *top* corners round prominently
        # — that creates a visible "dip" line where the fill ends, which
        # users mistake for an unwanted gap. Keeping radius small (2px) makes
        # the artifact imperceptible while preserving consistent rounding
        # with horizontal bars.
        radius = 2
        ctx.draw_rounded_rect((x, y, x + width, y + height), radius=radius, fill=bg_color)
        pct = max(0.0, min(100.0, self.percent))
        fill_h = int(height * pct / 100)
        if fill_h > 0:
            ctx.draw_rounded_rect(
                (x, y + height - fill_h, x + width, y + height),
                radius=radius,
                fill=fill_color,
            )


@dataclass
class Ring(Component):
    """Circular ring gauge component (Apple Activity-ring style).

    When `background` is None and the theme has tint_track enabled, the
    track is rendered as a soft tint of the ring color (watchOS look).
    """

    percent: float
    color: Color = (0, 255, 255)
    background: Color | None = None  # None = use theme tinted track
    thickness: int | None = None  # None = auto-calculate (Activity-ring proportions)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        size = min(max_width, max_height)
        return (size, size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        size = min(width, height)
        radius = size // 2
        center = (x + width // 2, y + height // 2)
        # Activity-ring proportions: ~14% of the ring radius, with a 5px floor.
        thickness = self.thickness or max(5, int(radius * 0.14))
        bg = self.background if self.background is not None else ctx.track_color(self.color)
        ctx.draw_ring_gauge(
            center,
            radius - thickness,
            self.percent,
            self.color,
            bg,
            thickness,
        )


@dataclass
class Arc(Component):
    """Arc gauge component (270-degree arc).

    Tinted track by default when the theme allows.
    """

    percent: float
    color: Color = (0, 255, 255)
    background: Color | None = None  # None = use theme tinted track
    width: int | None = None  # None = auto-calculate from size

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        size = min(max_width, max_height)
        return (size, size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        size = min(width, height)
        cx, cy = x + width // 2, y + height // 2
        half = size // 2
        bg = self.background if self.background is not None else ctx.track_color(self.color)
        # Auto thickness scales with arc radius, similar to ring proportions.
        stroke = self.width if self.width is not None else max(5, int(half * 0.13))
        ctx.draw_arc(
            (cx - half, cy - half, cx + half, cy + half),
            self.percent,
            self.color,
            bg,
            stroke,
        )


@dataclass
class Sparkline(Component):
    """Sparkline chart component."""

    data: list[float]
    color: Color = (0, 255, 255)
    fill: bool = True
    smooth: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        ctx.draw_sparkline(
            (x, y, x + width, y + height),
            self.data,
            self.color,
            fill=self.fill,
            smooth=self.smooth,
        )


@dataclass
class Panel(Component):
    """Background panel/card component.

    When color or radius are None, uses theme defaults.
    """

    child: Component | None = None
    color: Color | None = None  # None = use theme.surface
    radius: int | None = None  # None = use theme.corner_radius
    border_color: Color | None = None  # None = use theme.border if border_width > 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        if self.child:
            return self.child.measure(ctx, max_width, max_height)
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        theme = ctx.theme
        # Use theme defaults when not explicitly specified
        fill_color = self.color if self.color is not None else theme.surface
        corner_radius = self.radius if self.radius is not None else theme.corner_radius

        # Draw panel with optional border based on theme
        if theme.border_width > 0:
            border = self.border_color if self.border_color is not None else theme.border
            ctx.draw_panel(
                (x, y, x + width, y + height),
                fill_color,
                border_color=border,
                radius=corner_radius,
            )
        else:
            ctx.draw_panel((x, y, x + width, y + height), fill_color, radius=corner_radius)

        if self.child:
            self.child.render(ctx, x, y, width, height)


@dataclass
class Spacer(Component):
    """Flexible spacer that expands to fill available space."""

    min_size: int = 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (self.min_size, self.min_size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        pass  # Spacers are invisible


@dataclass
class Empty(Component):
    """Empty component that renders nothing (for conditional rendering)."""

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (0, 0)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        pass


@dataclass
class Flex(Component):
    """Wrap a child so a Row/Column gives it the remaining main-axis space.

    Spacer-like flex_grow distribution for non-spacer content (bars, text,
    sub-layouts). The child's intrinsic measurement is ignored on the main
    axis — the Flex receives whatever's left after fixed-size siblings.
    """

    child: Component
    grow: int = 1

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return self.child.measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        self.child.render(ctx, x, y, width, height)


# ============================================================================
# Layout Components
# ============================================================================


@dataclass
class Row(Component):
    """Horizontal layout container using flexbox."""

    children: list[Component] = field(default_factory=list)
    gap: int = 0
    align: Align = "center"  # Cross-axis (vertical) alignment
    justify: Justify = "start"  # Main-axis (horizontal) distribution
    padding: int = 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        inner_h = max_height - self.padding * 2
        total_width = self.padding * 2
        max_h = 0

        for i, child in enumerate(self.children):
            if child is None:
                continue
            if i > 0:
                total_width += self.gap
            w, h = child.measure(ctx, max_width, inner_h)
            total_width += w
            max_h = max(max_h, h)

        return (min(total_width, max_width), min(max_h + self.padding * 2, max_height))

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        # Filter out None children
        children = [c for c in self.children if c is not None]
        if not children:
            return

        inner_x = x + self.padding
        inner_y = y + self.padding
        inner_w = width - self.padding * 2
        inner_h = height - self.padding * 2

        # Build flex layout tree
        root = Node(
            flex_direction=FlexDirection.ROW,
            justify_content=_to_justify(self.justify),
            align_items=_to_align(self.align),
            gap=self.gap,
            size=(inner_w, inner_h),
        )

        for i, child in enumerate(children):
            cw, ch = child.measure(ctx, inner_w, inner_h)
            if isinstance(child, Spacer):
                root.add(Node(key=f"c{i}", flex_grow=1, size=(AUTO, 100 * PCT)))
            elif isinstance(child, Flex):
                # Flex children get the remaining main-axis space.
                cross = 100 * PCT if self.align == "stretch" else ch
                root.add(Node(key=f"c{i}", flex_grow=child.grow, size=(AUTO, cross)))
            elif self.align == "stretch":
                # Stretch to full container height
                root.add(Node(key=f"c{i}", size=(cw, 100 * PCT)))
            else:
                # Use measured height to preserve aspect ratios
                root.add(Node(key=f"c{i}", size=(cw, ch)))

        root.compute_layout()

        # Render children at computed positions
        for i, child in enumerate(children):
            node = root.find(f"/c{i}")
            box = node.get_box(Edge.CONTENT)
            child.render(
                ctx,
                inner_x + round(box.x),
                inner_y + round(box.y),
                round(box.width),
                round(box.height),
            )


@dataclass
class Column(Component):
    """Vertical layout container using flexbox."""

    children: list[Component] = field(default_factory=list)
    gap: int = 0
    align: Align = "center"  # Cross-axis (horizontal) alignment
    justify: Justify = "start"  # Main-axis (vertical) distribution
    padding: int = 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        inner_w = max_width - self.padding * 2
        total_height = self.padding * 2
        max_w = 0

        for i, child in enumerate(self.children):
            if child is None:
                continue
            if i > 0:
                total_height += self.gap
            w, h = child.measure(ctx, inner_w, max_height)
            total_height += h
            max_w = max(max_w, w)

        return (min(max_w + self.padding * 2, max_width), min(total_height, max_height))

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        # Filter out None children
        children = [c for c in self.children if c is not None]
        if not children:
            return

        inner_x = x + self.padding
        inner_y = y + self.padding
        inner_w = width - self.padding * 2
        inner_h = height - self.padding * 2

        # Build flex layout tree
        root = Node(
            flex_direction=FlexDirection.COLUMN,
            justify_content=_to_justify(self.justify),
            align_items=_to_align(self.align),
            gap=self.gap,
            size=(inner_w, inner_h),
        )

        for i, child in enumerate(children):
            cw, ch = child.measure(ctx, inner_w, inner_h)
            if isinstance(child, Spacer):
                root.add(Node(key=f"c{i}", flex_grow=1, size=(100 * PCT, AUTO)))
            elif isinstance(child, Flex):
                # Flex children get the remaining main-axis space.
                cross = 100 * PCT if self.align == "stretch" else cw
                root.add(Node(key=f"c{i}", flex_grow=child.grow, size=(cross, AUTO)))
            elif self.align == "stretch":
                # Stretch to full container width
                root.add(Node(key=f"c{i}", size=(100 * PCT, ch)))
            else:
                # Use measured width to preserve aspect ratios
                root.add(Node(key=f"c{i}", size=(cw, ch)))

        root.compute_layout()

        # Render children at computed positions
        for i, child in enumerate(children):
            node = root.find(f"/c{i}")
            box = node.get_box(Edge.CONTENT)
            child.render(
                ctx,
                inner_x + round(box.x),
                inner_y + round(box.y),
                round(box.width),
                round(box.height),
            )


@dataclass
class Stack(Component):
    """Overlay layout - children rendered on top of each other."""

    children: list[Component] = field(default_factory=list)
    align: Align = "center"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        max_w, max_h = 0, 0
        for child in self.children:
            if child is None:
                continue
            w, h = child.measure(ctx, max_width, max_height)
            max_w, max_h = max(max_w, w), max(max_h, h)
        return (max_w, max_h)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        for child in self.children:
            if child is None:
                continue
            child.render(ctx, x, y, width, height)


@dataclass
class Adaptive(Component):
    """Automatically adapts layout based on available space.

    Tries horizontal (Row) first, falls back to vertical (Column) if
    children don't fit horizontally.
    """

    children: list[Component] = field(default_factory=list)
    gap: int = 6  # Increased from 4 for better spacing
    padding: int = 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        children = [c for c in self.children if c is not None]
        if not children:
            return (0, 0)
        inner_w = max_width - self.padding * 2
        # Decide row vs column the same way render() does, so the outer
        # container budgets the correct height.
        total_width = sum(c.measure(ctx, inner_w, max_height)[0] for c in children)
        total_width += self.gap * (len(children) - 1)
        if total_width <= inner_w:
            return Row(
                children=children,
                gap=self.gap,
                padding=self.padding,
                justify="space-between",
            ).measure(ctx, max_width, max_height)
        return Column(
            children=children,
            gap=self.gap,
            padding=self.padding,
            justify="center",
            align="center",
        ).measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        # Filter out None children
        children = [c for c in self.children if c is not None]
        if not children:
            return

        # Measure total width if laid out horizontally
        inner_w = width - self.padding * 2
        total_width = sum(c.measure(ctx, inner_w, height)[0] for c in children)
        total_width += self.gap * (len(children) - 1)

        # Choose layout based on fit
        if total_width <= inner_w:
            # Fits horizontally
            Row(
                children=children,
                gap=self.gap,
                padding=self.padding,
                justify="space-between",
                align="center",
            ).render(ctx, x, y, width, height)
        else:
            # Fall back to vertical
            Column(
                children=children,
                gap=self.gap,
                padding=self.padding,
                justify="center",
                align="center",
            ).render(ctx, x, y, width, height)


@dataclass
class Center(Component):
    """Centers a single child component."""

    child: Component

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return self.child.measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        cw, ch = self.child.measure(ctx, width, height)
        cx = x + (width - cw) // 2
        cy = y + (height - ch) // 2
        self.child.render(ctx, cx, cy, cw, ch)


@dataclass
class Padding(Component):
    """Adds padding around a child component."""

    child: Component
    all: int = 0
    horizontal: int | None = None
    vertical: int | None = None
    top: int | None = None
    right: int | None = None
    bottom: int | None = None
    left: int | None = None

    def _get_padding(self) -> tuple[int, int, int, int]:
        """Return (top, right, bottom, left) padding values."""
        t = (
            self.top
            if self.top is not None
            else (self.vertical if self.vertical is not None else self.all)
        )
        r = (
            self.right
            if self.right is not None
            else (self.horizontal if self.horizontal is not None else self.all)
        )
        b = (
            self.bottom
            if self.bottom is not None
            else (self.vertical if self.vertical is not None else self.all)
        )
        l_pad = (
            self.left
            if self.left is not None
            else (self.horizontal if self.horizontal is not None else self.all)
        )
        return (t, r, b, l_pad)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        t, r, b, l_pad = self._get_padding()
        inner_w = max(0, max_width - l_pad - r)  # Clamp to prevent negative
        inner_h = max(0, max_height - t - b)  # Clamp to prevent negative
        cw, ch = self.child.measure(ctx, inner_w, inner_h)
        return (cw + l_pad + r, ch + t + b)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        t, r, b, l_pad = self._get_padding()
        child_w = max(0, width - l_pad - r)  # Clamp to prevent negative
        child_h = max(0, height - t - b)  # Clamp to prevent negative
        if child_w > 0 and child_h > 0:
            self.child.render(ctx, x + l_pad, y + t, child_w, child_h)


# ============================================================================
# Hierarchy and Priority Components
# ============================================================================


@dataclass
class FillText(Component):
    """Text that fills available space while maintaining aspect ratio.

    Primary text fills the container, secondary/tertiary scale proportionally.
    This is the preferred component for dynamic text sizing.

    Args:
        text: Text to display
        hierarchy: Size hierarchy - "primary" fills, "secondary"/"tertiary" scale smaller
        bold: Whether to use bold font
        color: Text color
        max_ratio: Maximum container fill ratio (0.95 = 95% of container)
        min_size: Minimum font size in pixels
    """

    text: str
    hierarchy: Literal["primary", "secondary", "tertiary"] = "primary"
    bold: bool = False
    color: Color = THEME_TEXT_PRIMARY
    max_ratio: float = 0.95
    min_size: int = 12

    # Scaling ratios relative to primary
    _RATIOS: dict[str, float] = field(
        default_factory=lambda: {"primary": 1.0, "secondary": 0.50, "tertiary": 0.30},
        repr=False,
    )

    def _get_font(self, ctx: RenderContext, width: int, height: int):
        """Get font sized for hierarchy and container."""
        ratio = self._RATIOS.get(self.hierarchy, 1.0)

        # Primary: fit to container
        if self.hierarchy == "primary":
            return ctx.fit_text(
                self.text,
                max_width=int(width * self.max_ratio),
                max_height=int(height * self.max_ratio),
                bold=self.bold,
            )
        # Secondary/tertiary: scale from what primary would be
        primary_font = ctx.fit_text(
            self.text,
            max_width=int(width * self.max_ratio),
            max_height=int(height * self.max_ratio),
            bold=self.bold,
        )
        # Get primary height and scale
        primary_height = ctx.get_text_size("Hg", primary_font)[1]
        target_height = max(self.min_size, int(primary_height * ratio))
        # Get font at target height
        return ctx.get_font_for_height(target_height, bold=self.bold)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        font = self._get_font(ctx, max_width, max_height)
        return ctx.get_text_size(self.text, font)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        font = self._get_font(ctx, width, height)
        _, text_h = ctx.get_text_size(self.text, font)

        # Check minimum size constraint
        if text_h < self.min_size:
            return  # Too small, skip

        # Resolve theme-aware colors
        resolved_color = _resolve_color(self.color, ctx)

        # Center in container
        tx = x + width // 2
        ty = y + height // 2
        ctx.draw_text(self.text, (tx, ty), font, resolved_color, anchor="mm")


@dataclass
class Prioritized(Component):
    """Wrapper that adds priority to any component for responsive hiding.

    Use with PriorityColumn or PriorityRow to enable auto-hiding of
    low-priority elements when space is insufficient.

    Args:
        child: The component to wrap
        priority: Display priority (CRITICAL always shows, LOW hides first)
        min_width: Minimum width needed to show this element
        min_height: Minimum height needed to show this element
    """

    child: Component
    priority: int = 1  # Priority.CRITICAL
    min_width: int = 0
    min_height: int = 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return self.child.measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        self.child.render(ctx, x, y, width, height)


@dataclass
class PriorityColumn(Component):
    """Column that auto-hides low-priority children when space is insufficient.

    Children are sorted by priority. Starting from highest priority (CRITICAL),
    children are allocated space. When remaining space is insufficient for
    the next child, it and all lower-priority children are hidden.

    Args:
        children: List of Prioritized components
        gap: Gap between visible children
        align: Horizontal alignment of children
        padding: Padding around all children
    """

    children: list[Prioritized] = field(default_factory=list)
    gap: int = 4
    align: Align = "center"
    padding: int = 0

    def _filter_visible(self, ctx: RenderContext, width: int, height: int) -> list[Prioritized]:
        """Determine which children fit based on priority."""
        if not self.children:
            return []

        # Sort by priority (lower number = higher priority)
        sorted_children = sorted(self.children, key=lambda c: c.priority)

        available = height - self.padding * 2
        visible: list[Prioritized] = []
        gap_used = 0

        for child in sorted_children:
            needed_h = child.measure(ctx, width - self.padding * 2, available)[1]

            # Check if child fits with its minimum requirements
            fits_space = needed_h + gap_used <= available
            fits_min = (
                needed_h >= child.min_height and (width - self.padding * 2) >= child.min_width
            )

            if fits_space and fits_min:
                visible.append(child)
                available -= needed_h + self.gap
                gap_used = self.gap
            elif child.priority == 1:  # Priority.CRITICAL
                # Critical elements always show, even if cramped
                visible.append(child)
                available -= needed_h + self.gap
                gap_used = self.gap

        return visible

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        visible = self._filter_visible(ctx, max_width, max_height)
        if not visible:
            return (0, 0)

        inner_w = max_width - self.padding * 2
        total_h = self.padding * 2 + self.gap * max(0, len(visible) - 1)
        max_w = 0

        for child in visible:
            w, h = child.measure(ctx, inner_w, max_height)
            total_h += h
            max_w = max(max_w, w)

        return (min(max_w + self.padding * 2, max_width), min(total_h, max_height))

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        visible = self._filter_visible(ctx, width, height)
        if not visible:
            return

        # Delegate to Column for actual layout
        Column(
            children=[c.child for c in visible],
            gap=self.gap,
            align=self.align,
            padding=self.padding,
            justify="center",
        ).render(ctx, x, y, width, height)


@dataclass
class PriorityRow(Component):
    """Row that auto-hides low-priority children when space is insufficient.

    Same as PriorityColumn but for horizontal layout.

    Args:
        children: List of Prioritized components
        gap: Gap between visible children
        align: Vertical alignment of children
        justify: Horizontal distribution of children
        padding: Padding around all children
    """

    children: list[Prioritized] = field(default_factory=list)
    gap: int = 4
    align: Align = "center"
    justify: Justify = "space-between"
    padding: int = 0

    def _filter_visible(self, ctx: RenderContext, width: int, height: int) -> list[Prioritized]:
        """Determine which children fit based on priority."""
        if not self.children:
            return []

        sorted_children = sorted(self.children, key=lambda c: c.priority)

        available = width - self.padding * 2
        visible: list[Prioritized] = []
        gap_used = 0

        for child in sorted_children:
            needed_w = child.measure(ctx, available, height - self.padding * 2)[0]

            fits_space = needed_w + gap_used <= available
            fits_min = (
                needed_w >= child.min_width and (height - self.padding * 2) >= child.min_height
            )

            if (fits_space and fits_min) or child.priority == 1:
                visible.append(child)
                available -= needed_w + self.gap
                gap_used = self.gap

        return visible

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        visible = self._filter_visible(ctx, max_width, max_height)
        if not visible:
            return (0, 0)

        inner_h = max_height - self.padding * 2
        total_w = self.padding * 2 + self.gap * max(0, len(visible) - 1)
        max_h = 0

        for child in visible:
            w, h = child.measure(ctx, max_width, inner_h)
            total_w += w
            max_h = max(max_h, h)

        return (min(total_w, max_width), min(max_h + self.padding * 2, max_height))

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        visible = self._filter_visible(ctx, width, height)
        if not visible:
            return

        Row(
            children=[c.child for c in visible],
            gap=self.gap,
            align=self.align,
            justify=self.justify,
            padding=self.padding,
        ).render(ctx, x, y, width, height)


@dataclass
class IconValueDisplay(Component):
    """Icon with value and label - handles layout internally for proper sizing.

    Vertical layout: Icon at top, value in middle (fills space), label at bottom.
    All sizing is computed together to ensure proper proportions.
    """

    icon: str
    value: str
    label: str
    icon_color: tuple[int, int, int] = THEME_TEXT_PRIMARY
    value_color: tuple[int, int, int] = THEME_TEXT_PRIMARY
    label_color: tuple[int, int, int] = THEME_TEXT_SECONDARY
    icon_size: int | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render icon, value, and label with proper proportions."""
        padding = int(width * 0.06)
        inner_width = width - padding * 2
        inner_height = height - padding * 2

        # Resolve theme-aware colors
        icon_color = _resolve_color(self.icon_color, ctx)
        value_color = _resolve_color(self.value_color, ctx)
        label_color = _resolve_color(self.label_color, ctx)

        # Calculate sizes based on container
        icon_size = self.icon_size or max(16, min(48, int(inner_height * 0.25)))
        label_height = int(inner_height * 0.15)
        value_height = inner_height - icon_size - label_height - 12  # gaps

        # Vertical positions (centered)
        total_content = icon_size + value_height + label_height + 12
        start_y = y + padding + (inner_height - total_content) // 2

        center_x = x + width // 2
        current_y = start_y

        # Draw icon at top
        ctx.draw_icon(
            self.icon,
            (center_x - icon_size // 2, current_y),
            size=icon_size,
            color=icon_color,
        )
        current_y += icon_size + 6

        # Draw value (fills available space)
        value_font = ctx.fit_text(
            self.value,
            max_width=int(inner_width * 0.95),
            max_height=int(value_height * 0.90),
            bold=True,
        )
        ctx.draw_text(
            self.value,
            (center_x, current_y + value_height // 2),
            font=value_font,
            color=value_color,
            anchor="mm",
        )
        current_y += value_height + 6

        # Draw label at bottom (watchOS hierarchy: caption tier).
        # Use fit_text to find the largest font that fits — guarantees no
        # truncation across cell sizes from 70px to 240px wide.
        label_text = self.label.upper()
        label_font = ctx.fit_text(
            label_text,
            max_width=int(inner_width * 0.92),
            max_height=int(label_height * 0.90),
            bold=False,
        )
        ctx.draw_text(
            label_text,
            (center_x, current_y + label_height // 2),
            font=label_font,
            color=label_color,
            anchor="mm",
        )


# ============================================================================
# Export all components
# ============================================================================

__all__ = [
    "THEME_ERROR",
    "THEME_INFO",
    "THEME_MUTED",
    "THEME_PRIMARY",
    "THEME_SECONDARY",
    "THEME_SUCCESS",
    "THEME_TEXT_PRIMARY",
    "THEME_TEXT_SECONDARY",
    "THEME_TEXT_TERTIARY",
    "THEME_WARNING",
    "Adaptive",
    "Align",
    "Arc",
    "Bar",
    "Center",
    "Color",
    "Column",
    "Component",
    "Empty",
    "FillText",
    "Flex",
    "Icon",
    "IconValueDisplay",
    "Justify",
    "Padding",
    "Panel",
    "Prioritized",
    "PriorityColumn",
    "PriorityRow",
    "Ring",
    "Row",
    "Spacer",
    "Sparkline",
    "Stack",
    "Text",
    "VerticalBar",
]
