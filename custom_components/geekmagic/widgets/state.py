"""Widget state containers for pure render pattern.

These immutable dataclasses are injected into widget render() methods,
providing all state needed for rendering without side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from PIL import Image

    from .base import Widget


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

    def numeric(self, attribute: str | None = None, default: float = 0.0) -> float:
        """Coerce the state (or an attribute) to float, with a safe fallback.

        Widgets reach for this constantly — gauges, progress bars, sparkline
        sources — and used to each carry their own ``_extract_numeric``
        helper. Centralising it here keeps the conversion rule (any
        ValueError/TypeError → ``default``) in one place.
        """
        raw = self.attributes.get(attribute) if attribute else self.state
        if raw is None:
            return default
        try:
            return float(raw)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return default


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


def build_entity_states(
    get_state: Callable[[str], Any],
    widget: Widget,
) -> tuple[EntityState | None, dict[str, EntityState]]:
    """Snapshot a widget's entity dependencies as EntityStates.

    Returns the primary entity (from ``widget.config.entity_id``) and a
    mapping of every additional entity declared by
    ``widget.get_entities()``. ``get_state`` is ``hass.states.get`` (or
    any lookalike returning objects with ``entity_id``/``state``/
    ``attributes``); missing entities are skipped so widgets keep their
    graceful unknown/empty fallbacks.

    Shared by the coordinator's production render and the websocket
    preview so both resolve the same dependencies for a widget.
    """

    def snapshot(entity_id: str) -> EntityState | None:
        ha_state = get_state(entity_id)
        if ha_state is None:
            return None
        return EntityState(
            entity_id=ha_state.entity_id,
            state=ha_state.state,
            attributes=dict(ha_state.attributes),
        )

    primary_id = widget.config.entity_id
    primary = snapshot(primary_id) if primary_id else None
    additional: dict[str, EntityState] = {}
    for eid in widget.get_entities():
        if eid == primary_id or eid in additional:
            continue
        entity = snapshot(eid)
        if entity is not None:
            additional[eid] = entity
    return primary, additional
