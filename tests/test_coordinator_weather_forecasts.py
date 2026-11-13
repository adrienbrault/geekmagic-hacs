"""Tests for the weather forecast pre-fetch on the coordinator.

weather.get_forecasts is an action, and HA 2026.11+ lists every action call
in its action history. Calling it on every render tick (every ~10s) flooded
that history (issue #224), so forecasts are cached per entity.
"""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import ServiceCall, SupportsResponse

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
    WEATHER_FORECAST_RETRY,
    WEATHER_FORECAST_TTL,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator

WEATHER_ENTITY = "weather.home"
FORECAST = [{"datetime": "2026-11-14T12:00:00+00:00", "temperature": 12, "templow": 4}]


class FakeClock:
    """Stand-in for time.monotonic that tests advance by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    """Patch the coordinator's monotonic clock."""
    fake = FakeClock()
    with patch("custom_components.geekmagic.coordinator.time.monotonic", fake):
        yield fake


@pytest.fixture
def forecast_service(hass):
    """Register a fake weather.get_forecasts that records its calls."""
    calls: list[ServiceCall] = []
    behaviour = {"fail": False}

    async def handler(call: ServiceCall):
        calls.append(call)
        if behaviour["fail"]:
            raise RuntimeError("forecast type not supported")
        return {WEATHER_ENTITY: {"forecast": FORECAST}}

    hass.services.async_register(
        "weather", "get_forecasts", handler, supports_response=SupportsResponse.ONLY
    )
    return calls, behaviour


def _coordinator(hass, *, show_forecast: bool = True) -> GeekMagicCoordinator:
    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_SCREENS: [
            {
                "name": "Weather",
                CONF_LAYOUT: LAYOUT_FULLSCREEN,
                CONF_WIDGETS: [
                    {
                        "type": "weather",
                        "slot": 0,
                        "entity_id": WEATHER_ENTITY,
                        "options": {"show_forecast": show_forecast},
                    },
                ],
            }
        ],
    }
    return GeekMagicCoordinator(hass, MagicMock(), options)


async def test_forecast_cached_between_renders(hass, clock, forecast_service):
    """Back-to-back renders make one action call and keep serving the forecast."""
    calls, _ = forecast_service
    hass.states.async_set(WEATHER_ENTITY, "sunny")
    coord = _coordinator(hass)

    await coord._async_fetch_weather_forecasts()
    clock.now += 10  # next render tick
    await coord._async_fetch_weather_forecasts()

    assert len(calls) == 1
    assert coord._weather_forecasts[WEATHER_ENTITY] == FORECAST


async def test_forecast_refetched_after_ttl(hass, clock, forecast_service):
    """Once the TTL elapses the forecast is fetched again."""
    calls, _ = forecast_service
    hass.states.async_set(WEATHER_ENTITY, "sunny")
    coord = _coordinator(hass)

    await coord._async_fetch_weather_forecasts()
    clock.now += WEATHER_FORECAST_TTL
    await coord._async_fetch_weather_forecasts()

    assert len(calls) == 2


async def test_failed_fetch_backs_off_and_keeps_last_forecast(hass, clock, forecast_service):
    """A failing action is not retried every tick, and the good forecast stays."""
    calls, behaviour = forecast_service
    hass.states.async_set(WEATHER_ENTITY, "sunny")
    coord = _coordinator(hass)

    await coord._async_fetch_weather_forecasts()
    clock.now += WEATHER_FORECAST_TTL
    behaviour["fail"] = True
    await coord._async_fetch_weather_forecasts()  # fails
    clock.now += 10
    await coord._async_fetch_weather_forecasts()  # within retry window: skipped

    assert len(calls) == 2
    assert coord._weather_forecasts[WEATHER_ENTITY] == FORECAST

    clock.now += WEATHER_FORECAST_RETRY
    behaviour["fail"] = False
    await coord._async_fetch_weather_forecasts()
    assert len(calls) == 3


async def test_no_fetch_when_forecast_hidden(hass, clock, forecast_service):
    """A weather widget with show_forecast off never calls the action."""
    calls, _ = forecast_service
    hass.states.async_set(WEATHER_ENTITY, "sunny")
    coord = _coordinator(hass, show_forecast=False)

    await coord._async_fetch_weather_forecasts()

    assert calls == []


@pytest.mark.parametrize("initial_state", [None, STATE_UNAVAILABLE])
async def test_missing_entity_fetched_once_it_appears(hass, clock, forecast_service, initial_state):
    """No call while the entity is missing/unavailable; fetch as soon as it loads."""
    calls, _ = forecast_service
    if initial_state is not None:
        hass.states.async_set(WEATHER_ENTITY, initial_state)
    coord = _coordinator(hass)

    await coord._async_fetch_weather_forecasts()
    assert calls == []

    hass.states.async_set(WEATHER_ENTITY, "sunny")
    clock.now += 10
    await coord._async_fetch_weather_forecasts()
    assert len(calls) == 1


async def test_options_update_bypasses_cache(hass, clock, forecast_service):
    """A config change fetches the forecast again on the next render."""
    calls, _ = forecast_service
    hass.states.async_set(WEATHER_ENTITY, "sunny")
    coord = _coordinator(hass)

    await coord._async_fetch_weather_forecasts()
    coord.update_options(coord.options)
    await coord._async_fetch_weather_forecasts()

    assert len(calls) == 2
