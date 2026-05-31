"""Tests for firmware driver detection."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.const import MODEL_PRO, MODEL_SDPRO, MODEL_ULTRA
from custom_components.geekmagic.drivers import detect_driver
from custom_components.geekmagic.drivers.sdpro import SdProDriver
from custom_components.geekmagic.drivers.stock import StockDriver

BASE_URL = "http://192.168.1.50"
HOST = "192.168.1.50"


def _response(*, status: int = 200, json_value=None):
    """Build a mock aiohttp response usable as an async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_value)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock()
    return resp


def _session(route_map: dict):
    """Build a mock session whose .get returns responses keyed by path substring.

    ``route_map`` maps a path fragment to a response (or an Exception to raise).
    Unmatched paths raise to emulate an absent endpoint.
    """

    def _get(url, *args, **kwargs):
        for fragment, result in route_map.items():
            if fragment in url:
                if isinstance(result, Exception):
                    raise result
                return result
        raise AssertionError(f"unexpected request: {url}")

    session = MagicMock()
    session.get = MagicMock(side_effect=_get)
    return session


async def _provider(session):
    return session


@pytest.mark.asyncio
async def test_detect_pro_via_v_json():
    """A /v.json with 'PRO' in the model resolves to the Pro stock driver."""
    session = _session(
        {"/v.json": _response(json_value={"m": "GeekMagic SmallTV-PRO", "v": "V3.3.76EN"})}
    )
    driver = await detect_driver(HOST, BASE_URL, lambda: _provider(session))
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_PRO
    assert driver.firmware_version == "V3.3.76EN"
    assert driver.capabilities.supports_navigation is True


@pytest.mark.asyncio
async def test_detect_ultra_via_v_json():
    """A /v.json with 'Ultra' in the model resolves to the Ultra stock driver."""
    session = _session(
        {"/v.json": _response(json_value={"m": "SmallTV-Ultra", "v": "Ultra-V9.0.40"})}
    )
    driver = await detect_driver(HOST, BASE_URL, lambda: _provider(session))
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_ULTRA
    assert driver.capabilities.supports_navigation is False


@pytest.mark.asyncio
async def test_detect_sdpro_via_config():
    """No /v.json but a /config with theme+brightness resolves to SD_PRO."""
    session = _session(
        {
            "/v.json": _response(status=404),
            "/config": _response(json_value={"theme": 2, "brightness": 50, "freespace": 1000}),
        }
    )
    driver = await detect_driver(HOST, BASE_URL, lambda: _provider(session))
    assert isinstance(driver, SdProDriver)
    assert driver.model == MODEL_SDPRO
    assert driver.capabilities.supports_on_demand_image is False


@pytest.mark.asyncio
async def test_detect_legacy_pro_via_sys_app_json():
    """Old Pro firmware without /v.json falls back to the /.sys/app.json probe."""
    session = _session(
        {
            "/v.json": _response(status=404),
            "/config": _response(status=404),
            "/.sys/app.json": _response(status=200),
        }
    )
    driver = await detect_driver(HOST, BASE_URL, lambda: _provider(session))
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_PRO


@pytest.mark.asyncio
async def test_detect_defaults_to_ultra():
    """When nothing is identifiable, default to the Ultra stock driver."""
    session = _session(
        {
            "/v.json": _response(status=404),
            "/config": _response(status=404),
            "/.sys/app.json": _response(status=404),
            "/app.json": _response(status=404),
        }
    )
    driver = await detect_driver(HOST, BASE_URL, lambda: _provider(session))
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_ULTRA
