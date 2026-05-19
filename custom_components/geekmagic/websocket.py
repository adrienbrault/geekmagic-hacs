"""WebSocket API for GeekMagic custom panel.

Provides commands for managing views, devices, and preview rendering.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

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
from .widgets import WIDGET_TYPE_SCHEMAS

if TYPE_CHECKING:
    from .coordinator import GeekMagicCoordinator
    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)


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
    from .history_fetcher import HistoryFetcher
    from .screen_builder import build_layout
    from .widget_state_builder import PrefetchedData, build_widget_states
    from .widgets.candlestick import INTERVAL_TO_SECONDS

    fetcher = HistoryFetcher(hass)

    chart_history: dict[str, list[float]] = {}
    candlestick_data: dict[str, list[tuple[float, float, float, float]]] = {}

    for widget_data in view_config.get("widgets", []):
        widget_type = widget_data.get("type")
        entity_id = widget_data.get("entity_id")
        if not entity_id:
            continue
        options = widget_data.get("options", {})

        if widget_type == "chart":
            period = options.get("period", "24 hours")
            period_hours = {
                "5 min": 5 / 60,
                "15 min": 15 / 60,
                "1 hour": 1,
                "6 hours": 6,
                "24 hours": 24,
            }.get(period, 24)
            values = await fetcher.fetch_numeric(entity_id, period_hours)
            if values:
                chart_history[entity_id] = values

        elif widget_type == "candlestick":
            candle_interval = options.get("candle_interval", "4 hours")
            candle_count = int(options.get("candle_count", 20))
            interval_hours = {"1 hour": 1, "4 hours": 4, "1 day": 24}.get(candle_interval, 4)
            interval_seconds = INTERVAL_TO_SECONDS.get(candle_interval, 14400)
            total_hours = interval_hours * candle_count
            candles = await fetcher.fetch_ohlc(
                entity_id, total_hours, interval_seconds, candle_count
            )
            if candles:
                candlestick_data[entity_id] = candles

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
                    forecast_response = (
                        response.get(entity_id) if isinstance(response, dict) else None
                    )
                    if isinstance(forecast_response, dict):
                        raw = forecast_response.get("forecast", [])
                        if isinstance(raw, list):
                            weather_forecasts[entity_id] = [
                                d for d in raw if isinstance(d, dict)
                            ]
                except Exception as err:
                    _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, err)

    def _render() -> bytes:
        """Render the view (runs in executor)."""
        renderer = Renderer()
        layout = build_layout(view_config)
        widget_states = build_widget_states(
            layout,
            hass,
            PrefetchedData(
                chart_history=chart_history,
                candlestick_data=candlestick_data,
                weather_forecasts=weather_forecasts,
            ),
        )
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
