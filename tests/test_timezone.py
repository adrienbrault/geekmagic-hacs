"""Timezone handling through the real device and preview state builders."""

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.websocket import _build_preview_widget_states
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME


@pytest.fixture(params=["device", "preview"])
def build_widget_state(hass, request):
    """Exercise each rendering path with the same widget and HA configuration."""

    def build(widget):
        if request.param == "preview":
            return _build_preview_widget_states(hass, {0: widget}, {}, {}, {})[0]
        layout = FullscreenLayout()
        layout.set_widget(0, widget)
        coordinator = GeekMagicCoordinator(hass, MagicMock(), {})
        return coordinator._build_widget_states(layout)[0]

    return build


@pytest.mark.parametrize(
    ("timezone", "instant", "timestamp", "expected"),
    [
        (
            "Asia/Jerusalem",
            "2026-01-15T22:30:00Z",
            "2026-01-16T23:30:00Z",
            "2026-01-16|2026-01-17 01:30",
        ),
        (
            "Asia/Jerusalem",
            "2026-07-15T21:30:00Z",
            "2026-07-16T22:30:00Z",
            "2026-07-16|2026-07-17 01:30",
        ),
        (
            "Asia/Jerusalem",
            "2026-03-26T12:00:00Z",
            "2026-03-27T15:00:00Z",
            "2026-03-26|2026-03-27 18:00",
        ),
        (
            "Asia/Jerusalem",
            "2026-10-24T12:00:00Z",
            "2026-10-25T15:00:00Z",
            "2026-10-24|2026-10-25 17:00",
        ),
        (
            "America/New_York",
            "2026-07-15T02:00:00Z",
            "2026-07-16T15:00:00Z",
            "2026-07-14|2026-07-16 11:00",
        ),
        (
            "UTC",
            "2026-07-15T02:00:00Z",
            "2026-07-16T15:00:00Z",
            "2026-07-15|2026-07-16 15:00",
        ),
    ],
)
async def test_html_uses_ha_timezone(
    hass, freezer, build_widget_state, timezone, instant, timestamp, expected
):
    """Templates get local dates and event-specific DST rules, not a fixed offset."""
    await hass.config.async_set_time_zone(timezone)
    freezer.move_to(instant)
    hass.states.async_set("sensor.candle_lighting", timestamp)
    widget = HtmlWidget(
        WidgetConfig(
            widget_type="html",
            slot=0,
            options={
                "html": "{{ now.strftime('%Y-%m-%d') }}|"
                "{{ now.fromisoformat(states('sensor.candle_lighting'))"
                ".astimezone(now.tzinfo).strftime('%Y-%m-%d %H:%M') }}"
            },
        )
    )
    state = build_widget_state(widget)
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    assert str(state.now.tzinfo) == timezone
    assert widget.render_html(ctx, state) == expected


@pytest.mark.parametrize(
    ("options", "expected_timezone", "expected_time"),
    [
        ({}, "Asia/Jerusalem", "15:00"),
        ({"timezone": ""}, "Asia/Jerusalem", "15:00"),
        ({"timezone": "Invalid/Timezone"}, "Asia/Jerusalem", "15:00"),
        ({"timezone": "America/New_York"}, "America/New_York", "08:00"),
    ],
)
async def test_clock_timezone(
    hass, freezer, build_widget_state, options, expected_timezone, expected_time
):
    """Clocks use HA's timezone unless a valid explicit override is configured."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    freezer.move_to("2026-07-15T12:00:00Z")
    widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, options=options))
    state = build_widget_state(widget)
    assert str(state.now.tzinfo) == expected_timezone
    assert state.now.strftime("%H:%M") == expected_time
