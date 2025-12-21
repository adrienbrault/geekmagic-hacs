"""RenderContext provides widgets with a local coordinate system.

This abstraction allows widgets to work in coordinates relative to their
container (0, 0 to width, height) instead of absolute canvas coordinates.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import COLOR_DARK_GRAY, COLOR_PANEL, COLOR_WHITE

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
    ) -> FreeTypeFont | ImageFont:
        """Get font scaled for this context's height.

        Args:
            size_name: Font size category. Supports two naming systems:
                - Semantic (preferred): "primary", "secondary", "tertiary"
                - Legacy: "tiny", "small", "regular", "medium", "large", "xlarge", "huge"
            bold: Whether to use bold variant
            adjust: Relative size adjustment (-2 to +2). Each step is ~15% size change.

        Returns:
            Font scaled appropriately for the container size
        """
        return self._renderer.get_scaled_font(
            size_name, self._scaled_height, bold=bold, adjust=adjust
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
        )

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
            color: RGB color tuple
            anchor: Text anchor (e.g., "mm" for center)
        """
        if font is None:
            font = self.get_font("regular")
        abs_pos = self._abs_point(*position)
        self._renderer.draw_text(self._draw, text, abs_pos, font=font, color=color, anchor=anchor)

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
            color: Icon color
        """
        abs_pos = self._abs_point(*position)
        self._renderer.draw_icon(self._draw, name, abs_pos, size=size, color=color)

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
