"""Widget state containers for pure render pattern.

These immutable dataclasses are injected into widget render() methods,
providing all state needed for rendering without side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from PIL import Image


@dataclass(frozen=True)
class EntityState:
    """Immutable snapshot of a Home Assistant entity state.

    Provides convenient properties for common attributes.
    """

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def friendly_name(self) -> str:
        """Get friendly name or entity_id as fallback."""
        return self.attributes.get("friendly_name", self.entity_id)

    @property
    def unit(self) -> str:
        """Get unit of measurement."""
        return self.attributes.get("unit_of_measurement", "")

    @property
    def icon(self) -> str | None:
        """Get icon name."""
        return self.attributes.get("icon")

    @property
    def device_class(self) -> str | None:
        """Get device class."""
        return self.attributes.get("device_class")

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value."""
        return self.attributes.get(key, default)


@dataclass(frozen=True)
class WidgetState:
    """All state a widget needs to render, injected by coordinator.

    This enables pure functional rendering - given the same ctx and state,
    render() returns the same Component tree.

    Attributes:
        entity: Primary entity from config.entity_id
        entities: Additional entities for multi-entity widgets
        history: Pre-fetched history data for charts
        image: Pre-fetched camera image
        forecast: Pre-fetched weather forecast data
        now: Current datetime with timezone
    """

    # Primary entity (from config.entity_id)
    entity: EntityState | None = None

    # Additional entities (for multi-entity widgets like weather)
    entities: dict[str, EntityState] = field(default_factory=dict)

    # Pre-fetched data
    history: list[float] = field(default_factory=list)
    candlestick_data: list[tuple[float, float, float, float]] = field(default_factory=list)
    image: Image.Image | None = field(default=None)
    forecast: list[dict[str, Any]] = field(default_factory=list)

    # Current time (for clock widgets)
    now: datetime | None = None

    def get_entity(self, entity_id: str) -> EntityState | None:
        """Get entity by ID, checking primary first then entities dict."""
        if self.entity and self.entity.entity_id == entity_id:
            return self.entity
        return self.entities.get(entity_id)

    def has_history(self) -> bool:
        """Check if history data is available."""
        return len(self.history) >= 2
