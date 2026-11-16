"""GeekMagic view editing as LLM tools.

Tools an AI agent uses to build and edit views, the same thing the panel
does. Assist (with an LLM conversation agent: Anthropic, OpenAI, Google,
Ollama...) and MCP clients (Claude Desktop, Claude Code... through Home
Assistant's MCP Server integration) both get them from an LLM API:

- Home Assistant 2026.11 and later: the built-in "Home Assistant" API,
  which manages Home Assistant itself and is admin-only. The ``llm``
  platform (``llm.py``) adds these tools to it, prefixed ``geekmagic__``
  like every integration's.
- Before: a "GeekMagic displays" API of its own, registered here.

The tools go through the same store and coordinators as the panel's
websocket commands, and are admin-only like them. The standalone API
gives anyone else no tools rather than an error, so it can sit next to
Assist for a voice satellite (no user) without breaking it.

Writes are validated against the widget ``SCHEMA``s before they are
saved, and every error says what was wrong and what is accepted, so a
model can correct itself instead of saving a view that renders blank.

Models cannot see the screen through either channel (tool results are
text), so ``geekmagic__render_view`` returns a short-lived signed URL to
the rendered PNG (for clients that can fetch it) and a per-slot report of
what each cell shows and what is wrong with it (for those that can't).
"""

from __future__ import annotations

import logging
import re
import secrets
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.http import KEY_HASS
from homeassistant.util.hass_dict import HassKey

from .const import (
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_NAMES,
    LAYOUT_SLOT_COUNTS,
    THEME_OPTIONS,
    THEME_WATCHOS,
)
from .view import build_layout
from .websocket import (
    _get_coordinator,
    _notify_coordinators_of_view_change,
    async_render_view_png,
)
from .widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS, build_widget, stored_slot
from .widgets.base import BrokenWidget

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)

LLM_API_ID = DOMAIN
LLM_API_NAME = "GeekMagic displays"

# Rendered PNGs, by unguessable token, until they expire.
DATA_RENDERS: HassKey[dict[str, tuple[float, bytes]]] = HassKey(f"{DOMAIN}_llm_renders")
DATA_RENDER_VIEW: HassKey[bool] = HassKey(f"{DOMAIN}_llm_render_view")
RENDER_URL = "/api/geekmagic/render/{token}.png"
RENDER_TTL = timedelta(minutes=10)
MAX_RENDERS = 20

_HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{6})$")

API_PROMPT = """\
GeekMagic displays: the geekmagic__ tools build and edit what they show.
- A display is a 240x240 px screen, about 3 cm wide, read from up to a metre \
away. It shows one view at a time and cycles through the views assigned to it.
- A view has a layout (how the screen is split into slots), a theme, and one \
widget per slot. Slots are numbered from 0, left to right then top to bottom.
- Start with geekmagic__get_catalog (layouts, themes, widget types and their \
options) and geekmagic__get_views (views and displays). Find entity ids with \
geekmagic__find_entities; never guess one.
- Fewer, bigger cells read better: prefer 2-4 slots. A widget's label is \
optional; leave it out unless the entity name is unclear.
- Colour comes from the theme (watchos unless the user wants another). Set a \
widget's colour only when the colour means something. The night theme is \
monochrome: it ignores widget colours.
- A display shows every change to a view assigned to it at once. To rework \
such a view, copy it with geekmagic__duplicate_view, edit and render the \
copy, then assign the copy in its place (deleting the old one is up to the \
user, in the panel), unless the user asked to change it in place.
- A new view shows nowhere until it is assigned to a display \
(geekmagic__assign_views, which replaces the display's list). \
geekmagic__show_view switches a display to one of its assigned views now.
- After changing a view, call geekmagic__render_view and fix every problem it \
reports. If you can fetch URLs, look at the image it links to.
"""


# =============================================================================
# Registration
# =============================================================================


def core_has_home_assistant_api() -> bool:
    """Whether this core's built-in "Home Assistant" API takes integration tools."""
    return hasattr(llm, "LLM_API_HOME_ASSISTANT")


def make_tools() -> list[llm.Tool]:
    """A fresh instance of every GeekMagic tool."""
    return [tool() for tool in _TOOLS]


@callback
def async_setup_llm_api(hass: HomeAssistant) -> None:
    """Set up the tools' plumbing (once per Home Assistant process).

    Registers the render image view: aiohttp freezes its router once
    Home Assistant's web server runs, so it can't wait for the first
    render. On cores without the "Home Assistant" API, registers the
    standalone GeekMagic API; newer ones get the tools from ``llm.py``.
    """
    if hass.http is not None and not hass.data.get(DATA_RENDER_VIEW):
        hass.http.register_view(RenderImageView())
        hass.data[DATA_RENDER_VIEW] = True
    if core_has_home_assistant_api():
        return
    try:
        llm.async_register_api(hass, GeekMagicAPI(hass=hass, id=LLM_API_ID, name=LLM_API_NAME))
    except HomeAssistantError:
        _LOGGER.debug("GeekMagic LLM API already registered")


class GeekMagicAPI(llm.API):
    """The standalone GeekMagic LLM API, for cores before 2026.11."""

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """The tools, or none for anyone but an admin.

        Not ``requires_admin`` (newer cores): that refuses the whole
        merged API, so a voice satellite (no user) would lose Assist too
        when an agent has both APIs ticked.
        """
        if not await _is_admin(self.hass, llm_context):
            return llm.APIInstance(
                api=self,
                api_prompt=(
                    "The GeekMagic display tools are only available to Home Assistant "
                    "administrators. Tell the user to ask from an administrator account."
                ),
                llm_context=llm_context,
                tools=[],
            )
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=make_tools(),
        )


async def _is_admin(hass: HomeAssistant, llm_context: llm.LLMContext) -> bool:
    context = llm_context.context
    if context is None or not context.user_id:
        return False
    user = await hass.auth.async_get_user(context.user_id)
    return user is not None and user.is_admin


# =============================================================================
# Tool plumbing
# =============================================================================


def _annotations(**kwargs: bool) -> Any:
    """``llm.ToolAnnotations`` where the core has them (MCP hints), else None."""
    cls = getattr(llm, "ToolAnnotations", None)
    return cls(**kwargs) if cls is not None else None


def _result(data: dict[str, Any]) -> Any:
    """A ``ToolResult`` where the core has it; a bare dict is deprecated there."""
    cls = getattr(llm, "ToolResult", None)
    return cls(data=data) if cls is not None else data


class GeekMagicTool(llm.Tool):
    """Base for the GeekMagic tools: admin check, store access, result type."""

    integration = DOMAIN

    def __init__(self) -> None:
        """Set MCP annotations where the core supports them."""
        annotations = self._annotations()
        if annotations is not None:
            self.annotations = annotations

    def _annotations(self) -> Any:
        return _annotations(read_only=False, destructive=False, open_world=False)

    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> Any:
        """Check the caller is an admin, then run the tool."""
        if not await _is_admin(hass, llm_context):
            raise HomeAssistantError("GeekMagic tools need a Home Assistant administrator")
        return _result(await self._async_run(hass, tool_input.tool_args))

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class _ReadOnlyTool(GeekMagicTool):
    def _annotations(self) -> Any:
        return _annotations(read_only=True, destructive=False, idempotent=True, open_world=False)


def _store(hass: HomeAssistant) -> GeekMagicStore:
    return hass.data[DOMAIN]["store"]


def _find_view(hass: HomeAssistant, ref: str) -> dict[str, Any]:
    """A view by id, or by name when no id matches (case-insensitive)."""
    store = _store(hass)
    if view := store.get_view(ref):
        return view
    matches = [v for v in store.views.values() if v.get("name", "").lower() == ref.lower()]
    if len(matches) == 1:
        return matches[0]
    known = ", ".join(f"{v['id']} ({v.get('name')})" for v in store.get_views_list()) or "none"
    if matches:
        raise HomeAssistantError(f'Several views are named "{ref}"; use an id: {known}')
    raise HomeAssistantError(f'No view "{ref}". Views: {known}')


def _find_display(hass: HomeAssistant, ref: str) -> ConfigEntry:
    """A display's config entry by entry id, or by name (case-insensitive)."""
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        if entry.entry_id == ref:
            return entry
    matches = [e for e in entries if _display_name(hass, e).lower() == ref.lower()]
    if len(matches) == 1:
        return matches[0]
    known = ", ".join(f"{e.entry_id} ({_display_name(hass, e)})" for e in entries) or "none"
    raise HomeAssistantError(f'No single display "{ref}". Displays: {known}')


def _display_name(hass: HomeAssistant, entry: ConfigEntry) -> str:
    coordinator = _get_coordinator(hass, entry.entry_id)
    return coordinator.device_name if coordinator else entry.title


def _layout_slot_sizes(layout_id: str, theme: str | None = None) -> list[str]:
    config: dict[str, Any] = {"layout": layout_id, "widgets": [{"type": "text"}]}
    if theme is not None:
        config["theme"] = theme
    layout = build_layout(config)
    return [f"{x2 - x1}x{y2 - y1}" for x1, y1, x2, y2 in (slot.rect for slot in layout.slots)]


async def _async_save_view(hass: HomeAssistant, view_id: str, **updates: Any) -> None:
    await _store(hass).async_update_view(view_id, **updates)
    await _notify_coordinators_of_view_change(hass, view_id)


# =============================================================================
# Validation
# =============================================================================


def _rgb(value: Any, where: str, errors: list[str]) -> list[int] | None:
    """``[r, g, b]`` from a list or a ``#rrggbb`` string."""
    if isinstance(value, str) and (match := _HEX_COLOR.match(value.strip())):
        raw = match.group(1)
        return [int(raw[i : i + 2], 16) for i in (0, 2, 4)]
    if (
        isinstance(value, list | tuple)
        and len(value) == 3
        and all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in value)
    ):
        return list(value)
    errors.append(f'{where}: a colour is "#rrggbb" or [r, g, b] (0-255), got {value!r}')
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_entity(
    hass: HomeAssistant,
    entity_id: Any,
    where: str,
    errors: list[str],
    domains: list[str] | None = None,
) -> None:
    if not isinstance(entity_id, str) or not entity_id:
        errors.append(f"{where}: an entity id is required")
        return
    if hass.states.get(entity_id) is None:
        errors.append(
            f"{where}: entity {entity_id} does not exist (find ids with geekmagic__find_entities)"
        )
        return
    if domains and entity_id.split(".", 1)[0] not in domains:
        errors.append(f"{where}: {entity_id} must be one of the domains {', '.join(domains)}")


_ITEM_FIELDS: dict[str, dict[str, str]] = {
    # Fields of each row of the list-valued option types.
    "thresholds": {"value": "number", "color": "color"},
    "progress_items": {
        "entity_id": "entity",
        "label": "text",
        "target": "number",
        "color": "color",
        "icon": "icon",
        "unit": "text",
    },
    "status_entities": {"entity_id": "entity", "label": "text", "icon": "icon"},
}


def _check_value(
    hass: HomeAssistant, spec_type: str, value: Any, where: str, errors: list[str]
) -> Any:
    """``value`` checked (and normalised) as an option of type ``spec_type``."""
    if spec_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{where}: expected true or false, got {value!r}")
    elif spec_type == "number":
        if not _is_number(value):
            errors.append(f"{where}: expected a number, got {value!r}")
    elif spec_type == "color":
        return _rgb(value, where, errors)
    elif spec_type == "icon":
        if not isinstance(value, str) or not value.startswith("mdi:"):
            errors.append(f'{where}: expected a Material Design icon like "mdi:lightbulb"')
    elif spec_type == "entity":
        _check_entity(hass, value, where, errors)
    elif spec_type in _ITEM_FIELDS:
        return _check_rows(hass, spec_type, value, where, errors)
    elif not isinstance(value, str):  # text, textarea, timezone, select (checked by caller)
        errors.append(f"{where}: expected a string, got {value!r}")
    return value


def _check_rows(
    hass: HomeAssistant, spec_type: str, value: Any, where: str, errors: list[str]
) -> Any:
    fields = _ITEM_FIELDS[spec_type]
    if not isinstance(value, list):
        errors.append(f"{where}: expected a list of objects with {', '.join(fields)}")
        return value
    rows = []
    for index, row in enumerate(value):
        here = f"{where}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{here}: expected an object with {', '.join(fields)}")
            continue
        if "entity_id" in fields and row.get("entity_id") == "":
            continue  # the panel's blank "Add" row: nothing to show
        clean = {}
        for key, item in row.items():
            if key not in fields:
                errors.append(f"{here}: unknown field {key!r} (fields: {', '.join(fields)})")
                continue
            clean[key] = _check_value(hass, fields[key], item, f"{here}.{key}", errors)
        required = "entity_id" if "entity_id" in fields else "value"
        if required not in row:
            errors.append(f"{here}: {required} is required")
        rows.append(clean)
    return rows


def validate_widget(
    hass: HomeAssistant, view: dict[str, Any], slot: int, args: dict[str, Any]
) -> dict[str, Any]:
    """The widget ``args`` describe, as the panel stores it, or raise every problem."""
    errors: list[str] = []
    widget_type = args["type"]
    schema = WIDGET_TYPE_SCHEMAS.get(widget_type)
    if widget_type not in WIDGET_CLASSES or schema is None:
        raise HomeAssistantError(
            f"Unknown widget type {widget_type!r}. Types: {', '.join(WIDGET_TYPE_SCHEMAS)}"
        )
    layout_id = view.get("layout", LAYOUT_GRID_2X2)
    slots = LAYOUT_SLOT_COUNTS.get(layout_id, 4)
    if not 0 <= slot < slots:
        errors.append(f"slot: layout {layout_id} has slots 0 to {slots - 1}")

    widget: dict[str, Any] = {"type": widget_type, "slot": slot}
    entity_id = args.get("entity_id")
    if entity_id:
        _check_entity(hass, entity_id, "entity_id", errors, schema.get("entity_domains"))
        widget["entity_id"] = entity_id
    elif schema.get("needs_entity"):
        errors.append(f"entity_id: a {widget_type} widget needs an entity")
    if label := args.get("label"):
        widget["label"] = label
    if (color := args.get("color")) is not None:
        widget["color"] = _rgb(color, "color", errors)

    specs = {spec["key"]: spec for spec in schema.get("options", [])}
    options: dict[str, Any] = {}
    for key, raw in (args.get("options") or {}).items():
        spec = specs.get(key)
        if spec is None:
            errors.append(
                f"options.{key}: not an option of {widget_type} "
                f"(options: {', '.join(specs) or 'none'})"
            )
            continue
        value = _check_value(hass, spec["type"], raw, f"options.{key}", errors)
        if spec["type"] == "select" and value not in spec.get("options", []):
            errors.append(f"options.{key}: one of {spec.get('options')}, got {value!r}")
        if (
            spec["type"] == "number"
            and _is_number(value)
            and (value < spec.get("min", value) or value > spec.get("max", value))
        ):
            errors.append(f"options.{key}: between {spec.get('min')} and {spec.get('max')}")
        options[key] = value
    if options:
        widget["options"] = options

    if errors:
        raise HomeAssistantError("Widget not saved:\n- " + "\n- ".join(errors))
    return widget


def _check_layout_theme(layout: str | None, theme: str | None) -> None:
    errors = []
    if layout is not None and layout not in LAYOUT_SLOT_COUNTS:
        errors.append(f"layout: one of {', '.join(LAYOUT_SLOT_COUNTS)}")
    if theme is not None and theme not in THEME_OPTIONS:
        errors.append(f"theme: one of {', '.join(THEME_OPTIONS)}")
    if errors:
        raise HomeAssistantError("Not saved:\n- " + "\n- ".join(errors))


# =============================================================================
# The report a model reads instead of the screen
# =============================================================================


def describe_view(hass: HomeAssistant, view: dict[str, Any]) -> dict[str, Any]:
    """What each slot of ``view`` shows, and what is wrong with it."""
    layout = build_layout(view)
    by_slot: dict[int, dict[str, Any]] = {}
    hidden = []
    for config in view.get("widgets", []):
        slot = stored_slot(config)
        if slot is None or not 0 <= slot < len(layout.slots):
            hidden.append(config)
        else:
            by_slot[slot] = config

    slots = []
    for index, slot in enumerate(layout.slots):
        x1, y1, x2, y2 = slot.rect
        entry: dict[str, Any] = {"slot": index, "size": f"{x2 - x1}x{y2 - y1}"}
        problems: list[str] = []
        config = by_slot.get(index)
        if config is None:
            problems.append("empty")
        else:
            entry["widget"] = {
                k: config[k]
                for k in ("type", "entity_id", "label", "color", "options")
                if config.get(k)
            }
            widget = build_widget(config)
            if widget is None:
                problems.append(f"unknown widget type {config.get('type')!r}: not shown")
            elif isinstance(widget, BrokenWidget):
                problems.append("the widget's options are invalid: the cell shows an error")
            else:
                for entity_id in widget.get_entities():
                    state = hass.states.get(entity_id)
                    if state is None:
                        problems.append(f"{entity_id} does not exist")
                    elif state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        problems.append(f"{entity_id} is {state.state}")
        if problems:
            entry["problems"] = problems
        slots.append(entry)

    description: dict[str, Any] = {
        "view_id": view.get("id"),
        "name": view.get("name"),
        "layout": view.get("layout"),
        "theme": view.get("theme"),
        "slots": slots,
    }
    if hidden:
        description["hidden_widgets"] = {
            "note": "outside this layout's slots, kept but not shown",
            "widgets": hidden,
        }
    return description


# =============================================================================
# Tools
# =============================================================================


class GetCatalogTool(_ReadOnlyTool):
    """Layouts, themes and widget types with every option."""

    name = "geekmagic__get_catalog"
    description = (
        "List the layouts (slot count and each slot's pixel size), themes and widget "
        "types of GeekMagic displays, with every widget option, its type and allowed "
        "values. Call this before creating or editing views."
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        widgets = {}
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            options = []
            for spec in schema.get("options", []):
                option = {k: v for k, v in spec.items() if k not in ("label", "placeholder")}
                option["label"] = spec.get("label")
                if spec["type"] in _ITEM_FIELDS:
                    option["row_fields"] = _ITEM_FIELDS[spec["type"]]
                options.append(option)
            widgets[widget_type] = {
                "description": schema.get("description"),
                "needs_entity": bool(schema.get("needs_entity")),
                "entity_domains": schema.get("entity_domains"),
                "uses_label": schema.get("uses_label", True),
                "options": options,
            }
        return {
            "layouts": {
                layout_id: {
                    "name": LAYOUT_NAMES.get(layout_id, layout_id),
                    "slot_sizes": _layout_slot_sizes(layout_id),
                }
                for layout_id in LAYOUT_SLOT_COUNTS
            },
            "themes": dict(THEME_OPTIONS),
            "widget_types": widgets,
            "value_formats": {
                "color": '"#rrggbb" or [r, g, b]',
                "icon": 'Material Design icon, "mdi:<name>"',
                "visible_when": "the option only applies when these other options match",
            },
        }


class GetViewsTool(_ReadOnlyTool):
    """Every view and every display."""

    name = "geekmagic__get_views"
    description = (
        "List every GeekMagic view (layout, theme, widgets per slot) and every display "
        "(its assigned views, the view on screen, whether it is online)."
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        views = [
            {k: v for k, v in view.items() if k not in ("created_at", "updated_at")}
            for view in _store(hass).get_views_list()
        ]
        displays = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = _get_coordinator(hass, entry.entry_id)
            options = coordinator.options if coordinator else entry.options
            displays.append(
                {
                    "display_id": entry.entry_id,
                    "name": _display_name(hass, entry),
                    "online": bool(coordinator and coordinator.last_update_success),
                    "assigned_views": options.get("assigned_views", []),
                    "current_view_id": coordinator.current_view_id if coordinator else None,
                }
            )
        return {"views": views, "displays": displays}


class FindEntitiesTool(_ReadOnlyTool):
    """Entities a widget can show.

    Every entity, like the panel's picker, not only those exposed to
    Assist: these tools are for admins configuring displays, as Home
    Assistant's own admin API is not bounded by exposure either.
    """

    name = "geekmagic__find_entities"
    description = (
        "Find Home Assistant entities to put in widgets, by words in their id or name, "
        "by domain, or by the widget type that will show them."
    )
    parameters = vol.Schema(
        {
            vol.Optional("query", description="Words to match in the entity id or name"): str,
            vol.Optional("domain", description='Entity domain, e.g. "sensor"'): str,
            vol.Optional("widget_type", description="Only entities this widget type accepts"): str,
            vol.Optional("limit", description="Maximum results (default 30)"): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=200)
            ),
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        domains: list[str] | None = None
        if widget_type := args.get("widget_type"):
            domains = WIDGET_TYPE_SCHEMAS.get(widget_type, {}).get("entity_domains")
        if domain := args.get("domain"):
            domains = [domain]
        words = str(args.get("query", "")).lower().split()
        limit = args.get("limit", 30)

        # Whole-word hits first: "temp" should rank temperature sensors
        # above an "attempted" backup sensor.
        ranked: list[tuple[int, str, dict[str, Any]]] = []
        for state in hass.states.async_all(domains):
            name = str(state.attributes.get("friendly_name", ""))
            haystack = f"{state.entity_id} {name}".lower()
            if any(word not in haystack for word in words):
                continue
            word_starts = re.findall(r"[a-z0-9]+", haystack)
            misses = sum(not any(token.startswith(word) for token in word_starts) for word in words)
            entity = {
                "entity_id": state.entity_id,
                "name": name,
                "state": state.state,
                "unit": state.attributes.get("unit_of_measurement"),
                "device_class": state.attributes.get("device_class"),
            }
            ranked.append((misses, state.entity_id, entity))
        ranked.sort(key=lambda r: r[:2])
        return {"entities": [r[2] for r in ranked[:limit]], "total": len(ranked)}


class CreateViewTool(GeekMagicTool):
    """Create an empty view."""

    name = "geekmagic__create_view"
    description = (
        "Create a GeekMagic view with a layout and theme. It starts empty: fill its "
        "slots with geekmagic__set_widget, then assign it to a display."
    )
    parameters = vol.Schema(
        {
            vol.Required("name", description="View name"): str,
            vol.Optional("layout", description="Layout id (default grid_2x2)"): str,
            vol.Optional("theme", description="Theme id (default watchos)"): str,
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        layout = args.get("layout", LAYOUT_GRID_2X2)
        theme = args.get("theme", THEME_WATCHOS)
        _check_layout_theme(layout, theme)
        store = _store(hass)
        view_id = await store.async_create_view(name=args["name"], layout=layout, theme=theme)
        view = store.get_view(view_id)
        assert view is not None
        return describe_view(hass, view)


class DuplicateViewTool(GeekMagicTool):
    """Copy a view, to rework it without touching the original."""

    name = "geekmagic__duplicate_view"
    description = (
        "Copy a GeekMagic view (layout, theme and widgets). Edit the copy to rework a "
        "view without changing what displays show, then assign the copy when it is done."
    )
    parameters = vol.Schema(
        {
            vol.Required("view", description="View id or name to copy"): str,
            vol.Optional("name", description='Name of the copy (default "<name> (Copy)")'): str,
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        source = _find_view(hass, args["view"])
        store = _store(hass)
        view_id = await store.async_duplicate_view(source["id"], args.get("name"))
        view = store.get_view(view_id) if view_id else None
        assert view is not None
        return describe_view(hass, view)


class UpdateViewTool(GeekMagicTool):
    """Rename a view, or change its layout or theme."""

    name = "geekmagic__update_view"
    description = (
        "Rename a GeekMagic view or change its layout or theme. Widgets keep their slot "
        "numbers; those beyond the new layout's slots are kept but hidden."
    )
    parameters = vol.Schema(
        {
            vol.Required("view", description="View id or name"): str,
            vol.Optional("name", description="New name"): str,
            vol.Optional("layout", description="New layout id"): str,
            vol.Optional("theme", description="New theme id"): str,
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        view = _find_view(hass, args["view"])
        _check_layout_theme(args.get("layout"), args.get("theme"))
        updates = {k: args[k] for k in ("name", "layout", "theme") if k in args}
        await _async_save_view(hass, view["id"], **updates)
        return describe_view(hass, view)


class SetWidgetTool(GeekMagicTool):
    """Put a widget in a slot, replacing what is there."""

    name = "geekmagic__set_widget"
    description = (
        "Put a widget in a slot of a GeekMagic view, replacing whatever is there. "
        "Options are the widget type's options from geekmagic__get_catalog; leave out "
        "those you don't need (they take their default)."
    )
    parameters = vol.Schema(
        {
            vol.Required("view", description="View id or name"): str,
            vol.Required("slot", description="Slot index, from 0"): vol.Coerce(int),
            vol.Required("type", description="Widget type"): str,
            vol.Optional("entity_id", description="Entity the widget shows"): str,
            vol.Optional("label", description="Caption (default: the entity name)"): str,
            vol.Optional("color", description='Accent colour, "#rrggbb"'): str,
            vol.Optional("options", description="Widget options, by key"): dict,
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        view = _find_view(hass, args["view"])
        slot = args["slot"]
        widget = validate_widget(hass, view, slot, args)
        widgets = [w for w in view.get("widgets", []) if stored_slot(w) != slot]
        widgets.append(widget)
        widgets.sort(key=lambda w: stored_slot(w) or 0)
        await _async_save_view(hass, view["id"], widgets=widgets)
        return describe_view(hass, view)


class ClearWidgetTool(GeekMagicTool):
    """Empty a slot."""

    name = "geekmagic__clear_widget"
    description = "Remove the widget from a slot of a GeekMagic view."
    parameters = vol.Schema(
        {
            vol.Required("view", description="View id or name"): str,
            vol.Required("slot", description="Slot index, from 0"): vol.Coerce(int),
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        view = _find_view(hass, args["view"])
        widgets = [w for w in view.get("widgets", []) if stored_slot(w) != args["slot"]]
        await _async_save_view(hass, view["id"], widgets=widgets)
        return describe_view(hass, view)


class AssignViewsTool(GeekMagicTool):
    """Set the views a display cycles through."""

    name = "geekmagic__assign_views"
    description = (
        "Set the views a GeekMagic display cycles through, in order. This replaces the "
        "display's list: include the views it already has to keep them."
    )
    parameters = vol.Schema(
        {
            vol.Required("display", description="Display id or name"): str,
            vol.Required("views", description="View ids or names, in order"): [str],
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        entry = _find_display(hass, args["display"])
        view_ids = [_find_view(hass, ref)["id"] for ref in args["views"]]
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "assigned_views": view_ids}
        )
        return {"display_id": entry.entry_id, "assigned_views": view_ids}


class ShowViewTool(GeekMagicTool):
    """Switch a display to one of its views now."""

    name = "geekmagic__show_view"
    description = "Switch a GeekMagic display to one of its assigned views now."
    parameters = vol.Schema(
        {
            vol.Required("display", description="Display id or name"): str,
            vol.Required("view", description="View id or name"): str,
        }
    )

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        entry = _find_display(hass, args["display"])
        view = _find_view(hass, args["view"])
        coordinator = _get_coordinator(hass, entry.entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"{entry.title} isn't connected ({entry.state.value})")
        try:
            await coordinator.async_show_view(view["id"])
        except ValueError as err:
            raise HomeAssistantError(
                f"{err}. Assign it first with geekmagic__assign_views"
            ) from err
        return {"display_id": entry.entry_id, "current_view_id": coordinator.current_view_id}


class RenderViewTool(GeekMagicTool):
    """Render a view: a link to the image, and a report of each slot."""

    name = "geekmagic__render_view"
    description = (
        "Render a GeekMagic view exactly as a display would show it. Returns each slot's "
        "pixel size, its widget and its problems (missing or unavailable entities, "
        "invalid options, empty slots), and image_url: a link to the 240x240 PNG, "
        "valid for 10 minutes, for clients that can fetch URLs."
    )
    parameters = vol.Schema({vol.Required("view", description="View id or name"): str})

    def _annotations(self) -> Any:
        return _annotations(read_only=True, destructive=False, idempotent=True, open_world=False)

    async def _async_run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        view = _find_view(hass, args["view"])
        description = describe_view(hass, view)
        try:
            png, _layout = await async_render_view_png(hass, view)
        except Exception as err:
            _LOGGER.exception("Error rendering view %s for an LLM", view["id"])
            description["render_error"] = str(err)
            return description
        if (url := _async_publish_render(hass, png)) is not None:
            description["image_url"] = url
        return description


_TOOLS: list[type[GeekMagicTool]] = [
    GetCatalogTool,
    GetViewsTool,
    FindEntitiesTool,
    CreateViewTool,
    DuplicateViewTool,
    UpdateViewTool,
    SetWidgetTool,
    ClearWidgetTool,
    AssignViewsTool,
    ShowViewTool,
    RenderViewTool,
]


# =============================================================================
# Rendered images, served for a few minutes behind a signed URL
# =============================================================================


@callback
def _async_publish_render(hass: HomeAssistant, png: bytes) -> str | None:
    """Keep ``png`` for ``RENDER_TTL`` and return a signed URL to it.

    The URL is signed for the caller's own token (the MCP client's, or
    the frontend's for Assist), so it works without an auth header, for
    ten minutes. None when the view isn't served (no HTTP at setup).
    """
    if not hass.data.get(DATA_RENDER_VIEW):
        return None
    from homeassistant.components.http.auth import async_sign_path  # noqa: PLC0415

    renders = hass.data.setdefault(DATA_RENDERS, {})
    now = time.monotonic()
    for token in [t for t, (expires, _) in renders.items() if expires < now]:
        del renders[token]
    while len(renders) >= MAX_RENDERS:
        del renders[next(iter(renders))]
    token = secrets.token_urlsafe(16)
    renders[token] = (now + RENDER_TTL.total_seconds(), png)

    path = async_sign_path(hass, RENDER_URL.format(token=token), RENDER_TTL)
    return f"{_base_url(hass)}{path}"


def _base_url(hass: HomeAssistant) -> str:
    """The origin the caller used (MCP), else Home Assistant's configured URL."""
    from homeassistant.helpers.http import current_request  # noqa: PLC0415
    from homeassistant.helpers.network import NoURLAvailableError, get_url  # noqa: PLC0415

    if (request := current_request.get()) is not None:
        return str(request.url.origin())
    try:
        return get_url(hass)
    except NoURLAvailableError:
        return ""


class RenderImageView(HomeAssistantView):
    """Serves a render to whoever holds its signed URL."""

    url = "/api/geekmagic/render/{token}.png"
    name = "api:geekmagic:render"
    requires_auth = True

    async def get(self, request: web.Request, token: str) -> web.Response:
        """The PNG, or 404 once it expired."""
        hass = request.app[KEY_HASS]
        render = hass.data.get(DATA_RENDERS, {}).get(token)
        if render is None or render[0] < time.monotonic():
            return web.Response(status=404)
        return web.Response(
            body=render[1], content_type="image/png", headers={"Cache-Control": "no-store"}
        )
