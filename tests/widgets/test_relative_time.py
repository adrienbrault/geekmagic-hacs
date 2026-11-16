"""Relative timestamps carry into the next unit instead of printing 60.

``format_relative_time`` rounded the remainder in whichever unit the raw
seconds fell into and stopped there, so 59m59s read "in 60 minutes" and
23h59m59s read "24 hours ago". One second later the same reading became
"in 1 hour" and "1 day ago" — the count appeared to go backwards, and a
timestamp widget could sit on "60 minutes" for a whole minute.

A rounded count that reaches the next unit's worth is promoted to that
unit, so no phrase ever reads "60 minutes" or "24 hours".
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.geekmagic.widgets.helpers import format_relative_time

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def _phrase(seconds: float) -> str:
    """The relative phrase ``seconds`` away from NOW (negative: past)."""
    return format_relative_time(NOW + timedelta(seconds=seconds), NOW)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        # The carry boundaries the bug hit.
        (3599, "in 1 hour"),
        (-3599, "1 hour ago"),
        (86399, "in 1 day"),
        (-86399, "1 day ago"),
        # ...and the readings either side of them.
        (59, "now"),
        (-59, "now"),
        (61, "in 1 minute"),
        (3500, "in 58 minutes"),
        (3600, "in 1 hour"),
        (5400, "in 2 hours"),
        (82800, "in 23 hours"),
        (86400, "in 1 day"),
        (129600, "in 2 days"),
    ],
)
def test_relative_phrase_carries_into_the_next_unit(seconds: int, expected: str) -> None:
    """A rounded count at the unit's carry point is promoted, not printed."""
    assert _phrase(seconds) == expected


# "in 60 minutes" / "24 hours ago" — the phrases the old rounding produced.
_BAD_PHRASE = re.compile(r"\b(60 minutes|24 hours)\b")


def test_no_phrase_ever_reports_a_full_sixty_minutes_or_twenty_four_hours() -> None:
    """Sweep a two-day window, densely around both carry points."""
    samples = list(range(0, 2 * 86400 + 1, 17))
    for boundary in (3599, 86399):
        samples.extend(range(boundary - 120, boundary + 121))
    for seconds in samples:
        for value in (seconds, -seconds):
            phrase = _phrase(value)
            assert not _BAD_PHRASE.search(phrase), f"{value}s rendered {phrase!r}"


def test_naive_and_aware_timestamps_agree() -> None:
    """The carry works the same when the inputs carry no timezone."""
    naive_now = NOW.replace(tzinfo=None)
    assert format_relative_time(naive_now + timedelta(seconds=3599), naive_now) == "in 1 hour"
