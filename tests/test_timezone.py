"""Timezone handling belongs to the clock widget, not to its callers.

Every render path (coordinator, websocket preview, sample scripts) hands
widgets the same HA-local ``state.now``. A clock with a ``timezone``
option converts that instant itself, so no caller has to special-case
what a clock is. These tests pin that contract at the widget interface.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.state import WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# Noon in Paris is 06:00 in New York — a shift big enough that the two
# renders can never be confused for one another.
PARIS_NOON = datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("Europe/Paris"))


def clock(**options) -> ClockWidget:
    """A clock widget configured with the given options."""
    return ClockWidget(WidgetConfig(widget_type="clock", slot=0, options=options))


class TestClockTimezone:
    """The clock converts the instant it is given."""

    def test_timezone_option_converts_the_instant(self):
        """A timezone option shifts the displayed wall clock, not the instant."""
        widget = clock(timezone="America/New_York", show_date=False)
        now = widget._now(WidgetState(now=PARIS_NOON))

        assert str(now.tzinfo) == "America/New_York"
        assert now.strftime("%H:%M") == "06:00"
        assert now == PARIS_NOON  # same instant, different wall clock
        assert "06:00" in widget.render_html(CTX, WidgetState(now=PARIS_NOON))

    def test_empty_timezone_uses_the_instant_as_given(self):
        """An empty timezone string is falsy — the caller's zone stands."""
        widget = clock(timezone="", show_date=False)
        now = widget._now(WidgetState(now=PARIS_NOON))

        assert str(now.tzinfo) == "Europe/Paris"
        assert "12:00" in widget.render_html(CTX, WidgetState(now=PARIS_NOON))

    def test_no_timezone_option_uses_the_instant_as_given(self):
        """Without the option the clock renders the caller's timezone."""
        widget = clock(show_date=False)
        now = widget._now(WidgetState(now=PARIS_NOON))

        assert str(now.tzinfo) == "Europe/Paris"
        assert now.strftime("%H:%M") == "12:00"

    def test_invalid_timezone_falls_back_to_the_instant(self):
        """An unusable zone name costs the conversion, not the cell."""
        widget = clock(timezone="Invalid/Timezone", show_date=False)
        now = widget._now(WidgetState(now=PARIS_NOON))

        assert str(now.tzinfo) == "Europe/Paris"
        assert "12:00" in widget.render_html(CTX, WidgetState(now=PARIS_NOON))

    def test_missing_now_falls_back_to_utc(self):
        """A state without ``now`` still renders — UTC stands in."""
        widget = clock(show_date=False)
        now = widget._now(WidgetState())

        assert now.tzinfo is UTC

    def test_missing_now_still_honours_the_timezone_option(self):
        """The UTC fallback is converted like any other instant."""
        widget = clock(timezone="Asia/Tokyo", show_date=False)
        now = widget._now(WidgetState())

        assert str(now.tzinfo) == "Asia/Tokyo"

    def test_naive_now_is_read_as_utc(self):
        """A naive instant must not be reinterpreted as host-local time.

        ``astimezone`` on a naive datetime assumes the *host's* zone, so
        the same naive instant would render as a different wall clock
        depending on where Home Assistant runs. Reading it as UTC makes
        the conversion deterministic: 12:00 naive is 07:00 in New York
        wherever this test happens to execute.
        """
        naive = datetime(2024, 1, 15, 12, 0)  # noqa: DTZ001 - the point of the test
        widget = clock(timezone="America/New_York", show_date=False)
        now = widget._now(WidgetState(now=naive))

        assert now == naive.replace(tzinfo=UTC)
        assert now.strftime("%H:%M") == "07:00"

    def test_naive_now_without_a_timezone_option_is_still_aware(self):
        """``_now`` always returns an aware instant, wall clock untouched."""
        naive = datetime(2024, 1, 15, 12, 0)  # noqa: DTZ001 - the point of the test
        now = clock(show_date=False)._now(WidgetState(now=naive))

        assert now.tzinfo is UTC
        assert now.strftime("%H:%M") == "12:00"

    def test_two_clocks_on_one_instant_read_differently(self):
        """The point of the option: a grid of city clocks from one ``now``."""
        state = WidgetState(now=PARIS_NOON)
        tokyo = clock(timezone="Asia/Tokyo", show_date=False).render_html(CTX, state)
        london = clock(timezone="Europe/London", show_date=False).render_html(CTX, state)

        assert "20:00" in tokyo
        assert "11:00" in london
