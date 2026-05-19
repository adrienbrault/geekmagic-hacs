"""Exponential backoff + smart logging for an unreliable connection.

Wraps three things the coordinator used to manage by hand: a consecutive-
failure counter, the exponential interval calculation, and the
"first failure WARN, periodic WARN, otherwise DEBUG" log cadence.

Used by the coordinator only today; kept as a separate module because the
state machine + logging cadence is one cohesive concept that the update
loop benefits from not having to spell out inline.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging


class ConnectionBackoff:
    """Tracks consecutive failures and produces the next update interval.

    The state machine:
      - On success: counter resets, interval returns to base.
      - On failure: counter increments; interval = base * 2**counter,
        capped at base * max_multiplier.
      - Logging cadence is offloaded to `log_failure`: WARN on the first
        failure and every Nth thereafter, DEBUG otherwise.
    """

    def __init__(
        self,
        logger: logging.Logger,
        base_interval_seconds: int,
        max_multiplier: int,
        log_interval: int,
    ) -> None:
        self._logger = logger
        self._base_interval = base_interval_seconds
        self._max_multiplier = max_multiplier
        self._log_interval = log_interval
        self._failures = 0
        self._offline = False

    @property
    def base_interval(self) -> int:
        return self._base_interval

    @base_interval.setter
    def base_interval(self, value: int) -> None:
        self._base_interval = value

    @property
    def failure_count(self) -> int:
        return self._failures

    @property
    def is_offline(self) -> bool:
        return self._offline

    def record_failure(self) -> timedelta:
        """Record a failure and return the next update interval to use."""
        self._failures += 1
        self._offline = True
        multiplier = min(2 ** min(self._failures, 10), self._max_multiplier)
        next_seconds = self._base_interval * multiplier
        self._logger.debug(
            "Applied backoff: interval=%ds (multiplier=%dx, failures=%d)",
            next_seconds,
            multiplier,
            self._failures,
        )
        return timedelta(seconds=next_seconds)

    def record_success(self) -> timedelta:
        """Mark the connection as healthy and return the base update interval."""
        self._failures = 0
        self._offline = False
        return timedelta(seconds=self._base_interval)

    def log_failure(self, host: str, message: str, current_interval_seconds: int) -> None:
        """Emit an appropriately verbose log line for the latest failure.

        WARN on the first failure (full context), WARN at every Nth
        subsequent failure (periodic summary), DEBUG otherwise to keep
        long-running offline devices from spamming the log.
        """
        if self._failures == 1:
            self._logger.warning(
                "GeekMagic device %s is offline: %s. Will retry with exponential backoff.",
                host,
                message,
            )
        elif self._failures % self._log_interval == 0:
            self._logger.warning(
                "GeekMagic device %s still offline after %d attempts (retry interval: %ds)",
                host,
                self._failures,
                current_interval_seconds,
            )
        else:
            self._logger.debug(
                "GeekMagic device %s offline (attempt %d): %s",
                host,
                self._failures,
                message,
            )

    def log_connection_error(
        self, host: str, err: BaseException, current_interval_seconds: int
    ) -> None:
        """Like log_failure but for unexpected exceptions during an update."""
        if self._failures == 1:
            self._logger.warning(
                "GeekMagic device %s connection failed: %s. Will retry with exponential backoff.",
                host,
                err,
            )
        elif self._failures % self._log_interval == 0:
            self._logger.warning(
                "GeekMagic device %s still failing after %d attempts: %s (retry interval: %ds)",
                host,
                self._failures,
                err,
                current_interval_seconds,
            )
        else:
            self._logger.debug(
                "GeekMagic update failed (attempt %d): %s",
                self._failures,
                err,
            )
