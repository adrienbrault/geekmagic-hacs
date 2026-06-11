"""Button entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from .base import GeekMagicEntity

if TYPE_CHECKING:
    from ..coordinator import GeekMagicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeekMagic button entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = [
        GeekMagicRefreshButton(coordinator),
        GeekMagicNextScreenButton(coordinator),
        GeekMagicPreviousScreenButton(coordinator),
    ]

    if coordinator.device.capabilities.supports_reboot:
        entities.append(GeekMagicRebootButton(coordinator))

    async_add_entities(entities)


class GeekMagicRefreshButton(GeekMagicEntity, ButtonEntity):
    """Button to force display refresh."""

    _attr_name = "Refresh Display"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize refresh button."""
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_refresh_display()


class GeekMagicNextScreenButton(GeekMagicEntity, ButtonEntity):
    """Button to switch to next screen."""

    _attr_name = "Next Screen"
    _attr_icon = "mdi:skip-next"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize next screen button."""
        super().__init__(coordinator, "next_screen")

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_next_screen()


class GeekMagicPreviousScreenButton(GeekMagicEntity, ButtonEntity):
    """Button to switch to previous screen."""

    _attr_name = "Previous Screen"
    _attr_icon = "mdi:skip-previous"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize previous screen button."""
        super().__init__(coordinator, "previous_screen")

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_previous_screen()


class GeekMagicRebootButton(GeekMagicEntity, ButtonEntity):
    """Button to reboot the device."""

    _attr_name = "Reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize reboot button."""
        super().__init__(coordinator, "reboot")

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.device.reboot()
