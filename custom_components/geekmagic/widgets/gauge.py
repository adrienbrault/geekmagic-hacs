"""Gauge widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .base import SIZE_ADJUST_OPTION, Widget, WidgetConfig
from .component_helpers import ArcGauge, BarGauge, RingGauge
from .components import Component
from .helpers import calculate_percent, format_value_with_unit

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class GaugeWidget(Widget):
    """Widget that displays a value as a gauge (bar or ring)."""

    WIDGET_TYPE: ClassVar[str] = "gauge"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Gauge",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {
                "key": "style",
                "type": "select",
                "label": "Style",
                "options": ["bar", "ring", "arc"],
                "default": "bar",
            },
            {
                # Only meaningful when style="bar". Auto picks based on
                # cell shape (vertical for tall+narrow, stacked for
                # square hero cells, compact for everything else).
                "key": "orientation",
                "type": "select",
                "label": "Bar Orientation",
                "options": ["auto", "compact", "stacked", "vertical"],
                "default": "auto",
            },
            {"key": "min", "type": "number", "label": "Minimum", "default": 0},
            {"key": "max", "type": "number", "label": "Maximum", "default": 100},
            {"key": "unit", "type": "text", "label": "Unit Override"},
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_value", "type": "boolean", "label": "Show Value", "default": True},
            {"key": "show_unit", "type": "boolean", "label": "Show Unit", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon"},
            {"key": "attribute", "type": "text", "label": "Entity Attribute"},
            {
                "key": "precision",
                "type": "number",
                "label": "Decimal Places",
                "min": 0,
                "max": 5,
            },
            {"key": "color_thresholds", "type": "thresholds", "label": "Color Thresholds"},
            SIZE_ADJUST_OPTION,
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the gauge widget."""
        super().__init__(config)
        self.style = config.options.get("style", "bar")  # bar, ring, arc
        # auto / compact / stacked / vertical — only meaningful for bar style.
        self.orientation = config.options.get("orientation", "auto")
        self.min_value = config.options.get("min", 0)
        self.max_value = config.options.get("max", 100)
        # Normalise icon: ``ha-icon-picker`` writes ``""`` when cleared, but
        # downstream the empty string used to render as ``help-circle``.
        self.icon = config.options.get("icon") or None
        self.show_name = config.options.get("show_name", True)
        self.show_value = config.options.get("show_value", True)
        self.show_unit = config.options.get("show_unit", True)
        self.unit = config.options.get("unit", "")
        # Attribute to read value from
        self.attribute = config.options.get("attribute")
        # Decimal places for the displayed value (None = legacy whole-number)
        self.precision = config.options.get("precision")
        # Color thresholds
        self.color_thresholds = config.options.get("color_thresholds", [])

    def _get_threshold_color(self, value: float) -> tuple[int, int, int] | None:
        """Get color based on value and thresholds."""
        if not self.color_thresholds:
            return None

        sorted_thresholds = sorted(self.color_thresholds, key=lambda t: t.get("value", 0))
        matching_color: tuple[int, int, int] | None = None
        for threshold in sorted_thresholds:
            threshold_value = threshold.get("value", 0)
            threshold_color = threshold.get("color")
            if (
                value >= threshold_value
                and isinstance(threshold_color, list | tuple)
                and len(threshold_color) == 3
            ):
                matching_color = (
                    int(threshold_color[0]),
                    int(threshold_color[1]),
                    int(threshold_color[2]),
                )

        return matching_color

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the gauge widget.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with entity data

        Returns:
            Component tree for rendering
        """
        entity = state.entity

        # Extract numeric value
        value = entity.numeric(self.attribute) if entity is not None else 0.0
        # The panel's number field stores parseFloat output, so precision can
        # arrive as a float over JSON — coerce to a non-negative int.
        try:
            precision = max(0, int(self.precision)) if self.precision is not None else 0
        except (TypeError, ValueError):
            precision = 0
        display_value = f"{value:.{precision}f}" if entity is not None else "--"

        # Get unit (override > entity unit, suppressed when show_unit is off).
        if not self.show_unit:
            unit = ""
        else:
            unit = self.unit
            if not unit and entity is not None:
                unit = entity.unit or ""

        # Calculate percentage
        percent = calculate_percent(value, self.min_value, self.max_value)

        # Get label — empty string when hidden so DataCard drops the caption band.
        name = self.label_for(entity) if self.show_name else ""

        # Determine color
        threshold_color = self._get_threshold_color(value)
        color = threshold_color or self.config.color or ctx.theme.get_accent_color(self.config.slot)

        # Format value with unit
        value_text = format_value_with_unit(display_value, unit) if self.show_value else ""

        # Track color stays None so the theme's tinted track applies
        if self.style == "ring":
            return RingGauge(percent=percent, value=value_text, label=name, color=color)
        if self.style == "arc":
            return ArcGauge(percent=percent, value=value_text, label=name, color=color)
        return BarGauge(
            percent=percent,
            value=value_text,
            label=name,
            color=color,
            icon=self.icon,
            mode=self.orientation,
        )
