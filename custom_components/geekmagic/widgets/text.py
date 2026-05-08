"""Text widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .components import THEME_TEXT_PRIMARY, Component
from .data_card import DataCard

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class TextWidget(Widget):
    """Widget that displays static or dynamic text via ``DataCard``.

    Maps to ``DataCard(caption=label, hero=text)`` — the watchOS
    caption-above-hero pattern. The hero auto-fits the cell, so the
    legacy ``size`` option (small/regular/large/xlarge) is no longer
    needed and is silently ignored if present in stored configs.
    Likewise the legacy ``align`` option is ignored — text is centred
    in the watchOS contract.
    """

    WIDGET_TYPE: ClassVar[str] = "text"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Text",
        "needs_entity": False,
        "options": [
            {"key": "text", "type": "text", "label": "Text Content"},
            {"key": "entity_id", "type": "entity", "label": "Entity (dynamic text)"},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the text widget."""
        super().__init__(config)
        self.text = config.options.get("text", "")
        # Entity ID for dynamic text (from options, takes precedence over widget entity_id)
        self.dynamic_entity_id = config.options.get("entity_id")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the text widget."""
        return DataCard(
            caption=self.config.label,
            hero=self._get_text(state),
            hero_color=self.config.color or THEME_TEXT_PRIMARY,
        )

    def _get_text(self, state: WidgetState) -> str:
        """Get the text to display.

        If entity_id is set (from options or widget config), returns the entity state.
        Otherwise returns the configured text.
        """
        if state.entity:
            return state.entity.state
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
