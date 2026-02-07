"""Base entity class for GeekMagic entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN, MODEL_PRO, MODEL_ULTRA

if TYPE_CHECKING:
    from ..coordinator import GeekMagicCoordinator


class GeekMagicEntity(CoordinatorEntity["GeekMagicCoordinator"]):
    """Base class for GeekMagic entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GeekMagicCoordinator, entity_suffix: str) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator
            entity_suffix: Suffix for the entity_id (e.g., "brightness")
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{entity_suffix}"

    @property
    def _device_model_name(self) -> str:
        """Return human-readable device model name."""
        model = self.coordinator.device.model
        if model == MODEL_PRO:
            return "SmallTV Pro"
        if model == MODEL_ULTRA:
            return "SmallTV Ultra"
        return "SmallTV"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.title,
            manufacturer="GeekMagic",
            model=self._device_model_name,
        )
