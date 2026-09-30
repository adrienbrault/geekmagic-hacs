"""Setup keeps the stored firmware profile when detection is inconclusive."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import (
    CONF_FIRMWARE_VERSION,
    CONF_MODEL_NAME,
    CONF_PROFILE_ID,
    DOMAIN,
    MODEL_PRO,
    MODEL_ULTRA,
)
from custom_components.geekmagic.profiles import (
    StockProProfile,
    StockUltraProfile,
    UnknownStockProfile,
)

from .test_ha_integration import DEVICE_HOST, setup_device_http_mocks

STORED = {
    CONF_PROFILE_ID: MODEL_PRO,
    CONF_MODEL_NAME: "SmallTV-PRO",
    CONF_FIRMWARE_VERSION: "V3.4.82EN",
}


async def _setup_with_detection(hass: HomeAssistant, aioclient_mock, detected) -> MockConfigEntry:
    setup_device_http_mocks(aioclient_mock, model="pro")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Display",
        data={"host": DEVICE_HOST, "name": "Test Display", **STORED},
    )
    entry.add_to_hass(hass)

    async def fake_detect(transport):
        return detected(transport)

    with patch("custom_components.geekmagic.device.detect_firmware_profile", fake_detect):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_inconclusive_detection_keeps_stored_profile(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A slow boot that defeats the 5s probes must not downgrade a known Pro."""
    entry = await _setup_with_detection(hass, aioclient_mock, UnknownStockProfile)

    assert {key: entry.data[key] for key in STORED} == STORED
    device = hass.data[DOMAIN][entry.entry_id].device
    assert device.model == MODEL_PRO
    assert device.firmware_version == "V3.4.82EN"


async def test_detection_without_version_keeps_stored_version(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Detecting the same profile through a path without a version keeps the known one."""
    entry = await _setup_with_detection(
        hass, aioclient_mock, lambda t: StockProProfile(t, model_name="SmallTV-PRO")
    )

    assert entry.data[CONF_FIRMWARE_VERSION] == "V3.4.82EN"


async def test_conclusive_detection_still_wins(hass: HomeAssistant, aioclient_mock) -> None:
    """A device that really changed firmware is re-profiled."""
    entry = await _setup_with_detection(
        hass, aioclient_mock, lambda t: StockUltraProfile(t, model_name="SmallTV Ultra")
    )

    assert entry.data[CONF_PROFILE_ID] == MODEL_ULTRA
    assert entry.data[CONF_MODEL_NAME] == "SmallTV Ultra"
    assert entry.data[CONF_FIRMWARE_VERSION] is None
