"""WebSocket API for GeekMagic custom panel.

Provides commands for managing views, devices, and preview rendering.
"""

from __future__ import annotations

import base64
import contextlib
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_SLOT_COUNTS,
    THEME_CLASSIC,
    THEME_OPTIONS,
)
from .renderer import Renderer
from .widgets.base import WidgetConfig
from .widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from .coordinator import GeekMagicCoordinator
    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)

# Widget type schemas for frontend form generation
WIDGET_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    "clock": {
        "name": "Clock",
        "needs_entity": False,
        "options": [
            {"key": "show_date", "type": "boolean", "label": "Show Date", "default": True},
            {"key": "show_seconds", "type": "boolean", "label": "Show Seconds", "default": False},
            {
                "key": "time_format",
                "type": "select",
                "label": "Time Format",
                "options": ["24h", "12h"],
                "default": "24h",
            },
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    },
    "entity": {
        "name": "Entity",
        "needs_entity": True,
        "entity_domains": None,  # All domains
        "options": [
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_unit", "type": "boolean", "label": "Show Unit", "default": True},
            {"key": "show_icon", "type": "boolean", "label": "Show Icon", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon Override"},
            {"key": "show_panel", "type": "boolean", "label": "Panel Background", "default": False},
            {
                "key": "precision",
                "type": "number",
                "label": "Decimal Places",
                "min": 0,
                "max": 5,
            },
        ],
    },
    "gauge": {
        "name": "Gauge",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {
                "key": "style",
                "type": "select",
                "label": "Style",
                "options": ["bar", "ring", "arc"],
                "default": "bar",
            },
            {"key": "min", "type": "number", "label": "Minimum", "default": 0},
            {"key": "max", "type": "number", "label": "Maximum", "default": 100},
            {"key": "unit", "type": "text", "label": "Unit Override"},
            {"key": "show_value", "type": "boolean", "label": "Show Value", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon"},
            {"key": "attribute", "type": "text", "label": "Entity Attribute"},
            {"key": "color_thresholds", "type": "thresholds", "label": "Color Thresholds"},
        ],
    },
    "candlestick": {
        "name": "Candlestick Chart",
        "needs_entity": True,
        "entity_domains": None,
        "options": [
            {
                "key": "candle_interval",
                "type": "select",
                "label": "Candle Interval",
                "options": ["1 hour", "4 hours", "1 day"],
                "default": "4 hours",
            },
            {
                "key": "candle_count",
                "type": "number",
                "label": "Number of Candles",
                "min": 5,
                "max": 40,
                "default": 20,
            },
            {
                "key": "show_value",
                "type": "boolean",
                "label": "Show Current Value",
                "default": True,
            },
        ],
    },
    "chart": {
        "name": "Chart",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {
                "key": "period",
                "type": "select",
                "label": "Period",
                "options": ["5 min", "15 min", "1 hour", "6 hours", "24 hours"],
                "default": "24 hours",
            },
            {
                "key": "show_value",
                "type": "boolean",
                "label": "Show Current Value",
                "default": True,
            },
            {
                "key": "show_range",
                "type": "boolean",
                "label": "Show Min/Max Range",
                "default": True,
            },
            {"key": "fill", "type": "boolean", "label": "Fill Area", "default": False},
            {
                "key": "color_gradient",
                "type": "boolean",
                "label": "Value Gradient",
                "default": False,
            },
        ],
    },
    "text": {
        "name": "Text",
        "needs_entity": False,
        "options": [
            {"key": "text", "type": "text", "label": "Text Content"},
            {"key": "entity_id", "type": "entity", "label": "Entity (dynamic text)"},
            {
                "key": "size",
                "type": "select",
                "label": "Size",
                "options": ["small", "regular", "large", "xlarge"],
                "default": "regular",
            },
            {
                "key": "align",
                "type": "select",
                "label": "Alignment",
                "options": ["left", "center", "right"],
                "default": "center",
            },
        ],
    },
    "progress": {
        "name": "Progress",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {"key": "target", "type": "number", "label": "Target Value", "default": 100},
            {"key": "unit", "type": "text", "label": "Unit"},
            {"key": "show_target", "type": "boolean", "label": "Show Target", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon"},
            {
                "key": "bar_height",
                "type": "select",
                "label": "Bar Height",
                "options": ["thin", "normal", "thick"],
                "default": "normal",
            },
        ],
    },
    "weather": {
        "name": "Weather",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [
            {"key": "show_forecast", "type": "boolean", "label": "Show Forecast", "default": True},
            {
                "key": "forecast_days",
                "type": "number",
                "label": "Forecast Days",
                "default": 3,
                "min": 1,
                "max": 5,
            },
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_high_low", "type": "boolean", "label": "Show High/Low", "default": True},
        ],
    },
    "status": {
        "name": "Status",
        "needs_entity": True,
        "entity_domains": None,  # Any entity (interprets state as on/off)
        "options": [
            {"key": "on_text", "type": "text", "label": "On Text", "default": "On"},
            {"key": "off_text", "type": "text", "label": "Off Text", "default": "Off"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [102, 166, 30],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [231, 76, 60],
            },
            {"key": "icon", "type": "icon", "label": "Icon"},
            {
                "key": "show_status_text",
                "type": "boolean",
                "label": "Show Status Text",
                "default": True,
            },
        ],
    },
    "media": {
        "name": "Media Player",
        "needs_entity": True,
        "entity_domains": ["media_player"],
        "options": [
            {"key": "show_artist", "type": "boolean", "label": "Show Artist", "default": True},
            {"key": "show_album", "type": "boolean", "label": "Show Album", "default": False},
            {"key": "show_progress", "type": "boolean", "label": "Show Progress", "default": True},
        ],
    },
    "camera": {
        "name": "Camera",
        "needs_entity": True,
        "entity_domains": ["camera"],
        "options": [
            {
                "key": "fit",
                "type": "select",
                "label": "Fit Mode",
                "options": ["cover", "contain"],
                "default": "cover",
            },
            {"key": "show_label", "type": "boolean", "label": "Show Label", "default": False},
        ],
    },
    "climate": {
        "name": "Climate",
        "needs_entity": True,
        "entity_domains": ["climate"],
        "options": [
            {"key": "show_target", "type": "boolean", "label": "Show Target Temp", "default": True},
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_mode", "type": "boolean", "label": "Show HVAC Mode", "default": True},
        ],
    },
    "multi_progress": {
        "name": "Multi Progress",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "items", "type": "progress_items", "label": "Progress Items"},
        ],
    },
    "status_list": {
        "name": "Status List",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "entities", "type": "status_entities", "label": "Status Entities"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [102, 166, 30],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [231, 76, 60],
            },
        ],
    },
}


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands."""
    # Views
    websocket_api.async_register_command(hass, ws_views_list)
    websocket_api.async_register_command(hass, ws_views_get)
    websocket_api.async_register_command(hass, ws_views_create)
    websocket_api.async_register_command(hass, ws_views_update)
    websocket_api.async_register_command(hass, ws_views_delete)
    websocket_api.async_register_command(hass, ws_views_duplicate)

    # Devices
    websocket_api.async_register_command(hass, ws_devices_list)
    websocket_api.async_register_command(hass, ws_devices_assign_views)
    websocket_api.async_register_command(hass, ws_devices_settings)

    # Preview
    websocket_api.async_register_command(hass, ws_preview_render)

    # Config
    websocket_api.async_register_command(hass, ws_get_config)

    # Entities
    websocket_api.async_register_command(hass, ws_entities_list)

    _LOGGER.debug("Registered GeekMagic WebSocket commands")


# =============================================================================
# Config Command
# =============================================================================


@websocket_api.websocket_command({vol.Required("type"): "geekmagic/config"})
@callback
def ws_get_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get full configuration for the panel."""
    connection.send_result(
        msg["id"],
        {
            "widget_types": WIDGET_TYPE_SCHEMAS,
            "layout_types": {
                k: {"slots": v, "name": k.replace("_", " ").title()}
                for k, v in LAYOUT_SLOT_COUNTS.items()
            },
            "themes": dict(THEME_OPTIONS.items()),
        },
    )


# =============================================================================
# View Commands
# =============================================================================


@websocket_api.websocket_command({vol.Required("type"): "geekmagic/views/list"})
@callback
def ws_views_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get all global views."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    connection.send_result(msg["id"], {"views": store.get_views_list()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/views/get",
        vol.Required("view_id"): str,
    }
)
@callback
def ws_views_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get a specific view configuration."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    view = store.get_view(msg["view_id"])
    if view:
        connection.send_result(msg["id"], {"view": view})
    else:
        connection.send_error(msg["id"], "not_found", "View not found")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/views/create",
        vol.Required("name"): str,
        vol.Optional("layout", default=LAYOUT_GRID_2X2): str,
        vol.Optional("theme", default=THEME_CLASSIC): str,
        vol.Optional("widgets", default=[]): list,
    }
)
@websocket_api.async_response
async def ws_views_create(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new view."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    view_id = await store.async_create_view(
        name=msg["name"],
        layout=msg["layout"],
        theme=msg["theme"],
        widgets=msg["widgets"],
    )
    connection.send_result(
        msg["id"],
        {
            "view_id": view_id,
            "view": store.get_view(view_id),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/views/update",
        vol.Required("view_id"): str,
        vol.Optional("name"): str,
        vol.Optional("layout"): str,
        vol.Optional("theme"): str,
        vol.Optional("widgets"): list,
    }
)
@websocket_api.async_response
async def ws_views_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update a view configuration."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    view_id = msg["view_id"]

    if not store.get_view(view_id):
        connection.send_error(msg["id"], "not_found", "View not found")
        return

    # Build update dict from optional fields
    updates = {}
    for key in ("name", "layout", "theme", "widgets"):
        if key in msg:
            updates[key] = msg[key]

    await store.async_update_view(view_id, **updates)

    # Notify all coordinators that use this view to refresh
    await _notify_coordinators_of_view_change(hass, view_id)

    connection.send_result(msg["id"], {"view": store.get_view(view_id)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/views/delete",
        vol.Required("view_id"): str,
    }
)
@websocket_api.async_response
async def ws_views_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a view."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    view_id = msg["view_id"]

    if not store.get_view(view_id):
        connection.send_error(msg["id"], "not_found", "View not found")
        return

    await store.async_delete_view(view_id)

    # Remove from all device assignments
    for key, data in hass.data[DOMAIN].items():
        if key == "store" or not hasattr(data, "config_entry"):
            continue
        coordinator: GeekMagicCoordinator = data
        assigned = coordinator.options.get("assigned_views", [])
        if view_id in assigned:
            entry = coordinator.config_entry
            if entry is None:
                continue
            new_assigned = [v for v in assigned if v != view_id]
            new_options = dict(entry.options)
            new_options["assigned_views"] = new_assigned
            hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/views/duplicate",
        vol.Required("view_id"): str,
        vol.Optional("name"): str,
    }
)
@websocket_api.async_response
async def ws_views_duplicate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Duplicate a view."""
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    new_id = await store.async_duplicate_view(msg["view_id"], msg.get("name"))

    if new_id:
        connection.send_result(
            msg["id"],
            {
                "view_id": new_id,
                "view": store.get_view(new_id),
            },
        )
    else:
        connection.send_error(msg["id"], "not_found", "Source view not found")


# =============================================================================
# Device Commands
# =============================================================================


@websocket_api.websocket_command({vol.Required("type"): "geekmagic/devices/list"})
@callback
def ws_devices_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get all GeekMagic devices with their assignments."""
    devices = []
    for key, data in hass.data.get(DOMAIN, {}).items():
        if key == "store" or not hasattr(data, "device"):
            continue
        coordinator: GeekMagicCoordinator = data
        devices.append(
            {
                "entry_id": coordinator.config_entry.entry_id if coordinator.config_entry else key,
                "name": coordinator.device_name,
                "host": coordinator.device.host,
                "assigned_views": coordinator.options.get("assigned_views", []),
                "current_view_index": coordinator.current_screen,
                "brightness": coordinator.brightness,
                "refresh_interval": coordinator.options.get(
                    CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                ),
                "cycle_interval": coordinator.options.get(
                    CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL
                ),
                "online": coordinator.last_update_success,
            }
        )
    connection.send_result(msg["id"], {"devices": devices})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/devices/assign_views",
        vol.Required("entry_id"): str,
        vol.Required("view_ids"): [str],
    }
)
@websocket_api.async_response
async def ws_devices_assign_views(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Assign views to a device."""
    entry_id = msg["entry_id"]

    coordinator = _get_coordinator(hass, entry_id)
    if not coordinator:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    entry = coordinator.config_entry
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Config entry not found")
        return

    new_options = dict(entry.options)
    new_options["assigned_views"] = msg["view_ids"]

    hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/devices/settings",
        vol.Required("entry_id"): str,
        vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("refresh_interval"): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Optional("cycle_interval"): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
    }
)
@websocket_api.async_response
async def ws_devices_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update device settings."""
    entry_id = msg["entry_id"]

    coordinator = _get_coordinator(hass, entry_id)
    if not coordinator:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    entry = coordinator.config_entry
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Config entry not found")
        return

    new_options = dict(entry.options)

    if "brightness" in msg:
        new_options["brightness"] = msg["brightness"]
        await coordinator.async_set_brightness(msg["brightness"])

    if "refresh_interval" in msg:
        new_options[CONF_REFRESH_INTERVAL] = msg["refresh_interval"]

    if "cycle_interval" in msg:
        new_options[CONF_SCREEN_CYCLE_INTERVAL] = msg["cycle_interval"]

    hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(msg["id"], {"success": True})


# =============================================================================
# Preview Command
# =============================================================================


def _fetch_entity_history(
    hass: HomeAssistant, entity_id: str, start: datetime, end: datetime
) -> list:
    """Fetch history for an entity (sync, runs in executor).

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to fetch history for
        start: Start time (datetime)
        end: End time (datetime)

    Returns:
        List of State objects for the entity
    """
    from homeassistant.components.recorder import history

    result = history.state_changes_during_period(
        hass,
        start,
        end,
        entity_id,
        include_start_time_state=True,
        no_attributes=True,
    )
    return result.get(entity_id, [])


def _extract_numeric_values(history_states: list) -> list[float]:
    """Extract numeric values from recorder history states.

    Args:
        history_states: List of State objects or dicts from recorder

    Returns:
        List of numeric float values
    """
    # Import the shared function from coordinator
    from .coordinator import extract_numeric_values

    return extract_numeric_values(history_states)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/preview/render",
        vol.Required("view_config"): dict,
    }
)
@websocket_api.async_response
async def ws_preview_render(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Render a preview image for a view configuration."""
    view_config = msg["view_config"]

    # Import here to avoid circular imports
    from .coordinator import LAYOUT_CLASSES, WIDGET_CLASSES
    from .widgets.theme import get_theme

    # Pre-fetch history for chart widgets
    chart_history: dict[str, list[float]] = {}

    try:
        from homeassistant.components.recorder import get_instance

        recorder = get_instance(hass)
        now = dt_util.utcnow()

        for widget_data in view_config.get("widgets", []):
            if widget_data.get("type") == "chart":
                entity_id = widget_data.get("entity_id")
                if entity_id:
                    # Get period from widget options (default 24 hours)
                    options = widget_data.get("options", {})
                    period = options.get("period", "24 hours")

                    # Convert period to hours
                    period_hours = {
                        "5 min": 5 / 60,
                        "15 min": 15 / 60,
                        "1 hour": 1,
                        "6 hours": 6,
                        "24 hours": 24,
                    }.get(period, 24)

                    start_time = now - timedelta(hours=period_hours)

                    # Fetch history in executor
                    history_states = await recorder.async_add_executor_job(
                        _fetch_entity_history,
                        hass,
                        entity_id,
                        start_time,
                        now,
                    )

                    if history_states:
                        values = _extract_numeric_values(history_states)
                        if values:
                            chart_history[entity_id] = values
    except (ImportError, KeyError):
        # Recorder not available, charts will show no data
        pass

    # Pre-fetch history for candlestick widgets
    candlestick_data: dict[str, list[tuple[float, float, float, float]]] = {}
    try:
        from homeassistant.components.recorder import get_instance

        from .widgets.candlestick import INTERVAL_TO_SECONDS, aggregate_ohlc

        recorder = get_instance(hass)
        now = dt_util.utcnow()

        for widget_data in view_config.get("widgets", []):
            if widget_data.get("type") == "candlestick":
                entity_id = widget_data.get("entity_id")
                if entity_id:
                    options = widget_data.get("options", {})
                    candle_interval = options.get("candle_interval", "4 hours")
                    candle_count = int(options.get("candle_count", 20))
                    interval_hours = {"1 hour": 1, "4 hours": 4, "1 day": 24}.get(
                        candle_interval, 4
                    )
                    interval_seconds = INTERVAL_TO_SECONDS.get(candle_interval, 14400)
                    total_hours = interval_hours * candle_count
                    start_time = now - timedelta(hours=total_hours)

                    history_states = await recorder.async_add_executor_job(
                        _fetch_entity_history,
                        hass,
                        entity_id,
                        start_time,
                        now,
                    )

                    if history_states:
                        timestamped: list[tuple[float, float]] = []
                        for state_obj in history_states:
                            try:
                                sv = (
                                    state_obj.state
                                    if hasattr(state_obj, "state")
                                    else state_obj.get("state")
                                )
                                ts = (
                                    state_obj.last_changed.timestamp()
                                    if hasattr(state_obj, "last_changed")
                                    else state_obj.get("last_changed", 0)
                                )
                                if sv is not None:
                                    timestamped.append((float(ts), float(sv)))
                            except (ValueError, TypeError, AttributeError):
                                continue
                        if timestamped:
                            candles = aggregate_ohlc(timestamped, interval_seconds, candle_count)
                            if candles:
                                candlestick_data[entity_id] = candles
    except (ImportError, KeyError):
        pass

    # Pre-fetch forecast for weather widgets
    # Uses weather.get_forecasts service (required since HA 2024.3+)
    weather_forecasts: dict[str, list[dict[str, Any]]] = {}
    for widget_data in view_config.get("widgets", []):
        if widget_data.get("type") == "weather":
            entity_id = widget_data.get("entity_id")
            if entity_id:
                try:
                    response = await hass.services.async_call(
                        "weather",
                        "get_forecasts",
                        {"type": "daily"},
                        target={"entity_id": entity_id},
                        blocking=True,
                        return_response=True,
                    )
                    if response and entity_id in response:
                        weather_forecasts[entity_id] = response[entity_id].get("forecast", [])
                except Exception as err:
                    _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, err)

    def _render() -> bytes:
        """Render the view (runs in executor)."""
        renderer = Renderer()

        # Create layout
        layout_type = view_config.get("layout", LAYOUT_GRID_2X2)
        layout_class = LAYOUT_CLASSES.get(layout_type)
        if not layout_class:
            layout_class = LAYOUT_CLASSES[LAYOUT_GRID_2X2]
        layout = layout_class()

        # Set theme
        theme_name = view_config.get("theme", THEME_CLASSIC)
        layout.theme = get_theme(theme_name)

        # Add widgets
        for widget_data in view_config.get("widgets", []):
            widget_type = widget_data.get("type")
            slot = widget_data.get("slot", 0)

            if slot >= layout.get_slot_count():
                continue

            widget_class = WIDGET_CLASSES.get(widget_type)
            if not widget_class:
                continue

            raw_color = widget_data.get("color")
            parsed_color = None
            if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
                parsed_color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))

            config = WidgetConfig(
                widget_type=widget_type,
                slot=slot,
                entity_id=widget_data.get("entity_id"),
                label=widget_data.get("label"),
                color=parsed_color,
                options=widget_data.get("options", {}),
            )
            widget = widget_class(config)
            layout.set_widget(slot, widget)

        # Build widget_states for rendering
        from datetime import UTC
        from zoneinfo import ZoneInfo

        widget_states: dict[int, WidgetState] = {}
        tz = getattr(hass.config, "time_zone_obj", None) or UTC
        now = datetime.now(tz=tz)

        for widget_data in view_config.get("widgets", []):
            slot = widget_data.get("slot", 0)
            if slot >= layout.get_slot_count():
                continue

            entity_id = widget_data.get("entity_id")
            entity: EntityState | None = None

            # Build entity state from hass
            if entity_id:
                state = hass.states.get(entity_id)
                if state:
                    entity = EntityState(
                        entity_id=entity_id,
                        state=state.state,
                        attributes=dict(state.attributes),
                    )

            # Get chart history if available
            history: list[float] = []
            widget_type = widget_data.get("type")
            if widget_type == "chart" and entity_id in chart_history:
                history = chart_history[entity_id]

            # Get candlestick data if available
            candle_data: list[tuple[float, float, float, float]] = []
            if widget_type == "candlestick" and entity_id in candlestick_data:
                candle_data = candlestick_data[entity_id]

            # Get weather forecast if available
            forecast: list[dict[str, Any]] = []
            if widget_type == "weather" and entity_id in weather_forecasts:
                forecast = weather_forecasts[entity_id]

            # Handle clock widget timezone override
            widget_now = now
            if widget_type == "clock":
                tz_option = widget_data.get("options", {}).get("timezone")
                if tz_option:
                    with contextlib.suppress(Exception):
                        widget_now = datetime.now(tz=ZoneInfo(tz_option))

            widget_states[slot] = WidgetState(
                entity=entity,
                entities={},
                history=history,
                candlestick_data=candle_data,
                forecast=forecast,
                image=None,
                now=widget_now,
            )

        # Render
        img, draw = renderer.create_canvas(background=layout.theme.background)
        layout.render(renderer, draw, widget_states)
        return renderer.to_png(img)

    try:
        png_data = await hass.async_add_executor_job(_render)
        connection.send_result(
            msg["id"],
            {
                "image": base64.b64encode(png_data).decode("utf-8"),
                "content_type": "image/png",
                "width": 240,
                "height": 240,
            },
        )
    except Exception as err:
        _LOGGER.exception("Error rendering preview")
        connection.send_error(msg["id"], "render_error", str(err))


# =============================================================================
# Entity List Command
# =============================================================================


@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/entities/list",
        vol.Optional("domain"): vol.Any(str, [str]),
        vol.Optional("device_class"): vol.Any(str, [str]),
        vol.Optional("search"): str,
        vol.Optional("widget_type"): str,
        vol.Optional("limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
    }
)
@callback
def ws_entities_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get filtered entity list for widget configuration."""
    # Determine domain filter
    domains: list[str] | None = None
    if "widget_type" in msg:
        schema = WIDGET_TYPE_SCHEMAS.get(msg["widget_type"], {})
        domains = schema.get("entity_domains")
    elif "domain" in msg:
        domain_val = msg["domain"]
        domains = [domain_val] if isinstance(domain_val, str) else domain_val

    device_classes: list[str] | None = None
    if "device_class" in msg:
        dc_val = msg["device_class"]
        device_classes = [dc_val] if isinstance(dc_val, str) else dc_val

    search = msg.get("search", "").lower()
    limit = msg.get("limit", 100)

    # Get registries
    entity_reg = er.async_get(hass)
    area_registry = hass.data.get("area_registry")
    device_registry = hass.data.get("device_registry")

    results = []
    for state in hass.states.async_all():
        entity_id = state.entity_id
        domain = entity_id.split(".")[0]

        # Domain filter
        if domains and domain not in domains:
            continue

        # Device class filter
        if device_classes:
            dc = state.attributes.get("device_class")
            if dc not in device_classes:
                continue

        # Search filter
        if search:
            friendly_name = state.attributes.get("friendly_name", "").lower()
            if search not in entity_id.lower() and search not in friendly_name:
                continue

        # Get additional info
        area_name = None
        device_name = None

        entity_entry = entity_reg.async_get(entity_id)
        if entity_entry:
            if entity_entry.area_id and area_registry:
                area_entry = area_registry.async_get_area(entity_entry.area_id)
                if area_entry:
                    area_name = area_entry.name

            if entity_entry.device_id and device_registry:
                device_entry = device_registry.async_get(entity_entry.device_id)
                if device_entry:
                    device_name = device_entry.name
                    if not area_name and device_entry.area_id and area_registry:
                        area_entry = area_registry.async_get_area(device_entry.area_id)
                        if area_entry:
                            area_name = area_entry.name

        results.append(
            {
                "entity_id": entity_id,
                "name": state.attributes.get("friendly_name", entity_id),
                "state": state.state,
                "unit": state.attributes.get("unit_of_measurement"),
                "device_class": state.attributes.get("device_class"),
                "area": area_name,
                "device": device_name,
                "domain": domain,
                "icon": state.attributes.get("icon"),
            }
        )

        if len(results) >= limit:
            break

    # Sort by name
    results.sort(key=lambda x: x["name"].lower())

    connection.send_result(
        msg["id"],
        {
            "entities": results,
            "total": len(results),
            "has_more": len(results) >= limit,
        },
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> GeekMagicCoordinator | None:
    """Get coordinator by entry ID."""
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data and hasattr(data, "device"):
        return data
    return None


async def _notify_coordinators_of_view_change(hass: HomeAssistant, view_id: str) -> None:
    """Notify all coordinators using a view that it changed."""
    for key, data in hass.data.get(DOMAIN, {}).items():
        if key == "store" or not hasattr(data, "device"):
            continue
        coordinator: GeekMagicCoordinator = data
        assigned = coordinator.options.get("assigned_views", [])
        if view_id in assigned:
            # Reload views from store and refresh display
            await coordinator.async_reload_views()
