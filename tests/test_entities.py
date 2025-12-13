"""Tests for GeekMagic entity platforms."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator for entity tests."""
    from custom_components.geekmagic.coordinator import GeekMagicCoordinator

    coordinator = MagicMock(spec=GeekMagicCoordinator)
    coordinator.device_name = "Test Display"
    coordinator.device_version = "1.0.0"
    coordinator.brightness = 50
    coordinator.current_screen_index = 0
    coordinator.current_screen_name = "Screen 1"
    coordinator._last_update_success = True
    coordinator._last_update_time = None
    coordinator.last_update_success = True
    coordinator.last_update_time = None
    coordinator.options = {
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
        CONF_SCREENS: [
            {
                "name": "Screen 1",
                "layout": "grid_2x2",
                "widgets": [{"type": "clock", "slot": 0}],
            }
        ],
    }
    coordinator.device = MagicMock()
    coordinator.device.host = "192.168.1.100"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_set_screen = AsyncMock()
    coordinator.async_next_screen = AsyncMock()
    coordinator.async_previous_screen = AsyncMock()
    coordinator.async_set_brightness = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


@pytest.fixture
def entity_entry() -> MockConfigEntry:
    """Create a mock config entry for entity testing."""
    from homeassistant.const import CONF_HOST, CONF_NAME

    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Display",
        data={CONF_HOST: "192.168.1.100", CONF_NAME: "Test Display"},
        options={
            CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
            CONF_SCREENS: [
                {
                    "name": "Screen 1",
                    "layout": "grid_2x2",
                    "widgets": [{"type": "clock", "slot": 0}],
                }
            ],
        },
        entry_id="test_entity_entry",
    )


class TestEntityBase:
    """Test base entity class."""

    def test_entity_unique_id(self, mock_coordinator, entity_entry):
        """Test entity unique_id generation."""
        from homeassistant.const import CONF_HOST

        from custom_components.geekmagic.entities.entity import GeekMagicEntity

        mock_coordinator.config_entry = entity_entry

        description = MagicMock()
        description.key = "test_key"

        entity = GeekMagicEntity(mock_coordinator, description)
        # Unique ID uses host to match image entity
        host = entity_entry.data[CONF_HOST]
        assert entity.unique_id == f"{host}_test_key"

    def test_entity_device_info(self, mock_coordinator, entity_entry):
        """Test entity device_info property."""
        from homeassistant.const import CONF_HOST

        from custom_components.geekmagic.entities.entity import GeekMagicEntity

        mock_coordinator.config_entry = entity_entry

        description = MagicMock()
        description.key = "test_key"

        entity = GeekMagicEntity(mock_coordinator, description)
        device_info = entity.device_info

        # Device identifier uses host to match image entity
        host = entity_entry.data[CONF_HOST]
        assert (DOMAIN, host) in device_info["identifiers"]
        assert device_info["name"] == "Test Display"
        assert device_info["manufacturer"] == "GeekMagic"


class TestNumberEntities:
    """Test number entity platform."""

    def test_number_entity_descriptions(self):
        """Test number entity descriptions are defined correctly."""
        from custom_components.geekmagic.entities.number import DEVICE_NUMBERS

        assert len(DEVICE_NUMBERS) == 4
        keys = [d.key for d in DEVICE_NUMBERS]
        assert "brightness" in keys
        assert "refresh_interval" in keys
        assert "screen_cycle_interval" in keys
        assert "screen_count" in keys

    def test_brightness_entity(self, mock_coordinator, entity_entry):
        """Test brightness number entity."""
        from custom_components.geekmagic.entities.number import (
            DEVICE_NUMBERS,
            GeekMagicNumberEntity,
        )

        mock_coordinator.config_entry = entity_entry
        brightness_desc = next(d for d in DEVICE_NUMBERS if d.key == "brightness")

        entity = GeekMagicNumberEntity(mock_coordinator, brightness_desc)
        assert entity.native_value == 50  # From mock_coordinator.brightness
        assert entity.entity_description.native_min_value == 0
        assert entity.entity_description.native_max_value == 100

    def test_screen_count_entity(self, mock_coordinator, entity_entry):
        """Test screen_count number entity."""
        from custom_components.geekmagic.entities.number import (
            DEVICE_NUMBERS,
            GeekMagicNumberEntity,
        )

        mock_coordinator.config_entry = entity_entry
        screen_count_desc = next(d for d in DEVICE_NUMBERS if d.key == "screen_count")

        entity = GeekMagicNumberEntity(mock_coordinator, screen_count_desc)
        assert entity.native_value == 1  # One screen in mock options


class TestButtonEntities:
    """Test button entity platform."""

    def test_button_entity_descriptions(self):
        """Test button entity descriptions are defined correctly."""
        from custom_components.geekmagic.entities.button import DEVICE_BUTTONS

        assert len(DEVICE_BUTTONS) == 3
        keys = [d.key for d in DEVICE_BUTTONS]
        assert "refresh_now" in keys
        assert "next_screen" in keys
        assert "previous_screen" in keys

    @pytest.mark.asyncio
    async def test_refresh_button_press(self, mock_coordinator, entity_entry):
        """Test refresh button triggers coordinator refresh."""
        from custom_components.geekmagic.entities.button import (
            DEVICE_BUTTONS,
            GeekMagicButtonEntity,
        )

        mock_coordinator.config_entry = entity_entry
        mock_coordinator.async_refresh_display = AsyncMock()
        refresh_desc = next(d for d in DEVICE_BUTTONS if d.key == "refresh_now")

        entity = GeekMagicButtonEntity(mock_coordinator, refresh_desc)
        await entity.async_press()

        mock_coordinator.async_refresh_display.assert_called_once()

    @pytest.mark.asyncio
    async def test_next_screen_button_press(self, mock_coordinator, entity_entry):
        """Test next screen button calls coordinator."""
        from custom_components.geekmagic.entities.button import (
            DEVICE_BUTTONS,
            GeekMagicButtonEntity,
        )

        mock_coordinator.config_entry = entity_entry
        next_screen_desc = next(d for d in DEVICE_BUTTONS if d.key == "next_screen")

        entity = GeekMagicButtonEntity(mock_coordinator, next_screen_desc)
        await entity.async_press()

        mock_coordinator.async_next_screen.assert_called_once()


class TestSensorEntities:
    """Test sensor entity platform."""

    def test_sensor_entity_descriptions(self):
        """Test sensor entity descriptions are defined correctly."""
        from custom_components.geekmagic.entities.sensor import DEVICE_SENSORS

        assert len(DEVICE_SENSORS) == 2
        keys = [d.key for d in DEVICE_SENSORS]
        assert "status" in keys
        assert "current_screen_name" in keys

    def test_status_sensor_connected(self, mock_coordinator, entity_entry):
        """Test status sensor shows connected."""
        from custom_components.geekmagic.entities.sensor import (
            DEVICE_SENSORS,
            GeekMagicSensorEntity,
        )

        mock_coordinator.config_entry = entity_entry
        status_desc = next(d for d in DEVICE_SENSORS if d.key == "status")

        entity = GeekMagicSensorEntity(mock_coordinator, status_desc)
        assert entity.native_value == "connected"

    def test_status_sensor_disconnected(self, mock_coordinator, entity_entry):
        """Test status sensor shows disconnected when update fails."""
        from custom_components.geekmagic.entities.sensor import (
            DEVICE_SENSORS,
            GeekMagicSensorEntity,
        )

        mock_coordinator.config_entry = entity_entry
        mock_coordinator.last_update_success = False
        status_desc = next(d for d in DEVICE_SENSORS if d.key == "status")

        entity = GeekMagicSensorEntity(mock_coordinator, status_desc)
        assert entity.native_value == "disconnected"

    def test_current_screen_name_sensor(self, mock_coordinator, entity_entry):
        """Test current screen name sensor."""
        from custom_components.geekmagic.entities.sensor import (
            DEVICE_SENSORS,
            GeekMagicSensorEntity,
        )

        mock_coordinator.config_entry = entity_entry
        screen_name_desc = next(d for d in DEVICE_SENSORS if d.key == "current_screen_name")

        entity = GeekMagicSensorEntity(mock_coordinator, screen_name_desc)
        assert entity.native_value == "Screen 1"


class TestSelectEntities:
    """Test select entity platform."""

    def test_layout_options_defined(self):
        """Test layout options are defined."""
        from custom_components.geekmagic.entities.select import LAYOUT_OPTIONS

        assert "grid_2x2" in LAYOUT_OPTIONS
        assert "hero" in LAYOUT_OPTIONS
        assert "split" in LAYOUT_OPTIONS

    def test_widget_options_defined(self):
        """Test widget options are defined."""
        from custom_components.geekmagic.entities.select import WIDGET_OPTIONS

        assert "empty" in WIDGET_OPTIONS
        assert "clock" in WIDGET_OPTIONS
        assert "entity" in WIDGET_OPTIONS


class TestSwitchEntities:
    """Test switch entity platform."""

    def test_widget_boolean_options_defined(self):
        """Test widget boolean options are defined."""
        from custom_components.geekmagic.entities.switch import WIDGET_BOOLEAN_OPTIONS

        assert "clock" in WIDGET_BOOLEAN_OPTIONS
        assert "entity" in WIDGET_BOOLEAN_OPTIONS
        assert "media" in WIDGET_BOOLEAN_OPTIONS

        # Check clock options
        clock_opts = WIDGET_BOOLEAN_OPTIONS["clock"]
        clock_keys = [opt[0] for opt in clock_opts]
        assert "show_seconds" in clock_keys
        assert "show_date" in clock_keys

        # Check entity options
        entity_opts = WIDGET_BOOLEAN_OPTIONS["entity"]
        entity_keys = [opt[0] for opt in entity_opts]
        assert "show_name" in entity_keys
        assert "show_unit" in entity_keys


class TestTextEntities:
    """Test text entity platform."""

    def test_screen_name_text_entity(self, mock_coordinator, entity_entry):
        """Test screen name text entity returns correct value."""
        from custom_components.geekmagic.entities.text import (
            GeekMagicScreenNameText,
            GeekMagicTextEntityDescription,
        )

        mock_coordinator.config_entry = entity_entry
        description = GeekMagicTextEntityDescription(
            key="screen_1_name",
            translation_key="screen_name",
            screen_index=0,
            text_type="screen_name",
        )

        entity = GeekMagicScreenNameText(mock_coordinator, description)
        assert entity.native_value == "Screen 1"

    def test_slot_label_text_entity(self, mock_coordinator, entity_entry):
        """Test slot label text entity returns correct value."""
        from custom_components.geekmagic.entities.text import (
            GeekMagicSlotLabelText,
            GeekMagicTextEntityDescription,
        )

        mock_coordinator.config_entry = entity_entry
        # Add label to widget
        mock_coordinator.options[CONF_SCREENS][0]["widgets"][0]["label"] = "Test Label"

        description = GeekMagicTextEntityDescription(
            key="screen_1_slot_1_label",
            translation_key="slot_label",
            screen_index=0,
            slot_index=0,
            text_type="slot_label",
        )

        entity = GeekMagicSlotLabelText(mock_coordinator, description)
        assert entity.native_value == "Test Label"


class TestEntityDynamicCreation:
    """Test dynamic entity creation based on configuration."""

    @pytest.mark.asyncio
    async def test_select_entities_created_for_screens(self, hass, mock_coordinator, entity_entry):
        """Test select entities are created for each screen."""
        from typing import Any

        from custom_components.geekmagic.entities.select import async_setup_entry

        entity_entry.add_to_hass(hass)
        mock_coordinator.config_entry = entity_entry
        hass.data[DOMAIN] = {entity_entry.entry_id: mock_coordinator}

        entities_added: list[Any] = []

        def mock_add_entities(entities: list[Any], update_before_add: bool = False) -> None:
            entities_added.extend(entities)

        await async_setup_entry(
            hass,
            entity_entry,
            mock_add_entities,  # type: ignore[arg-type]
        )

        # Should have current_screen + per-screen entities + per-slot entities
        assert len(entities_added) > 0

        # Check for current_screen selector
        entity_keys = [e.entity_description.key for e in entities_added]
        assert "current_screen" in entity_keys

    @pytest.mark.asyncio
    async def test_text_entities_created_for_screens(self, hass, mock_coordinator, entity_entry):
        """Test text entities are created for each screen and slot."""
        from typing import Any

        from custom_components.geekmagic.entities.text import async_setup_entry

        entity_entry.add_to_hass(hass)
        mock_coordinator.config_entry = entity_entry
        hass.data[DOMAIN] = {entity_entry.entry_id: mock_coordinator}

        entities_added: list[Any] = []

        def mock_add_entities(entities: list[Any], update_before_add: bool = False) -> None:
            entities_added.extend(entities)

        await async_setup_entry(
            hass,
            entity_entry,
            mock_add_entities,  # type: ignore[arg-type]
        )

        # Should have screen name + slot label entities
        assert len(entities_added) > 0

        entity_keys = [e.entity_description.key for e in entities_added]
        assert "screen_1_name" in entity_keys
