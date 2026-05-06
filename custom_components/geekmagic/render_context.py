"""RenderContext provides widgets with a local coordinate system.

This abstraction allows widgets to work in coordinates relative to their
container (0, 0 to width, height) instead of absolute canvas coordinates.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from .const import COLOR_DARK_GRAY, COLOR_PANEL, COLOR_WHITE


class SizeCategory(Enum):
    """Size categories for responsive widget layouts.

    These categories help widgets decide what content to show based on
    available vertical space. Thresholds are tuned for 240x240 displays
    with various grid layouts.
    """

    MICRO = "micro"  # < 78px  - minimal content (3x3 grid cells)
    TINY = "tiny"  # < 100px - very compact (2x3 cells)
    SMALL = "small"  # < 140px - compact (2x2 cells)
    MEDIUM = "medium"  # < 200px - standard
    LARGE = "large"  # >= 200px - full featured


# Threshold constants for size categories
SIZE_THRESHOLD_MICRO = 78
SIZE_THRESHOLD_TINY = 100
SIZE_THRESHOLD_SMALL = 140
SIZE_THRESHOLD_MEDIUM = 200


def get_size_category(height: int) -> SizeCategory:
    """Get size category for a given height.

    This standalone function can be used by components that receive
    explicit height parameters rather than relying on ctx.height.

    Args:
        height: Available height in pixels

    Returns:
        SizeCategory enum value
    """
    if height < SIZE_THRESHOLD_MICRO:
        return SizeCategory.MICRO
    if height < SIZE_THRESHOLD_TINY:
        return SizeCategory.TINY
    if height < SIZE_THRESHOLD_SMALL:
        return SizeCategory.SMALL
    if height < SIZE_THRESHOLD_MEDIUM:
        return SizeCategory.MEDIUM
    return SizeCategory.LARGE


if TYPE_CHECKING:
    from PIL import Image, ImageDraw
    from PIL.ImageFont import FreeTypeFont, ImageFont

    from .renderer import Renderer
    from .widgets.theme import Theme

_LOGGER = logging.getLogger(__name__)


class RenderContext:
    """Provides widget-local coordinate system and drawing methods.

    All coordinates passed to drawing methods are relative to the widget's
    own origin (0, 0), not the absolute canvas position.

    Attributes:
        width: Container width in unscaled pixels
        height: Container height in unscaled pixels
        theme: Theme configuration for styling
    """

    def __init__(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        renderer: Renderer,
        theme: Theme | None = None,
    ) -> None:
        """Initialize render context.

        Args:
            draw: PIL ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box in unscaled coordinates
            renderer: Renderer instance for drawing operations
            theme: Theme configuration for styling (optional, defaults to classic)
        """
        self._draw = draw
        self._renderer = renderer
        self._x1, self._y1, x2, y2 = rect
        self.width = x2 - self._x1
        self.height = y2 - self._y1
        self._theme = theme  # Store the theme

        # Pre-calculate scaled height for font sizing
        self._scaled_height = self.height * renderer.scale

    @property
    def theme(self) -> Theme:
        """Get the current theme.

        Returns:
            Theme instance (defaults to classic if not set)
        """
        if self._theme is not None:
            return self._theme
        # Lazy import to avoid circular dependency
        from .widgets.theme import DEFAULT_THEME

        return DEFAULT_THEME

    # =========================================================================
    # Responsive Size Helpers
    # =========================================================================

    @property
    def size_category(self) -> SizeCategory:
        """Get size category based on container height.

        This helps widgets decide what content to show:
        - MICRO: Show only essential info (title only)
        - TINY: Very compact, primary info only
        - SMALL: Compact, may include secondary info
        - MEDIUM: Standard layout with most info
        - LARGE: Full featured with all details

        Returns:
            SizeCategory enum value
        """
        if self.height < SIZE_THRESHOLD_MICRO:
            return SizeCategory.MICRO
        if self.height < SIZE_THRESHOLD_TINY:
            return SizeCategory.TINY
        if self.height < SIZE_THRESHOLD_SMALL:
            return SizeCategory.SMALL
        if self.height < SIZE_THRESHOLD_MEDIUM:
            return SizeCategory.MEDIUM
        return SizeCategory.LARGE

    @property
    def is_compact(self) -> bool:
        """True if space is limited (MICRO, TINY, or SMALL).

        Use this when you need to simplify layout or hide non-essential
        elements in constrained spaces.

        Returns:
            True for MICRO, TINY, or SMALL size categories
        """
        return self.size_category in (SizeCategory.MICRO, SizeCategory.TINY, SizeCategory.SMALL)

    @property
    def show_secondary(self) -> bool:
        """True if there's room for secondary info.

        Secondary info includes things like: artist name, date, humidity,
        additional labels, etc.

        Returns:
            True for MEDIUM or LARGE size categories
        """
        return self.size_category in (SizeCategory.MEDIUM, SizeCategory.LARGE)

    @property
    def show_tertiary(self) -> bool:
        """True if there's room for tertiary info (full details).

        Tertiary info includes things like: timestamps, detailed values,
        progress time, extended labels, etc.

        Returns:
            True for LARGE size category only
        """
        return self.size_category == SizeCategory.LARGE

    def _resolve_color(self, color: tuple[int, int, int]) -> tuple[int, int, int]:
        """Resolve theme-aware color sentinels to actual colors.

        Widgets construct components with sentinel values like THEME_PRIMARY
        or THEME_WARNING (negative-channel tuples — see widgets.components).
        This method swaps them for the active theme's colors at draw time.
        Lazy import of the sentinel table avoids a circular import.
        """
        if color[0] < 0:
            from .widgets.components import _THEME_COLOR_SENTINELS

            attr = _THEME_COLOR_SENTINELS.get(color)
            if attr is not None:
                return getattr(self.theme, attr)
        return color

    def _abs_point(self, x: int, y: int) -> tuple[int, int]:
        """Convert local point to absolute canvas coordinates."""
        return (self._x1 + x, self._y1 + y)

    def _abs_rect(self, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Convert local rect to absolute canvas coordinates."""
        x1, y1, x2, y2 = rect
        return (self._x1 + x1, self._y1 + y1, self._x1 + x2, self._y1 + y2)

    def _check_point_bounds(self, x: int, y: int, context: str = "") -> None:
        """Log warning if point is outside widget bounds.

        Args:
            x: X coordinate in local space
            y: Y coordinate in local space
            context: Description of the operation for logging
        """
        if x < 0 or x > self.width or y < 0 or y > self.height:
            _LOGGER.debug(
                "Drawing outside widget bounds: %s at (%d, %d), bounds=(0, 0, %d, %d)",
                context or "operation",
                x,
                y,
                self.width,
                self.height,
            )

    def _check_rect_bounds(self, rect: tuple[int, int, int, int], context: str = "") -> None:
        """Log warning if rect extends outside widget bounds.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            context: Description of the operation for logging
        """
        x1, y1, x2, y2 = rect
        if x1 < 0 or y1 < 0 or x2 > self.width or y2 > self.height:
            _LOGGER.debug(
                "Drawing outside widget bounds: %s rect=(%d, %d, %d, %d), bounds=(0, 0, %d, %d)",
                context or "operation",
                x1,
                y1,
                x2,
                y2,
                self.width,
                self.height,
            )

    def is_point_in_bounds(self, x: int, y: int) -> bool:
        """Check if a point is within widget bounds.

        Args:
            x: X coordinate in local space
            y: Y coordinate in local space

        Returns:
            True if point is within bounds
        """
        return 0 <= x <= self.width and 0 <= y <= self.height

    def is_rect_in_bounds(self, rect: tuple[int, int, int, int]) -> bool:
        """Check if a rect is fully within widget bounds.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates

        Returns:
            True if rect is fully within bounds
        """
        x1, y1, x2, y2 = rect
        return x1 >= 0 and y1 >= 0 and x2 <= self.width and y2 <= self.height

    # =========================================================================
    # Font Methods
    # =========================================================================

    def get_font(
        self,
        size_name: str = "secondary",
        bold: bool = False,
        adjust: int = 0,
        semibold: bool = False,
    ) -> FreeTypeFont | ImageFont:
        """Get font scaled for this context's height.

        Args:
            size_name: Font size category. Supports two naming systems:
                - Semantic (preferred): "primary", "secondary", "tertiary"
                - Legacy: "tiny", "small", "regular", "medium", "large", "xlarge", "huge"
            bold: Whether to use bold variant
            adjust: Relative size adjustment (-2 to +2). Each step is ~15% size change.
            semibold: Use SemiBold weight (between regular and bold).
                Takes precedence over `bold` and uses the rounded family.

        Returns:
            Font scaled appropriately for the container size
        """
        return self._renderer.get_scaled_font(
            size_name,
            self._scaled_height,
            bold=bold,
            adjust=adjust,
            rounded=self.theme.rounded_font,
            semibold=semibold,
        )

    def fit_text(
        self,
        text: str,
        max_width: int | None = None,
        max_height: int | None = None,
        bold: bool = False,
    ) -> FreeTypeFont | ImageFont:
        """Get the largest font that fits text within bounds.

        This is useful for text that should fill available space,
        like clock displays or large values.

        Args:
            text: Text to fit
            max_width: Maximum width in unscaled pixels. Defaults to 95% of container width.
            max_height: Maximum height in unscaled pixels. Defaults to 90% of container height.
            bold: Whether to use bold variant

        Returns:
            Font at the largest size that fits within bounds
        """
        # Default to most of the container size
        if max_width is None:
            max_width = int(self.width * 0.95)
        if max_height is None:
            max_height = int(self.height * 0.90)

        # Scale dimensions for supersampling
        scaled_width = max_width * self._renderer.scale
        scaled_height = max_height * self._renderer.scale

        return self._renderer.fit_text_font(
            text,
            max_width=scaled_width,
            max_height=scaled_height,
            bold=bold,
            rounded=self.theme.rounded_font,
        )

    def get_font_for_height(
        self,
        target_height: int,
        bold: bool = False,
    ) -> FreeTypeFont | ImageFont:
        """Get a font at a specific target height in unscaled pixels.

        Useful for scaling fonts proportionally from a measured size.

        Args:
            target_height: Desired font height in unscaled pixels
            bold: Whether to use bold variant

        Returns:
            Font at approximately the target height
        """
        # Scale for supersampling
        scaled_height = target_height * self._renderer.scale
        return self._renderer.get_scaled_font("primary", scaled_height, bold=bold)

    def get_text_size(
        self,
        text: str,
        font: FreeTypeFont | ImageFont | None = None,
    ) -> tuple[int, int]:
        """Get the size of rendered text.

        Args:
            text: Text to measure
            font: Font to use (default: context-scaled regular font)

        Returns:
            (width, height) tuple in unscaled pixels
        """
        if font is None:
            font = self.get_font("regular")
        return self._renderer.get_text_size(text, font)

    # =========================================================================
    # Drawing Methods - all take LOCAL coordinates
    # =========================================================================

    def draw_text(
        self,
        text: str,
        position: tuple[int, int],
        font: FreeTypeFont | ImageFont | None = None,
        color: tuple[int, int, int] = COLOR_WHITE,
        anchor: str | None = None,
    ) -> None:
        """Draw text at position relative to widget origin.

        Args:
            text: Text to draw
            position: (x, y) in local coordinates
            font: Font to use (default: context-scaled regular)
            color: RGB color tuple (supports theme sentinel values)
            anchor: Text anchor (e.g., "mm" for center)
        """
        if font is None:
            font = self.get_font("regular")
        abs_pos = self._abs_point(*position)
        resolved_color = self._resolve_color(color)
        self._renderer.draw_text(
            self._draw, text, abs_pos, font=font, color=resolved_color, anchor=anchor
        )

    def draw_rect(
        self,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_rect(self._draw, abs_rect, fill=fill, outline=outline, width=width)

    def draw_rounded_rect(
        self,
        rect: tuple[int, int, int, int],
        radius: int = 4,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rounded rectangle in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            radius: Corner radius
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_rounded_rect(
            self._draw, abs_rect, radius=radius, fill=fill, outline=outline, width=width
        )

    def draw_panel(
        self,
        rect: tuple[int, int, int, int],
        background: tuple[int, int, int] = COLOR_PANEL,
        border_color: tuple[int, int, int] | None = None,
        radius: int = 4,
    ) -> None:
        """Draw a panel/card background in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            background: Panel background color
            border_color: Optional border color
            radius: Corner radius
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_panel(
            self._draw, abs_rect, background=background, border_color=border_color, radius=radius
        )

    def draw_bar(
        self,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
    ) -> None:
        """Draw a horizontal progress bar in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            percent: Fill percentage (0-100)
            color: Bar fill color
            background: Background color
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_bar(self._draw, abs_rect, percent, color=color, background=background)

    def draw_arc(
        self,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        width: int = 8,
    ) -> None:
        """Draw a circular arc gauge in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            percent: Fill percentage (0-100)
            color: Arc color
            background: Background arc color
            width: Arc line width
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_arc(
            self._draw, abs_rect, percent, color=color, background=background, width=width
        )

    def draw_ring_gauge(
        self,
        center: tuple[int, int],
        radius: int,
        percent: float,
        color: tuple[int, int, int],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        width: int = 6,
    ) -> None:
        """Draw a full circular ring gauge in local coordinates.

        Args:
            center: (x, y) center point in local coordinates
            radius: Ring radius
            percent: Fill percentage (0-100)
            color: Ring color
            background: Background ring color
            width: Ring thickness
        """
        abs_center = self._abs_point(*center)
        self._renderer.draw_ring_gauge(
            self._draw,
            abs_center,
            radius,
            percent,
            color=color,
            background=background,
            width=width,
        )

    def draw_sparkline(
        self,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int],
        fill: bool = True,
        smooth: bool = True,
        gradient: bool = False,
    ) -> None:
        """Draw a sparkline chart in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            data: List of data points
            color: Line color
            fill: Whether to fill area under the line
            smooth: Whether to use spline interpolation
            gradient: Whether to use gradient fill (cool colors for low, warm for high)
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_sparkline(
            self._draw, abs_rect, data, color=color, fill=fill, smooth=smooth, gradient=gradient
        )

    def draw_timeline_bar(
        self,
        rect: tuple[int, int, int, int],
        data: list[float],
        on_color: tuple[int, int, int],
        off_color: tuple[int, int, int] | None = None,
    ) -> None:
        """Draw a timeline bar showing state changes over time.

        Used for binary sensors where data is 0.0 (off) or 1.0 (on).

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            data: List of data points (0.0 for off, 1.0 for on)
            on_color: Color for "on" state (1.0)
            off_color: Color for "off" state (0.0), defaults to gray
        """
        from .const import COLOR_GRAY

        abs_rect = self._abs_rect(rect)
        self._renderer.draw_timeline_bar(
            self._draw,
            abs_rect,
            data,
            on_color=on_color,
            off_color=off_color or COLOR_GRAY,
        )

    def draw_ellipse(
        self,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw an ellipse in local coordinates.

        Args:
            rect: (x1, y1, x2, y2) bounding box in local coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_ellipse(self._draw, abs_rect, fill=fill, outline=outline, width=width)

    def draw_icon(
        self,
        name: str,
        position: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = COLOR_WHITE,
    ) -> None:
        """Draw an icon in local coordinates.

        Args:
            name: Icon name (see Renderer.draw_icon for supported icons)
            position: (x, y) top-left corner in local coordinates
            size: Icon size
            color: Icon color (supports theme sentinel values)
        """
        abs_pos = self._abs_point(*position)
        resolved_color = self._resolve_color(color)
        self._renderer.draw_icon(self._draw, name, abs_pos, size=size, color=resolved_color)

    def draw_line(
        self,
        xy: list[tuple[int, int]],
        fill: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw lines in local coordinates.

        Args:
            xy: List of (x, y) points in local coordinates
            fill: Line color
            width: Line width
        """
        abs_xy = [self._abs_point(*p) for p in xy]
        self._renderer.draw_line(self._draw, abs_xy, fill=fill, width=width)

    def draw_gradient_fade(
        self,
        rect: tuple[int, int, int, int],
        color: tuple[int, int, int] = (0, 0, 0),
        direction: str = "down",
    ) -> None:
        """Draw a vertical alpha-faded gradient onto the canvas.

        Used for watchOS-style soft fades over album art / images.

        Args:
            rect: (x1, y1, x2, y2) in local coordinates
            color: Gradient color (typically black)
            direction: "down" (transparent → opaque) or "up" (opaque → transparent)
        """
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_gradient_fade(self._draw, abs_rect, color=color, direction=direction)

    def draw_image(
        self,
        source: Image.Image,  # type: ignore[name-defined]
        rect: tuple[int, int, int, int] | None = None,
        preserve_aspect: bool = True,
        fit_mode: str | None = None,
    ) -> None:
        """Draw/paste an image in local coordinates.

        Args:
            source: PIL Image to paste
            rect: (x1, y1, x2, y2) destination in local coordinates.
                  If None, fills the entire widget area.
            preserve_aspect: If True, preserve aspect ratio and center (legacy)
            fit_mode: "contain" (letterbox), "cover" (crop), or "stretch".
                      If specified, overrides preserve_aspect.
        """
        if rect is None:
            rect = (0, 0, self.width, self.height)
        abs_rect = self._abs_rect(rect)
        self._renderer.draw_image(
            self._draw, source, abs_rect, preserve_aspect=preserve_aspect, fit_mode=fit_mode
        )

    # =========================================================================
    # Color Utilities
    # =========================================================================

    def dim_color(self, color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
        """Dim a color by a factor."""
        return self._renderer.dim_color(color, factor)

    def blend_color(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        factor: float = 0.5,
    ) -> tuple[int, int, int]:
        """Blend two colors."""
        return self._renderer.blend_color(color1, color2, factor)

    def tint_at(
        self,
        color: tuple[int, int, int],
        opacity: float,
        background: tuple[int, int, int] | None = None,
    ) -> tuple[int, int, int]:
        """Mix `color` at `opacity` over `background` (theme background by default)."""
        bg = background if background is not None else self.theme.background
        return self._renderer.tint_at(color, opacity, background=bg)

    def track_color(self, tint: tuple[int, int, int]) -> tuple[int, int, int]:
        """Compute the bar/ring/arc track color for a given tint, honoring theme.

        watchOS-style themes return a soft tint of the accent color; classic
        themes can return a flat gray via Theme.tint_track=False.
        """
        if self.theme.tint_track:
            return self._renderer.tint_at(
                tint, self.theme.tint_track_opacity, self.theme.background
            )
        return self.theme.bar_background

    # =========================================================================
    # Semantic Drawing Helpers (watchOS-style hierarchy)
    # =========================================================================

    def draw_label(
        self,
        text: str,
        position: tuple[int, int],
        color: tuple[int, int, int] | None = None,
        anchor: str = "lt",
        size: str = "small",
        adjust: int = 0,
        uppercase: bool = True,
        track: int = 0,
        max_width: int | None = None,
    ) -> tuple[int, int]:
        """Draw a watchOS-style caption label.

        Defaults to uppercase, secondary color, fixed-size legacy 'small'
        font (≈14px) — small enough to never overflow even in big cells,
        large enough to remain readable. Tracking is OFF by default
        because per-glyph tracking inflates width by ~5-10% and tends to
        truncate longer labels; callers can opt in with track>0 when
        they have width budget.

        Args:
            text: Label text (will be uppercased unless uppercase=False)
            position: (x, y) anchor point in local coordinates
            color: Override color (default = theme.text_secondary)
            anchor: PIL text anchor (e.g. "lt", "lm", "rm")
            size: Font size name (default "small" — fixed legacy size)
            adjust: Relative size adjustment for the label font
            uppercase: Convert to uppercase
            track: Letter-spacing in px between glyphs. Defaults to 0
                (no tracking). Tracking is auto-dropped if it would
                overflow max_width.
            max_width: Width budget. Rendered text is truncated with an
                ellipsis when it exceeds this. Defaults to ~95% of widget
                width.

        Returns:
            (width, height) of rendered text in unscaled px
        """
        if uppercase:
            text = text.upper()
        if max_width is None:
            max_width = int(self.width * 0.95)

        font = self.get_font(size, adjust=adjust)
        c = color if color is not None else self.theme.text_secondary

        # Use full-string measurement (accurate, accounts for glyph bearings).
        full_w = self.get_text_size(text, font=font)[0]
        if full_w > max_width:
            ellipsis = "…"
            t = text
            while len(t) > 1 and self.get_text_size(t + ellipsis, font=font)[0] > max_width:
                t = t[:-1]
            text = (t + ellipsis) if len(t) >= 1 else ellipsis
            full_w = self.get_text_size(text, font=font)[0]
            track = 0  # No tracking on truncated labels
        elif track > 0 and full_w + track * (len(text) - 1) > max_width:
            track = 0  # Drop tracking if it would push us past the budget

        if track <= 0 or len(text) <= 1:
            self.draw_text(text, position, font=font, color=c, anchor=anchor)
            return self.get_text_size(text, font=font)

        # Glyph-by-glyph render with `track` px between to simulate letter-spacing.
        widths = [self.get_text_size(ch, font=font)[0] for ch in text]
        total_w = sum(widths) + track * (len(text) - 1)
        h = self.get_text_size("M", font=font)[1]

        x, y = position
        ax = anchor[0] if anchor else "l"
        ay = anchor[1] if len(anchor) > 1 else "t"
        if ax == "m":
            x = x - total_w // 2
        elif ax == "r":
            x = x - total_w
        if ay == "m":
            y = y - h // 2
        elif ay == "b":
            y = y - h
        elif ay == "s":
            y = y - int(h * 0.85)

        for i, ch in enumerate(text):
            self.draw_text(ch, (x, y), font=font, color=c, anchor="lt")
            x += widths[i] + track
        return total_w, h
