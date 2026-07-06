"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .components import Component
    from .state import EntityState, WidgetState

# Shared schema row for the per-widget text size adjustment (issue #31).
# Widgets that are primarily text-driven append this to their SCHEMA
# "options" list so the panel editor offers the field. The value is
# applied as a base font adjustment for every ctx.get_font() call
# (each step is ~15% size change); auto-fit text (ctx.fit_text) keeps
# its hard ceiling and may ignore an increase that wouldn't fit.
SIZE_ADJUST_OPTION: dict[str, Any] = {
    "key": "size_adjust",
    "type": "number",
    "label": "Text Size",
    "min": -2,
    "max": 2,
    "default": 0,
}


def _parse_size_adjust(value: Any) -> int:
    """Coerce a raw size_adjust option to an int clamped to [-2, 2].

    The panel's number field stores parseFloat output, so the value can
    arrive as a float over JSON; a cleared field can arrive as ""/None.
    """
    try:
        adjust = int(value or 0)
    except (TypeError, ValueError):
        adjust = 0
    return max(-2, min(2, adjust))


@dataclass
class WidgetConfig:
    """Configuration for a widget."""

    widget_type: str
    slot: int = 0
    entity_id: str | None = None
    label: str | None = None
    color: tuple[int, int, int] | None = None
    options: dict[str, Any] = field(default_factory=dict)


class Widget(ABC):
    """Base class for all widgets.

    Widgets render by returning a Component tree. All state needed for
    rendering is passed via the WidgetState parameter, enabling pure
    functional rendering.
    """

    WIDGET_TYPE: ClassVar[str] = ""
    SCHEMA: ClassVar[dict[str, Any]] = {}

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the widget.

        Args:
            config: Widget configuration
        """
        self.config = config
        # Per-widget base font adjustment (issue #31). Threaded into the
        # widget's RenderContext so every ctx.get_font() call picks it up.
        self.size_adjust = _parse_size_adjust(config.options.get("size_adjust", 0))

    @property
    def entity_id(self) -> str | None:
        """Get the entity ID this widget tracks."""
        return self.config.entity_id

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on.

        Override in subclasses that track entities.
        """
        if self.config.entity_id:
            return [self.config.entity_id]
        return []

    def label_for(self, entity: EntityState | None, *, fallback: str = "") -> str:
        """Resolve display label: ``config.label`` > ``entity.friendly_name`` > ``fallback``.

        Pretty much every widget that renders a name needs this chain.
        ``EntityState.friendly_name`` already falls back to ``entity_id``
        when no friendly name attribute is set, so widgets that previously
        wrote ``entity.friendly_name or entity.entity_id`` collapse to
        a single ``self.label_for(entity, fallback=...)``.
        """
        if self.config.label:
            return self.config.label
        if entity is not None:
            return entity.friendly_name
        return fallback

    @abstractmethod
    def render(
        self,
        ctx: RenderContext,
        state: WidgetState,
    ) -> Component:
        """Render the widget as a Component tree.

        Pure function: given the same ctx and state, returns the same Component.
        All state needed for rendering is provided via the state parameter.

        Args:
            ctx: RenderContext providing local coordinate system and drawing methods.
                 Use ctx.width and ctx.height for container dimensions.
                 All drawing coordinates are relative to widget origin (0, 0).
            state: Pre-fetched state including entity data, history, images, time.

        Returns:
            Component tree to render
        """
