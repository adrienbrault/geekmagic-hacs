"""Timezone handling through the real device and preview state builders."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.websocket import _build_preview_widget_states
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.datetime import DateTimeWidget
from custom_components.geekmagic.widgets.helpers import resolve_timezone
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.state import WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME


@pytest.fixture(params=["device", "preview"])
def build_widget_state(hass, request):
    """Exercise each rendering path with the same widget and HA configuration.

    Both builders run in an executor thread in production
    (``_render_display`` / ``_render``), so the tests run them there too.
    """

    async def build(widget):
        if request.param == "preview":
            return (
                await hass.async_add_executor_job(
                    _build_preview_widget_states, hass, {0: widget}, {}, {}, {}
                )
            )[0]
        layout = FullscreenLayout()
        layout.set_widget(0, widget)
        coordinator = GeekMagicCoordinator(hass, MagicMock(), {})
        return (await hass.async_add_executor_job(coordinator._build_widget_states, layout))[0]

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
    state = await build_widget_state(widget)
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    assert str(state.now.tzinfo) == timezone
    assert widget.render_html(ctx, state) == expected


@pytest.mark.parametrize(
    ("options", "expected_time"),
    [
        ({}, "15:00"),
        ({"timezone": ""}, "15:00"),
        ({"timezone": "Invalid/Timezone"}, "15:00"),
        ({"timezone": "America/New_York"}, "08:00"),
    ],
)
async def test_clock_timezone(hass, freezer, build_widget_state, options, expected_time):
    """Clocks use HA's timezone unless a valid explicit override is configured."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    freezer.move_to("2026-07-15T12:00:00Z")
    widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, options=options))
    state = await build_widget_state(widget)
    # The builder hands every widget HA's instant; the clock applies its own
    # override at render time.
    assert str(state.now.tzinfo) == "Asia/Jerusalem"
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    assert expected_time in widget.render_html(ctx, state)


async def test_clock_override_converts_shared_instant(hass, freezer, build_widget_state):
    """An overridden clock shows the frame's instant, not a later clock read."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    freezer.move_to("2026-07-15T12:59:59Z")
    widget = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            options={"timezone": "America/New_York", "show_seconds": True},
        )
    )
    state = await build_widget_state(widget)
    freezer.tick(2)  # the render happens after the frame's instant was taken
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    assert "08:59:59" in widget.render_html(ctx, state)


def test_unknown_clock_timezone_warns_once(caplog):
    """A mistyped override is reported instead of silently ignored."""
    resolve_timezone.cache_clear()
    widget = ClockWidget(
        WidgetConfig(widget_type="clock", slot=0, options={"timezone": "Europe/Pari"})
    )
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    state = WidgetState(now=datetime(2026, 7, 15, 12, 0, tzinfo=UTC))
    widget.render_html(ctx, state)
    widget.render_html(ctx, state)
    warnings = [r for r in caplog.records if "Europe/Pari" in r.getMessage()]
    assert len(warnings) == 1


@pytest.mark.parametrize(
    ("value", "options", "expected"),
    [
        # Aware timestamps convert into HA's zone, or the override.
        ("2026-07-15T18:30:00+00:00", {}, "21:30"),
        ("2026-07-15T18:30:00+00:00", {"timezone": "America/New_York"}, "14:30"),
        ("2026-07-15T18:30:00+00:00", {"timezone": "Invalid/Timezone"}, "21:30"),
        # Naive values (input_datetime) are HA-local wall time: shown as-is,
        # or localized to HA first and then converted.
        ("2026-07-15 21:30:00", {}, "21:30"),
        ("2026-07-15 21:30:00", {"timezone": "America/New_York"}, "14:30"),
    ],
)
async def test_datetime_timezone(hass, freezer, build_widget_state, value, options, expected):
    """Datetime values display in HA's timezone unless overridden."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    freezer.move_to("2026-07-15T12:00:00Z")
    hass.states.async_set("sensor.next_event", value)
    widget = DateTimeWidget(
        WidgetConfig(
            widget_type="datetime",
            slot=0,
            entity_id="sensor.next_event",
            options={"timestamp_format": "time", **options},
        )
    )
    state = await build_widget_state(widget)
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    assert expected in widget.render_html(ctx, state)


@pytest.mark.parametrize("value", ["2026-07-15T18:30:00+00:00", "2026-07-15 21:30:00"])
async def test_datetime_relative_ignores_override(hass, freezer, build_widget_state, value):
    """A relative time is the same in every zone, naive values included."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    freezer.move_to("2026-07-15T12:00:00Z")
    hass.states.async_set("sensor.next_event", value)
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

    async def render(options):
        widget = DateTimeWidget(
            WidgetConfig(
                widget_type="datetime",
                slot=0,
                entity_id="sensor.next_event",
                options={"timestamp_format": "relative", **options},
            )
        )
        return widget.render_html(ctx, await build_widget_state(widget))

    plain = await render({})
    assert "<div>in 6</div><div>hours</div>" in plain  # 18:30Z is 6.5h after 12:00Z
    assert await render({"timezone": "America/New_York"}) == plain
