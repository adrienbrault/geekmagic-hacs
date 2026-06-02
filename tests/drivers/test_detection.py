"""Tests for the firmware detection factory."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.const import (
    MODEL_PRO,
    MODEL_SDPRO,
    MODEL_ULTRA,
)
from custom_components.geekmagic.drivers import detect_driver
from custom_components.geekmagic.drivers.sdpro import SDProDriver
from custom_components.geekmagic.drivers.stock import StockDriver


def _make_response(*, status=200, json_data=None):
    response = MagicMock()
    response.status = status
    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _make_session(handlers):
    """`handlers` maps URL substring -> a pre-built response (MagicMock)."""

    session = MagicMock()

    def _get(url, **_kwargs):
        for needle, response in handlers.items():
            if needle in url:
                return response
        return _make_response(status=404)

    session.get = _get
    return session


@pytest.mark.asyncio
async def test_detects_stock_pro_from_v_json():
    session = _make_session(
        {"/v.json": _make_response(json_data={"m": "GeekMagic SmallTV-PRO", "v": "V3.3.76EN"})}
    )
    driver = await detect_driver("http://10.0.0.1", session)
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_PRO
    assert driver.sw_version == "V3.3.76EN"
    assert driver.custom_image_theme == 4
    assert driver.supports_navigation is True


@pytest.mark.asyncio
async def test_detects_stock_ultra_from_v_json():
    session = _make_session(
        {"/v.json": _make_response(json_data={"m": "SmallTV-Ultra", "v": "Ultra-V9.0.40"})}
    )
    driver = await detect_driver("http://10.0.0.1", session)
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_ULTRA
    assert driver.sw_version == "Ultra-V9.0.40"
    assert driver.custom_image_theme == 3
    assert driver.supports_navigation is False


@pytest.mark.asyncio
async def test_detects_sdpro_when_v_json_missing():
    session = _make_session(
        {"/config": _make_response(json_data={"brightness": 50, "freespace": 1024, "theme": 0})}
    )
    driver = await detect_driver("http://10.0.0.1", session)
    assert isinstance(driver, SDProDriver)
    assert driver.model == MODEL_SDPRO


@pytest.mark.asyncio
async def test_falls_back_to_legacy_app_json():
    session = _make_session({"/app.json": _make_response(json_data={"theme": 3})})
    driver = await detect_driver("http://10.0.0.1", session)
    assert isinstance(driver, StockDriver)
    assert driver.model == MODEL_ULTRA
    assert driver.sw_version is None


@pytest.mark.asyncio
async def test_returns_none_when_all_probes_fail():
    session = _make_session({})  # everything 404s
    driver = await detect_driver("http://10.0.0.1", session)
    assert driver is None


@pytest.mark.asyncio
async def test_config_without_sdpro_fingerprint_is_ignored():
    """A /config endpoint that doesn't look like SD_PRO falls through."""
    session = _make_session({"/config": _make_response(json_data={"something_else": True})})
    driver = await detect_driver("http://10.0.0.1", session)
    assert driver is None
