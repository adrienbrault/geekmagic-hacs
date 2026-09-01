"""Sandboxed Jinja templating shared by widget-authored strings.

The HTML widget introduced widget-level Jinja rendering; widget labels
reuse the exact same machinery so a template behaves identically
wherever it appears. Rendering is pure — everything comes from the
injected ``WidgetState`` snapshot, never from ``hass`` — so it works
unchanged in the coordinator's executor render, the panel preview, and
tests.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from jinja2.sandbox import SandboxedEnvironment

if TYPE_CHECKING:
    from .state import WidgetState

# Entity references inside a Jinja template, e.g. states('sensor.temp'),
# state_attr("climate.living", "current_temperature") or
# is_state('light.kitchen', 'on'). Used to declare entity dependencies so
# the coordinator pre-fetches them into WidgetState.
_ENTITY_REF_RE = re.compile(r"""\b(?:states|state_attr|is_state)\(\s*['"]([^'"]+)['"]""")

_TEMPLATE_MARKERS = ("{{", "{%")


def is_template(text: str | None) -> bool:
    """Whether ``text`` contains Jinja template syntax worth rendering."""
    return bool(text) and any(marker in text for marker in _TEMPLATE_MARKERS)


def template_entity_refs(text: str | None) -> list[str]:
    """Entity IDs referenced via ``states()``/``state_attr()``/``is_state()``."""
    if not text:
        return []
    refs: list[str] = []
    for entity_id in _ENTITY_REF_RE.findall(text):
        if entity_id not in refs:
            refs.append(entity_id)
    return refs


class _CallableNow(datetime):
    """A datetime that can also be *called*.

    Home Assistant templates write ``now()`` (a function) while the HTML
    widget documented ``now`` (a variable). Supporting both means a
    template pasted from an HA automation works unchanged.
    """

    __slots__ = ()

    def __call__(self) -> _CallableNow:
        return self

    @classmethod
    def from_datetime(cls, dt: datetime) -> _CallableNow:
        return cls(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
            dt.tzinfo,
            fold=dt.fold,
        )


def _build_template_context(
    state: WidgetState, primary_entity_id: str | None = None
) -> dict[str, Any]:
    """Build the Jinja context exposed to widget-authored templates.

    The convenience variables (``state``/``name``/``unit``/...) come from
    ``primary_entity_id`` when given (the widget's "Entity (template
    data)" selector, delivered by the coordinator in
    ``WidgetState.entities``), falling back to ``state.entity``.
    """

    def states(entity_id: str) -> str:
        entity = state.get_entity(entity_id)
        return entity.state if entity else "unknown"

    def state_attr(entity_id: str, attribute: str) -> Any:
        entity = state.get_entity(entity_id)
        return entity.get(attribute) if entity else None

    def is_state(entity_id: str, value: str) -> bool:
        return states(entity_id) == value

    entity = state.get_entity(primary_entity_id) if primary_entity_id else None
    if entity is None:
        entity = state.entity
    return {
        "entity": entity,
        "state": entity.state if entity else "",
        "name": entity.friendly_name if entity else "",
        "unit": entity.unit if entity else "",
        "attributes": entity.attributes if entity else {},
        "now": _CallableNow.from_datetime(state.now) if state.now else None,
        "states": states,
        "state_attr": state_attr,
        "is_state": is_state,
    }


def _render_template(source: str, state: WidgetState, primary_entity_id: str | None = None) -> str:
    """Render a widget-authored Jinja template against widget state.

    Uses a sandboxed environment: templates come from the user's own HA
    config, but sandboxing is cheap insurance against accidental access
    to Python internals.
    """
    env = SandboxedEnvironment(autoescape=False)
    return env.from_string(source).render(**_build_template_context(state, primary_entity_id))
