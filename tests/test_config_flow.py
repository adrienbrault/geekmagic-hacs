"""Tests for GeekMagic config flow.

Uses aioclient_mock to mock HTTP responses at the boundary, letting the
real GeekMagicDevice client run inside the config flow.
"""

import re

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.geekmagic.config_flow import (
    GeekMagicConfigFlow,
    GeekMagicOptionsFlow,
)
from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
)

# Base URL for mocked device
DEVICE_HOST = "192.168.1.100"
BASE_URL = f"http://{DEVICE_HOST}"


def _mock_device_success(aioclient_mock, host: str = DEVICE_HOST):
    """Mock HTTP endpoints for a successful device connection (stock Ultra)."""
    base = f"http://{host}"
    # Firmware identification — drives detect_driver
    aioclient_mock.get(f"{base}/v.json", json={"m": "SmallTV-Ultra", "v": "Ultra-V9.0.40"})
    # Connection probe and storage info
    aioclient_mock.get(f"{base}/space.json", json={"total": 1048576, "free": 524288})
    # Device state, brightness
    aioclient_mock.get(f"{base}/app.json", json={"theme": 0, "brt": 50, "img": None})
    aioclient_mock.get(f"{base}/brt.json", json={"brt": "50"})
    # Upload + /set?... commands (for full setup after entry creation)
    aioclient_mock.post(f"{base}/doUpload?dir=/image/", status=200)
    aioclient_mock.get(re.compile(rf"^{re.escape(base)}/set\?"), status=200)


class TestConfigFlowImports:
    """Test that config flow can be imported without errors."""

    def test_import_config_flow(self):
        """Test config flow module imports successfully."""
        from custom_components.geekmagic import config_flow

        assert config_flow.GeekMagicConfigFlow is not None
        assert config_flow.GeekMagicOptionsFlow is not None

    def test_config_flow_class_attributes(self):
        """Test GeekMagicConfigFlow has required attributes."""
        assert hasattr(GeekMagicConfigFlow, "VERSION")
        assert hasattr(GeekMagicConfigFlow, "async_step_user")
        assert hasattr(GeekMagicConfigFlow, "async_get_options_flow")


class TestConfigFlowUser:
    """Test user config flow step with real device client via aioclient_mock."""

    async def test_user_flow_shows_form(self, hass: HomeAssistant):
        """Test that user flow shows the configuration form."""
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        data_schema = result["data_schema"]
        assert data_schema is not None
        assert "host" in data_schema.schema

    async def test_user_flow_connection_timeout(self, hass: HomeAssistant, aioclient_mock):
        """Test user flow shows timeout error when device times out."""
        aioclient_mock.get(
            f"{BASE_URL}/v.json",
            exc=TimeoutError("Connection timed out"),
        )

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "Test Display"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "timeout"}

    async def test_user_flow_connection_refused(self, hass: HomeAssistant, aioclient_mock):
        """Test user flow shows connection refused error."""
        aioclient_mock.get(
            f"{BASE_URL}/v.json",
            exc=OSError("Connection refused"),
        )

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "Test Display"},
        )

        assert result["type"] == FlowResultType.FORM
        # OSError is caught by the generic except → "unknown"
        errors = result["errors"]
        assert errors is not None
        assert errors["base"] in ("connection_refused", "unknown")

    async def test_sdpro_flow_shows_confirm_step_and_disables_themes(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """SD_PRO firmware setup pauses to confirm + disable built-in themes."""
        base = f"http://{DEVICE_HOST}"
        # /v.json 404 so detection falls through to /config (SD_PRO fingerprint)
        aioclient_mock.get(f"{base}/v.json", status=404)
        aioclient_mock.get(
            f"{base}/config",
            json={"theme": 0, "brightness": 50, "freespace": 1024 * 1024},
        )
        # Confirm-step preview of currently-enabled themes
        aioclient_mock.get(
            f"{base}/theme/list",
            json={
                "interval": 10,
                "themes": [
                    {"id": 0, "name": "Classic", "enabled": True},
                    {"id": 1, "name": "Weather", "enabled": True},
                    {"id": 2, "name": "Photo", "enabled": True},
                ],
            },
        )
        # Toggle endpoint (matches anything under /theme/toggle)
        aioclient_mock.get(re.compile(rf"^{re.escape(base)}/theme/toggle\?"), status=200)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "SD_PRO Display"},
        )

        # Should show the SD_PRO confirmation form, not create the entry yet.
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "sdpro_confirm"

        # Confirm with default (disable themes)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"disable_other_themes": True},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "SD_PRO Display"

        # Confirm the two non-Photo themes were disabled via /theme/toggle
        toggle_urls = [
            str(call[1]) for call in aioclient_mock.mock_calls if "/theme/toggle" in str(call[1])
        ]
        assert any("id=0" in url and "state=0" in url for url in toggle_urls)
        assert any("id=1" in url and "state=0" in url for url in toggle_urls)
        # Photo theme (id=2) must NOT be disabled
        assert not any("id=2" in url and "state=0" in url for url in toggle_urls)

    async def test_sdpro_flow_skips_theme_disable_when_unchecked(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """If the user unchecks the box, no /theme/toggle calls are made."""
        base = f"http://{DEVICE_HOST}"
        aioclient_mock.get(f"{base}/v.json", status=404)
        aioclient_mock.get(
            f"{base}/config",
            json={"theme": 0, "brightness": 50, "freespace": 1024 * 1024},
        )
        aioclient_mock.get(
            f"{base}/theme/list",
            json={
                "themes": [
                    {"id": 0, "name": "Classic", "enabled": True},
                    {"id": 2, "name": "Photo", "enabled": True},
                ],
            },
        )
        aioclient_mock.get(re.compile(rf"^{re.escape(base)}/theme/toggle\?"), status=200)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "SD_PRO Display"},
        )
        assert result["step_id"] == "sdpro_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"disable_other_themes": False},
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY

        toggle_urls = [
            str(call[1]) for call in aioclient_mock.mock_calls if "/theme/toggle" in str(call[1])
        ]
        assert toggle_urls == []

    async def test_user_flow_success(self, hass: HomeAssistant, aioclient_mock):
        """Test successful user flow creates entry with default options."""
        _mock_device_success(aioclient_mock)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "Test Display"},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Display"
        assert result["data"]["host"] == DEVICE_HOST

        # Check default options were created
        assert CONF_SCREENS in result["options"]
        assert CONF_REFRESH_INTERVAL in result["options"]
        assert CONF_SCREEN_CYCLE_INTERVAL in result["options"]

    async def test_user_flow_success_with_url(self, hass: HomeAssistant, aioclient_mock):
        """Test successful user flow with URL input normalizes the host."""
        # The device client normalizes "http://192.168.1.100" → host="192.168.1.100"
        _mock_device_success(aioclient_mock)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            # User enters URL with http://
            user_input={"host": f"http://{DEVICE_HOST}", "name": "Test Display"},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Display"
        # Data stores original user input
        assert result["data"]["host"] == f"http://{DEVICE_HOST}"

    async def test_user_flow_creates_full_integration(self, hass: HomeAssistant, aioclient_mock):
        """Test that successful config flow leads to a fully working integration."""
        _mock_device_success(aioclient_mock)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": DEVICE_HOST, "name": "Test Display"},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify the integration actually set up (entities registered)
        state = hass.states.get("sensor.test_display_status")
        assert state is not None
        assert state.state == "Connected"


class TestOptionsFlowInit:
    """Test options flow initialization."""

    def test_options_flow_init(self):
        """Test GeekMagicOptionsFlow can be instantiated."""
        flow = GeekMagicOptionsFlow()
        assert flow is not None


class TestDefaultOptions:
    """Test default options generation."""

    def test_get_default_options(self):
        """Test default options are properly structured."""
        flow = GeekMagicConfigFlow()
        defaults = flow._get_default_options()

        assert CONF_REFRESH_INTERVAL in defaults
        assert defaults[CONF_REFRESH_INTERVAL] == DEFAULT_REFRESH_INTERVAL
        assert CONF_SCREEN_CYCLE_INTERVAL in defaults
        assert defaults[CONF_SCREEN_CYCLE_INTERVAL] == DEFAULT_SCREEN_CYCLE_INTERVAL
        assert CONF_SCREENS in defaults
        assert len(defaults[CONF_SCREENS]) == 1
        assert defaults[CONF_SCREENS][0]["name"] == "Screen 1"
        assert defaults[CONF_SCREENS][0][CONF_LAYOUT] == LAYOUT_GRID_2X2
        assert len(defaults[CONF_SCREENS][0][CONF_WIDGETS]) == 1
        assert defaults[CONF_SCREENS][0][CONF_WIDGETS][0]["type"] == "clock"
