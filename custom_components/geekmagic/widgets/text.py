"""Text widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
    Component,
    _resolve_color,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


# Map widget align to component align
ALIGN_MAP: dict[str, Literal["start", "center", "end"]] = {
    "left": "start",
    "center": "center",
    "right": "end",
}


@dataclass
class TextDisplay(Component):
    """Text display component that fills available space.

    The main text automatically sizes to fill the container.
    Optional label appears above the main text.
    """

    text: str
    label: str | None = None
    color: Color = THEME_TEXT_PRIMARY
    label_color: Color = THEME_TEXT_SECONDARY
    align: Literal["start", "center", "end"] = "center"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render text filling available space."""
        padding = int(width * 0.05)
        inner_width = width - padding * 2
        inner_height = height - padding * 2

        # Resolve theme-aware colors
        text_color = _resolve_color(self.color, ctx)
        label_color = _resolve_color(self.label_color, ctx)

        # Calculate vertical space distribution
        label_height = 0
        gap = 4

        if self.label:
            label_height = int(inner_height * 0.15)

        # Text gets remaining space
        text_height = inner_height - label_height
        if self.label:
            text_height -= gap

        # Vertical centering
        total_content = label_height + text_height
        if self.label:
            total_content += gap
        start_y = y + padding + (inner_height - total_content) // 2

        current_y = start_y

        # Horizontal alignment
        if self.align == "start":
            text_x = x + padding
            anchor_h = "l"
        elif self.align == "end":
            text_x = x + width - padding
            anchor_h = "r"
        else:
            text_x = x + width // 2
            anchor_h = "m"

        # Draw label if provided
        if self.label:
            label_font = ctx.get_font("small")
            ctx.draw_text(
                self.label.upper(),
                (x + width // 2, current_y + label_height // 2),
                font=label_font,
                color=label_color,
                anchor="mm",
            )
            current_y += label_height + gap

        # Draw main text (fills available space)
        text_font = ctx.fit_text(
            self.text,
            max_width=int(inner_width * 0.95),
            max_height=int(text_height * 0.90),
            bold=False,
        )
        ctx.draw_text(
            self.text,
            (text_x, current_y + text_height // 2),
            font=text_font,
            color=text_color,
            anchor=f"{anchor_h}m",
        )


class TextWidget(Widget):
    """Widget that displays static or dynamic text."""

    WIDGET_TYPE: ClassVar[str] = "text"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Text",
        "needs_entity": False,
        "options": [
            {"key": "text", "type": "text", "label": "Text Content"},
            {"key": "entity_id", "type": "entity", "label": "Entity (dynamic text)"},
            {
                "key": "size",
                "type": "select",
                "label": "Size",
                "options": ["small", "regular", "large", "xlarge"],
                "default": "regular",
            },
            {
                "key": "align",
                "type": "select",
                "label": "Alignment",
                "options": ["left", "center", "right"],
                "default": "center",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the text widget."""
        super().__init__(config)
        self.text = config.options.get("text", "")
        self.size = config.options.get("size", "regular")  # small, regular, large, xlarge
        self.align = config.options.get("align", "center")  # left, center, right
        # Entity ID for dynamic text (from options, takes precedence over widget entity_id)
        self.dynamic_entity_id = config.options.get("entity_id")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the text widget.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with entity data

        Returns:
            Component tree for rendering
        """
        text = self._get_text(state)
        color = self.config.color or THEME_TEXT_PRIMARY
        align = ALIGN_MAP.get(self.align, "center")

        return TextDisplay(
            text=text,
            label=self.config.label,
            color=color,
            align=align,
        )

    def _get_text(self, state: WidgetState) -> str:
        """Get the text to display.

        If entity_id is set (from options or widget config), returns the entity state.
        Otherwise returns the configured text.
        """
        # Check for entity in state (from config.entity_id or dynamic_entity_id)
        if state.entity:
            return state.entity.state

        # Check for dynamic entity in additional entities
        if self.dynamic_entity_id:
            entity = state.get_entity(self.dynamic_entity_id)
            if entity:
                return entity.state

        return self.text

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on."""
        entities = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.dynamic_entity_id and self.dynamic_entity_id != self.config.entity_id:
            entities.append(self.dynamic_entity_id)
        return entities
