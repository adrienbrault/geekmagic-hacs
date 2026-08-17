"""Recorder history → plottable numbers.

Pure transforms over what ``homeassistant.components.recorder`` hands
back: no ``hass``, no I/O, no knowledge of who asked. The recorder
stores state *changes*, in whatever shape the query was made (``State``
objects, or dicts under ``minimal_response``); widgets want plottable
floats. Everything between those two ends lives here — the sparkline
path (``extract_timestamped_numeric_values`` → ``resample_history``)
and the candle path (``extract_timestamped_values``), which read the
same recorder rows under different rules.

Kept as its own module rather than inside ``widget_data`` because the
rules are about *history data*, not about orchestration: what counts as
numeric, which binary states map to 1/0 (and where they must not), and
how a step signal is resampled onto a time axis. That makes them
testable without a Home Assistant instance and reusable by anything
that grows a need for history later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from datetime import datetime

# Binary states that should be converted to 1.0 (on/true)
BINARY_ON_STATES = frozenset({"on", "true", "open", "home", "unlocked", "playing", "active"})
# Binary states that should be converted to 0.0 (off/false)
BINARY_OFF_STATES = frozenset(
    {"off", "false", "closed", "not_home", "locked", "paused", "idle", "standby"}
)

# Number of evenly-spaced time slices a chart's history is resampled into.
CHART_RESAMPLE_BUCKETS = 96


def extract_timestamped_numeric_values(history_states: list) -> list[tuple[float, float]]:
    """Extract (timestamp, value) pairs from recorder history states.

    Handles both State objects (with ``.state``/``.last_changed``) and
    dictionaries (the ``minimal_response=True`` format), including the
    mix of the two that a real query returns. Each state's timestamp is
    kept so history can be resampled onto an evenly-spaced time axis.
    Binary states (on/off, open/closed, ...) are converted to 1.0/0.0 —
    a sparkline of a door sensor is a useful step plot. Candles are not,
    so ``extract_timestamped_values`` deliberately drops them instead.

    Args:
        history_states: List of State objects or dicts from recorder

    Returns:
        List of (timestamp_seconds, value) tuples sorted by timestamp.
        States without a usable timestamp or value are skipped.
    """
    result: list[tuple[float, float]] = []
    for state in history_states:
        try:
            state_value = state.state if hasattr(state, "state") else state.get("state")
            if state_value is None:
                continue

            last_changed = (
                state.last_changed if hasattr(state, "last_changed") else state.get("last_changed")
            )
            if last_changed is None:
                continue
            ts = (
                last_changed.timestamp()
                if hasattr(last_changed, "timestamp")
                else float(last_changed)
            )

            try:
                value = float(state_value)
            except (ValueError, TypeError):
                state_lower = str(state_value).lower()
                if state_lower in BINARY_ON_STATES:
                    value = 1.0
                elif state_lower in BINARY_OFF_STATES:
                    value = 0.0
                else:
                    continue
        except (AttributeError, ValueError, TypeError):
            continue
        result.append((ts, value))

    result.sort(key=lambda pair: pair[0])
    return result


def extract_timestamped_values(history_states: list) -> list[tuple[float, float]]:
    """Extract (timestamp, value) pairs for OHLC candle aggregation.

    Deliberately *not*
    ``extract_timestamped_numeric_values``: a candle chart is open /
    high / low / close over an interval, which is meaningless for a
    binary sensor, so a non-numeric state is dropped here rather than
    mapped to 1.0/0.0. The result is also left in recorder order — the
    aggregator walks it as a time series and the recorder already
    returns it sorted.

    Unlike the sparkline extractor it never calls ``.timestamp()`` on a
    dict's ``last_changed``, so a dict row carrying a ``datetime`` there
    is dropped rather than read. Kept as-is: the candle path only ever
    sees ``State`` objects, because ``widget_data._state_changes`` does
    not query with ``minimal_response``.

    Args:
        history_states: List of State objects (or dicts whose
            ``last_changed`` is already an epoch float) from the
            recorder.

    Returns:
        List of (timestamp_seconds, numeric_value) tuples, in recorder
        order. States without a numeric value are skipped; a dict
        without ``last_changed`` is timestamped 0.
    """
    timestamped: list[tuple[float, float]] = []
    for state_obj in history_states:
        try:
            state_value = state_obj.state if hasattr(state_obj, "state") else state_obj.get("state")
            ts = (
                state_obj.last_changed.timestamp()
                if hasattr(state_obj, "last_changed")
                else state_obj.get("last_changed", 0)
            )
            if state_value is not None:
                timestamped.append((float(ts), float(state_value)))
        except (ValueError, TypeError, AttributeError):
            continue
    return timestamped


def resample_history(
    history_states: list,
    start: datetime,
    end: datetime,
    buckets: int = CHART_RESAMPLE_BUCKETS,
) -> list[float]:
    """Resample recorder history onto an evenly-spaced time axis.

    The recorder stores state *changes*, not periodic samples, so a value
    held steady for hours is a single point. Plotting those points at even
    horizontal spacing distorts time: long flat stretches (e.g. power at
    0 W) collapse to a sliver while busy periods get stretched.

    This buckets the window into `buckets` equal time slices. Each slice
    holds the time-weighted average of the value over that slice, treating
    the signal as a step function (each value held until the next recorded
    change). The result is a time-faithful series suitable for a sparkline.

    Args:
        history_states: State objects/dicts from the recorder.
        start: Window start (inclusive).
        end: Window end (exclusive).
        buckets: Number of evenly-spaced slices to produce.

    Returns:
        Resampled values. Empty when there is no usable data.
    """
    timestamped = extract_timestamped_numeric_values(history_states)
    if not timestamped:
        return []

    start_ts = start.timestamp()
    end_ts = end.timestamp()
    if end_ts <= start_ts or buckets < 1:
        return [value for _, value in timestamped]

    is_binary = all(value in (0.0, 1.0) for _, value in timestamped)
    bucket_dur = (end_ts - start_ts) / buckets

    # Seed the carried-forward value from the last point at or before the
    # window start (recorder include_start_time_state provides one).
    idx = 0
    n = len(timestamped)
    carried: float | None = None
    while idx < n and timestamped[idx][0] <= start_ts:
        carried = timestamped[idx][1]
        idx += 1

    raw: list[float | None] = []
    for b in range(buckets):
        b_start = start_ts + b * bucket_dur
        b_end = b_start + bucket_dur
        weighted = 0.0
        known_dur = 0.0
        cursor = b_start
        seg_val = carried
        while idx < n and timestamped[idx][0] < b_end:
            ts, value = timestamped[idx]
            if ts > cursor and seg_val is not None:
                weighted += seg_val * (ts - cursor)
                known_dur += ts - cursor
            cursor = ts
            seg_val = value
            idx += 1
        if b_end > cursor and seg_val is not None:
            weighted += seg_val * (b_end - cursor)
            known_dur += b_end - cursor
        carried = seg_val
        raw.append(weighted / known_dur if known_dur > 0 else None)

    # Drop leading buckets with no data, forward-fill any interior gaps.
    first = next((i for i, value in enumerate(raw) if value is not None), None)
    if first is None:
        return []
    result: list[float] = []
    last = cast("float", raw[first])
    for value in raw[first:]:
        last = value if value is not None else last
        result.append(last)

    if is_binary:
        return [1.0 if value >= 0.5 else 0.0 for value in result]
    return result
