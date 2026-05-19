"""Fetch numeric / OHLC history from the Home Assistant recorder.

Wraps the recorder's `state_changes_during_period` lookup, the executor-job
positional-arg workaround, the time-range math, and the numeric / OHLC
extraction step. Callers ask for "give me numeric history for this entity
over the last N hours" and don't need to know about the recorder API.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .widgets.candlestick import aggregate_ohlc, extract_timestamped_values

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# Binary states that should be converted to 1.0 (on/true)
BINARY_ON_STATES = frozenset({"on", "true", "open", "home", "unlocked", "playing", "active"})
# Binary states that should be converted to 0.0 (off/false)
BINARY_OFF_STATES = frozenset(
    {"off", "false", "closed", "not_home", "locked", "paused", "idle", "standby"}
)


def extract_numeric_values(history_states: list) -> list[float]:
    """Extract numeric values from recorder history states.

    Handles both State objects and dicts (from minimal_response=True).
    Converts on/off-style binary states to 1.0/0.0 so binary_sensor
    entities can be charted. Unparseable values (unavailable, unknown,
    text states) are skipped.
    """
    values: list[float] = []
    for state in history_states:
        try:
            state_value = state.state if hasattr(state, "state") else state.get("state")
            if state_value is None:
                continue
            try:
                values.append(float(state_value))
            except (ValueError, TypeError):
                state_lower = str(state_value).lower()
                if state_lower in BINARY_ON_STATES:
                    values.append(1.0)
                elif state_lower in BINARY_OFF_STATES:
                    values.append(0.0)
        except AttributeError:
            continue
    return values


class HistoryFetcher:
    """Resolves the recorder and fetches entity history asynchronously.

    A fetcher whose recorder isn't available (HA without recorder, or
    during early-startup) becomes a no-op — every method returns an
    empty list. Callers don't need to special-case absence.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._recorder = self._resolve_recorder()

    def _resolve_recorder(self):
        """Return the recorder instance, or None if unavailable."""
        try:
            from homeassistant.components.recorder import get_instance  # noqa: PLC0415
        except ImportError:
            _LOGGER.debug("Recorder not available")
            return None
        try:
            return get_instance(self.hass)
        except KeyError:
            _LOGGER.debug("Recorder instance not available")
            return None

    @property
    def available(self) -> bool:
        return self._recorder is not None

    def _fetch_sync(self, entity_id: str, start: datetime, end: datetime) -> list:
        """Sync history fetch — must run in the recorder's executor.

        Wraps `state_changes_during_period` so it can be invoked through
        `recorder.async_add_executor_job`, which only forwards positional
        arguments but the underlying function has many keyword-only ones.
        """
        from homeassistant.components.recorder import history  # noqa: PLC0415

        result = history.state_changes_during_period(
            self.hass,
            start,
            end,
            entity_id,
            include_start_time_state=True,
            no_attributes=True,
        )
        return result.get(entity_id, [])

    async def fetch_numeric(self, entity_id: str, hours: float) -> list[float]:
        """Fetch numeric history values for `entity_id` over the last `hours`.

        Returns an empty list if the recorder is unavailable, the entity
        has no history, or no values were parseable as numeric.
        """
        if self._recorder is None:
            return []
        now = dt_util.utcnow()
        start = now - timedelta(hours=hours)
        try:
            states = await self._recorder.async_add_executor_job(
                self._fetch_sync, entity_id, start, now
            )
        except Exception as err:
            _LOGGER.warning("Failed to fetch history for %s: %s", entity_id, err)
            return []
        return extract_numeric_values(states) if states else []

    async def fetch_ohlc(
        self,
        entity_id: str,
        hours: float,
        interval_seconds: int,
        candle_count: int,
    ) -> list[tuple[float, float, float, float]]:
        """Fetch and aggregate OHLC candles for `entity_id`.

        Returns an empty list if the recorder is unavailable, the entity
        has no numeric history in the window, or aggregation produced no
        candles.
        """
        if self._recorder is None:
            return []
        now = dt_util.utcnow()
        start = now - timedelta(hours=hours)
        try:
            states = await self._recorder.async_add_executor_job(
                self._fetch_sync, entity_id, start, now
            )
        except Exception as err:
            _LOGGER.warning("Failed to fetch candlestick history for %s: %s", entity_id, err)
            return []
        if not states:
            return []
        timestamped = extract_timestamped_values(states)
        if not timestamped:
            return []
        return aggregate_ohlc(timestamped, interval_seconds, candle_count)
