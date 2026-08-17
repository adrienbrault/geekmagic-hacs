"""Compact-cell identity contract for the gauge and weather widgets.

Small cells must keep saying *what* they show. Python decides which
bands survive — by measuring what the cell can hold — instead of a magic
pixel cliff or a blanket ``hide-*`` class, and a caption gives up size
(down to a 10px floor) before it gives up letters.

These are regressions for confirmed misses:

* round gauges going anonymous in the most common small slots, and
  rendering a completely empty ring when the value is switched off;
* the narrow list-mode forecast wrapping its weekday under the icon and
  bleeding the low temperature past the cell edge;
* the forecast strip's low row clipping against the bottom edge in
  ~150px square cells.

Assertions are on fragment substrings and on the geometry the fragment
carries (inline pixel sizes), never on exact full strings.
"""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.htmldoc import CellContext, mdi_span
from custom_components.geekmagic.widgets._cellkit import cell_box, label_px
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from custom_components.geekmagic.widgets.weather import WeatherWidget

FIXED_NOW = datetime(2025, 12, 29, 13, 45, 30, tzinfo=UTC)

FORECAST = [
    {
        "datetime": "2025-12-29T00:00:00+00:00",
        "condition": "sunny",
        "temperature": 26,
        "templow": 14,
    },
    {
        "datetime": "2025-12-30T00:00:00+00:00",
        "condition": "rainy",
        "temperature": 19,
        "templow": 10,
    },
    {
        "datetime": "2025-12-31T00:00:00+00:00",
        "condition": "cloudy",
        "temperature": 18,
        "templow": 9,
    },
]

# The small slots the layouts actually produce: 3x3 tiles, hero footers,
# 2x2 quadrants, and the short band that used to fall into the gap.
SMALL_CELLS = [(69, 65), (72, 67), (72, 72), (74, 71), (111, 76), (111, 88), (111, 111)]


def cell(width: int, height: int) -> CellContext:
    """Cell context of a given size on the default theme."""
    return CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)


def gauge(style: str, label: str = "CPU", **options: Any) -> GaugeWidget:
    """Gauge widget of a given style, labelled for identity checks."""
    return GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            label=label,
            options={"style": style, **options},
        )
    )


def gauge_state(value: str = "73", unit: str = "%") -> WidgetState:
    """Numeric entity snapshot for a gauge."""
    entity = EntityState(
        entity_id="sensor.cpu",
        state=value,
        attributes={"friendly_name": "CPU", "unit_of_measurement": unit},
    )
    return WidgetState(entity=entity, now=FIXED_NOW)


def weather(**options: Any) -> WeatherWidget:
    """Weather widget with the given options."""
    return WeatherWidget(
        WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home", options=options)
    )


def weather_state(*, forecast: list[dict] | None = None, entity: bool = True) -> WidgetState:
    """Weather snapshot (partly cloudy, 22°, 62% humidity)."""
    state = (
        EntityState(
            entity_id="weather.home",
            state="partlycloudy",
            attributes={"friendly_name": "Home", "temperature": 22, "humidity": 62},
        )
        if entity
        else None
    )
    return WidgetState(entity=state, forecast=forecast or [], now=FIXED_NOW)


def body(fragment: str) -> str:
    """The markup only — widget-scoped <style> names every class."""
    return fragment.rsplit("</style>", 1)[-1]


def font_px(fragment: str, marker: str) -> float:
    """First inline ``font-size`` at or under the element carrying ``marker``."""
    match = re.search(rf'class="{marker}".*?font-size: ([\d.]+)px', body(fragment))
    assert match, f"no inline font-size for {marker} in {fragment}"
    return float(match.group(1))


def glyph(name: str) -> str:
    """The MDI codepoint ``mdi_span`` emits for an icon name."""
    match = re.search(r">(&#x[0-9A-Fa-f]+;)<", mdi_span(name))
    assert match, name
    return match.group(1)


# ============================================================================
# Round gauges keep their identity (G1, G2, G3, G5)
# ============================================================================


class TestRoundGaugeIdentity:
    """Ring and arc gauges in small cells."""

    @pytest.mark.parametrize("style", ["ring", "arc"])
    @pytest.mark.parametrize(("width", "height"), SMALL_CELLS)
    def test_small_cells_keep_the_caption(self, style, width, height):
        """A bare ring is a number without a meaning — the name stays."""
        fragment = gauge(style).render_html(cell(width, height), gauge_state())
        assert "CPU" in fragment
        assert "hide-short" not in fragment

    @pytest.mark.parametrize("style", ["ring", "arc"])
    @pytest.mark.parametrize("height", range(65, 131, 5))
    def test_caption_visibility_is_monotonic(self, style, height):
        """No hole: a taller cell never loses a caption a shorter one kept."""
        fragment = gauge(style).render_html(cell(111, height), gauge_state())
        assert "CPU" in fragment

    @pytest.mark.parametrize("style", ["ring", "arc"])
    @pytest.mark.parametrize(("width", "height"), [(69, 65), (72, 72), (111, 88), (48, 40)])
    def test_valueless_gauge_is_never_anonymous(self, style, width, height):
        """show_value off + no unit: the caption is the only reading left."""
        widget = gauge(style, show_value=False, show_unit=False)
        fragment = widget.render_html(cell(width, height), gauge_state())
        assert "CPU" in fragment
        assert ">73<" not in fragment

    def test_caption_shrinks_before_it_truncates(self):
        """A whole word at 11px beats "HUMID…" at the kit's 12px."""
        fragment = gauge("ring", label="Humidity").render_html(cell(69, 65), gauge_state())
        assert "HUMIDITY" in fragment
        assert "…" not in fragment
        assert font_px(fragment, "t-label caption-row") < label_px(cell(69, 65))

    def test_inside_caption_shrinks_to_the_hole(self):
        """The fullscreen ring's inner caption fits whole, not ellipsized."""
        widget = gauge("ring", label="Living Room Humidity")
        fragment = widget.render_html(cell(240, 240), gauge_state())
        assert "LIVING ROOM HUMIDITY" in fragment
        assert "…" not in fragment

    def test_wide_short_row_keeps_the_caption(self):
        """A 200x56 row has room for a 10px label beside its value."""
        fragment = gauge("ring").render_html(cell(200, 56), gauge_state())
        assert "CPU" in fragment

    def test_tall_cell_keeps_the_value_in_the_hole(self):
        """A gauge's reading lives INSIDE the ring (user contract) — a
        ring with an empty hole and its number floating elsewhere reads
        as two broken widgets. The tall column grows the ring to the
        full width, and the hole value grows with it."""
        ctx = cell(71, 228)
        fragment = gauge("ring").render_html(ctx, gauge_state())
        assert "CPU" in fragment
        assert "position: absolute" in fragment  # the in-hole overlay
        hero = font_px(fragment, "t-hero")
        square = font_px(gauge("ring").render_html(cell(71, 71), gauge_state()), "t-hero")
        # Width-bound in both shapes: the tall column's reading is at
        # least as large as the square tile's.
        assert hero >= square * 0.9

    def test_wide_row_keeps_the_value_in_the_hole(self):
        """Same contract for the Fitness-row treatment: value in the
        hole, the caption beside the ring."""
        fragment = gauge("ring").render_html(cell(228, 71), gauge_state())
        assert "CPU" in fragment
        assert "position: absolute" in fragment
        assert ">73<" in fragment


# ============================================================================
# Weather in narrow, small and empty cells (W1..W5, S5)
# ============================================================================


class TestWeatherNarrowList:
    """Row-per-day forecast in split-v columns."""

    @pytest.mark.parametrize("width", [71, 73, 87])
    def test_tight_rows_shed_the_low(self, width):
        """Under ~88px DAY + icon + hi + lo cannot share a row."""
        fragment = body(weather().render_html(cell(width, 228), weather_state(forecast=FORECAST)))
        assert "wx-list tight" in fragment
        assert "wx-lo" not in fragment
        assert "14°" not in fragment  # today's low would bleed off the cell
        assert "MON" in fragment
        assert "26°" in fragment

    def test_wider_lists_keep_the_low(self):
        """A 114px split-v column has the width for the pair."""
        fragment = body(weather().render_html(cell(114, 228), weather_state(forecast=FORECAST)))
        assert "tight" not in fragment
        assert "14°" in fragment


class TestWeatherStripFits:
    """The forecast strip must not be clipped by the cell's bottom edge."""

    @pytest.mark.parametrize(("width", "height"), [(148, 148), (160, 160), (148, 140), (148, 155)])
    def test_bands_fit_the_cell(self, width, height):
        """Caption + icon + value + strip stay inside the content box."""
        ctx = cell(width, height)
        widget = weather()
        fragment = widget.render_html(ctx, weather_state(forecast=FORECAST))
        columns = widget._strip_columns(ctx, FORECAST)
        high_only = "wx-lo" not in body(fragment)
        strip = widget._strip_height(ctx, len(columns), high_only=high_only)
        spent = label_px(ctx) + font_px(fragment, "wx-icon") + font_px(fragment, "t-hero") + strip
        assert spent <= cell_box(ctx)[1]

    def test_strip_height_counts_gaps_and_rule(self):
        """The reserve models the flex gaps, not just the type."""
        ctx = cell(240, 240)
        # day 15 + icon 22 + (hi 19 + lo 16) * 1.05, plus three 0.2em
        # gaps, the block gap and the hairline.
        assert weather()._strip_height(ctx, 3, high_only=False) >= 95.0


class TestWeatherMiniStrip:
    """Short-wide cells keep a forecast instead of a lone temperature."""

    @pytest.mark.parametrize(("width", "height"), [(108, 69), (111, 72)])
    def test_short_wide_cells_show_icon_and_high(self, width, height):
        """Three tinted glyphs with their highs — no day names, no lows."""
        fragment = body(
            weather().render_html(cell(width, height), weather_state(forecast=FORECAST))
        )
        assert "wx-strip mini" in fragment
        assert "26°" in fragment and "19°" in fragment and "18°" in fragment
        assert "wx-day" not in fragment
        assert "wx-lo" not in fragment
        # The strip replaces the hi/lo chips in these cells.
        assert "chips" not in fragment
        assert "26° / 14°" not in fragment

    def test_wide_mini_strip_regains_lows(self):
        """Columns wide enough set the low beside the high."""
        fragment = body(weather().render_html(cell(240, 80), weather_state(forecast=FORECAST)))
        assert "wx-strip mini" in fragment
        assert "wx-lo" in fragment
        assert "wx-day" not in fragment  # 80px has no band for day names

    def test_tall_mini_strip_regains_day_names(self):
        """From ~92px of height the day names ride above the icons."""
        fragment = body(weather().render_html(cell(240, 120), weather_state(forecast=FORECAST)))
        assert "wx-strip mini" in fragment
        assert "wx-day" in fragment
        assert "MON" in fragment
        assert "wx-lo" in fragment

    def test_mini_strip_shares_the_cell_with_the_hero(self):
        """Hero row plus mini strip must both fit the content box."""
        ctx = cell(111, 72)
        widget = weather()
        fragment = widget.render_html(ctx, weather_state(forecast=FORECAST))
        strip = widget._strip_height(ctx, 3, high_only=True)
        pair = max(font_px(fragment, "wx-icon"), font_px(fragment, "t-hero"))
        assert pair + strip <= cell_box(ctx)[1]

    def test_cells_too_narrow_for_columns_keep_the_hero_alone(self):
        """A 3x3 tile has no room for a strip — it stays icon + value."""
        fragment = body(weather().render_html(cell(74, 71), weather_state(forecast=FORECAST)))
        assert "wx-strip" not in fragment
        assert "22°" in fragment


class TestWeatherBands:
    """Caption, chips and the solo hero."""

    def test_humidity_survives_in_the_largest_cells(self):
        """The pair is fitted, not measured at the kit size and dropped."""
        fragment = weather().render_html(cell(240, 240), weather_state())
        assert "PARTLY CLOUDY" in fragment
        assert "62%" in fragment

    @pytest.mark.parametrize(("width", "height"), [(111, 111), (111, 72)])
    def test_quadrant_cells_carry_the_hi_lo_pair(self, width, height):
        """A 2x2 tile has room for the pair — arrowless below 150px."""
        fragment = weather(show_forecast=False).render_html(
            cell(width, height), weather_state(forecast=FORECAST)
        )
        assert "26° / 14°" in fragment
        assert glyph("arrow-up-thin") not in fragment

    def test_wide_cells_keep_the_arrow_chips(self):
        fragment = weather(show_forecast=False).render_html(
            cell(240, 120), weather_state(forecast=FORECAST)
        )
        assert glyph("arrow-up-thin") in fragment
        assert glyph("arrow-down-thin") in fragment

    def test_solo_hero_fills_the_cell(self):
        """No strip, no chips: icon and value are sized from the height."""
        ctx = cell(240, 240)
        fragment = weather(show_forecast=False, show_high_low=False).render_html(
            ctx, weather_state()
        )
        icon = font_px(fragment, "wx-icon")
        hero = font_px(fragment, "t-hero")
        # The CSS clamp caps the icon at 78px and leaves the bottom half
        # of the cell empty; sized from the free height it goes bigger.
        assert icon > 78.0
        assert icon + hero > cell_box(ctx)[1] * 0.75


class TestWeatherPlaceholder:
    """The no-entity cell must not impersonate a reading."""

    @pytest.mark.parametrize(("width", "height"), [(69, 65), (74, 71), (111, 72)])
    def test_short_cells_keep_a_caption(self, width, height):
        fragment = weather().render_html(cell(width, height), weather_state(entity=False))
        assert "NO DATA" in fragment
        assert "hide-short" not in fragment
        assert glyph("alert-circle-outline") in fragment

    def test_glyph_is_an_alert_not_a_cloud(self):
        fragment = weather().render_html(cell(240, 240), weather_state(entity=False))
        assert glyph("alert-circle-outline") in fragment
        assert glyph("weather-cloudy") not in fragment
        assert "NO WEATHER DATA" in fragment
