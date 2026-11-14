"""WebSocket API for GeekMagic custom panel.

Provides commands for managing views, devices, and preview rendering.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_NAMES,
    LAYOUT_SLOT_COUNTS,
    THEME_CLASSIC,
    THEME_OPTIONS,
)
from .frame import FrameInputs, build_layout, layout_widgets, render_still
from .renderer import Renderer
from .widgets import WIDGET_TYPE_SCHEMAS

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .coordinator import GeekMagicCoordinator
    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)

# Upper bound, in seconds, for each camera snapshot and album-art fetch of a
# preview render. Shorter than the device's: the user is waiting on the
# editor, and a slow picture should cost them the picture (placeholder or
# text fallback), not the preview.
PREVIEW_IMAGE_TIMEOUT = 5


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands.

    Every command is ``require_admin``. The panel that calls them is
    admin-only, but websocket commands are reachable by any logged-in
    user. They save views and render previews, and labels can hold Home
    Assistant templates, which core only lets admins render.
    """
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
    websocket_api.async_register_command(hass, ws_devices_show_view)

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


@websocket_api.require_admin
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
                k: {
                    "slots": v,
                    "name": LAYOUT_NAMES.get(k, k.replace("_", " ").title()),
                    "rects": _layout_rects(k),
                }
                for k, v in LAYOUT_SLOT_COUNTS.items()
            },
            "themes": dict(THEME_OPTIONS.items()),
        },
    )


def _layout_rects(layout_type: str) -> list[list[float]]:
    """Slot rectangles as fractions ``[x, y, w, h]`` of the screen (default theme).

    For the panel's layout tiles; the preview returns the exact pixel rects
    for the view's own theme (padding and gap vary by theme).
    """
    from .frame import LAYOUT_CLASSES

    layout = LAYOUT_CLASSES[layout_type]()
    size = float(layout.width)
    return [
        [
            round(x1 / size, 4),
            round(y1 / size, 4),
            round((x2 - x1) / size, 4),
            round((y2 - y1) / size, 4),
        ]
        for x1, y1, x2, y2 in (slot.rect for slot in layout.slots)
    ]


# =============================================================================
# View Commands
# =============================================================================


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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

    # Remove from every display's assignments, loaded or not: a display
    # that is offline now would otherwise come back pointing at it.
    for entry in hass.config_entries.async_entries(DOMAIN):
        assigned = entry.options.get("assigned_views", [])
        if view_id in assigned:
            new_options = dict(entry.options)
            new_options["assigned_views"] = [v for v in assigned if v != view_id]
            hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "geekmagic/devices/list"})
@callback
def ws_devices_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get every GeekMagic display with its assignments.

    Every config entry is listed, loaded or not: a display Home Assistant
    can't reach (``setup_retry``) is still configured and its assigned views
    still live in the entry's options. Fields only a running coordinator
    knows (brightness, what is on screen, entities) are null or empty for
    an entry that isn't loaded; ``state`` and ``reason`` say why.
    """
    devices = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = _get_coordinator(hass, entry.entry_id)
        devices.append(
            _loaded_device(hass, entry, coordinator) if coordinator else _unloaded_device(entry)
        )
    connection.send_result(msg["id"], {"devices": devices})


def _entry_fields(entry: ConfigEntry, options: Mapping[str, Any]) -> dict[str, Any]:
    """What the panel needs that the config entry alone knows."""
    return {
        "entry_id": entry.entry_id,
        "assigned_views": options.get("assigned_views", []),
        "refresh_interval": options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        "cycle_interval": options.get(CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL),
        "state": entry.state.value,
        "reason": entry.reason,
        "disabled": entry.disabled_by is not None,
    }


def _loaded_device(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: GeekMagicCoordinator
) -> dict[str, Any]:
    return {
        **_entry_fields(entry, coordinator.options),
        "name": coordinator.device_name,
        "host": coordinator.device.host,
        "current_view_index": coordinator.current_screen,
        "brightness": coordinator.brightness,
        "online": coordinator.last_update_success,
        "display_mode": coordinator.display_mode,
        "current_view_id": coordinator.current_view_id,
        "builtin_mode": _builtin_mode_name(coordinator),
        "entities": _device_entities(hass, coordinator),
    }


def _unloaded_device(entry: ConfigEntry) -> dict[str, Any]:
    return {
        **_entry_fields(entry, entry.options),
        "name": entry.title,
        "host": entry.data.get(CONF_HOST, ""),
        "current_view_index": None,
        "brightness": None,
        "online": False,
        "display_mode": None,
        "current_view_id": None,
        "builtin_mode": None,
        "entities": {},
    }


# Entities the panel drives directly, by unique-id suffix. Resolved through
# the registry because users can rename entity ids.
_PANEL_ENTITIES = {
    "display": ("select", "display"),
    "brightness": ("number", "brightness"),
    "cycle_interval": ("number", "cycle_interval"),
    "view_cycling": ("switch", "view_cycling"),
    "active": ("switch", "active"),
    "status": ("sensor", "status"),
}


def _device_entities(hass: HomeAssistant, coordinator: GeekMagicCoordinator) -> dict[str, str]:
    """Current entity ids of a device's panel controls (missing ones omitted)."""
    entry = coordinator.config_entry
    if entry is None:
        return {}
    registry = er.async_get(hass)
    found: dict[str, str] = {}
    for key, (domain, suffix) in _PANEL_ENTITIES.items():
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{suffix}")
        if entity_id:
            found[key] = entity_id
    preview = registry.async_get_entity_id("image", DOMAIN, f"{coordinator.device.host}_preview")
    if preview:
        found["preview"] = preview
    return found


def _builtin_mode_name(coordinator: GeekMagicCoordinator) -> str | None:
    """Name of the firmware built-in mode on screen, if any."""
    if coordinator.display_mode != "builtin":
        return None
    for name, theme in coordinator.device.builtin_modes.items():
        if theme == coordinator.builtin_theme:
            return name
    return None


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "geekmagic/devices/show_view",
        vol.Required("entry_id"): str,
        vol.Required("view_id"): str,
    }
)
@websocket_api.async_response
async def ws_devices_show_view(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Show one of a device's assigned views now, by id."""
    coordinator = _live_coordinator_or_error(hass, connection, msg)
    if not coordinator:
        return
    try:
        await coordinator.async_show_view(msg["view_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_assigned", str(err))
        return
    connection.send_result(msg["id"], {"current_view_id": coordinator.current_view_id})


@websocket_api.require_admin
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
    """Assign views to a device.

    Works whether or not the display is loaded: the assignment is an entry
    option. A loaded display applies it at once (the options listener); one
    Home Assistant can't reach yet starts with it when its setup succeeds.
    """
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    new_options = dict(entry.options)
    new_options["assigned_views"] = msg["view_ids"]

    hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
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
    """Update device settings.

    The intervals are entry options and apply to a display that isn't
    loaded once it is. Brightness is sent to the device, so it needs a
    loaded display: for one that isn't, the whole request is refused
    (``not_loaded``) before anything is saved.
    """
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return

    new_options = dict(entry.options)

    if "brightness" in msg:
        coordinator = _live_coordinator_or_error(hass, connection, msg)
        if not coordinator:
            return
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


@websocket_api.require_admin
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
    """Render a preview of a (possibly unsaved) view configuration.

    The view goes through the device's own frame pipeline (``frame``):
    the same layout builder, the same inputs (camera snapshots, album art,
    pictures, history, forecasts, templates) and the same render, so the
    preview is the frame a device showing this view is sent. Only the
    encoding differs: a PNG, never rotated, and never animated.
    """
    try:
        layout = build_layout(msg["view_config"])
        inputs = FrameInputs(hass, fetch_timeout=PREVIEW_IMAGE_TIMEOUT, quiet=True)
        # Templates render last, in the event loop, with no await before
        # the executor job below.
        await inputs.async_gather(layout_widgets(layout))

        def _render() -> bytes:
            renderer = Renderer()
            image = render_still(renderer, layout, inputs.widget_states(layout))
            return renderer.to_png(image)

        png_data = await hass.async_add_executor_job(_render)
        connection.send_result(
            msg["id"],
            {
                "image": base64.b64encode(png_data).decode("utf-8"),
                "content_type": "image/png",
                "width": 240,
                "height": 240,
                # Pixel rects [x1, y1, x2, y2] of each slot, for the panel's
                # click-to-select overlay (theme-dependent padding and gap).
                "slots": [list(slot.rect) for slot in layout.slots],
            },
        )
    except Exception as err:
        _LOGGER.exception("Error rendering preview")
        connection.send_error(msg["id"], "render_error", str(err))


# =============================================================================
# Entity List Command
# =============================================================================


@websocket_api.require_admin
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

    # Get registries. Use the public helpers rather than reaching into
    # ``hass.data`` by string key: the keys are ``HassKey`` objects that only
    # happen to subclass ``str``, and a raw lookup returns ``None`` (dropping
    # the device and area names) whenever the registry singleton has not been
    # created yet.
    entity_reg = er.async_get(hass)
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)

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
            if entity_entry.area_id:
                area_entry = area_registry.async_get_area(entity_entry.area_id)
                if area_entry:
                    area_name = area_entry.name

            if entity_entry.device_id:
                device_entry = device_registry.async_get(entity_entry.device_id)
                if device_entry:
                    device_name = device_entry.name
                    if not area_name and device_entry.area_id:
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


def _entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """This integration's config entry ``entry_id``, loaded or not."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _live_coordinator_or_error(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> GeekMagicCoordinator | None:
    """The running coordinator of ``msg["entry_id"]``, or send why there is none.

    ``not_loaded`` for a configured display Home Assistant hasn't set up
    (unreachable, disabled, failed), ``not_found`` for an unknown entry.
    """
    coordinator = _get_coordinator(hass, msg["entry_id"])
    if coordinator:
        return coordinator
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Device not found")
        return None
    detail = f": {entry.reason}" if entry.reason else ""
    connection.send_error(
        msg["id"],
        "not_loaded",
        f"{entry.title} isn't connected ({entry.state.value}{detail}). "
        "Home Assistant sets it up again once it can reach the display.",
    )
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
