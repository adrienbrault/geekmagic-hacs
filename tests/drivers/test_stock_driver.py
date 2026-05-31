"""Tests for the stock firmware driver (Pro and Ultra variants)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.drivers.stock import PRO, ULTRA, StockDriver

BASE_URL = "http://192.168.1.50"
HOST = "192.168.1.50"


@pytest.fixture
def response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock()
    return resp


@pytest.fixture
def session(response):
    sess = MagicMock()
    sess.get = MagicMock(return_value=response)
    sess.post = MagicMock(return_value=response)
    return sess


def _driver(variant, session):
    return StockDriver(variant, HOST, BASE_URL, AsyncMock(return_value=session))


@pytest.mark.asyncio
async def test_pro_uses_picture_theme(session):
    """Pro custom mode must select theme 4 (Picture), not 3 (Weather)."""
    driver = _driver(PRO, session)
    await driver.set_theme_custom()
    session.get.assert_called_with(f"{BASE_URL}/set?theme=4")


@pytest.mark.asyncio
async def test_ultra_uses_photo_album_theme(session):
    """Ultra custom mode selects theme 3 (Photo Album)."""
    driver = _driver(ULTRA, session)
    await driver.set_theme_custom()
    session.get.assert_called_with(f"{BASE_URL}/set?theme=3")


def test_builtin_modes_are_per_firmware():
    """Pro and Ultra expose different built-in theme maps, excluding custom."""
    pro_modes = PRO.capabilities.builtin_modes
    ultra_modes = ULTRA.capabilities.builtin_modes

    # Custom theme is never offered as a built-in mode.
    assert PRO.capabilities.custom_theme == 4
    assert 4 not in pro_modes.values()
    assert ULTRA.capabilities.custom_theme == 3
    assert 3 not in ultra_modes.values()

    # Pro's theme numbers differ from Ultra's (per the device reports).
    assert pro_modes["Weather"] == 3
    assert pro_modes["Clock"] == 6
    assert ultra_modes["Weather Clock Today"] == 1
    # The two maps are genuinely distinct, not a shared global table.
    assert pro_modes != ultra_modes


@pytest.mark.asyncio
async def test_pro_reads_brightness_from_sys_path(session, response):
    """Pro reads brightness from /.sys/brt.json."""
    response.json = AsyncMock(return_value={"brt": "85"})
    driver = _driver(PRO, session)
    brightness = await driver.get_brightness()
    assert brightness == 85
    session.get.assert_called_once_with(f"{BASE_URL}/.sys/brt.json")


@pytest.mark.asyncio
async def test_ultra_reads_brightness_from_root_path(session, response):
    """Ultra reads brightness from /brt.json."""
    response.json = AsyncMock(return_value={"brt": "71"})
    driver = _driver(ULTRA, session)
    brightness = await driver.get_brightness()
    assert brightness == 71
    session.get.assert_called_once_with(f"{BASE_URL}/brt.json")


@pytest.mark.asyncio
async def test_pro_get_state_makes_no_request(session):
    """Pro has no /app.json, so get_state returns a null state without a call."""
    driver = _driver(PRO, session)
    state = await driver.get_state()
    assert state.theme is None
    assert state.brightness is None
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_ultra_get_state_reads_app_json(session, response):
    """Ultra reads theme from /app.json."""
    response.json = AsyncMock(return_value={"theme": 3})
    driver = _driver(ULTRA, session)
    state = await driver.get_state()
    assert state.theme == 3
    session.get.assert_called_once_with(f"{BASE_URL}/app.json")
