"""Sensor entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation
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
    """Set up GeekMagic sensor entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GeekMagicStatusSensor(coordinator),
        GeekMagicStorageUsedSensor(coordinator),
        GeekMagicStorageFreeSensor(coordinator),
    ]

    async_add_entities(entities)


class GeekMagicStatusSensor(GeekMagicEntity, SensorEntity):
    """Sensor showing device connection status."""

    _attr_name = "Status"
    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize status sensor."""
        super().__init__(coordinator, "status")

    @property
    def native_value(self) -> str:
        """Return connection status."""
        if self.coordinator.last_update_success:
            return "Connected"
        return "Disconnected"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes.

        Only configuration that changes when the user edits it: any
        attribute that moves between refreshes makes the recorder store
        a new state row every update (issue #208). The current screen,
        brightness and display mode have their own entities.
        """
        return {
            "host": self.coordinator.device.host,
            "refresh_interval": self.coordinator.options.get("refresh_interval", 30),
            "assigned_views": len(self.coordinator.options.get("assigned_views", [])),
        }


class GeekMagicStorageUsedSensor(GeekMagicEntity, SensorEntity):
    """Sensor showing storage usage percentage."""

    _attr_name = "Storage Used"
    _attr_icon = "mdi:harddisk"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize storage used sensor."""
        super().__init__(coordinator, "storage_used")

    @property
    def native_value(self) -> float | None:
        """Return storage usage percentage."""
        if self.coordinator.space_info and self.coordinator.space_info.total > 0:
            used = self.coordinator.space_info.total - self.coordinator.space_info.free
            return round((used / self.coordinator.space_info.total) * 100, 1)
        return None


class GeekMagicStorageFreeSensor(GeekMagicEntity, SensorEntity):
    """Sensor showing free storage in KB."""

    _attr_name = "Storage Free"
    _attr_icon = "mdi:harddisk"
    _attr_native_unit_of_measurement = UnitOfInformation.KILOBYTES
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize storage free sensor."""
        super().__init__(coordinator, "storage_free")

    @property
    def native_value(self) -> float | None:
        """Return free storage in KB."""
        if self.coordinator.space_info:
            return round(self.coordinator.space_info.free / 1024, 1)
        return None
