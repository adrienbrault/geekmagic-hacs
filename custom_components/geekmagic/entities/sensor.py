"""Sensor entities for GeekMagic integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from .entity import GeekMagicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from ..coordinator import GeekMagicCoordinator


@dataclass(frozen=True, kw_only=True)
class GeekMagicSensorEntityDescription(SensorEntityDescription):
    """Describes a GeekMagic sensor entity."""


DEVICE_SENSORS: tuple[GeekMagicSensorEntityDescription, ...] = (
    GeekMagicSensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:monitor-eye",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    GeekMagicSensorEntityDescription(
        key="current_screen_name",
        translation_key="current_screen_name",
        icon="mdi:monitor",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeekMagic sensor entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        GeekMagicSensorEntity(coordinator, description) for description in DEVICE_SENSORS
    ]

    async_add_entities(entities)


class GeekMagicSensorEntity(GeekMagicEntity, SensorEntity):
    """A GeekMagic sensor entity."""

    entity_description: GeekMagicSensorEntityDescription

    def __init__(
        self,
        coordinator: GeekMagicCoordinator,
        description: GeekMagicSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> str | None:
        """Return the sensor value."""
        key = self.entity_description.key

        if key == "status":
            if self.coordinator.last_update_success:
                return "connected"
            return "disconnected"
        if key == "current_screen_name":
            return self.coordinator.current_screen_name

        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        """Return additional state attributes."""
        key = self.entity_description.key

        if key == "status":
            return {
                "host": self.coordinator.device.host,
                "screen_count": self.coordinator.screen_count,
                "current_screen": self.coordinator.current_screen,
            }
        if key == "current_screen_name":
            return {
                "screen_index": self.coordinator.current_screen,
                "total_screens": self.coordinator.screen_count,
            }

        return None
