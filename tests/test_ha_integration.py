"""HA core-style integration tests for GeekMagic.

These tests mock only at the HTTP boundary (via aioclient_mock) and let
Home Assistant's real machinery run: config entry setup, platform forwarding,
entity registration, coordinator updates, and state management.

This tests the actual wiring — platform discovery, entity registration,
coordinator lifecycle — rather than testing classes in isolation.
"""

import re

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import DOMAIN

# Device host used across all tests
DEVICE_HOST = "192.168.1.100"
BASE_URL = f"http://{DEVICE_HOST}"


def setup_device_http_mocks(
    aioclient_mock,
    *,
    host: str = DEVICE_HOST,
    theme: int = 0,
    brightness: int = 50,
    total_storage: int = 1_048_576,
    free_storage: int = 524_288,
    model: str = "ultra",
) -> None:
    """Register all HTTP mocks needed for a GeekMagic device.

    Args:
        aioclient_mock: The aioclient mock fixture.
        host: Device IP address.
        theme: Device theme (0-2 = builtin, 3+ = custom).
            Use theme < 3 to skip rendering (fast tests).
        brightness: Device brightness (0-100).
        total_storage: Total storage bytes.
        free_storage: Free storage bytes.
        model: "ultra" or "pro" — controls /.sys/app.json response.
    """
    base = f"http://{host}"

    # Connection test (test_connection → get_space)
    aioclient_mock.get(
        f"{base}/space.json",
        json={"total": total_storage, "free": free_storage},
    )

    # Model detection
    if model == "pro":
        aioclient_mock.get(
            f"{base}/.sys/app.json",
            json={"theme": theme, "brt": brightness, "img": None},
        )
    else:
        aioclient_mock.get(f"{base}/.sys/app.json", status=404)

    # Device state
    aioclient_mock.get(
        f"{base}/app.json",
        json={"theme": theme, "brt": brightness, "img": "/image/dashboard.jpg"},
    )

    # Brightness poll
    aioclient_mock.get(f"{base}/brt.json", json={"brt": str(brightness)})

    # Upload image (POST)
    aioclient_mock.post(f"{base}/doUpload?dir=/image/", status=200)

    # Set commands (image, brightness, theme) — use regex to match any /set?...
    aioclient_mock.get(re.compile(rf"^{re.escape(base)}/set\?"), status=200)


def create_entry(
    *,
    host: str = DEVICE_HOST,
    title: str = "Test Display",
    options: dict | None = None,
) -> MockConfigEntry:
    """Create a MockConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={"host": host, "name": title},
        options=options or {},
    )


async def setup_integration(
    hass: HomeAssistant,
    aioclient_mock,
    *,
    theme: int = 0,
    model: str = "ultra",
    options: dict | None = None,
) -> MockConfigEntry:
    """Set up the integration with HTTP mocks and return the config entry.

    By default uses theme=0 (builtin mode) to skip rendering for speed.
    """
    setup_device_http_mocks(aioclient_mock, theme=theme, model=model)
    entry = create_entry(options=options)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


class TestSetupLifecycle:
    """Test the full integration setup and teardown lifecycle."""

    async def test_setup_loads_entry(self, hass: HomeAssistant, aioclient_mock):
        """Test that async_setup_entry loads successfully."""
        entry = await setup_integration(hass, aioclient_mock)
        assert entry.state is ConfigEntryState.LOADED

    async def test_setup_stores_coordinator(self, hass: HomeAssistant, aioclient_mock):
        """Test that the coordinator is stored in hass.data."""
        entry = await setup_integration(hass, aioclient_mock)
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]

    async def test_setup_connection_failure_raises_not_ready(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """Test that connection failure results in ConfigEntryNotReady."""
        base = f"http://{DEVICE_HOST}"
        aioclient_mock.get(
            f"{base}/space.json",
            exc=TimeoutError("Connection timed out"),
        )

        entry = create_entry()
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_RETRY

    async def test_setup_detects_ultra_model(self, hass: HomeAssistant, aioclient_mock):
        """Test that setup detects Ultra model when /.sys/app.json returns 404."""
        entry = await setup_integration(hass, aioclient_mock, model="ultra")

        from custom_components.geekmagic.coordinator import GeekMagicCoordinator

        coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.device.model == "ultra"

    async def test_setup_detects_pro_model(self, hass: HomeAssistant, aioclient_mock):
        """Test that setup detects Pro model when /.sys/app.json returns 200."""
        entry = await setup_integration(hass, aioclient_mock, model="pro")

        from custom_components.geekmagic.coordinator import GeekMagicCoordinator

        coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.device.model == "pro"

    async def test_unload_entry(self, hass: HomeAssistant, aioclient_mock):
        """Test that unloading an entry cleans up."""
        entry = await setup_integration(hass, aioclient_mock)
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


class TestEntityCreation:
    """Test that all expected entities are created with correct initial states."""

    @pytest.fixture
    async def loaded_entry(self, hass: HomeAssistant, aioclient_mock):
        """Set up the integration and return the entry."""
        return await setup_integration(hass, aioclient_mock)

    async def test_status_sensor(self, hass: HomeAssistant, loaded_entry):
        """Test status sensor shows Connected after successful setup."""
        state = hass.states.get("sensor.test_display_status")
        assert state is not None
        assert state.state == "Connected"

    async def test_brightness_number(self, hass: HomeAssistant, loaded_entry):
        """Test brightness number entity has correct initial value."""
        state = hass.states.get("number.test_display_brightness")
        assert state is not None
        assert state.state == "50"

    async def test_storage_used_sensor(self, hass: HomeAssistant, loaded_entry):
        """Test storage used sensor shows correct percentage."""
        state = hass.states.get("sensor.test_display_storage_used")
        assert state is not None
        # (1048576 - 524288) / 1048576 * 100 = 50.0
        assert float(state.state) == pytest.approx(50.0)

    async def test_storage_free_sensor(self, hass: HomeAssistant, loaded_entry):
        """Test storage free sensor shows correct value in KB."""
        state = hass.states.get("sensor.test_display_storage_free")
        assert state is not None
        # 524288 / 1024 = 512.0
        assert float(state.state) == pytest.approx(512.0)

    async def test_view_cycling_switch(self, hass: HomeAssistant, loaded_entry):
        """Test view cycling switch is off by default (cycle_interval=0)."""
        state = hass.states.get("switch.test_display_view_cycling")
        assert state is not None
        assert state.state == "off"

    async def test_display_select(self, hass: HomeAssistant, loaded_entry):
        """Test display select entity exists."""
        state = hass.states.get("select.test_display_display")
        assert state is not None

    async def test_rotation_select(self, hass: HomeAssistant, loaded_entry):
        """Test display rotation select entity exists."""
        state = hass.states.get("select.test_display_display_rotation")
        assert state is not None

    async def test_refresh_button(self, hass: HomeAssistant, loaded_entry):
        """Test refresh button entity exists."""
        # Button entities don't have meaningful state, just check existence
        state = hass.states.get("button.test_display_refresh_display")
        assert state is not None

    async def test_next_screen_button(self, hass: HomeAssistant, loaded_entry):
        """Test next screen button entity exists."""
        state = hass.states.get("button.test_display_next_screen")
        assert state is not None

    async def test_previous_screen_button(self, hass: HomeAssistant, loaded_entry):
        """Test previous screen button entity exists."""
        state = hass.states.get("button.test_display_previous_screen")
        assert state is not None

    async def test_refresh_interval_number(self, hass: HomeAssistant, loaded_entry):
        """Test refresh interval number entity exists."""
        state = hass.states.get("number.test_display_refresh_interval")
        assert state is not None

    async def test_image_quality_number(self, hass: HomeAssistant, loaded_entry):
        """Test JPEG quality number entity exists."""
        state = hass.states.get("number.test_display_image_quality")
        assert state is not None

    async def test_cycle_interval_number(self, hass: HomeAssistant, loaded_entry):
        """Test view cycle interval number entity exists."""
        state = hass.states.get("number.test_display_view_cycle_interval")
        assert state is not None

    async def test_image_entity(self, hass: HomeAssistant, loaded_entry):
        """Test image preview entity exists."""
        state = hass.states.get("image.test_display_display_preview")
        assert state is not None


class TestEntityInteractions:
    """Test that entity state changes trigger correct HTTP calls."""

    async def test_brightness_change(self, hass: HomeAssistant, aioclient_mock):
        """Test changing brightness sends HTTP request to device."""
        await setup_integration(hass, aioclient_mock)

        # Change brightness via HA service
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.test_display_brightness", "value": 75},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Verify HTTP call was made to the device
        calls = [
            (method, url) for method, url, *_ in aioclient_mock.mock_calls if "brt" in str(url)
        ]
        assert len(calls) > 0, f"Expected brightness HTTP call, got: {aioclient_mock.mock_calls}"

    async def test_select_builtin_mode(self, hass: HomeAssistant, aioclient_mock):
        """Test selecting a builtin display mode sends theme HTTP request."""
        await setup_integration(hass, aioclient_mock)

        state = hass.states.get("select.test_display_display")
        if state is None:
            pytest.skip("Display select entity not found")

        # Try selecting a builtin mode
        options = state.attributes.get("options", [])
        builtin_options = [o for o in options if o not in ("Custom", "custom")]
        if not builtin_options:
            pytest.skip("No builtin options available")

        await hass.services.async_call(
            "select",
            "select_option",
            {
                "entity_id": "select.test_display_display",
                "option": builtin_options[0],
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        # Verify theme HTTP call was made
        calls = [
            (method, url) for method, url, *_ in aioclient_mock.mock_calls if "theme" in str(url)
        ]
        assert len(calls) > 0, f"Expected theme HTTP call, got: {aioclient_mock.mock_calls}"


class TestFullRenderPipeline:
    """Test the full render + upload pipeline with custom theme."""

    async def test_custom_mode_renders_and_uploads(self, hass: HomeAssistant, aioclient_mock):
        """Test that custom mode (theme=3) renders an image and uploads it."""
        await setup_integration(hass, aioclient_mock, theme=3)

        # In custom mode, the coordinator should have rendered and uploaded
        upload_calls = [
            (method, url)
            for method, url, *_ in aioclient_mock.mock_calls
            if method.upper() == "POST" and "doUpload" in str(url)
        ]
        assert len(upload_calls) > 0, (
            f"Expected upload call in custom mode, got: {aioclient_mock.mock_calls}"
        )

        # Should also have set the image
        set_img_calls = [
            (method, url)
            for method, url, *_ in aioclient_mock.mock_calls
            if method.upper() == "GET" and "set" in str(url) and "img" in str(url)
        ]
        assert len(set_img_calls) > 0, "Expected set image call after upload"


class TestCoordinatorUpdate:
    """Test coordinator refresh cycles."""

    async def test_manual_refresh_via_button(self, hass: HomeAssistant, aioclient_mock):
        """Test that pressing the refresh button triggers a coordinator update."""
        await setup_integration(hass, aioclient_mock)

        initial_call_count = aioclient_mock.call_count

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_display_refresh_display"},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Refresh should have made additional HTTP calls
        assert aioclient_mock.call_count > initial_call_count, (
            "Expected additional HTTP calls after refresh button press"
        )


class TestDeviceRegistry:
    """Test device registry integration."""

    async def test_device_registered(self, hass: HomeAssistant, aioclient_mock):
        """Test that a device is registered in the device registry."""
        from homeassistant.helpers import device_registry as dr

        entry = await setup_integration(hass, aioclient_mock)

        dev_reg = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        assert len(devices) >= 1

        # Find the GeekMagic device
        geekmagic_devices = [d for d in devices if d.manufacturer == "GeekMagic"]
        assert len(geekmagic_devices) >= 1
        assert "Test Display" in (geekmagic_devices[0].name or "")

    async def test_device_model_name(self, hass: HomeAssistant, aioclient_mock):
        """Test that the device model name reflects the detected model."""
        from homeassistant.helpers import device_registry as dr

        entry = await setup_integration(hass, aioclient_mock, model="ultra")

        dev_reg = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        geekmagic_devices = [d for d in devices if d.manufacturer == "GeekMagic"]
        assert len(geekmagic_devices) >= 1
        # The main device (identified by entry_id) should have the detected model
        main_device = [d for d in geekmagic_devices if (DOMAIN, entry.entry_id) in d.identifiers]
        assert len(main_device) == 1
        assert "Ultra" in (main_device[0].model or "")


class TestOptionsUpdate:
    """Test that options updates propagate correctly."""

    async def test_options_update_reloads_entry(self, hass: HomeAssistant, aioclient_mock):
        """Test that changing options triggers entry reload."""
        entry = await setup_integration(hass, aioclient_mock)
        assert entry.state is ConfigEntryState.LOADED

        # Update options — this should trigger the update listener
        # which reloads the entry
        hass.config_entries.async_update_entry(
            entry,
            options={"refresh_interval": 30},
        )
        await hass.async_block_till_done()

        # Entry should still be loaded (reloaded successfully)
        # Note: The reload re-runs setup, so we need enough mocks for a second setup.
        # Since aioclient_mock keeps mocks registered, this should work.
        assert entry.state is ConfigEntryState.LOADED
