"""Custom free-form layout for GeekMagic displays."""

from __future__ import annotations

from .base import Layout, Slot


def _int_or(value: object, default: int) -> int:
    """Coerce ``value`` to an int, returning ``default`` on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


class CustomLayout(Layout):
    """Free-form layout where each widget defines its own position and size.

    Widgets are placed using absolute coordinates on the 240x240 display.
    This allows arbitrary overlapping or non-grid layouts while keeping the
    same rendering pipeline as the fixed slot layouts.
    """

    def __init__(
        self,
        widgets: list[dict] | None = None,
        padding: int | None = None,
        gap: int | None = None,
        background_image: str | None = None,
        background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0,
    ) -> None:
        """Initialize the custom layout.

        Args:
            widgets: List of widget configuration dicts. Each dict should
                contain ``x``, ``y``, ``width``, ``height`` plus the usual
                widget config keys. Coordinates are clamped to the display.
            padding: Ignored for custom layouts (outer padding is controlled
                by widget coordinates), kept for API compatibility.
            gap: Ignored for custom layouts.
            background_image: Optional path to a local background image.
            background_mode: How to fit the image: stretch, contain, cover.
            widget_contrast: Opacity of dark contrast panel behind widgets.
            text_scale: Extra scaling factor for text and icons.
            text_opacity: Opacity multiplier for text/icon colors.
        """
        self._widgets_config = widgets or []
        # padding/gap are intentionally not used for slot calculation, but we
        # still pass them through so the base Layout constructor is happy.
        super().__init__(
            padding=0,
            gap=0,
            background_image=background_image,
            background_mode=background_mode,
            widget_contrast=widget_contrast,
            text_scale=text_scale,
            text_opacity=text_opacity,
        )

    def _calculate_slots(self) -> None:
        """Build slots from the supplied widget coordinates."""
        self.slots = []
        for index, widget_config in enumerate(self._widgets_config):
            x = _int_or(widget_config.get("x", 0), 0)
            y = _int_or(widget_config.get("y", 0), 0)
            width = _int_or(widget_config.get("width", self.width), self.width)
            height = _int_or(widget_config.get("height", self.height), self.height)

            # Clamp to display bounds so widgets cannot render outside the canvas.
            x1 = max(0, min(x, self.width))
            y1 = max(0, min(y, self.height))
            x2 = max(x1, min(x + width, self.width))
            y2 = max(y1, min(y + height, self.height))

            self.slots.append(Slot(index=index, rect=(x1, y1, x2, y2)))
