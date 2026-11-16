"""HTML widget templates: data functions, their detection, and drawing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from markupsafe import Markup

from custom_components.geekmagic.htmldoc import CellContext, css_rgb, css_rgba
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.html import (
    HISTORY_DEFAULT_HOURS,
    HtmlWidget,
    _render_template,
)
from custom_components.geekmagic.widgets.state import WidgetState
from custom_components.geekmagic.widgets.theme import THEMES, get_theme

FORECAST = [
    {"datetime": "2026-11-16T23:00:00+00:00", "condition": "rainy", "temperature": 9},
    {"datetime": "2026-11-17T23:00:00+00:00", "condition": "partlycloudy", "temperature": 12},
]


def _widget(html: str, entity_id: str | None = None) -> HtmlWidget:
    return HtmlWidget(
        WidgetConfig(widget_type="html", slot=0, entity_id=entity_id, options={"html": html})
    )


def _ctx(theme: str = "watchos", slot: int = 0) -> CellContext:
    return CellContext(width=240, height=240, slot_index=slot, theme=get_theme(theme))


def _render(source: str, state: WidgetState | None = None, ctx: CellContext | None = None) -> str:
    return _render_template(source, state or WidgetState(), ctx=ctx or _ctx())


class TestDetection:
    """Only literal arguments are fetched ahead of the render."""

    def test_literal_calls_are_detected(self):
        widget = _widget(
            "{{ forecast('weather.home') }}{{ picture(\"camera.door\") }}"
            "{{ history('sensor.a') }}{{ history('sensor.b', 6) }}"
            "{{ history( 'sensor.c' , hours = 0.5 ) }}{{ history('sensor.d', hours=.25) }}"
        )

        assert widget.forecast_entities == ["weather.home"]
        assert widget.picture_entities == ["camera.door"]
        assert widget.history_series == [
            ("sensor.a", HISTORY_DEFAULT_HOURS),
            ("sensor.b", 6.0),
            ("sensor.c", 0.5),
            ("sensor.d", 0.25),
        ]

    def test_non_literal_calls_are_not_detected(self):
        widget = _widget(
            "{% set e = 'weather.home' %}{{ forecast(e) }}{{ picture(e) }}"
            "{{ history(e) }}{{ history('sensor.a', hours=h) }}{{ history('sensor.b', 2 * 3) }}"
        )

        assert widget.forecast_entities == []
        assert widget.picture_entities == []
        assert widget.history_series == []

    def test_out_of_range_hours_are_not_fetched(self):
        widget = _widget("{{ history('sensor.a', hours=0) }}{{ history('sensor.a', hours=48) }}")

        assert widget.history_series == []

    def test_repeats_are_fetched_once(self):
        widget = _widget(
            "{{ history('sensor.a') }}{{ history('sensor.a', hours=24) }}"
            "{{ history('sensor.a', 24.0) }}{{ picture('camera.x') }}{{ picture('camera.x') }}"
        )

        assert widget.history_series == [("sensor.a", 24.0)]
        assert widget.picture_entities == ["camera.x"]

    def test_data_entities_are_snapshotted_too(self):
        widget = _widget(
            "{{ forecast('weather.home') }}{{ history('sensor.a') }}{{ picture('camera.x') }}",
            entity_id="sensor.primary",
        )

        assert widget.get_entities() == ["sensor.primary", "weather.home", "sensor.a", "camera.x"]

    def test_non_string_template_is_empty(self):
        widget = HtmlWidget(WidgetConfig(widget_type="html", slot=0, options={"html": None}))

        assert widget.html == ""
        assert widget.forecast_entities == []


class TestDataFunctions:
    """The functions read what FrameInputs carried in WidgetState."""

    def test_forecast_entries_gain_day_icon_and_color(self):
        state = WidgetState(
            forecasts={"weather.home": FORECAST},
            now=datetime(2026, 11, 16, 12, tzinfo=ZoneInfo("Europe/Paris")),
        )

        out = _render(
            "{% for d in forecast('weather.home') %}"
            "{{ d.day }} {{ d.icon }} {{ d.color }} {{ d.temperature }};{% endfor %}",
            state,
        )

        # 23:00 UTC is the next day in Paris, as the Weather widget reads it
        assert out == (
            "Tue mdi:weather-rainy var(--info) 9;Wed mdi:weather-partly-cloudy var(--primary) 12;"
        )

    def test_forecast_day_without_a_known_condition_is_no_data_not_sunny(self):
        days = [
            {"datetime": "2026-11-17T12:00:00+00:00", "temperature": 9},
            {"datetime": "2026-11-18T12:00:00+00:00", "condition": "unavailable", "temperature": 8},
            {"datetime": "2026-11-19T12:00:00+00:00", "condition": "smoky", "temperature": 7},
        ]
        state = WidgetState(forecasts={"weather.home": days}, now=datetime.now(UTC))

        out = _render(
            "{% for d in forecast('weather.home') %}{{ d.icon }} {{ d.color }};{% endfor %}",
            state,
        )

        assert out == "mdi:cloud-question var(--muted);" * 3

    def test_forecast_never_hands_out_the_cached_entries(self):
        cached = [dict(day) for day in FORECAST]
        state = WidgetState(forecasts={"weather.home": cached}, now=datetime.now(UTC))

        _render("{% set d = forecast('weather.home') %}{% set _ = d[0].update(x=1) %}", state)

        assert cached == FORECAST

    def test_history_reads_its_own_window(self):
        state = WidgetState(
            histories={("sensor.a", 24.0): [1.0, 2.0], ("sensor.a", 6.0): [5.0, 6.0]}
        )

        assert _render("{{ history('sensor.a') }}", state) == "[1.0, 2.0]"
        assert _render("{{ history('sensor.a', 24) }}", state) == "[1.0, 2.0]"
        assert _render("{{ history('sensor.a', hours=6) }}", state) == "[5.0, 6.0]"

    def test_missing_data_is_empty(self):
        out = _render(
            "{{ forecast('weather.x') }}|{{ history('sensor.x') }}|{{ history('sensor.x', -1) }}"
            "|{{ picture('camera.x') }}|{{ 'none' if not picture('camera.x') }}"
        )

        assert out == "[]|[]|[]||none"

    def test_picture_is_the_carried_data_uri(self):
        state = WidgetState(pictures={"camera.door": "data:image/png;base64,AAAA"})

        out = _render("<img src=\"{{ picture('camera.door') }}\">", state)

        assert out == '<img src="data:image/png;base64,AAAA">'


class TestColorResolution:
    """Helpers take theme roles and resolve them to the cell theme's colours."""

    @pytest.mark.parametrize("theme_name", sorted(THEMES))
    @pytest.mark.parametrize("role", ["primary", "warning", "success", "muted", "info"])
    def test_roles_resolve_per_theme(self, theme_name, role):
        theme = get_theme(theme_name)

        out = _render(f"{{{{ color('{role}') }}}}", ctx=_ctx(theme_name))

        assert out == css_rgb(getattr(theme, role))

    def test_spellings(self):
        theme = get_theme("watchos")
        expected = css_rgb(theme.text_secondary)

        for spelling in (
            "text-secondary",
            "text_secondary",
            "var(--text-secondary)",
            "Text-Secondary",
        ):
            assert _render(f"{{{{ color('{spelling}') }}}}") == expected

    def test_accent_follows_the_slot(self):
        theme = get_theme("watchos")

        assert _render("{{ color() }}", ctx=_ctx(slot=1)) == css_rgb(theme.get_accent_color(1))
        assert _render("{{ color('accent') }}", ctx=_ctx(slot=2)) == css_rgb(
            theme.get_accent_color(2)
        )
        assert _render("{{ color('accent-0') }}", ctx=_ctx(slot=2)) == css_rgb(
            theme.accent_colors[0]
        )

    def test_literal_colours_pass_through_escaped(self):
        assert _render("{{ color('rgb(1, 2, 3)') }}") == "rgb(1, 2, 3)"
        assert _render("""{{ color('red" onload="x') }}""") == "red&quot; onload=&quot;x"

    def test_night_drops_literal_colours_for_the_accent(self):
        night = get_theme("night")

        out = _render("{{ color('rgb(0, 255, 0)') }}", ctx=_ctx("night", slot=1))

        assert out == css_rgb(night.get_accent_color(1))

    def test_night_roles_stay_in_its_ramp(self):
        night = get_theme("night")

        out = _render("{{ ring(50, 'success') }}", ctx=_ctx("night"))

        assert css_rgb(night.success) in out
        assert css_rgba(night.success, night.tint_track_opacity) in out


class TestHelpers:
    """The helpers draw the built-ins' markup with concrete colours."""

    def test_ring_matches_the_gauge(self):
        theme = get_theme("watchos")

        out = _render("{{ ring('25', 'warning', size=120) }}")

        assert "width: 120px; height: 120px" in out
        assert f'stroke="{css_rgb(theme.warning)}"' in out
        # The gauge's tinted track and stroke width, not svg_ring's defaults
        assert f'stroke="{css_rgba(theme.warning, theme.tint_track_opacity)}"' in out
        assert 'stroke-width="12.0"' in out
        assert "var(" not in out

    def test_ring_scales_value_on_min_max(self):
        full = _render("{{ ring(3, max=6) }}")
        half = _render("{{ ring(50) }}")

        assert full == half

    def test_ring_handles_unavailable(self):
        assert _render("{{ ring('unavailable') }}") == _render("{{ ring(0) }}")

    def test_missing_data_draws_empty_not_an_error(self):
        """``history() | last`` with no history is Jinja's Undefined, not a crash."""
        assert _render("{{ ring(history('sensor.x') | last) }}") == _render("{{ ring(0) }}")
        assert _render("{{ arc(nope, size=nope) }}") == _render("{{ arc(0) }}")
        assert _render("{{ bar(nope) }}") == _render("{{ bar(0) }}")
        assert _render("{{ sparkline([1, 2], min=nope) }}") == _render("{{ sparkline([1, 2]) }}")

    def test_arc(self):
        out = _render("{{ arc(80, 'info') }}")

        assert "<path" in out
        assert css_rgb(get_theme("watchos").info) in out

    def test_unparseable_literal_gets_the_neutral_track(self):
        theme = get_theme("watchos")

        out = _render("{{ ring(50, 'tomato') }}")

        assert 'stroke="tomato"' in out
        assert css_rgba(theme.text_primary, 0.12) in out

    def test_bar(self):
        out = _render("{{ bar(40, 'success') }}")

        assert "width: 40.0%" in out or "40.0%" in out
        assert css_rgb(get_theme("watchos").success) in out

    def test_sparklines_in_one_cell_keep_their_own_gradient(self):
        out = _render("{{ sparkline([1, 3, 2], 'warning') }}{{ sparkline([2, 1, 3], 'info') }}")

        assert 'id="spark0"' in out
        assert 'id="spark1"' in out
        assert "url(#spark1)" in out

    def test_sparkline_box_sets_aspect(self):
        out = _render("{{ sparkline(['1', 'unavailable', 2, 4], width=200, height=50) }}")

        assert "width: 200px; height: 50px" in out
        assert 'viewBox="0 0 400 100"' in out

    def test_sparkline_needs_two_points(self):
        assert _render("{{ sparkline([1]) }}|{{ sparkline(5) }}") == "|"

    def test_icon(self):
        out = _render("{{ icon('mdi:lock', 'success', 24) }}")

        assert out.startswith('<span class="icon"')
        assert f"color: {css_rgb(get_theme('watchos').success)}" in out
        assert "font-size: 24px" in out
        # An unknown name draws the same help circle as built-in widgets
        assert _render("{{ icon('mdi:not-a-real-icon') }}") == _render("{{ icon('help-circle') }}")

    def test_helpers_return_markup(self):
        widget_ctx = _ctx()
        from custom_components.geekmagic.widgets._htmlkit import template_helpers

        helpers = template_helpers(widget_ctx)

        for name in ("ring", "arc", "bar", "sparkline", "icon"):
            args = ([1, 2],) if name == "sparkline" else ("mdi:lock",) if name == "icon" else (5,)
            assert isinstance(helpers[name](*args), Markup), name

    def test_widget_renders_helpers_against_its_cell(self):
        widget = _widget("{{ ring(50) }}")
        ctx = _ctx("standby", slot=3)

        out = widget.render_html(ctx, WidgetState())

        assert css_rgb(get_theme("standby").get_accent_color(3)) in out
