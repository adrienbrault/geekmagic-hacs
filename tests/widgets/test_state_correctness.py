"""Regression tests for widgets that painted misleading states.

Each section pins one finding from the correctness review: a value the
widget rendered as if it were a real reading when it was not (negative,
unavailable, NaN), or a state rendered with the wrong meaning.
"""

from __future__ import annotations

import re
from typing import Any

from custom_components.geekmagic.htmldoc import CellContext, css_rgb
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets._cellkit import hairline_css, tint_css
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.helpers import calculate_percent
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget, StatusWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME, get_theme

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


def _entity(entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> EntityState:
    return EntityState(entity_id=entity_id, state=state, attributes=attributes or {})


def _fill_widths(fragment: str) -> list[float]:
    """Every bar fill width (``width: N%``) the fragment paints."""
    return [float(w) for w in re.findall(r"width: (-?[\d.]+)%", fragment)]


# ---------------------------------------------------------------------------
# Progress: a negative reading must not paint a full bar
# ---------------------------------------------------------------------------


def test_progress_negative_value_paints_empty_bar() -> None:
    widget = ProgressWidget(
        WidgetConfig(widget_type="progress", slot=0, entity_id="sensor.x", options={"target": 100})
    )
    fragment = widget.render_html(CTX, WidgetState(entity=_entity("sensor.x", "-20")))
    # ``width: -20%`` is invalid CSS and Blitz falls back to a full-width fill.
    assert all(w >= 0 for w in _fill_widths(fragment))
    assert "width: 0.0%" in fragment


def test_multi_progress_negative_value_paints_empty_bar() -> None:
    widget = MultiProgressWidget(
        WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={"items": [{"entity_id": "sensor.x", "target": 100, "label": "X"}]},
        )
    )
    state = WidgetState(entities={"sensor.x": _entity("sensor.x", "-20")})
    fragment = widget.render_html(CTX, state)
    assert all(w >= 0 for w in _fill_widths(fragment))
    assert "width: 0.0%" in fragment


# ---------------------------------------------------------------------------
# Gauge / progress: unavailable, unknown and NaN are not readings
# ---------------------------------------------------------------------------

_NOT_READINGS = ("unavailable", "unknown", "nan", "inf", "garbage")


def test_numeric_or_none_rejects_non_readings() -> None:
    for raw in _NOT_READINGS:
        assert _entity("sensor.x", raw).numeric_or_none() is None, raw
    assert _entity("sensor.x", "42.5").numeric_or_none() == 42.5
    assert _entity("sensor.x", "1", {"level": float("nan")}).numeric_or_none("level") is None


def test_calculate_percent_nan_is_empty_not_full() -> None:
    assert calculate_percent(float("nan"), 0, 100) == 0.0
    assert calculate_percent(float("inf"), 0, 100) == 0.0


def test_progress_unavailable_renders_dimmed_placeholder() -> None:
    widget = ProgressWidget(
        WidgetConfig(widget_type="progress", slot=0, entity_id="sensor.x", options={"target": 100})
    )
    for raw in _NOT_READINGS:
        state = WidgetState(entity=_entity("sensor.x", raw, {"friendly_name": "Battery"}))
        fragment = widget.render_html(CTX, state)
        assert ">--<" in fragment, raw
        assert ">nan<" not in fragment.lower(), raw
        assert ">0<" not in fragment, raw
        assert "var(--text-tertiary)" in fragment, raw
        # Empty fill: never a full (100%) bar for a NaN.
        assert "width: 0.0%" in fragment, raw
        assert "width: 100.0%" not in fragment, raw
        assert widget.hero_hint(CTX, state) is None, raw


def test_multi_progress_unavailable_row_is_placeholder() -> None:
    widget = MultiProgressWidget(
        WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={"items": [{"entity_id": "sensor.x", "target": 100, "label": "X"}]},
        )
    )
    for raw in ("unavailable", "nan"):
        fragment = widget.render_html(
            CTX, WidgetState(entities={"sensor.x": _entity("sensor.x", raw)})
        )
        assert ">--<" in fragment, raw
        assert "0%<" not in fragment, raw
        assert "width: 0.0%" in fragment, raw
        assert "width: 100.0%" not in fragment, raw


def test_gauge_unavailable_renders_dimmed_placeholder() -> None:
    muted = css_rgb(DEFAULT_THEME.muted)
    for style in ("bar", "ring", "arc"):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.x",
                options={"style": style, "unit": "%"},
            )
        )
        for raw in _NOT_READINGS:
            state = WidgetState(entity=_entity("sensor.x", raw, {"friendly_name": "Battery"}))
            fragment = widget.render_html(CTX, state)
            assert ">--<" in fragment, (style, raw)
            assert ">0<" not in fragment, (style, raw)
            assert ">nan<" not in fragment.lower(), (style, raw)
            # The value (and the SVG stroke) take the concrete muted tone.
            assert muted in fragment, (style, raw)
            assert widget.hero_hint(CTX, state) is None, (style, raw)


# ---------------------------------------------------------------------------
# tint_css: translucent fills are emitted as rgba, not pre-flattened
# ---------------------------------------------------------------------------


def test_tint_css_emits_rgba() -> None:
    assert tint_css((255, 159, 10), 0.22) == "rgba(255, 159, 10, 0.22)"
    assert hairline_css(DEFAULT_THEME).startswith("rgba(")


def test_translucent_tint_composites_at_stated_strength() -> None:
    """16% white over the watchOS black lands at 41 — no double alpha.

    The old flattening compensated for a premultiplied double-alpha bug
    in a compositing path that no longer exists; on standby's translucent
    card it painted a darker hole (41) instead of a tint over the card.
    """
    fill = tint_css((255, 255, 255), 0.16)
    html = f'<div style="position:absolute; inset:0; background: {fill}"></div>'
    for theme_name, expected in (("watchos", 41), ("standby", 57)):
        renderer = Renderer()
        img, draw = renderer.create_canvas()
        layout = FullscreenLayout()
        layout.theme = get_theme(theme_name)
        layout.set_widget(
            0, HtmlWidget(WidgetConfig(widget_type="html", slot=0, options={"html": html}))
        )
        layout.render(renderer, draw, {0: WidgetState()})
        pixel = img.convert("RGB").getpixel((img.width // 2, img.height // 2))
        assert isinstance(pixel, tuple)
        assert abs(pixel[0] - expected) <= 3, (theme_name, pixel)


# ---------------------------------------------------------------------------
# Status: locked and unlocked are not both a green "ON"
# ---------------------------------------------------------------------------


def _hero_text(fragment: str) -> str:
    match = re.search(r'class="t-hero" style="color: ([^;]+);[^"]*">([^<]*)<', fragment)
    assert match is not None, fragment
    return f"{match.group(2)}|{match.group(1)}"


def test_status_lock_locked_is_secure_and_unlocked_needs_attention() -> None:
    widget = StatusWidget(WidgetConfig(widget_type="status", slot=0, entity_id="lock.front"))
    locked = widget.render_html(CTX, WidgetState(entity=_entity("lock.front", "locked")))
    unlocked = widget.render_html(CTX, WidgetState(entity=_entity("lock.front", "unlocked")))
    assert _hero_text(locked) == "Locked|var(--muted)"
    assert _hero_text(unlocked) == "Unlocked|var(--warning)"
    assert "var(--success)" not in unlocked


def test_status_lock_class_binary_sensor_names_its_state() -> None:
    widget = StatusWidget(
        WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.lock")
    )
    attrs = {"device_class": "lock"}
    on = widget.render_html(CTX, WidgetState(entity=_entity("binary_sensor.lock", "on", attrs)))
    off = widget.render_html(CTX, WidgetState(entity=_entity("binary_sensor.lock", "off", attrs)))
    assert _hero_text(on) == "Unlocked|var(--warning)"
    assert _hero_text(off) == "Locked|var(--muted)"


def test_status_lock_respects_configured_text_and_colour() -> None:
    widget = StatusWidget(
        WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="lock.front",
            options={"on_text": "OPEN!", "on_color": [255, 0, 0]},
        )
    )
    fragment = widget.render_html(CTX, WidgetState(entity=_entity("lock.front", "unlocked")))
    assert _hero_text(fragment) == "OPEN!|rgb(255, 0, 0)"


def test_status_non_lock_entities_keep_on_off() -> None:
    widget = StatusWidget(WidgetConfig(widget_type="status", slot=0, entity_id="switch.fan"))
    fragment = widget.render_html(CTX, WidgetState(entity=_entity("switch.fan", "on")))
    assert _hero_text(fragment) == "ON|var(--success)"


def test_status_list_lock_rows() -> None:
    widget = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={"entities": ["lock.front", "lock.back"]},
        )
    )
    state = WidgetState(
        entities={
            "lock.front": _entity("lock.front", "locked", {"friendly_name": "Front"}),
            "lock.back": _entity("lock.back", "unlocked", {"friendly_name": "Back"}),
        }
    )
    fragment = widget.render_html(CTX, state)
    assert re.search(r"color: var\(--muted\)\">Locked<", fragment)
    assert re.search(r"color: var\(--warning\)\">Unlocked<", fragment)
    assert ">On<" not in fragment


# ---------------------------------------------------------------------------
# Status: an unavailable sensor is not a genuine "OFF"
# ---------------------------------------------------------------------------


def test_status_unavailable_is_not_off() -> None:
    widget = StatusWidget(
        WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door")
    )
    attrs = {"device_class": "door", "friendly_name": "Door"}
    for raw in ("unavailable", "unknown"):
        fragment = widget.render_html(
            CTX, WidgetState(entity=_entity("binary_sensor.door", raw, attrs))
        )
        assert _hero_text(fragment) == "--|var(--text-tertiary)", raw
        assert ">OFF<" not in fragment, raw
        assert "door-closed" not in fragment, raw
        # The chip carries the alert glyph (MDI alert-circle-outline).
        assert "&#xF05D6;" in fragment, raw


def test_status_list_unavailable_row_is_not_off() -> None:
    widget = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={"entities": ["binary_sensor.door", "binary_sensor.window"]},
        )
    )
    attrs = {"device_class": "door"}
    state = WidgetState(
        entities={
            "binary_sensor.door": _entity("binary_sensor.door", "unavailable", attrs),
            "binary_sensor.window": _entity("binary_sensor.window", "off", attrs),
        }
    )
    fragment = widget.render_html(CTX, state)
    assert re.search(r"color: var\(--text-tertiary\)\">--<", fragment)
    # The genuinely closed window still reads as closed.
    assert re.search(r"color: var\(--muted\)\">Closed<", fragment)
    assert fragment.count(">Closed<") == 1
