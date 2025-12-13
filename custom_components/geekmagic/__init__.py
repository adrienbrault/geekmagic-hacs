"""GeekMagic Display integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import GeekMagicCoordinator
from .device import GeekMagicDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GeekMagic from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup successful
    """
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)
    device = GeekMagicDevice(host, session=session)

    # Test connection
    if not await device.test_connection():
        _LOGGER.error("Could not connect to GeekMagic device at %s", host)
        return False

    # Create coordinator
    coordinator = GeekMagicCoordinator(
        hass=hass,
        device=device,
        options=dict(entry.options),
    )

    # Do first refresh
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))

    # Register services
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload successful
    """
    # Remove coordinator
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        del hass.data[DOMAIN][entry.entry_id]

    return True


async def async_options_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_options(dict(entry.options))


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up GeekMagic services.

    Args:
        hass: Home Assistant instance
    """
    # Skip if already registered
    if hass.services.has_service(DOMAIN, "refresh"):
        return

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call."""
        entry_id = call.data.get("entry_id")

        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
            if coordinator:
                await coordinator.async_refresh_display()
        else:
            # Refresh all displays
            for coordinator in hass.data[DOMAIN].values():
                await coordinator.async_refresh_display()

    async def handle_brightness(call: ServiceCall) -> None:
        """Handle brightness service call."""
        entry_id = call.data.get("entry_id")
        brightness = call.data.get("brightness", 50)

        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
            if coordinator:
                await coordinator.async_set_brightness(brightness)
        else:
            # Set brightness on all displays
            for coordinator in hass.data[DOMAIN].values():
                await coordinator.async_set_brightness(brightness)

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    hass.services.async_register(DOMAIN, "brightness", handle_brightness)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed
    """
    # Clean up any resources if needed
    pass
