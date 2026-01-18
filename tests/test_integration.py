"""Integration tests for GeekMagic."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic import async_setup_entry, async_unload_entry
from custom_components.geekmagic.const import DOMAIN
from custom_components.geekmagic.device import ConnectionResult


class TestIntegrationSetup:
    """Test integration setup and teardown."""

    @pytest.fixture
    def integration_entry(self) -> MockConfigEntry:
        """Create a mock config entry for integration testing."""
        return MockConfigEntry(
            domain=DOMAIN,
            title="Test Display",
            data={"host": "192.168.1.100", "name": "Test Display"},
            options={},
            entry_id="test_entry_123",
        )

    @pytest.mark.asyncio
    async def test_setup_entry_connection_failure(self, hass, integration_entry):
        """Test setup raises ConfigEntryNotReady when device is offline."""
        integration_entry.add_to_hass(hass)

        with patch("custom_components.geekmagic.async_get_clientsession") as mock_session:
            mock_session.return_value = MagicMock()

            with patch("custom_components.geekmagic.GeekMagicDevice") as mock_device_class:
                mock_device = MagicMock()
                # Return a ConnectionResult with success=False and a message
                connection_result = ConnectionResult(
                    success=False, error="timeout", message="Connection timed out"
                )
                mock_device.test_connection = AsyncMock(return_value=connection_result)
                mock_device_class.return_value = mock_device

                # Should raise ConfigEntryNotReady for automatic retry
                with pytest.raises(ConfigEntryNotReady) as exc_info:
                    await async_setup_entry(hass, integration_entry)

                assert "Connection timed out" in str(exc_info.value)
                mock_device.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_success(self, hass, integration_entry):
        """Test successful setup creates coordinator and registers services."""
        integration_entry.add_to_hass(hass)

        with patch("custom_components.geekmagic.async_get_clientsession") as mock_session:
            mock_session.return_value = MagicMock()

            with patch("custom_components.geekmagic.GeekMagicDevice") as mock_device_class:
                mock_device = MagicMock()
                mock_device.test_connection = AsyncMock(return_value=True)
                mock_device_class.return_value = mock_device

                with patch(
                    "custom_components.geekmagic.GeekMagicCoordinator"
                ) as mock_coordinator_class:
                    mock_coordinator = MagicMock()
                    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
                    mock_coordinator_class.return_value = mock_coordinator

                    # Mock the platform forward setup to avoid state issues
                    with patch.object(
                        hass.config_entries,
                        "async_forward_entry_setups",
                        new=AsyncMock(return_value=True),
                    ):
                        result = await async_setup_entry(hass, integration_entry)

                        assert result is True
                        assert DOMAIN in hass.data
                        assert integration_entry.entry_id in hass.data[DOMAIN]


class TestIntegrationUnload:
    """Test integration unload."""

    @pytest.fixture
    def unload_entry(self) -> MockConfigEntry:
        """Create a mock config entry for unload testing."""
        return MockConfigEntry(
            domain=DOMAIN,
            title="Test Display",
            data={"host": "192.168.1.100", "name": "Test Display"},
            options={},
            entry_id="test_unload_entry",
        )

    @pytest.mark.asyncio
    async def test_unload_entry_success(self, hass, unload_entry):
        """Test successful unload removes coordinator."""
        unload_entry.add_to_hass(hass)
        # Set up the data structure as if setup was called
        hass.data[DOMAIN] = {unload_entry.entry_id: MagicMock()}

        with patch.object(
            hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)
        ):
            result = await async_unload_entry(hass, unload_entry)

            assert result is True
            assert unload_entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_entry_failure(self, hass, unload_entry):
        """Test failed unload keeps coordinator."""
        unload_entry.add_to_hass(hass)
        # Set up the data structure as if setup was called
        hass.data[DOMAIN] = {unload_entry.entry_id: MagicMock()}

        with patch.object(
            hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=False)
        ):
            result = await async_unload_entry(hass, unload_entry)

            assert result is False
            # Coordinator should still be present on failure
            assert unload_entry.entry_id in hass.data[DOMAIN]
