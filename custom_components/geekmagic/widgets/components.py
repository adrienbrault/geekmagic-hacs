"""Declarative component system for widget rendering.

This module provides a React-like component tree system where widgets
declare WHAT to show (component trees) and the layout system figures out
HOW to arrange it.

Example usage:
    def render(self, ctx, state) -> Component:
        return Column(children=[
            Text("75%", font="medium", bold=True),  # Uses THEME_TEXT_PRIMARY by default
            Bar(percent=75, color=THEME_PRIMARY),   # Theme accent, resolved at render
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
from .colors import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SECONDARY,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_TEXT_TERTIARY,
    THEME_WARNING,
    Color,
    resolve_theme_color,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext


def _resolve_color(color: Color, ctx: RenderContext) -> Color:
    """Resolve theme-aware color sentinels to actual colors at render time."""
    return resolve_theme_color(color, ctx.theme)


Align = Literal["start", "center", "end", "stretch"]
Justify = Literal["start", "center", "end", "space-between", "space-around", "space-evenly"]


def _to_justify(justify: Justify) -> JustifyContent:
    """Convert justify string to flex enum."""
    mapping = {
        "start": JustifyContent.START,
        "center": JustifyContent.CENTER,
        "end": JustifyContent.END,
        "space-between": JustifyContent.SPACE_BETWEEN,
        "space-around": JustifyContent.SPACE_AROUND,
        "space-evenly": JustifyContent.SPACE_EVENLY,
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
    When wrap=True, over-wide text flows onto up to ``max_lines`` lines instead
    (``wrap`` takes precedence over ``truncate``); if the wrapped block is too
    tall for the available height, it falls back to a single truncated line.
    """

    text: str
    font: str = "regular"
    bold: bool = False
    color: Color = THEME_TEXT_PRIMARY  # Theme-aware by default
    align: Align = "center"
    truncate: bool = False  # Auto-truncate with ellipsis if text exceeds width
    auto_fit: bool = False  # Shrink font progressively until text fits, then truncate
    wrap: bool = False  # Word/char-wrap onto up to `max_lines` lines when too wide
    max_lines: int = 2  # Maximum number of lines when wrap=True

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

    def _pick_font(self, ctx: RenderContext, max_width: int, max_height: int | None = None):
        """Return the largest font in the shrink chain that fits the text.

        When ``wrap`` is enabled a font "fits" if the text can be laid out
        across at most ``max_lines`` lines without truncation — so a long
        label keeps a readable size on two lines instead of shrinking to a
        tiny single line. The wrapped block must also fit ``max_height``
        (when given), so the chain keeps shrinking instead of overflowing
        the cell vertically.
        """
        chain = self._resolved_font_chain()
        for name in chain:
            f = ctx.get_font(name, bold=self.bold)
            if self.wrap:
                _lines, fits = self._layout_lines(ctx, f, max_width, max_height)
                if fits:
                    return f
            elif ctx.get_text_size(self.text, f)[0] <= max_width:
                return f
        return ctx.get_font(chain[-1], bold=self.bold)

    def _layout_lines(
        self, ctx: RenderContext, font, max_width: int, max_height: int | None
    ) -> tuple[list[str], bool]:
        """Wrap within ``max_width``, then enforce the vertical budget.

        ``Column`` lays children out at their measured heights, so a wrapped
        block taller than ``max_height`` would collide with neighbouring
        bands. In that case fall back to a single truncated line (which
        reports ``fits=False`` so an auto-fit chain keeps shrinking).
        """
        lines, fits = self._wrap(ctx, font, max_width)
        if len(lines) > 1 and max_height is not None:
            line_h = self._line_height(ctx, font)
            gap = self._line_gap(line_h)
            block_h = line_h * len(lines) + gap * (len(lines) - 1)
            if block_h > max_height:
                return [ctx.truncate_to_width(self.text, font, max_width)], False
        return lines, fits

    def _wrap(self, ctx: RenderContext, font, max_width: int) -> tuple[list[str], bool]:
        """Word/char-wrap ``text`` to at most ``max_lines`` lines.

        Returns ``(lines, fits)`` where ``fits`` is ``False`` when the text
        had to be truncated to honour the line budget. Single long labels
        with no spaces ("TEMPERATURE") are split into balanced hyphenated
        halves ("TEMPER-" / "ATURE") rather than ellipsized.
        """
        text = self.text
        if max_width <= 0:
            return [text], False

        def width_of(s: str) -> int:
            return ctx.get_text_size(s, font)[0]

        if width_of(text) <= max_width:
            return [text], True

        words = text.split()
        # Single token (no usable spaces): balanced character split.
        if len(words) <= 1:
            return self._char_split(ctx, font, text, max_width, width_of)

        # Greedy word wrap.
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if current and width_of(candidate) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)

        if len(lines) <= self.max_lines:
            # A lone over-long word on a line still won't fit — truncating it
            # marks the layout as not-fitting so auto_fit keeps shrinking.
            fits = all(width_of(line) <= max_width for line in lines)
            return [ctx.truncate_to_width(line, font, max_width) for line in lines], fits
        # Too many lines: cram the overflow into the last allowed line.
        head = lines[: self.max_lines - 1]
        tail = " ".join(lines[self.max_lines - 1 :])
        return [*head, ctx.truncate_to_width(tail, font, max_width)], False

    def _char_split(
        self, ctx: RenderContext, font, word: str, max_width: int, width_of
    ) -> tuple[list[str], bool]:
        """Split a single over-long word into balanced hyphenated lines.

        Every line except the last gets a trailing ``-`` so the pieces still
        read as one word; the hyphen counts toward the width budget.
        """
        # Prefer the fewest lines whose balanced chunks all fit.
        for n in range(2, self.max_lines + 1):
            chunks = self._hyphenate(self._even_chunks(word, n))
            if all(width_of(c) <= max_width for c in chunks):
                return chunks, True
        # Even a balanced max_lines split overflows: greedy-fill, ellipsizing
        # the final line so nothing escapes the cell.
        lines: list[str] = []
        chunk = ""
        for idx, ch in enumerate(word):
            if chunk and width_of(chunk + ch + "-") > max_width:
                if len(lines) == self.max_lines - 1:
                    remainder = chunk + word[idx:]
                    lines.append(ctx.truncate_to_width(remainder, font, max_width))
                    return lines, False
                lines.append(chunk + "-")
                chunk = ch
            else:
                chunk += ch
        if chunk:
            lines.append(chunk)
        return lines, len(lines) <= self.max_lines

    @staticmethod
    def _hyphenate(chunks: list[str]) -> list[str]:
        """Append a continuation hyphen to every chunk but the last."""
        return [f"{c}-" for c in chunks[:-1]] + chunks[-1:]

    @staticmethod
    def _even_chunks(word: str, n: int) -> list[str]:
        """Split ``word`` into ``n`` contiguous, near-equal-length chunks."""
        length = len(word)
        base, extra = divmod(length, n)
        chunks: list[str] = []
        i = 0
        for k in range(n):
            size = base + (1 if k < extra else 0)
            chunks.append(word[i : i + size])
            i += size
        return chunks

    def _line_gap(self, line_height: int) -> int:
        """Vertical gap between wrapped lines."""
        return max(1, line_height // 6)

    @staticmethod
    def _line_height(ctx: RenderContext, font) -> int:
        """Reference line height for wrapped blocks.

        Measured from "Ag" (ascender + descender) so measure() and render()
        budget the same height regardless of which glyphs each line contains.
        """
        return ctx.get_text_size("Ag", font)[1]

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        if self.auto_fit:
            font = self._pick_font(ctx, max_width, max_height)
        else:
            font = ctx.get_font(self.font, bold=self.bold)
        if self.wrap:
            lines, _ = self._layout_lines(ctx, font, max_width, max_height)
            if len(lines) > 1:
                w = max(ctx.get_text_size(line, font)[0] for line in lines)
                line_h = self._line_height(ctx, font)
                gap = self._line_gap(line_h)
                n = len(lines)
                return (w, line_h * n + gap * (n - 1))
        return ctx.get_text_size(self.text, font)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if self.auto_fit:
            font = self._pick_font(ctx, width, height)
        else:
            font = ctx.get_font(self.font, bold=self.bold)
        anchor_map = {"start": "lm", "center": "mm", "end": "rm", "stretch": "mm"}
        anchor = anchor_map.get(self.align, "mm")

        if self.wrap:
            lines, _ = self._layout_lines(ctx, font, width, height)
        else:
            # Apply truncation if enabled
            display_text = self.text
            if self.truncate or self.auto_fit:
                display_text = ctx.truncate_to_width(self.text, font, width)
            lines = [display_text]

        if self.align == "start":
            text_x = x
        elif self.align == "end":
            text_x = x + width
        else:
            text_x = x + width // 2

        # Resolve theme-aware colors at render time
        resolved_color = _resolve_color(self.color, ctx)

        if len(lines) == 1:
            ctx.draw_text(lines[0], (text_x, y + height // 2), font, resolved_color, anchor)
            return

        # Center the stacked block of lines vertically within the box.
        line_h = self._line_height(ctx, font)
        gap = self._line_gap(line_h)
        n = len(lines)
        block_h = line_h * n + gap * (n - 1)
        start_y = y + (height - block_h) // 2 + line_h // 2
        for i, line in enumerate(lines):
            ctx.draw_text(
                line, (text_x, start_y + i * (line_h + gap)), font, resolved_color, anchor
            )


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
    color: Color = THEME_PRIMARY  # Theme-aware; resolves at render time
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
    color: Color = THEME_PRIMARY  # Theme-aware; resolves at render time
    background: Color | None = None  # None = theme tinted track
    width: int | None = None  # None = sensible default relative to container

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        w = self.width or max(12, min(32, int(max_width * 0.30)))
        return (w, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        bg_raw = self.background if self.background is not None else ctx.track_color(self.color)
        fill_color = _resolve_color(self.color, ctx)
        bg_color = _resolve_color(bg_raw, ctx)

        # Small fixed radius matches horizontal Bar; larger radii produce a
        # visible dip line where the fill ends.
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
    color: Color = THEME_PRIMARY  # Theme-aware; resolves at render time
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
    color: Color = THEME_PRIMARY  # Theme-aware; resolves at render time
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
    color: Color = THEME_PRIMARY  # Theme-aware; resolves at render time
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
    "Flex",
    "Icon",
    "Justify",
    "Panel",
    "Ring",
    "Row",
    "Spacer",
    "Sparkline",
    "Stack",
    "Text",
    "VerticalBar",
]
