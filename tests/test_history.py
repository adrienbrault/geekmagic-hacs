"""Tests for ``history.py`` — recorder history → plottable numbers.

Two paths off the same recorder rows, and the contract between them is
what counts as a value. The sparkline path:
``extract_timestamped_numeric_values`` decides that (numeric strings,
plus the ``BINARY_ON_STATES``/``BINARY_OFF_STATES`` rosters mapped to
1.0/0.0, everything else dropped), and ``resample_history`` inherits it
wholesale — so the value rules are exercised on the extractor and the
time rules on the resampler. The candle path:
``extract_timestamped_values`` drops non-numeric states instead of
mapping them, because open/high/low/close over an interval says nothing
about a door sensor.

The extractor sees whatever shape the recorder query was made in: full
``State`` objects, plain dicts under ``minimal_response=True``, or —
the case that actually ships — a mix, with State objects at the ends and
dicts in between. Every accessor here takes both.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.geekmagic.history import (
    extract_timestamped_numeric_values,
    extract_timestamped_values,
    resample_history,
)

BASE = datetime(2024, 1, 1, tzinfo=UTC)


class MockState:
    """A recorder ``State`` with no ``last_changed``."""

    def __init__(self, state_value: str) -> None:
        """Initialize with a state value."""
        self.state = state_value


class MockTimedState:
    """A recorder ``State`` with ``.state`` and ``.last_changed``."""

    def __init__(self, state_value: str, last_changed: datetime) -> None:
        """Initialize with a state value and its last_changed timestamp."""
        self.state = state_value
        self.last_changed = last_changed


def _at(hours: float) -> datetime:
    """A timestamp ``hours`` into the test window."""
    return BASE + timedelta(hours=hours)


def _dict(state_value: str | None, hours: float) -> dict:
    """The ``minimal_response=True`` shape of one recorded change."""
    return {"state": state_value, "last_changed": _at(hours)}


def _values(history: list) -> list[float]:
    """Just the values, for the tests that do not care about time."""
    return [value for _, value in extract_timestamped_numeric_values(history)]


class TestExtractTimestampedNumericValues:
    """What the extractor accepts, converts, drops and orders."""

    def test_keeps_timestamps_and_values(self):
        """State objects yield (timestamp, value) pairs."""
        history = [MockTimedState("20.0", BASE), MockTimedState("21.5", _at(1))]

        result = extract_timestamped_numeric_values(history)

        assert result == [(BASE.timestamp(), 20.0), (_at(1).timestamp(), 21.5)]

    def test_parse_dict_objects(self):
        """Dicts from ``minimal_response=True`` parse like State objects."""
        history = [_dict("20.0", 0), _dict("21.5", 1), _dict("22.0", 2)]

        assert _values(history) == [20.0, 21.5, 22.0]

    def test_parse_mixed_format(self):
        """The shape ``minimal_response=True`` really returns.

        HA hands back State objects for the first/last rows and dicts for
        everything in between. All five points must survive, not just the
        two ends.
        """
        history = [
            MockTimedState("20.0", BASE),
            _dict("21.5", 1),
            _dict("22.0", 2),
            _dict("23.0", 3),
            MockTimedState("24.0", _at(4)),
        ]

        assert _values(history) == [20.0, 21.5, 22.0, 23.0, 24.0]

    def test_parse_integer_values(self):
        """Integer strings come back as floats."""
        history = [MockTimedState("20", BASE), _dict("21", 1), MockTimedState("22", _at(2))]

        values = _values(history)

        assert values == [20.0, 21.0, 22.0]
        assert all(isinstance(value, float) for value in values)

    def test_sorts_by_timestamp(self):
        """Out-of-order states are sorted by timestamp."""
        history = [
            MockTimedState("2.0", _at(2)),
            MockTimedState("0.0", BASE),
            MockTimedState("1.0", _at(1)),
        ]

        assert _values(history) == [0.0, 1.0, 2.0]

    def test_skips_states_without_timestamp(self):
        """States lacking last_changed are skipped."""
        assert extract_timestamped_numeric_values([MockState("20.0")]) == []

    def test_skips_none_state_values(self):
        """A None state value is skipped."""
        history = [MockTimedState("20.0", BASE), _dict(None, 1), MockTimedState("22.0", _at(2))]

        assert _values(history) == [20.0, 22.0]

    def test_skips_dict_missing_state_key(self):
        """A dict without a 'state' key is skipped."""
        history = [
            MockTimedState("20.0", BASE),
            {"last_changed": _at(1)},
            MockTimedState("22.0", _at(2)),
        ]

        assert _values(history) == [20.0, 22.0]

    def test_converts_binary_states(self):
        """on/off states are converted to 1.0/0.0."""
        history = [MockTimedState("off", BASE), MockTimedState("on", _at(1))]

        assert _values(history) == [0.0, 1.0]

    def test_converts_the_whole_binary_roster(self):
        """Every pair in BINARY_ON_STATES/BINARY_OFF_STATES maps to 1/0.

        These rosters are what makes a binary_sensor, a lock, a
        device_tracker or a media_player chartable at all — a domain
        missing from them silently plots nothing.
        """
        pairs = [
            ("open", "closed"),
            ("home", "not_home"),
            ("unlocked", "locked"),
            ("playing", "paused"),
            ("active", "idle"),
            ("true", "false"),
            ("on", "standby"),
        ]
        history = [
            MockTimedState(state, _at(index))
            for index, state in enumerate(value for pair in pairs for value in pair)
        ]

        assert _values(history) == [1.0, 0.0] * len(pairs)

    def test_binary_matching_is_case_insensitive(self):
        """Binary state matching ignores case."""
        history = [
            MockTimedState("ON", BASE),
            MockTimedState("Off", _at(1)),
            _dict("OPEN", 2),
            _dict("Closed", 3),
        ]

        assert _values(history) == [1.0, 0.0, 1.0, 0.0]

    def test_mixes_binary_and_numeric(self):
        """A sensor that changed type still yields both kinds of value."""
        history = [
            MockTimedState("23.5", BASE),
            MockTimedState("on", _at(1)),
            _dict("off", 2),
            _dict("42.0", 3),
        ]

        assert _values(history) == [23.5, 1.0, 0.0, 42.0]

    def test_skips_unavailable_and_unknown(self):
        """A device that drops offline leaves gaps, not zeroes.

        ``unavailable``/``unknown`` are not states of the thing being
        charted; mapping them to 0.0 would draw an outage as a real value.
        """
        history = [
            MockTimedState("locked", BASE),
            MockTimedState("unknown", _at(1)),
            MockTimedState("unlocked", _at(2)),
            _dict("unavailable", 3),
            _dict("locked", 4),
            MockTimedState("unavailable", _at(5)),
            MockTimedState("unlocked", _at(6)),
        ]

        assert _values(history) == [0.0, 1.0, 0.0, 1.0]

    def test_all_unavailable_yields_nothing(self):
        """Nothing usable in, nothing out."""
        history = [
            MockTimedState("unavailable", BASE),
            _dict("unknown", 1),
            MockTimedState("unavailable", _at(2)),
        ]

        assert extract_timestamped_numeric_values(history) == []

    def test_empty_history(self):
        """An empty list returns an empty result."""
        assert extract_timestamped_numeric_values([]) == []


class TestExtractTimestampedValues:
    """The candle extractor — same rows, deliberately different rules."""

    def test_keeps_timestamps_and_values(self):
        history = [MockTimedState("20.0", BASE), MockTimedState("21.5", _at(1))]

        assert extract_timestamped_values(history) == [
            (BASE.timestamp(), 20.0),
            (_at(1).timestamp(), 21.5),
        ]

    def test_dict_rows_need_a_numeric_last_changed(self):
        """Dict rows are read, but only with an epoch-float timestamp.

        Unlike the sparkline extractor, this one never calls
        ``.timestamp()`` on a dict's ``last_changed``, so a ``datetime``
        there fails the ``float()`` and the row is dropped. Pinned as-is
        because the candle path only ever sees ``State`` objects —
        ``widget_data._state_changes`` does not pass
        ``minimal_response``.
        """
        assert extract_timestamped_values([{"state": "3.5", "last_changed": 1704074400.0}]) == [
            (1704074400.0, 3.5)
        ]
        assert extract_timestamped_values([_dict("3.5", 2)]) == []

    def test_binary_states_are_dropped_not_mapped(self):
        """Open/high/low/close over an interval is meaningless for on/off.

        This is the one rule that separates the two extractors: the
        sparkline path maps ``on``/``off`` to 1.0/0.0, the candle path
        drops them.
        """
        history = [MockTimedState("on", BASE), MockTimedState("off", _at(1))]

        assert extract_timestamped_values(history) == []
        assert [value for _, value in extract_timestamped_numeric_values(history)] == [1.0, 0.0]

    def test_unusable_states_are_dropped(self):
        history = [
            MockTimedState("unavailable", BASE),
            MockTimedState("12.0", _at(1)),
            {"state": None, "last_changed": 0.0},
        ]

        assert extract_timestamped_values(history) == [(_at(1).timestamp(), 12.0)]

    def test_dict_without_last_changed_is_timestamped_zero(self):
        assert extract_timestamped_values([{"state": "7"}]) == [(0.0, 7.0)]

    def test_recorder_order_is_preserved(self):
        """Left unsorted: the recorder already returns rows in order."""
        history = [MockTimedState("2.0", _at(3)), MockTimedState("1.0", BASE)]

        assert [ts for ts, _ in extract_timestamped_values(history)] == [
            _at(3).timestamp(),
            BASE.timestamp(),
        ]

    def test_empty_history(self):
        assert extract_timestamped_values([]) == []


class TestResampleHistory:
    """Tests for resample_history.

    Regression coverage for issue #133: the recorder stores state *changes*,
    not periodic samples, so plotting raw points at even horizontal spacing
    distorts time. resample_history puts history back on an even time axis.
    """

    def test_empty_history(self):
        """No history returns an empty list."""
        assert resample_history([], BASE, _at(24)) == []

    def test_constant_value_is_flat(self):
        """A single steady value resamples to a flat line."""
        result = resample_history([MockTimedState("42.0", BASE)], BASE, _at(24), buckets=24)

        assert result == [42.0] * 24

    def test_long_flat_period_is_not_collapsed(self):
        """A value held at 0 for most of the window stays flat at 0.

        This is the core of issue #133: power sits at 0 W for hours (one
        recorded point) with a brief spike. The 0 W stretch must occupy
        most of the resampled series, not collapse to a sliver.
        """
        history = [
            MockTimedState("0", BASE),
            MockTimedState("3000", _at(12)),
            MockTimedState("0", _at(12.25)),
        ]

        result = resample_history(history, BASE, _at(24), buckets=96)

        assert len(result) == 96
        # The spike lasts 15 min out of a 24 h window; the vast majority of
        # the resampled points must still read 0.
        assert result.count(0.0) >= 94
        # The spike is preserved somewhere in the series.
        assert max(result) > 0

    def test_time_weighted_average_within_bucket(self):
        """A change mid-bucket yields a time-weighted average."""
        # Value 0 for the first 45 min, then 100 for the last 15 min.
        history = [MockTimedState("0", BASE), MockTimedState("100", _at(0.75))]

        result = resample_history(history, BASE, _at(1), buckets=1)

        assert result == [pytest.approx(25.0)]

    def test_binary_history_thresholded(self):
        """Binary history resamples to 0.0/1.0 values only."""
        history = [MockTimedState("off", BASE), MockTimedState("on", _at(12))]

        result = resample_history(history, BASE, _at(24), buckets=96)

        assert set(result) <= {0.0, 1.0}
        assert result.count(0.0) == 48
        assert result.count(1.0) == 48

    def test_leading_gap_is_dropped(self):
        """Buckets before the first data point are dropped."""
        # First (and only) data point arrives 6 h into the window.
        result = resample_history([MockTimedState("50", _at(6))], BASE, _at(24), buckets=96)

        # 24 of 96 buckets precede the data point and are dropped.
        assert result == [50.0] * 72
