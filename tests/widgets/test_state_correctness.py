"""Regression tests for widgets that painted misleading states.

Each section pins one finding from the correctness review: a value the
widget rendered as if it were a real reading when it was not (negative,
unavailable, NaN), or a state rendered with the wrong meaning.
"""

from __future__ import annotations

import re
from typing import Any

from custom_components.geekmagic.htmldoc import CellContext, css_rgb
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.helpers import calculate_percent
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

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
