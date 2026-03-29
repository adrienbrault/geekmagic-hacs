"""Switch entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import CONF_SCREEN_CYCLE_INTERVAL, DOMAIN
from .base import GeekMagicEntity

if TYPE_CHECKING:
    from ..coordinator import GeekMagicCoordinator

_LOGGER = logging.getLogger(__name__)

# Default cycle interval when turning on (if no previous value stored)
DEFAULT_CYCLE_ON_INTERVAL = 30


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeekMagic switch entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GeekMagicViewCyclingSwitch(coordinator),
    ]

    async_add_entities(entities)


class GeekMagicViewCyclingSwitch(GeekMagicEntity, SwitchEntity):
    """Switch to enable/disable automatic view cycling.

    When enabled, the display automatically cycles through configured views.
    The cycle interval can be adjusted via the View Cycle Interval number entity.
    """

    _attr_name = "View Cycling"
    _attr_icon = "mdi:view-carousel"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize view cycling switch."""
        super().__init__(coordinator, "view_cycling")
        # Store the last non-zero interval so we can restore it when turning on
        self._last_interval: int = DEFAULT_CYCLE_ON_INTERVAL

    @property
    def is_on(self) -> bool:
        """Return True if view cycling is enabled."""
        interval = self.coordinator.options.get(CONF_SCREEN_CYCLE_INTERVAL, 0)
        return interval > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on view cycling."""
        # Get current interval - if already > 0, keep it; otherwise use last or default
        current_interval = self.coordinator.options.get(CONF_SCREEN_CYCLE_INTERVAL, 0)
        if current_interval > 0:
            # Already on, nothing to do
            return

        # Use the last known interval, or default
        new_interval = self._last_interval

        self._update_options(**{CONF_SCREEN_CYCLE_INTERVAL: new_interval})
        _LOGGER.debug("View cycling enabled with interval %ds", new_interval)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off view cycling."""
        current_interval = self.coordinator.options.get(CONF_SCREEN_CYCLE_INTERVAL, 0)
        if current_interval == 0:
            # Already off, nothing to do
            return

        # Store the current interval so we can restore it later
        self._last_interval = current_interval

        self._update_options(**{CONF_SCREEN_CYCLE_INTERVAL: 0})
        _LOGGER.debug("View cycling disabled (was %ds)", current_interval)
