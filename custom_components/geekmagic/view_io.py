"""Views and entity data as files: check, remap, and render without Home Assistant.

The offline view renderer (``skills/geekmagic-views/scripts/render_view.py``)
and the panel's import/export speak these formats:

- a **view**: the JSON the panel stores (``layout``, ``theme``, ``widgets``
  with ``type``, ``slot``, ``entity_id``, ``label``, ``color``, ``options``).
  ``validate_view`` is strict where ``view.build_layout`` is forgiving: an
  unknown layout, theme or widget type, or a slot outside the layout, is an
  error rather than a silent fallback.
- a **states file** (``STATES_VERSION``)::

      {"version": 1,
       "now": "2026-11-16T08:30:00+01:00",              (optional)
       "timezone": "Europe/Paris",                      (optional)
       "entities": {"sensor.x": {
           "state": "21.5", "attributes": {...},
           "history": [20.1, 20.4, ...]                 (any window)
                    | {"24": [...], "6": [...]},        (by hours)
           "candles": [[open, high, low, close], ...]   (any candlestick)
                    | {"3600x24": [...]},               (by interval x count)
           "forecast": [{"datetime": "+1", ...}, ...],  ("+N": N days on)
           "picture": "cover.jpg"}},                    (demo data only)
       "templates": {"<slot>": {"<source>": "<rendered>"}},
       "images": {"<image widget source>": "file.png"}}

  Paths are relative to the states file. ``templates`` holds what Home
  Assistant rendered for each widget's label/text templates (they render
  per widget: ``{{ name }}`` differs between two cells). ``timezone`` (an
  IANA name) is Home Assistant's: ``now`` alone only carries a UTC
  offset, which is wrong across a DST change (forecast day names, a
  clock's date).
- an **export** (``export_states``, the panel's "Copy for AI"): a states
  file of the entities a view reads, as Home Assistant has them, with the
  view itself under ``view`` and the integration version that wrote it
  under ``integration_version``. Never pictures; never tokens, pictures'
  URLs or locations (``is_private_attribute``).

``render_view`` paints a view from a states file through the device's own
code (``view.build_layout``, ``view.assemble_widget_states``,
``view.render_still``), so the PNG is the frame the device would show.

HA-free, like ``view.py``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .const import LAYOUT_NAMES
from .image_decode import decode_image
from .renderer import Renderer
from .view import (
    LAYOUT_CLASSES,
    PictureKind,
    assemble_widget_states,
    build_layout,
    forecast_entities,
    history_series,
    layout_widgets,
    picture_entities,
    render_still,
)
from .widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS, build_widget
from .widgets.base import BrokenWidget
from .widgets.candlestick import CandlestickWidget
from .widgets.image import ImageWidget
from .widgets.state import EntityState
from .widgets.theme import THEMES

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import tzinfo
    from pathlib import Path

    from PIL import Image

    from .layouts.base import Layout
    from .widgets.base import Widget

_LOGGER = logging.getLogger(__name__)

STATES_VERSION = 1

# Keys the panel stores on a view and on a widget
_VIEW_KEYS = {"id", "name", "layout", "theme", "widgets", "created_at", "updated_at"}
_WIDGET_KEYS = {"type", "slot", "entity_id", "label", "color", "options"}


class ViewFileError(ValueError):
    """A view or states file that can't be used."""


# =============================================================================
# Checking a view
# =============================================================================


@dataclass
class ViewCheck:
    """What ``validate_view`` found: errors stop a render, warnings don't."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """No errors."""
        return not self.errors


def validate_view(view: Any) -> ViewCheck:
    """Check a view the way an import should: unknown names are errors.

    Errors: not an object, a missing or unknown layout, an unknown theme, a
    widget that isn't an object, of an unknown type, in a slot the layout
    doesn't have (or one already taken), with a malformed color, or that
    can't be built from its config. Warnings: keys the panel doesn't store,
    unknown options, select values outside their choices, a widget that
    needs an entity and has none.
    """
    check = ViewCheck()
    if not isinstance(view, dict):
        check.errors.append("a view is a JSON object")
        return check

    check.warnings.extend(f"unknown view key {key!r}" for key in sorted(set(view) - _VIEW_KEYS))
    layout_id = view.get("layout")
    layout_class = LAYOUT_CLASSES.get(layout_id) if isinstance(layout_id, str) else None
    if layout_class is None:
        check.errors.append(
            f"unknown layout {layout_id!r} (one of: {', '.join(sorted(LAYOUT_CLASSES))})"
        )
    theme = view.get("theme")
    if theme is None:
        check.warnings.append("no theme: devices show it in their default theme")
    elif not isinstance(theme, str) or theme not in THEMES:
        check.errors.append(f"unknown theme {theme!r} (one of: {', '.join(sorted(THEMES))})")

    widgets = view.get("widgets", [])
    if not isinstance(widgets, list):
        check.errors.append("widgets is a list")
        return check
    slot_count = layout_class().get_slot_count() if layout_class is not None else None
    taken: set[int] = set()
    for position, config in enumerate(widgets):
        _check_widget(check, position, config, slot_count, taken)
    return check


def _check_widget(
    check: ViewCheck, position: int, config: Any, slot_count: int | None, taken: set[int]
) -> None:
    where = f"widget #{position}"
    if not isinstance(config, dict):
        check.errors.append(f"{where}: a widget is a JSON object")
        return
    widget_type = config.get("type")
    where = f"widget #{position} ({widget_type})"
    if not isinstance(widget_type, str) or widget_type not in WIDGET_CLASSES:
        check.errors.append(
            f"{where}: unknown widget type (one of: {', '.join(sorted(WIDGET_CLASSES))})"
        )
        return
    check.warnings.extend(
        f"{where}: unknown key {key!r}" for key in sorted(set(config) - _WIDGET_KEYS)
    )

    slot = config.get("slot", 0)
    if not isinstance(slot, int) or isinstance(slot, bool):
        check.errors.append(f"{where}: slot {slot!r} is not an integer")
        return
    if slot_count is not None and not 0 <= slot < slot_count:
        check.errors.append(f"{where}: slot {slot} is outside the layout (0-{slot_count - 1})")
    elif slot in taken:
        check.errors.append(f"{where}: slot {slot} already has a widget")
    else:
        taken.add(slot)

    color = config.get("color")
    if color is not None and not (
        isinstance(color, list) and len(color) == 3 and all(isinstance(c, int) for c in color)
    ):
        check.errors.append(f"{where}: color is [r, g, b], got {color!r}")
        return

    options = config.get("options", {})
    if not isinstance(options, dict):
        check.errors.append(f"{where}: options is a JSON object")
        return
    # Widgets the panel doesn't offer (YAML-era types) have no schema to check
    schema = WIDGET_TYPE_SCHEMAS.get(widget_type)
    known = {option["key"]: option for option in (schema or {}).get("options", [])}
    for key, value in options.items() if schema else ():
        option = known.get(key)
        if option is None:
            check.warnings.append(f"{where}: unknown option {key!r}")
        elif option.get("type") == "select" and value not in option.get("options", []):
            check.warnings.append(
                f"{where}: option {key!r} is {value!r}, not one of {option.get('options')}"
            )
    if schema and schema.get("needs_entity") and not config.get("entity_id"):
        check.warnings.append(f"{where}: needs an entity_id")

    if isinstance(build_widget(config), BrokenWidget):
        check.errors.append(f"{where}: can't be built from this config")


# =============================================================================
# The entities a view reads
# =============================================================================

# Entity ids a Home Assistant template reads by name: states('sensor.x'),
# state_attr("sensor.x", ...), is_state(...), and states.sensor.x
_TEMPLATE_ENTITY_RE = re.compile(
    r"""\b(?:states|state_attr|is_state)\(\s*['"]([a-z0-9_]+\.[a-z0-9_]+)['"]"""
    r"""|(?<![\w.])states\.([a-z0-9_]+\.[a-z0-9_]+)"""
)


def view_entities(view: Any) -> list[str]:
    """Every entity id the view reads, in widget order, each once.

    A widget's entity, the entities its options name (status rows,
    progress items, HTML templates), and those its label / text templates
    read by name. Malformed widgets are skipped (``validate_view`` says
    why).
    """
    found: dict[str, None] = {}
    widgets = view.get("widgets") if isinstance(view, dict) else None
    for config in widgets if isinstance(widgets, list) else []:
        if not isinstance(config, dict) or not isinstance(config.get("type"), str):
            continue
        try:
            widget = build_widget(config)
        except (TypeError, ValueError):  # a slot or color that isn't a number
            continue
        if widget is None:
            continue
        ids = [widget.config.entity_id, *widget.get_entities()]
        for source in widget.template_sources():
            ids.extend(a or b for a, b in _TEMPLATE_ENTITY_RE.findall(source))
        found.update((e, None) for e in ids if isinstance(e, str) and e)
    return list(found)


# =============================================================================
# Remapping entity ids
# =============================================================================


def remap_entities(view: Any, mapping: Mapping[str, str]) -> Any:
    """A copy of ``view`` with entity ids replaced as ``mapping`` says.

    Every string in the view is visited, whatever option holds it: one
    equal to a mapped id is replaced, and inside longer strings (HTML and
    label templates) so is every quoted literal equal to a mapped id
    (``states('sensor.x')``, ``state_attr("sensor.x", ...)``,
    ``forecast('weather.x')``, ``{% set e = 'sensor.x' %}``...) and every
    ``states.sensor.x`` reference. Ids merely containing a mapped id are
    left alone.
    """
    mapping = {old: new for old, new in mapping.items() if old and old != new}
    if not mapping:
        return json.loads(json.dumps(view))
    ids = "|".join(re.escape(old) for old in sorted(mapping, key=len, reverse=True))
    quoted = re.compile(rf"""(['"])({ids})\1""")
    dotted = re.compile(rf"""(?<![\w.])states\.({ids})(?![\w])""")

    def text(value: str) -> str:
        if value in mapping:
            return mapping[value]
        value = quoted.sub(lambda m: m[1] + mapping[m[2]] + m[1], value)
        return dotted.sub(lambda m: "states." + mapping[m[1]], value)

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return text(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value

    return walk(view)


# =============================================================================
# States files
# =============================================================================


@dataclass
class States:
    """Entity data for offline renders: one or more states files, merged."""

    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    # slot -> {template source -> rendered}
    templates: dict[int, dict[str, str]] = field(default_factory=dict)
    # Image widget source -> picture file
    images: dict[str, Path] = field(default_factory=dict)
    now: datetime | None = None
    # Home Assistant's timezone: ``now`` (and the default instant) in it
    timezone: tzinfo | None = None

    def get(self, entity_id: str) -> EntityState | None:
        """An entity as ``hass.states.get`` would give it (or None)."""
        data = self.entities.get(entity_id)
        if data is None:
            return None
        return EntityState(
            entity_id=entity_id,
            state=str(data.get("state", "unknown")),
            attributes=dict(data.get("attributes") or {}),
        )

    def merge(self, other: States) -> States:
        """These states with ``other``'s on top (whole entities are replaced)."""
        templates = {slot: dict(sources) for slot, sources in self.templates.items()}
        for slot, sources in other.templates.items():
            templates.setdefault(slot, {}).update(sources)
        return States(
            entities={**self.entities, **other.entities},
            templates=templates,
            images={**self.images, **other.images},
            now=other.now or self.now,
            timezone=other.timezone or self.timezone,
        )

    def instant(self) -> datetime:
        """The frame's instant: ``now`` if set, else the current time; in ``timezone``."""
        instant = self.now or datetime.now().astimezone()
        return instant.astimezone(self.timezone) if self.timezone else instant


def parse_states(data: Any, base_dir: Path) -> States:
    """A states file's content; picture paths resolve against ``base_dir``."""
    if not isinstance(data, dict):
        raise ViewFileError("a states file is a JSON object")
    version = data.get("version", STATES_VERSION)
    if version != STATES_VERSION:
        raise ViewFileError(
            f"states file version {version!r}: this renderer reads version {STATES_VERSION}"
        )
    entities: dict[str, dict[str, Any]] = {}
    for entity_id, entity in (data.get("entities") or {}).items():
        if not isinstance(entity, dict):
            raise ViewFileError(f"{entity_id}: an entity is a JSON object")
        entities[entity_id] = dict(entity)
        if entity.get("picture"):
            entities[entity_id]["picture"] = base_dir / entity["picture"]
    templates = {
        int(slot): {str(source): str(out) for source, out in sources.items()}
        for slot, sources in (data.get("templates") or {}).items()
    }
    images = {source: base_dir / path for source, path in (data.get("images") or {}).items()}
    now = datetime.fromisoformat(data["now"]) if data.get("now") else None
    if now is not None and now.tzinfo is None:
        raise ViewFileError(f"now {data['now']!r} needs a UTC offset")
    timezone = None
    if data.get("timezone"):
        try:
            timezone = ZoneInfo(str(data["timezone"]))
        except (ZoneInfoNotFoundError, ValueError):
            # An unknown name, or no tz database here (Windows without the
            # tzdata package): now's UTC offset alone is right but near DST
            _LOGGER.warning("Unknown timezone %r: using now's UTC offset", data["timezone"])
    return States(entities=entities, templates=templates, images=images, now=now, timezone=timezone)


def load_states(*paths: Path) -> States:
    """States files merged in order (later ones win, per entity)."""
    states = States()
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            raise ViewFileError(f"{path}: {err}") from err
        states = states.merge(parse_states(data, path.parent))
    return states


def resolve_forecast(days: Iterable[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """A forecast with each ``"+N"`` datetime made N days after ``now``, at noon."""
    resolved = []
    for day in days:
        when = str(day.get("datetime", ""))
        if when.startswith("+"):
            date = (now + timedelta(days=int(when[1:]))).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            resolved.append({**day, "datetime": date.isoformat()})
        else:
            resolved.append(day)
    return resolved


def history_key(hours: float) -> str:
    """A history window's key in a states file, read back exactly: "24", "0.08333333333333333"."""
    return str(int(hours)) if float(hours).is_integer() else repr(float(hours))


def candles_key(interval_seconds: int, count: int) -> str:
    """A candlestick series' key in a states file: ``"3600x24"``."""
    return f"{interval_seconds}x{count}"


def _candles(candles: Any, interval_seconds: int, count: int) -> list[Any] | None:
    """The candles to serve a candlestick: a list fits any, a dict is by series."""
    if isinstance(candles, dict):
        candles = candles.get(candles_key(interval_seconds, count))
    return candles if isinstance(candles, list) and candles else None


def _series(history: Any, hours: float) -> list[float] | None:
    """The history to serve for a window: a list fits any, a dict is by hours."""
    if isinstance(history, list):
        return [float(v) for v in history]
    if isinstance(history, dict):
        for key, values in history.items():
            if float(key) == hours:
                return [float(v) for v in values]
    return None


class StatesFrameData:
    """A ``view.FrameData`` read from ``States`` for one layout."""

    def __init__(self, states: States, layout: Layout, now: datetime) -> None:
        """Take what the layout's widgets read from ``states``.

        Only what they read, as ``frame.FrameInputs`` fetches only that: a
        weather widget without its forecast strip gets no forecast.
        """
        self._states = states
        self._pictures: dict[Path, Image.Image] = {}
        self.chart_history: dict[tuple[str, float], list[float]] = {}
        # A list of candles serves every candlestick of its entity
        self.candlestick_data: dict[
            tuple[str, int, int], list[tuple[float, float, float, float]]
        ] = {}
        self.weather_forecasts: dict[str, list[dict[str, Any]]] = {}
        self.source_images: dict[str, Image.Image] = {}
        self.templates: dict[Widget, dict[str, str]] = {}
        widgets = layout_widgets(layout)
        entities = states.entities
        self._wanted: dict[str, set[str]] = {
            kind: picture_entities(widgets, kind) for kind in ("camera", "media")
        }

        for entity_id, hours in history_series(widgets):
            history = entities.get(entity_id, {}).get("history")
            if (values := _series(history, hours)) is not None:
                self.chart_history[entity_id, hours] = values
        for entity_id in forecast_entities(widgets):
            if "forecast" in entities.get(entity_id, {}):
                forecast = entities[entity_id]["forecast"]
                self.weather_forecasts[entity_id] = resolve_forecast(forecast, now)
        for slot in layout.slots:
            widget = slot.widget
            if widget is None:
                continue
            entity_id = widget.config.entity_id
            if isinstance(widget, CandlestickWidget) and entity_id:
                interval, count = widget.interval_seconds, widget.candle_count
                candles = _candles(entities.get(entity_id, {}).get("candles"), interval, count)
                if candles:
                    self.candlestick_data[entity_id, interval, count] = [
                        (float(o), float(h), float(lo), float(c)) for o, h, lo, c in candles
                    ]
            if isinstance(widget, ImageWidget) and widget.source in states.images:
                self.source_images[widget.source] = self._decode(states.images[widget.source])
            if templates := states.templates.get(slot.index):
                self.templates[widget] = templates

    def _decode(self, path: Path) -> Image.Image:
        if path not in self._pictures:
            try:
                data = path.read_bytes()
            except OSError as err:
                raise ViewFileError(f"picture {path}: {err}") from err
            self._pictures[path] = decode_image(data)
        return self._pictures[path]

    def picture(self, entity_id: str, kind: PictureKind) -> Image.Image | None:
        """The entity's ``picture`` file, decoded as the device decodes one.

        A states file has one picture per entity, served as either kind,
        to the widgets that draw it.
        """
        if entity_id not in self._wanted[kind]:
            return None
        path = self._states.entities.get(entity_id, {}).get("picture")
        return self._decode(path) if path else None


# =============================================================================
# Exporting
# =============================================================================

# What a view is, wherever it goes: never the panel's id or timestamps
PORTABLE_VIEW_KEYS = ("name", "layout", "theme", "widgets")

# Attributes an export never carries: secrets, pictures (and the URLs that
# fetch them), and where people and things are
_PRIVATE_ATTRIBUTES = frozenset(
    {
        "access_token",
        "entity_picture",
        "entity_picture_local",
        "media_image_url",
        "latitude",
        "longitude",
        "gps_accuracy",
        "altitude",
        "vertical_accuracy",
        "course",
        "gps",
        "location",
        "address",
        "full_address",
        "street",
    }
)
_PRIVATE_WORDS = ("token", "password", "secret", "api_key")


def portable_view(view: Mapping[str, Any]) -> dict[str, Any]:
    """The view without what only this panel means.

    No id or timestamps, and no widget in a slot the layout doesn't have:
    the panel keeps those after a switch to a smaller layout, but no
    device shows them and ``validate_view`` (an import) refuses them.
    """
    portable = {key: view[key] for key in PORTABLE_VIEW_KEYS if key in view}
    layout_id, widgets = view.get("layout"), portable.get("widgets")
    layout_class = LAYOUT_CLASSES.get(layout_id) if isinstance(layout_id, str) else None
    if layout_class is not None and isinstance(widgets, list):
        count = layout_class().get_slot_count()
        portable["widgets"] = [
            w
            for w in widgets
            if not (isinstance(w, dict) and isinstance(w.get("slot"), int) and w["slot"] >= count)
        ]
    return portable


def is_private_attribute(name: str) -> bool:
    """An attribute an export leaves out: a secret, a picture, a location."""
    lowered = name.lower()
    return lowered in _PRIVATE_ATTRIBUTES or any(word in lowered for word in _PRIVATE_WORDS)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, set | frozenset | tuple):
        return list(value)
    return str(value)


def _jsonable(value: Any) -> Any:
    """``value`` as plain JSON data (datetimes as ISO strings, sets as lists)."""
    return json.loads(json.dumps(value, default=_json_default))


def public_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """An entity's attributes as an export carries them."""
    return _jsonable({k: v for k, v in attributes.items() if not is_private_attribute(k)})


def export_states(
    view: Mapping[str, Any],
    *,
    states: Mapping[str, Any],
    chart_history: Mapping[tuple[str, float], list[float]],
    candlestick_data: Mapping[tuple[str, int, int], list[tuple[float, float, float, float]]],
    weather_forecasts: Mapping[str, list[dict[str, Any]]],
    templates: Mapping[int, Mapping[str, str]],
    now: datetime,
    timezone: str | None,
    integration_version: str,
) -> dict[str, Any]:
    """A view and what it reads, as a states file (``parse_states`` reads it).

    ``states`` maps each entity id to its state object (``.state`` and
    ``.attributes``); the other inputs are what ``frame.FrameInputs``
    fetched for the view, and ``templates`` its rendered label / text
    templates by slot. No pictures, and no private attributes.
    """
    entities: dict[str, dict[str, Any]] = {}
    for entity_id, state in states.items():
        entities[entity_id] = {
            "state": str(state.state),
            "attributes": public_attributes(state.attributes),
        }
    for (entity_id, hours), values in chart_history.items():
        if entity_id in entities:
            history = entities[entity_id].setdefault("history", {})
            history[history_key(hours)] = list(values)
    series: dict[str, dict[str, list[list[float]]]] = {}
    for (entity_id, interval, count), candles in candlestick_data.items():
        if entity_id in entities:
            series.setdefault(entity_id, {})[candles_key(interval, count)] = [
                list(candle) for candle in candles
            ]
    for entity_id, by_key in series.items():
        # One series: a plain list, which serves any candlestick
        entities[entity_id]["candles"] = next(iter(by_key.values())) if len(by_key) == 1 else by_key
    for entity_id, forecast in weather_forecasts.items():
        if entity_id in entities:
            entities[entity_id]["forecast"] = _jsonable(forecast)

    export: dict[str, Any] = {
        "version": STATES_VERSION,
        "integration_version": integration_version,
        "now": now.isoformat(),
    }
    if timezone:
        export["timezone"] = timezone
    export["view"] = _jsonable(portable_view(view))
    export["entities"] = entities
    export["templates"] = {
        str(slot): dict(rendered) for slot, rendered in sorted(templates.items()) if rendered
    }
    return export


# =============================================================================
# Rendering
# =============================================================================


def _hours(hours: Any) -> str:
    """A history window as "6h" (a states file's key as given if it isn't a number)."""
    try:
        return f"{float(hours):g}h"
    except (TypeError, ValueError):
        return repr(hours)


def _missing_widget_data(widget: Widget, states: States) -> list[str]:
    """The history, candles, forecast and pictures ``widget`` reads that ``states`` lacks.

    Entities ``states`` doesn't have at all are left out: they already
    warn as having no state.
    """
    entities = states.entities
    problems = []
    for entity_id, hours in sorted(history_series([widget])):
        if entity_id not in entities:
            continue
        history = entities[entity_id].get("history")
        if not _series(history, hours):
            windows = (
                ", ".join(_hours(h) for h, values in history.items() if values)
                if isinstance(history, dict)
                else ""
            )
            has = f" (has {windows})" if windows else ""
            problems.append(f"no history for {entity_id} over {_hours(hours)}{has}")
    entity_id = widget.config.entity_id
    if isinstance(widget, CandlestickWidget) and entity_id in entities:
        interval, count = widget.interval_seconds, widget.candle_count
        candles = entities[entity_id].get("candles")
        if not _candles(candles, interval, count):
            series = ""
            if isinstance(candles, dict):
                there = ", ".join(str(key) for key, series in candles.items() if series)
                has = f"; has {there}" if there else ""
                series = f" ({candles_key(interval, count)}{has})"
            problems.append(f"no candles for {entity_id}{series}")
    problems.extend(
        f"no forecast for {entity_id}"
        for entity_id in sorted(forecast_entities([widget]))
        if entity_id in entities and not entities[entity_id].get("forecast")
    )
    problems.extend(
        f"no picture for {entity_id}"
        for entity_id in sorted(
            picture_entities([widget], "camera") | picture_entities([widget], "media")
        )
        if entity_id in entities and not entities[entity_id].get("picture")
    )
    if isinstance(widget, ImageWidget) and widget.source and widget.source not in states.images:
        problems.append(f"no picture for image source {widget.source!r}")
    return problems


def missing_data(view: dict[str, Any], states: States) -> list[str]:
    """What the view reads that ``states`` lacks (renders, but not as intended).

    Entities without a state, then, per widget, the history window, candles,
    forecast or picture it draws that ``states`` lacks (the cell would say
    "No data"), and templates without rendered output.
    """
    layout = build_layout(view)
    problems = []
    seen: set[str] = set()
    for slot in layout.slots:
        widget = slot.widget
        if widget is None:
            continue
        for entity_id in [widget.config.entity_id, *widget.get_entities()]:
            if entity_id and entity_id not in states.entities and entity_id not in seen:
                seen.add(entity_id)
                problems.append(f"slot {slot.index}: no state for {entity_id}")
        problems.extend(f"slot {slot.index}: {p}" for p in _missing_widget_data(widget, states))
        rendered = states.templates.get(slot.index, {})
        problems.extend(
            f"slot {slot.index}: template {source!r} has no rendered output, shown as is"
            for source in widget.template_sources()
            if source not in rendered
        )
    return problems


def render_view(view: dict[str, Any], states: States, *, now: datetime | None = None) -> bytes:
    """The PNG the device would show for ``view`` with ``states``.

    ``now`` defaults to the states' ``now``, else the current time (in
    the states' ``timezone`` when they have one). The same bytes as the
    panel preview for the same inputs.
    """
    layout = build_layout(view)
    instant = now or states.instant()
    data = StatesFrameData(states, layout, instant)
    renderer = Renderer()
    image = render_still(
        renderer, layout, assemble_widget_states(layout, states.get, data, instant)
    )
    return renderer.to_png(image)


def zoom_png(png: bytes, zoom: int) -> bytes:
    """A render upscaled ``zoom`` times (nearest neighbour: device pixels stay sharp)."""
    if zoom <= 1:
        return png
    image = PILImage.open(BytesIO(png))
    image = image.resize((image.width * zoom, image.height * zoom), PILImage.Resampling.NEAREST)
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def contact_sheet(rows: list[list[tuple[str, bytes]]], zoom: int = 1) -> bytes:
    """Labelled renders on one PNG: rows (scenarios) of columns (themes)."""
    size, gap, label = 240 * zoom, 12, 22
    columns = max(len(row) for row in rows)
    sheet = PILImage.new(
        "RGB", (gap + columns * (size + gap), gap + len(rows) * (size + label + gap)), (64, 64, 64)
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(16)
    for r, row in enumerate(rows):
        for c, (text, png) in enumerate(row):
            x, y = gap + c * (size + gap), gap + r * (size + label + gap)
            draw.text((x, y), text, fill=(235, 235, 235), font=font)
            frame = PILImage.open(BytesIO(png)).resize((size, size), PILImage.Resampling.NEAREST)
            sheet.paste(frame, (x, y + label))
    out = BytesIO()
    sheet.save(out, format="PNG")
    return out.getvalue()


def schema() -> dict[str, Any]:
    """Every layout (slot rects in px), theme and widget type with its options."""
    layouts = {}
    for layout_id, layout_class in LAYOUT_CLASSES.items():
        layout = layout_class()
        layouts[layout_id] = {
            "name": LAYOUT_NAMES.get(layout_id, layout_id),
            "slots": [list(slot.rect) for slot in layout.slots],
        }
    return {
        "screen": {"width": 240, "height": 240},
        "layouts": layouts,
        "themes": sorted(THEMES),
        "widgets": WIDGET_TYPE_SCHEMAS,
    }
