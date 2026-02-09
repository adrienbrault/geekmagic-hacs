"""Switch entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import CONF_FLIP_DISPLAY, CONF_SCREEN_CYCLE_INTERVAL, DOMAIN
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
        GeekMagicFlipDisplaySwitch(coordinator),
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

        new_options = {
            **self.coordinator.entry.options,
            CONF_SCREEN_CYCLE_INTERVAL: new_interval,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("View cycling enabled with interval %ds", new_interval)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off view cycling."""
        current_interval = self.coordinator.options.get(CONF_SCREEN_CYCLE_INTERVAL, 0)
        if current_interval == 0:
            # Already off, nothing to do
            return

        # Store the current interval so we can restore it later
        self._last_interval = current_interval

        new_options = {
            **self.coordinator.entry.options,
            CONF_SCREEN_CYCLE_INTERVAL: 0,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("View cycling disabled (was %ds)", current_interval)


class GeekMagicFlipDisplaySwitch(GeekMagicEntity, SwitchEntity):
    """Switch to flip the display 180 degrees.

    Useful when the device is mounted upside down in an alternate enclosure.
    This composes with the existing display rotation setting.
    """

    _attr_name = "Flip Display"
    _attr_icon = "mdi:phone-rotate-landscape"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize flip display switch."""
        super().__init__(coordinator, "flip_display")

    @property
    def is_on(self) -> bool:
        """Return True if display flip is enabled."""
        return self.coordinator.options.get(CONF_FLIP_DISPLAY, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable display flip."""
        if self.is_on:
            return

        new_options = {
            **self.coordinator.entry.options,
            CONF_FLIP_DISPLAY: True,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("Display flip enabled")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable display flip."""
        if not self.is_on:
            return

        new_options = {
            **self.coordinator.entry.options,
            CONF_FLIP_DISPLAY: False,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("Display flip disabled")
