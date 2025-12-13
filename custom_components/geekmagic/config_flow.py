"""Config flow for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_REFRESH_INTERVAL,
    CONF_LAYOUT,
    DEFAULT_REFRESH_INTERVAL,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_HERO,
    LAYOUT_SPLIT,
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
    """Handle a config flow for GeekMagic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            session = async_get_clientsession(self.hass)
            device = GeekMagicDevice(host, session=session)

            if await device.test_connection():
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"GeekMagic ({host})"),
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GeekMagicOptionsFlow:
        """Get the options flow for this handler."""
        return GeekMagicOptionsFlow(config_entry)


class GeekMagicOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for GeekMagic."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_INTERVAL,
                        default=options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                    vol.Required(
                        CONF_LAYOUT,
                        default=options.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
                    ): vol.In(
                        {
                            LAYOUT_GRID_2X2: "Grid 2x2",
                            LAYOUT_GRID_2X3: "Grid 2x3",
                            LAYOUT_HERO: "Hero",
                            LAYOUT_SPLIT: "Split",
                        }
                    ),
                }
            ),
        )
