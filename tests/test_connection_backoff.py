"""Tests for the connection_backoff module."""

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import MagicMock

from custom_components.geekmagic.connection_backoff import ConnectionBackoff


def _make_backoff(base: int = 10, max_mult: int = 16, log_interval: int = 30):
    logger = MagicMock(spec=logging.Logger)
    return ConnectionBackoff(
        logger=logger,
        base_interval_seconds=base,
        max_multiplier=max_mult,
        log_interval=log_interval,
    )


class TestState:
    def test_initial_state(self):
        b = _make_backoff()
        assert b.failure_count == 0
        assert b.is_offline is False
        assert b.base_interval == 10

    def test_base_interval_is_settable(self):
        b = _make_backoff()
        b.base_interval = 30
        assert b.base_interval == 30


class TestRecordFailure:
    def test_exponential_progression(self):
        b = _make_backoff(base=10)
        assert b.record_failure() == timedelta(seconds=20)
        assert b.record_failure() == timedelta(seconds=40)
        assert b.record_failure() == timedelta(seconds=80)
        assert b.record_failure() == timedelta(seconds=160)

    def test_capped_at_max_multiplier(self):
        b = _make_backoff(base=10, max_mult=16)
        for _ in range(100):
            interval = b.record_failure()
        assert interval == timedelta(seconds=160)  # 10 * 16

    def test_failure_marks_offline(self):
        b = _make_backoff()
        b.record_failure()
        assert b.is_offline is True
        assert b.failure_count == 1


class TestRecordSuccess:
    def test_success_resets_state(self):
        b = _make_backoff(base=10)
        for _ in range(5):
            b.record_failure()
        assert b.is_offline is True

        interval = b.record_success()
        assert interval == timedelta(seconds=10)
        assert b.failure_count == 0
        assert b.is_offline is False


class TestLogging:
    def test_first_failure_logs_warning(self):
        b = _make_backoff()
        b.record_failure()
        b._logger.reset_mock()
        b.log_failure("host", "boom", 20)
        b._logger.warning.assert_called_once()
        b._logger.debug.assert_not_called()

    def test_subsequent_failure_logs_debug(self):
        b = _make_backoff(log_interval=30)
        b.record_failure()
        b.record_failure()  # second failure
        b._logger.reset_mock()
        b.log_failure("host", "boom", 40)
        b._logger.debug.assert_called_once()
        b._logger.warning.assert_not_called()

    def test_periodic_summary_logs_warning(self):
        b = _make_backoff(log_interval=5)
        # 5 failures = periodic summary
        for _ in range(5):
            b.record_failure()
        b._logger.reset_mock()
        b.log_failure("host", "boom", 160)
        b._logger.warning.assert_called_once()
        b._logger.debug.assert_not_called()

    def test_log_connection_error_first_failure_warns(self):
        b = _make_backoff()
        b.record_failure()
        b._logger.reset_mock()
        b.log_connection_error("host", Exception("boom"), 20)
        b._logger.warning.assert_called_once()

    def test_log_connection_error_subsequent_debug(self):
        b = _make_backoff(log_interval=30)
        b.record_failure()
        b.record_failure()
        b._logger.reset_mock()
        b.log_connection_error("host", Exception("boom"), 40)
        b._logger.debug.assert_called_once()
        b._logger.warning.assert_not_called()
