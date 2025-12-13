"""Declarative component system for widget rendering.

This module provides a React-like component tree system where widgets
declare WHAT to show (component trees) and the layout system figures out
HOW to arrange it.

Example usage:
    def render(self, ctx, hass) -> Component:
        return Column(children=[
            Text("75%", font="medium", bold=True),
            Bar(percent=75, color=COLOR_CYAN),
            Text("CPU", font="tiny", color=COLOR_GRAY),
        ])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from stretchable import Edge, Node
from stretchable.style import (
    AUTO,
    PCT,
    AlignItems,
    FlexDirection,
    JustifyContent,
)

from ..const import COLOR_DARK_GRAY, COLOR_WHITE

if TYPE_CHECKING:
    from ..render_context import RenderContext

# Type aliases
Color = tuple[int, int, int]
Align = Literal["start", "center", "end", "stretch"]
Justify = Literal["start", "center", "end", "space-between", "space-around"]


def _to_justify(justify: Justify) -> JustifyContent:
    """Convert justify string to stretchable enum."""
    mapping = {
        "start": JustifyContent.START,
        "center": JustifyContent.CENTER,
        "end": JustifyContent.END,
        "space-between": JustifyContent.SPACE_BETWEEN,
        "space-around": JustifyContent.SPACE_AROUND,
    }
    return mapping.get(justify, JustifyContent.START)


def _to_align(align: Align) -> AlignItems:
    """Convert align string to stretchable enum."""
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
    """Text component with font and color options."""

    text: str
    font: str = "regular"
    bold: bool = False
    color: Color = COLOR_WHITE
    align: Align = "center"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        font = ctx.get_font(self.font, bold=self.bold)
        return ctx.get_text_size(self.text, font)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        font = ctx.get_font(self.font, bold=self.bold)
        anchor_map = {"start": "lm", "center": "mm", "end": "rm", "stretch": "mm"}
        anchor = anchor_map.get(self.align, "mm")

        if self.align == "start":
            text_x = x
        elif self.align == "end":
            text_x = x + width
        else:
            text_x = x + width // 2

        ctx.draw_text(self.text, (text_x, y + height // 2), font, self.color, anchor)


@dataclass
class Icon(Component):
    """Icon component with optional fixed size.

    Args:
        name: Icon name (e.g., "cpu", "temp", "lock")
        size: Fixed size in pixels, or None for auto-sizing
        color: Icon color as RGB tuple
        min_size: Minimum size for readability (default 12px)
        max_size: Maximum size to prevent icons dominating layout (default 32px)
    """

    name: str
    size: int | None = None  # None = auto-size to container
    color: Color = COLOR_WHITE
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
        ctx.draw_icon(self.name, (ix, iy), size, self.color)


@dataclass
class Bar(Component):
    """Horizontal progress bar component.

    When background is None, uses theme-appropriate dark color.
    """

    percent: float
    color: Color = (0, 255, 255)
    background: Color | None = None  # None = use theme-aware dark color
    height: int | None = None  # None = use default relative to container

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        h = self.height or max(6, int(max_height * 0.15))
        return (max_width, h)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        # Use theme-aware background if not specified
        bg = self.background if self.background is not None else COLOR_DARK_GRAY
        ctx.draw_bar((x, y, x + width, y + height), self.percent, self.color, bg)


@dataclass
class Ring(Component):
    """Circular ring gauge component."""

    percent: float
    color: Color = (0, 255, 255)
    background: Color = COLOR_DARK_GRAY
    thickness: int | None = None  # None = auto-calculate

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        size = min(max_width, max_height)
        return (size, size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        size = min(width, height)
        radius = size // 2
        center = (x + width // 2, y + height // 2)
        thickness = self.thickness or max(4, radius // 5)
        ctx.draw_ring_gauge(
            center,
            radius - thickness,
            self.percent,
            self.color,
            self.background,
            thickness,
        )


@dataclass
class Arc(Component):
    """Arc gauge component (270-degree arc)."""

    percent: float
    color: Color = (0, 255, 255)
    background: Color = COLOR_DARK_GRAY
    width: int = 8

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        size = min(max_width, max_height)
        return (size, size)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        size = min(width, height)
        cx, cy = x + width // 2, y + height // 2
        half = size // 2
        ctx.draw_arc(
            (cx - half, cy - half, cx + half, cy + half),
            self.percent,
            self.color,
            self.background,
            self.width,
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
    color: Color | None = None  # None = use theme.panel_fill
    radius: int | None = None  # None = use theme.corner_radius
    border_color: Color | None = None  # None = use theme.panel_border if border_width > 0

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        if self.child:
            return self.child.measure(ctx, max_width, max_height)
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        theme = ctx.theme
        # Use theme defaults when not explicitly specified
        fill_color = self.color if self.color is not None else theme.panel_fill
        corner_radius = self.radius if self.radius is not None else theme.corner_radius

        # Draw panel with optional border based on theme
        if theme.border_width > 0:
            border = self.border_color if self.border_color is not None else theme.panel_border
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

        # Build stretchable layout tree
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
                inner_x + int(box.x),
                inner_y + int(box.y),
                int(box.width),
                int(box.height),
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

        # Build stretchable layout tree
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
                inner_x + int(box.x),
                inner_y + int(box.y),
                int(box.width),
                int(box.height),
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
        # Measure as row first
        row = Row(
            children=self.children, gap=self.gap, padding=self.padding, justify="space-between"
        )
        return row.measure(ctx, max_width, max_height)

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
# Export all components
# ============================================================================

__all__ = [
    "Adaptive",
    "Align",
    "Arc",
    "Bar",
    "Center",
    "Color",
    "Column",
    "Component",
    "Empty",
    "Icon",
    "Justify",
    "Padding",
    "Panel",
    "Ring",
    "Row",
    "Spacer",
    "Sparkline",
    "Stack",
    "Text",
]
