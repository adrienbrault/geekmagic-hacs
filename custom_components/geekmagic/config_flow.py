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
    CONF_JPEG_QUALITY,
    CONF_LAYOUT,
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
    MODEL_SDPRO,
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

STEP_SDPRO_CONFIRM_SCHEMA = vol.Schema(
    {
        vol.Required("disable_other_themes", default=True): bool,
    }
)


class GeekMagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GeekMagic.

    This flow handles initial device setup only.
    All screen/widget configuration is done through entities (WLED-style).
    """

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        # Carried across steps when the SD_PRO confirmation screen is shown.
        self._pending_user_input: dict[str, Any] | None = None
        self._pending_device_host: str | None = None
        self._pending_theme_names: list[str] = []

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
                _LOGGER.info("Config flow: connected to %s (model=%s)", host, device.model)

                # SD_PRO firmware rotates through built-in themes by default,
                # which would replace the integration's rendered image every
                # few seconds. Ask the user before disabling those themes.
                if device.model == MODEL_SDPRO:
                    try:
                        themes = await device.list_themes()
                    except Exception as err:
                        _LOGGER.warning("SD_PRO theme list lookup failed: %s", err)
                        themes = []
                    self._pending_theme_names = [
                        str(t.get("name", f"theme {t.get('id')}"))
                        for t in themes
                        if t.get("enabled")
                        and int(t.get("id", -1)) != device.driver.custom_image_theme
                    ]
                    self._pending_user_input = user_input
                    self._pending_device_host = host
                    return await self.async_step_sdpro_confirm()

                # Create entry with default options
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"GeekMagic ({device.host})"),
                    data=user_input,
                    options=self._get_default_options(),
                )
            _LOGGER.warning("Config flow: failed to connect to %s: %s", host, result.message)
            errors["base"] = result.error

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_sdpro_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Warn the SD_PRO user that built-in themes will be disabled."""
        assert self._pending_user_input is not None
        assert self._pending_device_host is not None

        if user_input is not None:
            if user_input.get("disable_other_themes", True):
                session = async_get_clientsession(self.hass)
                device = GeekMagicDevice(self._pending_device_host, session=session)
                await device.detect_model()
                try:
                    disabled = await device.disable_other_themes()
                    if disabled:
                        _LOGGER.info(
                            "SD_PRO: disabled built-in themes: %s",
                            ", ".join(disabled),
                        )
                except Exception as err:
                    _LOGGER.warning("SD_PRO: could not disable built-in themes: %s", err)

            saved_input = self._pending_user_input
            self._pending_user_input = None
            self._pending_device_host = None
            self._pending_theme_names = []

            return self.async_create_entry(
                title=saved_input.get(CONF_NAME, f"GeekMagic ({self.unique_id})"),
                data=saved_input,
                options=self._get_default_options(),
            )

        themes_text = (
            ", ".join(self._pending_theme_names)
            if self._pending_theme_names
            else "(none currently enabled)"
        )
        return self.async_show_form(
            step_id="sdpro_confirm",
            data_schema=STEP_SDPRO_CONFIRM_SCHEMA,
            description_placeholders={"themes": themes_text},
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {
                            "reset_defaults": "Reset to Default Configuration",
                        }
                    )
                }
            ),
            description_placeholders={
                "tip": "Tip: Configure your display using the device entities "
                "(brightness, screens, widgets, etc.) on the device page."
            },
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
