"""Switch entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import (
    CONF_ENABLE_ANIMATIONS,
    CONF_SCREEN_CYCLE_INTERVAL,
    DEFAULT_ENABLE_ANIMATIONS,
    DOMAIN,
)
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
        GeekMagicActiveSwitch(coordinator),
        GeekMagicViewCyclingSwitch(coordinator),
        GeekMagicAnimationsSwitch(coordinator),
    ]

    async_add_entities(entities)


class GeekMagicActiveSwitch(GeekMagicEntity, SwitchEntity, RestoreEntity):
    """Switch to pause/resume the render and upload cycle.

    When off, all rendering and device uploads are skipped and the screen is
    dimmed to zero. Intended for presence-based automations so the display
    does not refresh (or stay lit) when no one is in the room.

    The paused state only lives in HA (the device has no notion of it), so
    it is restored across restarts — otherwise a reboot would report the
    display as active while the screen is still dimmed.
    """

    _attr_name = "Active"
    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize active switch."""
        super().__init__(coordinator, "active")

    async def async_added_to_hass(self) -> None:
        """Restore the paused state after a Home Assistant restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state == STATE_OFF and self.coordinator.is_active:
            await self.coordinator.async_restore_paused()

    @property
    def is_on(self) -> bool:
        """Return True when the display is active (not paused)."""
        return self.coordinator.is_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume the display."""
        await self.coordinator.async_set_active(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause the display and dim the screen."""
        await self.coordinator.async_set_active(False)


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


class GeekMagicAnimationsSwitch(GeekMagicEntity, SwitchEntity):
    """Opt-in switch for animated (GIF) rendering.

    Off by default: animated GIFs cost upload size and device decode
    time. When on, views containing widgets that declare animations
    (e.g. an HTML widget with its Animate option enabled) are rendered
    as looping GIFs — CSS animations evaluated frame by frame — instead
    of a still JPEG. Views without animated widgets keep the JPEG path.
    """

    _attr_name = "Animations"
    _attr_icon = "mdi:animation-play"
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize animations switch."""
        super().__init__(coordinator, "animations")

    @property
    def is_on(self) -> bool:
        """Return True when animated rendering is enabled."""
        return bool(self.coordinator.options.get(CONF_ENABLE_ANIMATIONS, DEFAULT_ENABLE_ANIMATIONS))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable animated rendering."""
        new_options = {
            **self.coordinator.entry.options,
            CONF_ENABLE_ANIMATIONS: True,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("Animated rendering enabled")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable animated rendering."""
        new_options = {
            **self.coordinator.entry.options,
            CONF_ENABLE_ANIMATIONS: False,
        }
        self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
        _LOGGER.debug("Animated rendering disabled")
