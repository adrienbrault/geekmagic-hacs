"""Attribute list widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..const import COLOR_CYAN, PLACEHOLDER_NAME, PLACEHOLDER_VALUE
from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_SECONDARY,
    Color,
    Column,
    Component,
    Text,
    _resolve_color,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


@dataclass
class LabelValueRow(Component):
    """A row with label on the left and value on the right, with proper truncation.

    This component properly allocates width between label and value,
    ensuring text is truncated based on actual pixel measurements rather
    than character count estimates.
    """

    label: str
    value: str
    label_color: Color = THEME_TEXT_SECONDARY
    value_color: Color = (0, 255, 255)
    gap: int = 8  # Minimum gap between label and value

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        font = ctx.get_font("small", bold=False)
        _, h = ctx.get_text_size("Hg", font)
        return (max_width, h)

    def _truncate_to_width(self, ctx: RenderContext, text: str, font: Any, max_width: int) -> str:
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
        label_font = ctx.get_font("small", bold=False)
        value_font = ctx.get_font("small", bold=True)

        # Measure natural sizes
        label_width, _ = ctx.get_text_size(self.label, label_font)
        value_width, _ = ctx.get_text_size(self.value, value_font)

        # Resolve colors
        label_color = _resolve_color(self.label_color, ctx)
        value_color = _resolve_color(self.value_color, ctx)

        available = width - self.gap
        total_needed = label_width + value_width

        if total_needed <= available:
            # Everything fits - no truncation needed
            display_label = self.label
            display_value = self.value
            # Position: label at start, value at end
            label_x = x
            value_x = x + width
        else:
            # Need to truncate - allocate space proportionally
            # Give slightly more space to value (40% label, 60% value when both overflow)
            label_max = int(available * 0.40)
            value_max = available - label_max

            # But if one side doesn't need its full allocation, give extra to the other
            if label_width <= label_max:
                # Label fits, give remaining to value
                value_max = available - label_width
                display_label = self.label
            elif value_width <= value_max:
                # Value fits, give remaining to label
                label_max = available - value_width
                display_label = self._truncate_to_width(ctx, self.label, label_font, label_max)
            else:
                # Both need truncation
                display_label = self._truncate_to_width(ctx, self.label, label_font, label_max)

            display_value = self._truncate_to_width(ctx, self.value, value_font, value_max)
            label_x = x
            value_x = x + width

        # Draw label (left-aligned)
        ctx.draw_text(
            display_label,
            (label_x, y + height // 2),
            label_font,
            label_color,
            anchor="lm",
        )

        # Draw value (right-aligned)
        ctx.draw_text(
            display_value,
            (value_x, y + height // 2),
            value_font,
            value_color,
            anchor="rm",
        )


@dataclass
class AttributeListDisplay(Component):
    """Attribute list display component."""

    items: list[tuple[str, str, Color]] = field(default_factory=list)  # (label, value, color)
    title: str | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render attribute list using component primitives."""
        padding = int(width * 0.05)

        # Build list of rows
        rows: list[Component] = []

        # Add title if provided
        if self.title:
            rows.append(
                Text(
                    text=self.title.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                    truncate=True,
                )
            )

        # Build each item row using LabelValueRow for proper truncation
        for label, value, color in self.items:
            rows.append(
                LabelValueRow(
                    label=label,
                    value=str(value),
                    label_color=THEME_TEXT_SECONDARY,
                    value_color=color,
                    gap=6,
                )
            )

        # Render all rows in a column
        Column(
            children=rows,
            gap=4 if self.title else 2,
            padding=padding,
            align="stretch",
            justify="start",
        ).render(ctx, x, y, width, height)


class AttributeListWidget(Widget):
    """Widget that displays a list of entity attributes as key-value pairs.

    Configuration example:
        widget:
          type: attribute_list
          entity_id: sensor.bus_arrival
          options:
            title: "Bus Info"
            attributes:
              - key: route_name
                label: "Route"
              - key: destination
                label: "To"
              - key: state
                label: "Arrives"
    """

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the attribute list widget."""
        super().__init__(config)
        self.attributes = config.options.get("attributes", [])
        self.title = config.options.get("title")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the attribute list widget."""
        entity = state.entity
        color = self.config.color or COLOR_CYAN

        items: list[tuple[str, str, Color]] = []

        for attr_config in self.attributes:
            # Support both dict format and simple string format
            if isinstance(attr_config, dict):
                key = attr_config.get("key", "")
                label = attr_config.get("label", key)
                item_color = attr_config.get("color", color)
                if isinstance(item_color, list):
                    item_color = tuple(item_color)
            else:
                # Simple string format: use attribute name as both key and label
                key = str(attr_config)
                label = key
                item_color = color

            # Get value from entity
            if entity is None:
                value = PLACEHOLDER_VALUE
            elif key == "state":
                # Special case: "state" refers to entity state, not an attribute
                value = entity.state
            else:
                raw_value = entity.get(key)
                value = self._format_value(raw_value)

            items.append((label, value, item_color))

        # If no attributes configured, show friendly name as title
        title = self.title
        if not title and entity:
            title = entity.friendly_name
        elif not title:
            title = self.config.entity_id or PLACEHOLDER_NAME

        return AttributeListDisplay(
            items=items,
            title=title if not self.attributes else self.title,
        )

    def _format_value(self, value: Any) -> str:
        """Format attribute value for display."""
        if value is None:
            return PLACEHOLDER_VALUE
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, float):
            # Format floats with reasonable precision
            return str(int(value)) if value == int(value) else f"{value:.1f}"
        if isinstance(value, list):
            return f"[{len(value)} items]"
        if isinstance(value, dict):
            return f"{{{len(value)} keys}}"
        return str(value)
