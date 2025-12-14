"""GeekMagic Display integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import GeekMagicCoordinator
from .device import GeekMagicDevice
from .panel import async_register_panel
from .store import GeekMagicStore
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

# Only keep IMAGE platform - entity-based config is replaced by custom panel
PLATFORMS: list[Platform] = [
    Platform.IMAGE,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the GeekMagic domain.

    This is called once when the integration is first loaded.
    It initializes the global store, WebSocket commands, and panel.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary

    Returns:
        True if setup successful
    """
    _LOGGER.debug("Setting up GeekMagic domain")

    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})

    # Initialize global store for views
    store = GeekMagicStore(hass)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store

    # Register WebSocket commands
    async_register_websocket_commands(hass)

    # Register custom panel
    await async_register_panel(hass)

    _LOGGER.info("GeekMagic domain setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GeekMagic from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup successful
    """
    # Ensure domain is set up
    if DOMAIN not in hass.data:
        await async_setup(hass, {})

    host = entry.data[CONF_HOST]
    _LOGGER.debug("Setting up GeekMagic integration for %s", host)

    session = async_get_clientsession(hass)
    device = GeekMagicDevice(host, session=session)

    # Test connection
    if not await device.test_connection():
        _LOGGER.error("Could not connect to GeekMagic device at %s", host)
        return False

    _LOGGER.debug("Successfully connected to GeekMagic device at %s", host)

    # Create coordinator
    coordinator = GeekMagicCoordinator(
        hass=hass,
        device=device,
        options=dict(entry.options),
        config_entry=entry,
    )

    # Do first refresh
    _LOGGER.debug("Performing first refresh for %s", host)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))

    # Register services
    await async_setup_services(hass)

    # Set up platforms (camera)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("GeekMagic integration successfully set up for %s", host)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload successful
    """
    host = entry.data.get(CONF_HOST, "unknown")
    _LOGGER.debug("Unloading GeekMagic integration for %s", host)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove coordinator
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        del hass.data[DOMAIN][entry.entry_id]
        _LOGGER.debug("GeekMagic integration unloaded for %s", host)

    return unload_ok


async def async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    host = entry.data.get(CONF_HOST, "unknown")
    _LOGGER.debug("Options updated for GeekMagic device %s", host)
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_options(dict(entry.options))
    # Trigger immediate refresh so device displays updated config
    await coordinator.async_request_refresh()


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up GeekMagic services.

    Args:
        hass: Home Assistant instance
    """
    # Skip if already registered
    if hass.services.has_service(DOMAIN, "refresh"):
        return

    def _get_coordinators(entry_id: str | None) -> list[GeekMagicCoordinator]:
        """Get coordinators for service call."""
        if entry_id:
            coord = hass.data[DOMAIN].get(entry_id)
            return [coord] if coord and hasattr(coord, "device") else []
        return [c for c in hass.data[DOMAIN].values() if hasattr(c, "device")]

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call."""
        for coordinator in _get_coordinators(call.data.get("entry_id")):
            await coordinator.async_refresh_display()

    async def handle_brightness(call: ServiceCall) -> None:
        """Handle brightness service call."""
        brightness = call.data.get("brightness", 50)
        for coordinator in _get_coordinators(call.data.get("entry_id")):
            await coordinator.async_set_brightness(brightness)

    async def handle_set_screen(call: ServiceCall) -> None:
        """Handle set_screen service call."""
        screen_index = call.data.get("screen_index", 0)
        for coordinator in _get_coordinators(call.data.get("entry_id")):
            await coordinator.async_set_screen(screen_index)

    async def handle_next_screen(call: ServiceCall) -> None:
        """Handle next_screen service call."""
        for coordinator in _get_coordinators(call.data.get("entry_id")):
            await coordinator.async_next_screen()

    async def handle_previous_screen(call: ServiceCall) -> None:
        """Handle previous_screen service call."""
        for coordinator in _get_coordinators(call.data.get("entry_id")):
            await coordinator.async_previous_screen()

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    hass.services.async_register(DOMAIN, "brightness", handle_brightness)
    hass.services.async_register(DOMAIN, "set_screen", handle_set_screen)
    hass.services.async_register(DOMAIN, "next_screen", handle_next_screen)
    hass.services.async_register(DOMAIN, "previous_screen", handle_previous_screen)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed
    """
    # Clean up any resources if needed
