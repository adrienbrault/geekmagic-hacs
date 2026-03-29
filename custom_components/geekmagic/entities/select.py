"""Select entities for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from .base import GeekMagicEntity

if TYPE_CHECKING:
    from ..coordinator import GeekMagicCoordinator

_LOGGER = logging.getLogger(__name__)

# Built-in device modes with their theme numbers
# These are handled by the device firmware, not rendered by the integration
# Theme 3 (Photo Album) is intentionally omitted - used for custom rendered views
BUILTIN_MODES = {
    "Weather Clock Today": 1,
    "Weather Forecast": 2,
    "Time Style 1": 4,
    "Time Style 2": 5,
    "Time Style 3": 6,
    "Simple Weather Clock": 7,
}

# Prefix used to identify custom views in the combined select
CUSTOM_VIEW_PREFIX = ""  # No prefix - views shown by name directly


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeekMagic select entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GeekMagicDisplaySelect(coordinator),
        GeekMagicRotationSelect(coordinator),
    ]

    async_add_entities(entities)


class GeekMagicDisplaySelect(GeekMagicEntity, SelectEntity):
    """Unified select entity for choosing what to display.

    Combines device built-in modes (Clock, Weather, System Info) with
    custom views configured in the integration. This provides a single
    control point for users to choose what appears on the display.

    Note: This entity intentionally does not update state during automatic
    view cycling to prevent spamming the recorder/logbook. State only updates
    when the user explicitly selects an option or when available options change.
    """

    _attr_name = "Display"
    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize display select."""
        super().__init__(coordinator, "display")
        # Track last known options to detect when views are added/removed
        self._last_options: list[str] | None = None

    def _get_custom_view_names(self) -> list[str]:
        """Get list of custom view names."""
        store = self.coordinator.get_store()
        if not store:
            return []

        assigned_views = self.coordinator.options.get("assigned_views", [])
        names = []
        for view_id in assigned_views:
            view = store.get_view(view_id)
            if view:
                names.append(view.get("name", view_id))
        return names

    @property
    def options(self) -> list[str]:
        """Return all available display options.

        Built-in modes come first, followed by custom views.
        """
        options = list(BUILTIN_MODES.keys())
        options.extend(self._get_custom_view_names())
        return options or ["Clock"]

    @property
    def current_option(self) -> str | None:
        """Return currently selected display option."""
        # Check if coordinator is in builtin mode
        if self.coordinator.display_mode == "builtin":
            theme = self.coordinator.builtin_theme
            for mode_name, mode_theme in BUILTIN_MODES.items():
                if mode_theme == theme:
                    return mode_name
            return "Clock"

        # In custom mode - return current view name
        view_names = self._get_custom_view_names()
        if not view_names:
            # No custom views, default to Clock
            return "Clock"

        current_idx = self.coordinator.current_screen
        if 0 <= current_idx < len(view_names):
            return view_names[current_idx]

        return view_names[0] if view_names else "Clock"

    async def async_select_option(self, option: str) -> None:
        """Handle selection of a display option."""
        if option in BUILTIN_MODES:
            # Built-in mode selected - set device theme and enter builtin mode
            theme = BUILTIN_MODES[option]
            _LOGGER.debug("Switching to built-in mode: %s (theme=%d)", option, theme)
            await self.coordinator.device.set_theme(theme)
            self.coordinator.set_display_mode("builtin", theme)
            # Don't refresh - just poll state to update UI
            await self.coordinator.async_request_refresh()
        else:
            # Custom view selected
            view_names = self._get_custom_view_names()
            if option in view_names:
                view_idx = view_names.index(option)
                _LOGGER.debug("Switching to custom view: %s (index=%d)", option, view_idx)
                self.coordinator.set_display_mode("custom", view_idx)
                # Immediate refresh to show the custom view
                await self.coordinator.async_refresh_display()

        # Explicitly write state after user selection
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update.

        Override to prevent state updates during automatic view cycling.
        This prevents spamming the recorder/logbook when cycle interval is enabled.
        State is only written when:
        - User explicitly selects an option (in async_select_option)
        - Available options change (views added/removed)
        """
        current_options = self.options
        if self._last_options is None:
            # First update - record options and write state
            self._last_options = current_options
            self.async_write_ha_state()
        elif current_options != self._last_options:
            # Options changed (views added/removed) - update state
            self._last_options = current_options
            self.async_write_ha_state()
        # Otherwise: do NOT write state (cycling doesn't trigger recorder)


# Rotation options mapping display name to degrees
ROTATION_OPTIONS = {
    "0°": 0,
    "90°": 90,
    "180°": 180,
    "270°": 270,
}


class GeekMagicRotationSelect(GeekMagicEntity, SelectEntity):
    """Select entity for display rotation.

    Allows rotating the display output in 90° increments.
    """

    _attr_name = "Display Rotation"
    _attr_icon = "mdi:rotate-right"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GeekMagicCoordinator) -> None:
        """Initialize rotation select."""
        super().__init__(coordinator, "display_rotation")

    @property
    def options(self) -> list[str]:
        """Return rotation options."""
        return list(ROTATION_OPTIONS.keys())

    @property
    def current_option(self) -> str | None:
        """Return currently selected rotation."""
        current_rotation = self.coordinator.options.get("display_rotation", 0)
        for name, degrees in ROTATION_OPTIONS.items():
            if degrees == current_rotation:
                return name
        return "0°"

    async def async_select_option(self, option: str) -> None:
        """Handle rotation selection."""
        if option in ROTATION_OPTIONS:
            rotation = ROTATION_OPTIONS[option]
            _LOGGER.debug("Setting display rotation to %d degrees", rotation)
            new_options = {
                **self.coordinator.entry.options,
                "display_rotation": rotation,
            }
            self.hass.config_entries.async_update_entry(self.coordinator.entry, options=new_options)
            # Refresh display to apply rotation
            await self.coordinator.async_refresh_display()
