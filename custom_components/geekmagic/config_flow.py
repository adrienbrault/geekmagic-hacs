"""Config flow for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DISPLAY_ROTATION,
    CONF_FIRMWARE_VERSION,
    CONF_JPEG_QUALITY,
    CONF_LAYOUT,
    CONF_MANAGE_PRO_ALBUM,
    CONF_MODEL_NAME,
    CONF_PROFILE_ID,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREEN_THEME,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_DISPLAY_ROTATION,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
    MODEL_PRO,
    THEME_WATCHOS,
)
from .device import GeekMagicDevice

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default="GeekMagic Display"): str,
    }
)


class GeekMagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GeekMagic.

    This flow handles initial device setup only.
    All screen/widget configuration is done through entities (WLED-style).
    """

    VERSION = 1
    _pending_entry_data: dict[str, Any] | None = None
    _pending_entry_title: str | None = None
    _pending_entry_options: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step - device connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            _LOGGER.debug("Config flow: attempting to configure device at %s", host)

            # Check if already configured (use normalized host for uniqueness)
            session = async_get_clientsession(self.hass)
            device = GeekMagicDevice(host, session=session)
            await self.async_set_unique_id(device.host)
            self._abort_if_unique_id_configured()

            # Test connection
            result = await device.test_connection()

            if result.success:
                _LOGGER.info("Config flow: successfully connected to %s", host)
                await device.detect_model()
                entry_data = self._entry_data_with_profile(user_input, device)

                # Pro Picture mode is a slideshow. For deterministic HA rendering,
                # the integration must own the image album and keep only its
                # dashboard file on the device. The user still needs to select
                # the Picture app manually because the Pro menu state is not
                # exposed reliably enough for automatic button navigation.
                if device.capabilities.requires_managed_album:
                    self._pending_entry_data = entry_data
                    self._pending_entry_title = user_input.get(
                        CONF_NAME, f"GeekMagic ({device.host})"
                    )
                    self._pending_entry_options = self._get_default_options()
                    return await self.async_step_pro_managed_album()

                # Create entry with default options
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"GeekMagic ({device.host})"),
                    data=entry_data,
                    options=self._get_default_options(),
                )
            _LOGGER.warning("Config flow: failed to connect to %s: %s", host, result.message)
            errors["base"] = result.error

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Point an existing entry at a new address.

        DHCP hands these devices a new lease sooner or later, and the host lives
        in entry data where nothing in the UI could reach it -- the options flow
        only covers screens and the Pro album. Without this step the only way to
        follow a moved device was to delete the entry and add it again, which
        drops the assigned views and renumbers every entity.
        """
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input[CONF_HOST]
            _LOGGER.debug("Reconfigure: moving %s to %s", entry.title, host)

            session = async_get_clientsession(self.hass)
            device = GeekMagicDevice(host, session=session)

            # The unique ID *is* the host, so moving the device has to move the
            # unique ID with it. That rules out _abort_if_unique_id_mismatch,
            # which would reject the very change being made here; collisions
            # with other entries have to be checked directly instead.
            if any(
                other.entry_id != entry.entry_id and other.unique_id == device.host
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")

            result = await device.test_connection()

            if result.success:
                await device.detect_model()
                _LOGGER.info("Reconfigure: %s now at %s", entry.title, device.host)
                # Redetecting also refreshes the stored model and firmware, which
                # go stale when a device is upgraded between setup and reconfigure.
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=device.host,
                    data_updates=self._entry_data_with_profile(user_input, device),
                )
            _LOGGER.warning("Reconfigure: failed to connect to %s: %s", host, result.message)
            errors["base"] = result.error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                {
                    CONF_HOST: entry.data.get(CONF_HOST),
                    CONF_NAME: entry.data.get(CONF_NAME, entry.title),
                },
            ),
            errors=errors,
        )

    async def async_step_pro_managed_album(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Warn Pro users that HA needs exclusive control of the Picture album."""
        errors: dict[str, str] = {}

        if self._pending_entry_data is None or self._pending_entry_options is None:
            return await self.async_step_user()

        if user_input is not None:
            if user_input.get(CONF_MANAGE_PRO_ALBUM):
                options = dict(self._pending_entry_options)
                options[CONF_MANAGE_PRO_ALBUM] = True
                return self.async_create_entry(
                    title=self._pending_entry_title or "GeekMagic Display",
                    data=self._pending_entry_data,
                    options=options,
                )
            errors["base"] = "confirm_required"

        return self.async_show_form(
            step_id="pro_managed_album",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MANAGE_PRO_ALBUM, default=False): bool,
                }
            ),
            errors=errors,
        )

    def _get_default_options(self) -> dict[str, Any]:
        """Get default options for a new device."""
        return {
            CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
            CONF_JPEG_QUALITY: DEFAULT_JPEG_QUALITY,
            CONF_DISPLAY_ROTATION: DEFAULT_DISPLAY_ROTATION,
            CONF_SCREENS: [
                {
                    "name": "Screen 1",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_SCREEN_THEME: THEME_WATCHOS,
                    CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                }
            ],
        }

    @staticmethod
    def _entry_data_with_profile(
        user_input: dict[str, Any],
        device: GeekMagicDevice,
    ) -> dict[str, Any]:
        """Persist detected profile metadata for offline options/UI flows."""
        data = dict(user_input)
        data[CONF_PROFILE_ID] = device.profile_id
        data[CONF_MODEL_NAME] = device.model_name
        data[CONF_FIRMWARE_VERSION] = device.firmware_version
        return data

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GeekMagicOptionsFlow:
        """Get the options flow for this handler."""
        return GeekMagicOptionsFlow()


class GeekMagicOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for GeekMagic.

    Note: Most configuration is done through entities now (WLED-style).
    This options flow is kept minimal for advanced users who want to
    reset to defaults or import/export configurations.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show options menu."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "reset_defaults":
                return await self.async_step_reset_defaults()
            if action == "enable_pro_managed_album" and self._supports_managed_album_option():
                return await self.async_step_pro_managed_album()
            if action == "disable_pro_managed_album" and self._supports_managed_album_option():
                options = dict(self.config_entry.options)
                options[CONF_MANAGE_PRO_ALBUM] = False
                return self.async_create_entry(title="", data=options)

        actions = {
            "reset_defaults": "Reset to Default Configuration",
        }
        if self._supports_managed_album_option():
            if self.config_entry.options.get(CONF_MANAGE_PRO_ALBUM):
                actions["disable_pro_managed_album"] = "Stop Managing Pro Picture Album"
            else:
                actions["enable_pro_managed_album"] = "Manage Pro Picture Album"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("action"): vol.In(actions)}),
            description_placeholders={
                "tip": "Tip: Configure your display using the device entities "
                "(brightness, screens, widgets, etc.) on the device page."
            },
        )

    async def async_step_pro_managed_album(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Warn before enabling destructive Pro album management from options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(CONF_MANAGE_PRO_ALBUM):
                options = dict(self.config_entry.options)
                options[CONF_MANAGE_PRO_ALBUM] = True
                return self.async_create_entry(title="", data=options)
            errors["base"] = "confirm_required"

        return self.async_show_form(
            step_id="pro_managed_album",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MANAGE_PRO_ALBUM, default=False): bool,
                }
            ),
            errors=errors,
        )

    def _supports_managed_album_option(self) -> bool:
        """Return whether this entry should expose Pro album controls offline."""
        return bool(
            self.config_entry.data.get(CONF_PROFILE_ID) == MODEL_PRO
            or self.config_entry.options.get(CONF_MANAGE_PRO_ALBUM)
        )

    async def async_step_reset_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reset to default configuration."""
        if user_input is not None:
            if user_input.get("confirm"):
                # Reset to defaults
                default_options = {
                    CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                    CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
                    CONF_SCREENS: [
                        {
                            "name": "Screen 1",
                            CONF_LAYOUT: LAYOUT_GRID_2X2,
                            CONF_SCREEN_THEME: THEME_WATCHOS,
                            CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                        }
                    ],
                }
                if self.config_entry.options.get(CONF_MANAGE_PRO_ALBUM):
                    default_options[CONF_MANAGE_PRO_ALBUM] = True
                return self.async_create_entry(title="", data=default_options)
            # User cancelled
            return await self.async_step_init()

        return self.async_show_form(
            step_id="reset_defaults",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): bool,
                }
            ),
            description_placeholders={
                "warning": "This will reset all screens and widgets to defaults. "
                "Your current configuration will be lost."
            },
        )
