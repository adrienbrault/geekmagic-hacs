"""Shared test doubles.

``WidgetDataResolver.build_states`` only touches two attributes of
``hass`` — ``states.get`` and ``config`` — so tests exercise it through
this narrow duck-typed adapter instead of the full HA harness. Kept
deliberately dumb: ``set`` stores exactly what it is handed, so a test
asserting on attributes sees only what it wrote (unlike
``scripts/mock_hass.py``, whose sample-generation variant auto-resolves
an ``icon`` attribute).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockState:
    """Mock entity state."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


class MockStates:
    """Mock states registry."""

    def __init__(self) -> None:
        """Initialize the mock states registry."""
        self._states: dict[str, MockState] = {}

    def set(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> None:
        """Set a mock entity state."""
        self._states[entity_id] = MockState(
            entity_id=entity_id,
            state=state,
            attributes=attributes or {},
        )

    def get(self, entity_id: str) -> MockState | None:
        """Get a mock entity state."""
        return self._states.get(entity_id)


class MockConfig:
    """Mock Home Assistant config."""

    time_zone_obj = None


class MockHass:
    """Mock Home Assistant instance."""

    def __init__(self) -> None:
        """Initialize the mock Home Assistant."""
        self.states = MockStates()
        self.config = MockConfig()
