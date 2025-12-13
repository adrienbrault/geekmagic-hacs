"""Config flow for GeekMagic integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_HERO,
    LAYOUT_SLOT_COUNTS,
    LAYOUT_SPLIT,
    WIDGET_TYPE_NAMES,
)
from .device import GeekMagicDevice

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default="GeekMagic Display"): str,
    }
)

LAYOUT_OPTIONS = {
    LAYOUT_GRID_2X2: "Grid 2x2 (4 slots)",
    LAYOUT_GRID_2X3: "Grid 2x3 (6 slots)",
    LAYOUT_HERO: "Hero (4 slots)",
    LAYOUT_SPLIT: "Split (2 slots)",
}


class GeekMagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GeekMagic."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            _LOGGER.debug("Config flow: attempting to configure device at %s", host)

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            session = async_get_clientsession(self.hass)
            device = GeekMagicDevice(host, session=session)

            if await device.test_connection():
                _LOGGER.info("Config flow: successfully connected to %s", host)
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"GeekMagic ({host})"),
                    data=user_input,
                )
            _LOGGER.warning("Config flow: failed to connect to %s", host)
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
        self._options: dict[str, Any] = {}
        self._current_screen_index: int = 0
        self._current_slot: int = 0
        self._screen_config: dict[str, Any] = {}
        self._current_widget_type: str = ""
        self._current_widget_config: dict[str, Any] = {}
        self._editing_screen: bool = False

    def _migrate_options(self, options: dict[str, Any]) -> dict[str, Any]:
        """Migrate old options format to new multi-screen format."""
        if CONF_SCREENS in options:
            return dict(options)

        return {
            CONF_REFRESH_INTERVAL: options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            CONF_SCREEN_CYCLE_INTERVAL: options.get(
                CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL
            ),
            CONF_SCREENS: [
                {
                    "name": "Screen 1",
                    CONF_LAYOUT: options.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
                    CONF_WIDGETS: options.get(CONF_WIDGETS, [{"type": "clock", "slot": 0}]),
                }
            ],
        }

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Main menu for options."""
        # Initialize options from current config
        self._options = self._migrate_options(dict(self.config_entry.options))
        _LOGGER.debug(
            "Options flow: initialized with %d screens",
            len(self._options.get(CONF_SCREENS, [])),
        )

        if user_input is not None:
            action = user_input.get("action")
            _LOGGER.debug("Options flow: user selected action '%s'", action)
            if action == "global_settings":
                return await self.async_step_global_settings()
            if action == "manage_screens":
                return await self.async_step_manage_screens()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {
                            "global_settings": "Global Settings",
                            "manage_screens": "Manage Screens",
                        }
                    )
                }
            ),
        )

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure global settings."""
        if user_input is not None:
            self._options[CONF_REFRESH_INTERVAL] = user_input[CONF_REFRESH_INTERVAL]
            self._options[CONF_SCREEN_CYCLE_INTERVAL] = user_input[CONF_SCREEN_CYCLE_INTERVAL]
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="global_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_INTERVAL,
                        default=self._options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                    vol.Required(
                        CONF_SCREEN_CYCLE_INTERVAL,
                        default=self._options.get(
                            CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
                }
            ),
        )

    async def async_step_manage_screens(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage screens menu."""
        screens = self._options.get(CONF_SCREENS, [])

        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                self._editing_screen = False
                return await self.async_step_add_screen()
            if action == "done":
                return self.async_create_entry(title="", data=self._options)
            if action and action.startswith("edit_"):
                self._current_screen_index = int(action.split("_")[1])
                self._editing_screen = True
                return await self.async_step_edit_screen()
            if action and action.startswith("delete_"):
                self._current_screen_index = int(action.split("_")[1])
                return await self.async_step_delete_screen()

        # Build action choices
        actions = {"add": "+ Add New Screen"}
        for i, screen in enumerate(screens):
            name = screen.get("name", f"Screen {i + 1}")
            layout = screen.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
            slot_count = LAYOUT_SLOT_COUNTS.get(layout, 4)
            widget_count = len(screen.get(CONF_WIDGETS, []))
            layout_name = LAYOUT_OPTIONS.get(layout, layout)
            actions[f"edit_{i}"] = f"{name} ({layout_name}, {widget_count}/{slot_count})"
        for i, screen in enumerate(screens):
            if len(screens) > 1:  # Can't delete if only one screen
                name = screen.get("name", f"Screen {i + 1}")
                actions[f"delete_{i}"] = f"Delete: {name}"
        actions["done"] = "Save and Exit"

        return self.async_show_form(
            step_id="manage_screens",
            data_schema=vol.Schema({vol.Required("action"): vol.In(actions)}),
        )

    async def async_step_add_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new screen."""
        if user_input is not None:
            self._screen_config = {
                "name": user_input["name"],
                CONF_LAYOUT: user_input[CONF_LAYOUT],
                CONF_WIDGETS: [],
            }
            self._current_slot = 0
            return await self.async_step_configure_slot()

        screen_count = len(self._options.get(CONF_SCREENS, []))

        return self.async_show_form(
            step_id="add_screen",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=f"Screen {screen_count + 1}"): str,
                    vol.Required(CONF_LAYOUT, default=LAYOUT_GRID_2X2): vol.In(LAYOUT_OPTIONS),
                }
            ),
        )

    async def async_step_edit_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit existing screen."""
        screens = self._options.get(CONF_SCREENS, [])
        screen = screens[self._current_screen_index]

        if user_input is not None:
            old_layout = screen.get(CONF_LAYOUT)
            new_layout = user_input[CONF_LAYOUT]

            # Preserve widgets in compatible slots if layout changes
            old_widgets = screen.get(CONF_WIDGETS, [])
            if old_layout != new_layout:
                new_slot_count = LAYOUT_SLOT_COUNTS.get(new_layout, 4)
                preserved_widgets = [w for w in old_widgets if w.get("slot", 0) < new_slot_count]
            else:
                preserved_widgets = old_widgets

            self._screen_config = {
                "name": user_input["name"],
                CONF_LAYOUT: new_layout,
                CONF_WIDGETS: preserved_widgets,
            }

            self._current_slot = 0
            return await self.async_step_configure_slot()

        return self.async_show_form(
            step_id="edit_screen",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=screen.get("name", "")): str,
                    vol.Required(
                        CONF_LAYOUT, default=screen.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
                    ): vol.In(LAYOUT_OPTIONS),
                }
            ),
        )

    async def async_step_configure_slot(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a single slot."""
        layout = self._screen_config[CONF_LAYOUT]
        slot_count = LAYOUT_SLOT_COUNTS.get(layout, 4)

        if user_input is not None:
            widget_type = user_input["widget_type"]

            if widget_type == "empty":
                # Remove any existing widget for this slot
                self._screen_config[CONF_WIDGETS] = [
                    w
                    for w in self._screen_config[CONF_WIDGETS]
                    if w.get("slot") != self._current_slot
                ]
            else:
                # Store widget type and proceed to widget options
                self._current_widget_type = widget_type
                self._current_widget_config = {
                    "type": widget_type,
                    "slot": self._current_slot,
                }
                return await self.async_step_widget_options()

            # Move to next slot or finish
            self._current_slot += 1
            if self._current_slot < slot_count:
                return await self.async_step_configure_slot()
            return await self._finish_screen_config()

        # Get existing widget for this slot if editing
        existing_widget = None
        for w in self._screen_config.get(CONF_WIDGETS, []):
            if w.get("slot") == self._current_slot:
                existing_widget = w
                break

        default_type = existing_widget.get("type", "empty") if existing_widget else "empty"

        # Build widget type options
        widget_options = {"empty": "Empty (skip)"}
        widget_options.update(WIDGET_TYPE_NAMES)

        return self.async_show_form(
            step_id="configure_slot",
            data_schema=vol.Schema(
                {
                    vol.Required("widget_type", default=default_type): vol.In(widget_options),
                }
            ),
            description_placeholders={
                "slot_number": str(self._current_slot + 1),
                "total_slots": str(slot_count),
                "layout_name": LAYOUT_OPTIONS.get(layout, layout),
            },
        )

    async def async_step_widget_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure widget-specific options."""
        widget_type = self._current_widget_type
        layout = self._screen_config[CONF_LAYOUT]
        slot_count = LAYOUT_SLOT_COUNTS.get(layout, 4)

        if user_input is not None:
            # Build complete widget config
            widget_config = self._current_widget_config.copy()

            # Extract entity_id if present
            if user_input.get("entity_id"):
                widget_config["entity_id"] = user_input.pop("entity_id")
            elif "entity_id" in user_input:
                user_input.pop("entity_id")

            if user_input.get("label"):
                widget_config["label"] = user_input.pop("label")
            elif "label" in user_input:
                user_input.pop("label")

            # Remaining options go in options dict
            if user_input:
                widget_config["options"] = user_input

            # Remove any existing widget for this slot and add new one
            self._screen_config[CONF_WIDGETS] = [
                w for w in self._screen_config[CONF_WIDGETS] if w.get("slot") != self._current_slot
            ]
            self._screen_config[CONF_WIDGETS].append(widget_config)

            # Move to next slot
            self._current_slot += 1

            if self._current_slot < slot_count:
                return await self.async_step_configure_slot()
            return await self._finish_screen_config()

        # Get existing widget options if editing
        existing_widget = None
        for w in self._screen_config.get(CONF_WIDGETS, []):
            slot_match = w.get("slot") in (self._current_slot - 1, self._current_slot)
            if slot_match and w.get("type") == widget_type:
                existing_widget = w
                break

        # Build schema based on widget type
        schema = self._get_widget_schema(widget_type, existing_widget)

        return self.async_show_form(
            step_id="widget_options",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "widget_type": WIDGET_TYPE_NAMES.get(widget_type, widget_type),
                "slot_number": str(self._current_slot + 1),
            },
        )

    def _get_widget_schema(  # noqa: PLR0911
        self, widget_type: str, existing: dict[str, Any] | None = None
    ) -> dict:
        """Get voluptuous schema for widget type."""
        existing = existing or {}
        options = existing.get("options", {})

        if widget_type == "clock":
            return {
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("show_date", default=options.get("show_date", True)): bool,
                vol.Optional("show_seconds", default=options.get("show_seconds", False)): bool,
                vol.Optional("time_format", default=options.get("time_format", "24h")): vol.In(
                    {
                        "24h": "24 Hour",
                        "12h": "12 Hour",
                    }
                ),
            }
        if widget_type == "entity":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("show_name", default=options.get("show_name", True)): bool,
                vol.Optional("show_unit", default=options.get("show_unit", True)): bool,
            }
        if widget_type == "media":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="media_player")),
                vol.Optional("show_artist", default=options.get("show_artist", True)): bool,
                vol.Optional("show_album", default=options.get("show_album", False)): bool,
                vol.Optional("show_progress", default=options.get("show_progress", True)): bool,
            }
        if widget_type == "chart":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("hours", default=options.get("hours", 24)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=168)
                ),
                vol.Optional("show_value", default=options.get("show_value", True)): bool,
                vol.Optional("show_range", default=options.get("show_range", True)): bool,
            }
        if widget_type == "text":
            return {
                vol.Optional("text", default=options.get("text", "")): str,
                vol.Optional(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("size", default=options.get("size", "regular")): vol.In(
                    {
                        "small": "Small",
                        "regular": "Regular",
                        "large": "Large",
                        "xlarge": "Extra Large",
                    }
                ),
                vol.Optional("align", default=options.get("align", "center")): vol.In(
                    {
                        "left": "Left",
                        "center": "Center",
                        "right": "Right",
                    }
                ),
            }
        if widget_type == "gauge":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("style", default=options.get("style", "bar")): vol.In(
                    {
                        "bar": "Bar",
                        "ring": "Ring",
                        "arc": "Arc",
                    }
                ),
                vol.Optional("min", default=options.get("min", 0)): vol.Coerce(float),
                vol.Optional("max", default=options.get("max", 100)): vol.Coerce(float),
                vol.Optional("unit", default=options.get("unit", "")): str,
                vol.Optional("show_value", default=options.get("show_value", True)): bool,
            }
        if widget_type == "progress":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("target", default=options.get("target", 100)): vol.Coerce(float),
                vol.Optional("unit", default=options.get("unit", "")): str,
                vol.Optional("show_target", default=options.get("show_target", True)): bool,
            }
        if widget_type == "status":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "switch", "light", "lock", "device_tracker"]
                    )
                ),
                vol.Optional("label", default=existing.get("label", "")): str,
                vol.Optional("on_text", default=options.get("on_text", "ON")): str,
                vol.Optional("off_text", default=options.get("off_text", "OFF")): str,
                vol.Optional(
                    "show_status_text", default=options.get("show_status_text", True)
                ): bool,
            }
        if widget_type == "weather":
            return {
                vol.Required(
                    "entity_id", default=existing.get("entity_id", "")
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
                vol.Optional("show_forecast", default=options.get("show_forecast", True)): bool,
                vol.Optional("forecast_days", default=options.get("forecast_days", 3)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=5)
                ),
                vol.Optional("show_humidity", default=options.get("show_humidity", True)): bool,
                vol.Optional("show_wind", default=options.get("show_wind", False)): bool,
            }
        if widget_type == "multi_progress":
            # For list-based widgets, we use a simplified approach
            return {
                vol.Optional("title", default=options.get("title", "")): str,
                vol.Optional("entity_id_1", default=""): selector.EntitySelector(),
                vol.Optional("label_1", default=""): str,
                vol.Optional("target_1", default=100): vol.Coerce(float),
                vol.Optional("entity_id_2", default=""): selector.EntitySelector(),
                vol.Optional("label_2", default=""): str,
                vol.Optional("target_2", default=100): vol.Coerce(float),
                vol.Optional("entity_id_3", default=""): selector.EntitySelector(),
                vol.Optional("label_3", default=""): str,
                vol.Optional("target_3", default=100): vol.Coerce(float),
            }
        if widget_type == "status_list":
            return {
                vol.Optional("title", default=options.get("title", "")): str,
                vol.Optional("entity_id_1", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "switch", "light", "lock", "device_tracker"]
                    )
                ),
                vol.Optional("label_1", default=""): str,
                vol.Optional("entity_id_2", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "switch", "light", "lock", "device_tracker"]
                    )
                ),
                vol.Optional("label_2", default=""): str,
                vol.Optional("entity_id_3", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "switch", "light", "lock", "device_tracker"]
                    )
                ),
                vol.Optional("label_3", default=""): str,
                vol.Optional("entity_id_4", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "switch", "light", "lock", "device_tracker"]
                    )
                ),
                vol.Optional("label_4", default=""): str,
            }
        return {}

    async def _finish_screen_config(self) -> ConfigFlowResult:
        """Finish configuring a screen and save."""
        screen_name = self._screen_config.get("name", "Unknown")
        widget_count = len(self._screen_config.get(CONF_WIDGETS, []))
        _LOGGER.debug(
            "Options flow: finishing screen config '%s' with %d widgets",
            screen_name,
            widget_count,
        )
        screens = self._options.get(CONF_SCREENS, [])

        # Handle multi_progress and status_list special conversion
        for widget in self._screen_config.get(CONF_WIDGETS, []):
            options = widget.get("options", {})

            if widget.get("type") == "multi_progress":
                # Convert numbered fields to items list
                items = []
                for i in range(1, 4):
                    entity_id = options.pop(f"entity_id_{i}", "")
                    label = options.pop(f"label_{i}", "")
                    target = options.pop(f"target_{i}", 100)
                    if entity_id:
                        items.append({"entity_id": entity_id, "label": label, "target": target})
                if items:
                    options["items"] = items
                widget["options"] = options

            elif widget.get("type") == "status_list":
                # Convert numbered fields to entities list
                entities = []
                for i in range(1, 5):
                    entity_id = options.pop(f"entity_id_{i}", "")
                    label = options.pop(f"label_{i}", "")
                    if entity_id:
                        entities.append([entity_id, label] if label else entity_id)
                if entities:
                    options["entities"] = entities
                widget["options"] = options

        if self._editing_screen and self._current_screen_index < len(screens):
            # Editing existing screen
            screens[self._current_screen_index] = self._screen_config
        else:
            # Adding new screen
            screens.append(self._screen_config)

        self._options[CONF_SCREENS] = screens
        return await self.async_step_manage_screens()

    async def async_step_delete_screen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm screen deletion."""
        screens = self._options.get(CONF_SCREENS, [])
        screen = screens[self._current_screen_index]

        if user_input is not None:
            if user_input.get("confirm"):
                screens.pop(self._current_screen_index)
                self._options[CONF_SCREENS] = screens
            return await self.async_step_manage_screens()

        return self.async_show_form(
            step_id="delete_screen",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): bool,
                }
            ),
            description_placeholders={
                "screen_name": screen.get("name", f"Screen {self._current_screen_index + 1}"),
            },
        )
