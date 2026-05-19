"""Tests for the history_fetcher module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.history_fetcher import (
    HistoryFetcher,
    extract_numeric_values,
)


class FakeState:
    def __init__(self, state: str) -> None:
        self.state = state


class TestExtractNumericValues:
    def test_numeric_strings_are_parsed(self):
        states = [FakeState("1"), FakeState("2.5"), FakeState("-3")]
        assert extract_numeric_values(states) == [1.0, 2.5, -3.0]

    def test_binary_on_states_become_1(self):
        states = [FakeState("on"), FakeState("OPEN"), FakeState("playing")]
        assert extract_numeric_values(states) == [1.0, 1.0, 1.0]

    def test_binary_off_states_become_0(self):
        states = [FakeState("off"), FakeState("Closed"), FakeState("IDLE")]
        assert extract_numeric_values(states) == [0.0, 0.0, 0.0]

    def test_non_numeric_non_binary_skipped(self):
        states = [FakeState("unavailable"), FakeState("unknown"), FakeState("hello")]
        assert extract_numeric_values(states) == []

    def test_none_state_skipped(self):
        states = [FakeState(None), FakeState("1")]  # type: ignore[arg-type]
        assert extract_numeric_values(states) == [1.0]

    def test_dict_minimal_response_format(self):
        states = [{"state": "5"}, {"state": "on"}, {"state": None}]
        assert extract_numeric_values(states) == [5.0, 1.0]

    def test_empty_list_returns_empty(self):
        assert extract_numeric_values([]) == []


class TestHistoryFetcher:
    @pytest.mark.asyncio
    async def test_fetch_numeric_returns_empty_when_recorder_unavailable(self):
        hass = MagicMock()
        with patch("homeassistant.components.recorder.get_instance", side_effect=KeyError):
            fetcher = HistoryFetcher(hass)
        assert not fetcher.available
        assert await fetcher.fetch_numeric("sensor.foo", 1) == []
        assert await fetcher.fetch_ohlc("sensor.foo", 1, 60, 10) == []

    @pytest.mark.asyncio
    async def test_fetch_numeric_returns_values_from_recorder(self):
        hass = MagicMock()

        recorder = MagicMock()
        recorder.async_add_executor_job = AsyncMock(
            return_value=[FakeState("1"), FakeState("2"), FakeState("on")]
        )

        with patch("homeassistant.components.recorder.get_instance", return_value=recorder):
            fetcher = HistoryFetcher(hass)

        result = await fetcher.fetch_numeric("sensor.foo", 1)
        assert result == [1.0, 2.0, 1.0]
        recorder.async_add_executor_job.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_numeric_swallows_executor_errors(self):
        hass = MagicMock()
        recorder = MagicMock()
        recorder.async_add_executor_job = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("homeassistant.components.recorder.get_instance", return_value=recorder):
            fetcher = HistoryFetcher(hass)

        assert await fetcher.fetch_numeric("sensor.foo", 1) == []

    @pytest.mark.asyncio
    async def test_fetch_ohlc_returns_empty_when_no_history(self):
        hass = MagicMock()
        recorder = MagicMock()
        recorder.async_add_executor_job = AsyncMock(return_value=[])
        with patch("homeassistant.components.recorder.get_instance", return_value=recorder):
            fetcher = HistoryFetcher(hass)

        assert await fetcher.fetch_ohlc("sensor.foo", 1, 60, 10) == []
