"""Tests for shared model helpers."""

from __future__ import annotations

import pytest

from custom_components.geekmagic.models import brightness_from_percent, brightness_to_percent


@pytest.mark.parametrize(
    ("percent", "brightness_range", "raw"),
    [
        (0, (0, 255), 0),
        (50, (0, 255), 128),
        (80, (0, 255), 204),
        (100, (0, 255), 255),
        (150, (0, 255), 255),
        (-5, (0, 255), 0),
        (0, (2, 99), 2),
        (1, (2, 99), 2),
        (50, (2, 99), 50),
        (100, (2, 99), 99),
        (75, (0, 100), 75),
        (74.6, (0, 100), 75),
    ],
)
def test_brightness_from_percent(percent, brightness_range, raw) -> None:
    """Percentages map linearly onto the firmware range, clamped."""
    assert brightness_from_percent(percent, brightness_range) == raw


@pytest.mark.parametrize(
    ("raw", "brightness_range", "percent"),
    [
        (0, (0, 255), 0),
        (204, (0, 255), 80),
        (255, (0, 255), 100),
        (400, (0, 255), 100),
        (-10, (0, 255), 0),
        (2, (2, 99), 2),
        (50, (2, 99), 50),
        (99, (2, 99), 99),
        (50, (0, 100), 50),
        (0, (0, 0), 0),
    ],
)
def test_brightness_to_percent(raw, brightness_range, percent) -> None:
    """Ranges past 100 scale; ranges inside 0-100 pass through, clamped."""
    assert brightness_to_percent(raw, brightness_range) == percent


def test_brightness_round_trip_on_ultra_range() -> None:
    """Every slider percentage survives a round trip through the raw value."""
    for percent in range(101):
        raw = brightness_from_percent(percent, (0, 255))
        assert brightness_to_percent(raw, (0, 255)) == percent


@pytest.mark.parametrize("brightness_range", [(2, 99), (0, 100)])
def test_percent_ranges_round_trip(brightness_range) -> None:
    """Firmware that already speaks percent never moves the slider on a set."""
    low, high = brightness_range
    for percent in range(low, high + 1):
        raw = brightness_from_percent(percent, brightness_range)
        assert raw == percent
        assert brightness_to_percent(raw, brightness_range) == percent
