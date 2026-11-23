"""The view services: ``geekmagic.show_view`` and ``geekmagic.set_view_cycling``.

Both name a view the way a person does, by its name (or its id), among
the views assigned to each targeted display (issue #160).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import CONF_SKIPPED_VIEWS, DOMAIN
from .coordinator import CONF_ASSIGNED_VIEWS, GeekMagicCoordinator

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

    from .store import GeekMagicStore

SERVICE_SHOW_VIEW = "show_view"
SERVICE_SET_VIEW_CYCLING = "set_view_cycling"

_DEVICES = vol.All(cv.ensure_list, [cv.string])

SHOW_VIEW_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): _DEVICES,
        vol.Required("view"): cv.string,
        vol.Optional("duration"): cv.positive_time_period,
    }
)

SET_VIEW_CYCLING_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): _DEVICES,
        vol.Required("view"): vol.All(cv.ensure_list, [cv.string]),
        vol.Required("cycle"): cv.boolean,
    }
)


def with_skipped_views(options: Mapping[str, Any], skipped: Iterable[str]) -> dict[str, Any]:
    """``options`` with ``skipped`` as its skipped views.

    Kept to assigned views, in assigned order: a view removed from the
    display must not come back skipped when it is assigned again.
    """
    keep = set(skipped)
    assigned = options.get(CONF_ASSIGNED_VIEWS, [])
    return {**options, CONF_SKIPPED_VIEWS: [v for v in assigned if v in keep]}


def set_views_cycling(
    hass: HomeAssistant, entry: ConfigEntry, view_ids: Iterable[str], cycle: bool
) -> None:
    """Include views in (``cycle``) or skip them from a display's View Cycling.

    An entry option, like the assignment itself: it persists, and applies
    to a display that isn't loaded once it is.
    """
    current = set(entry.options.get(CONF_SKIPPED_VIEWS, []))
    skipped = current - set(view_ids) if cycle else current | set(view_ids)
    options = with_skipped_views(entry.options, skipped)
    if options.get(CONF_SKIPPED_VIEWS) != entry.options.get(CONF_SKIPPED_VIEWS, []):
        hass.config_entries.async_update_entry(entry, options=options)


def _entries(hass: HomeAssistant, device_ids: list[str]) -> list[ConfigEntry]:
    """The GeekMagic config entry of each device, or a validation error."""
    registry = dr.async_get(hass)
    entries = []
    for device_id in device_ids:
        device = registry.async_get(device_id)
        entry = None
        if device is not None:
            entry = next(
                (
                    found
                    for entry_id in device.config_entries
                    if (found := hass.config_entries.async_get_entry(entry_id))
                    and found.domain == DOMAIN
                ),
                None,
            )
        if entry is None:
            raise ServiceValidationError(f"Device {device_id} is not a GeekMagic display")
        entries.append(entry)
    return entries


def _resolve_view(hass: HomeAssistant, entry: ConfigEntry, ref: str) -> str:
    """The id of the view ``ref`` names (id or name) among the display's own."""
    assigned: list[str] = entry.options.get(CONF_ASSIGNED_VIEWS, [])
    if ref in assigned:
        return ref
    store: GeekMagicStore = hass.data[DOMAIN]["store"]
    wanted = ref.strip().casefold()
    matches = [
        view_id
        for view_id in assigned
        if (view := store.get_view(view_id)) and str(view.get("name", "")).casefold() == wanted
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ServiceValidationError(
            f'{entry.title} has {len(matches)} views named "{ref}": rename one of them'
        )
    raise ServiceValidationError(f'{entry.title} has no view named "{ref}"')


def _coordinator(hass: HomeAssistant, entry: ConfigEntry) -> GeekMagicCoordinator:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not isinstance(coordinator, GeekMagicCoordinator):
        raise ServiceValidationError(f"{entry.title} is not loaded")
    return coordinator


def async_register_services(hass: HomeAssistant) -> None:
    """Register the view services (once per Home Assistant)."""

    async def show_view(call: ServiceCall) -> None:
        # Resolve every target first: a typo fails the call, not half of it
        targets = [
            (_coordinator(hass, entry), _resolve_view(hass, entry, call.data["view"]))
            for entry in _entries(hass, call.data["device_id"])
        ]
        duration = call.data.get("duration")
        seconds = duration.total_seconds() if duration else None
        for coordinator, view_id in targets:
            try:
                await coordinator.async_show_view_for(view_id, seconds)
            except ValueError as err:  # the view store no longer has it
                raise ServiceValidationError(str(err)) from err

    async def set_view_cycling(call: ServiceCall) -> None:
        targets = [
            (entry, [_resolve_view(hass, entry, ref) for ref in call.data["view"]])
            for entry in _entries(hass, call.data["device_id"])
        ]
        for entry, view_ids in targets:
            set_views_cycling(hass, entry, view_ids, call.data["cycle"])

    hass.services.async_register(DOMAIN, SERVICE_SHOW_VIEW, show_view, schema=SHOW_VIEW_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_VIEW_CYCLING, set_view_cycling, schema=SET_VIEW_CYCLING_SCHEMA
    )
