"""Base entity class for GeekMagic entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN

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
        capabilities = getattr(self.coordinator.device, "capabilities", None)
        display_name = getattr(capabilities, "display_name", None)
        if isinstance(display_name, str) and display_name:
            return display_name
        model_name = self.coordinator.device.model_name
        if isinstance(model_name, str) and model_name:
            return model_name
        return "SmallTV"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.title,
            manufacturer="GeekMagic",
            model=self._device_model_name,
        )
        capabilities = getattr(self.coordinator.device, "capabilities", None)
        firmware_version = (
            getattr(capabilities, "firmware_version", None)
            if capabilities is not None
            else self.coordinator.device.firmware_version
        )
        if isinstance(firmware_version, str) and firmware_version:
            device_info["sw_version"] = firmware_version
        return device_info
