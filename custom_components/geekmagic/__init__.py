"""GeekMagic Display integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_FIRMWARE_VERSION, CONF_MODEL_NAME, CONF_PROFILE_ID, DOMAIN
from .coordinator import GeekMagicCoordinator
from .device import GeekMagicDevice
from .panel import async_register_panel
from .store import GeekMagicStore
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

LEGACY_PREVIEW_MODEL = "SmallTV Pro"

# Schema for integrations configured via UI only (no YAML support)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Platforms for device control entities and image output
PLATFORMS: list[Platform] = [
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
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

    # Register notify service
    async def async_handle_notify(call):
        """Handle the notify service call."""
        device_ids = call.data.get("device_id")
        if not isinstance(device_ids, list):
            device_ids = [device_ids]

        # Get device registry to map device_ids to config entries
        dev_reg = dr.async_get(hass)

        for device_id in device_ids:
            device = dev_reg.async_get(device_id)
            if not device:
                continue

            # Find config entry for this device
            for entry_id in device.config_entries:
                if entry_id in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN][entry_id]
                    if isinstance(coordinator, GeekMagicCoordinator):
                        await coordinator.trigger_notification(call.data)

    hass.services.async_register(DOMAIN, "notify", async_handle_notify)

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

    # Test connection - raise ConfigEntryNotReady if device is offline
    # This allows HA to automatically retry instead of showing a "Setup Error"
    result = await device.test_connection()
    if not result:
        raise ConfigEntryNotReady(
            f"Could not connect to GeekMagic device at {host}: {result.message}"
        )

    _LOGGER.debug("Successfully connected to GeekMagic device at %s", host)

    # Detect firmware profile and persist it for offline options/UI flows.
    await device.detect_model()
    detected_data = {
        CONF_PROFILE_ID: device.profile_id,
        CONF_MODEL_NAME: device.model_name,
        CONF_FIRMWARE_VERSION: device.firmware_version,
    }
    if any(entry.data.get(key) != value for key, value in detected_data.items()):
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **detected_data},
        )

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

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_cleanup_legacy_preview_device(hass, entry, device)

    _LOGGER.info("GeekMagic integration successfully set up for %s", host)
    return True


def _async_cleanup_legacy_preview_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: GeekMagicDevice,
) -> None:
    """Remove duplicate devices created by the old preview image identifier.

    Older versions registered the preview image entity as a separate HA device
    using ``(DOMAIN, host)`` and a hardcoded ``SmallTV Pro`` model. Current
    entities all identify the physical display by config entry id, so those
    host-identifier devices are stale duplicates after users upgrade.
    """
    dev_reg = dr.async_get(hass)
    current_device = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    legacy_identifier_values = {
        str(entry.data.get(CONF_HOST, "")),
        device.host,
        device.base_url,
    }
    for identifier_value in legacy_identifier_values:
        if not identifier_value or identifier_value == entry.entry_id:
            continue

        legacy_device = dev_reg.async_get_device(identifiers={(DOMAIN, identifier_value)})
        if legacy_device is None:
            continue
        if current_device is not None and legacy_device.id == current_device.id:
            continue
        if entry.entry_id not in legacy_device.config_entries:
            continue
        if legacy_device.manufacturer != "GeekMagic" or legacy_device.model != LEGACY_PREVIEW_MODEL:
            continue

        _LOGGER.info(
            "Removing legacy duplicate GeekMagic preview device %s for %s",
            legacy_device.id,
            entry.title,
        )
        dev_reg.async_remove_device(legacy_device.id)


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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed
    """
    # Clean up any resources if needed
