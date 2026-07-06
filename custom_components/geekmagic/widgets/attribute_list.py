"""Attribute list widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import PLACEHOLDER_NAME, PLACEHOLDER_VALUE
from .base import Widget, WidgetConfig
from .components import (
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
    Column,
    Component,
    Text,
    _resolve_color,
)
from .helpers import abbreviate_label

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
    value_color: Color = THEME_PRIMARY  # Theme-aware sentinel
    gap: int = 8  # Minimum gap between label and value

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        font = ctx.get_font("small", bold=False)
        _, h = ctx.get_text_size("Hg", font)
        return (max_width, h)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        label_font = ctx.get_font("small", bold=False)
        value_font = ctx.get_font("small", bold=True)

        # Measure natural sizes
        label = self.label
        label_width, _ = ctx.get_text_size(label, label_font)
        value_width, _ = ctx.get_text_size(self.value, value_font)

        # Resolve colors
        label_color = _resolve_color(self.label_color, ctx)
        value_color = _resolve_color(self.value_color, ctx)

        available = width - self.gap
        total_needed = label_width + value_width

        if total_needed > available:
            # Try a conventional abbreviation ("Temperature" → "Temp")
            # before resorting to an ellipsis.
            short = abbreviate_label(label)
            if short:
                label = short
                label_width, _ = ctx.get_text_size(label, label_font)
                total_needed = label_width + value_width

        if total_needed <= available:
            # Everything fits - no truncation needed
            display_label = label
            display_value = self.value
        elif value_width >= int(width * 0.7):
            # Drop the label entirely if the value alone barely fits — the
            # value carries the actual information, and "Arr… 5 m…" is worse
            # than just "5 min".
            display_label = ""
            display_value = ctx.truncate_to_width(self.value, value_font, width)
        elif value_width <= available:
            # Value fits in full; give the rest to a truncated label.
            display_label = ctx.truncate_to_width(label, label_font, available - value_width)
            display_value = self.value
        else:
            # Value doesn't fit either — give value 60% of available width,
            # label 40%, and truncate both.
            value_max = max(int(available * 0.60), available - label_width)
            label_max = available - value_max
            display_label = ctx.truncate_to_width(label, label_font, label_max)
            display_value = ctx.truncate_to_width(self.value, value_font, value_max)

        # Draw label (left-aligned)
        if display_label:
            ctx.draw_text(
                display_label,
                (x, y + height // 2),
                label_font,
                label_color,
                anchor="lm",
            )

        # Draw value (right-aligned when there's a label, else left-aligned)
        anchor = "rm" if display_label else "lm"
        value_x = x + width if display_label else x
        ctx.draw_text(
            display_value,
            (value_x, y + height // 2),
            value_font,
            value_color,
            anchor=anchor,
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
        padding = max(2, int(min(width, height) * 0.05))

        # At narrow widths the title eats a row that would be better spent
        # on actual data; drop it.
        show_title = bool(self.title) and width >= 100
        title = self.title or ""

        rows: list[Component] = []
        if show_title:
            rows.append(
                Text(
                    text=title.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                    truncate=True,
                )
            )

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

        # Use a tight gap so all rows have a chance to fit before the flex
        # shrink kicks in. Column will proportionally shrink each row's
        # height if total content exceeds the container.
        # space-evenly distributes the rows across tall cells (fullscreen /
        # hero slots) instead of clustering them at the top; when content
        # overflows it degrades to the same packed layout as justify="start".
        Column(
            children=rows,
            gap=3 if show_title else 2,
            padding=padding,
            align="stretch",
            justify="space-evenly",
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

    WIDGET_TYPE: ClassVar[str] = "attribute_list"

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the attribute list widget."""
        super().__init__(config)
        self.attributes = config.options.get("attributes", [])
        self.title = config.options.get("title")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the attribute list widget."""
        entity = state.entity
        # Per design system: list-row values default to text_primary (white)
        # — they're "values", not gauge accents. Users (or per-attribute
        # config) can still tint individual rows by passing an explicit
        # `color`. self.config.color overrides the default for the whole
        # widget; the slot accent is only used as a final fallback when
        # the widget config explicitly marks the colour as
        # accent-controlled (kept for backwards compat).
        default_color: Color = self.config.color or THEME_TEXT_PRIMARY

        items: list[tuple[str, str, Color]] = []

        for attr_config in self.attributes:
            # Support both dict format and simple string format
            if isinstance(attr_config, dict):
                key = attr_config.get("key", "")
                label = attr_config.get("label", key)
                item_color = attr_config.get("color", default_color)
                if isinstance(item_color, list):
                    item_color = tuple(item_color)
            else:
                # Simple string format: use attribute name as both key and label
                key = str(attr_config)
                label = key
                item_color = default_color

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
