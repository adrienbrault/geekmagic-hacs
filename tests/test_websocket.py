"""Tests for GeekMagic WebSocket API handlers.

These tests verify that the WebSocket commands return the correct
response shapes that the TypeScript frontend expects. They test
the store ↔ WebSocket ↔ frontend contract.
"""

from __future__ import annotations

import re

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import (
    DOMAIN,
    LAYOUT_SLOT_COUNTS,
    THEME_OPTIONS,
)
from custom_components.geekmagic.store import GeekMagicStore
from custom_components.geekmagic.websocket import (
    WIDGET_TYPE_SCHEMAS,
    async_register_websocket_commands,
)

DEVICE_HOST = "192.168.1.100"


async def _setup_domain(hass: HomeAssistant) -> GeekMagicStore:
    """Initialize the GeekMagic domain with store and WebSocket commands."""
    hass.data.setdefault(DOMAIN, {})
    store = GeekMagicStore(hass)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store
    async_register_websocket_commands(hass)
    return store


def _setup_device_http_mocks(aioclient_mock, host: str = DEVICE_HOST) -> None:
    """Register minimal HTTP mocks for a device."""
    base = f"http://{host}"
    aioclient_mock.get(f"{base}/space.json", json={"total": 1048576, "free": 524288})
    aioclient_mock.get(f"{base}/.sys/app.json", status=404)
    aioclient_mock.get(f"{base}/app.json", json={"theme": 0, "brt": 50, "img": None})
    aioclient_mock.get(f"{base}/brt.json", json={"brt": "50"})
    aioclient_mock.post(f"{base}/doUpload?dir=/image/", status=200)
    aioclient_mock.get(re.compile(rf"^{re.escape(base)}/set\?"), status=200)


async def _setup_with_device(
    hass: HomeAssistant,
    aioclient_mock,
) -> tuple[GeekMagicStore, MockConfigEntry]:
    """Set up domain + a real device entry for device-related tests."""
    _setup_device_http_mocks(aioclient_mock)
    store = await _setup_domain(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Display",
        data={"host": DEVICE_HOST, "name": "Test Display"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return store, entry


# =============================================================================
# Config Command
# =============================================================================


class TestConfigEndpoint:
    """Test the geekmagic/config WebSocket command."""

    async def test_config_returns_all_sections(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Config response must contain widget_types, layout_types, and themes."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/config"})
        msg = await client.receive_json()

        assert msg["success"]
        result = msg["result"]
        assert "widget_types" in result
        assert "layout_types" in result
        assert "themes" in result

    async def test_config_returns_all_layout_types(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Every layout in LAYOUT_SLOT_COUNTS must appear in config response."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/config"})
        msg = await client.receive_json()

        layout_types = msg["result"]["layout_types"]
        for layout_key, expected_slots in LAYOUT_SLOT_COUNTS.items():
            assert layout_key in layout_types, f"Missing layout: {layout_key}"
            assert layout_types[layout_key]["slots"] == expected_slots
            assert "name" in layout_types[layout_key]

    async def test_config_returns_all_themes(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Every theme in THEME_OPTIONS must appear in config response."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/config"})
        msg = await client.receive_json()

        themes = msg["result"]["themes"]
        for key, name in THEME_OPTIONS.items():
            assert key in themes, f"Missing theme: {key}"
            assert themes[key] == name

    async def test_config_returns_all_widget_types(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Every widget type in WIDGET_TYPE_SCHEMAS must appear in config."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/config"})
        msg = await client.receive_json()

        widget_types = msg["result"]["widget_types"]
        for wtype in WIDGET_TYPE_SCHEMAS:
            assert wtype in widget_types, f"Missing widget type: {wtype}"
            assert "name" in widget_types[wtype]
            assert "options" in widget_types[wtype]

    async def test_layout_type_info_shape(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Each layout type entry must have 'slots' (int) and 'name' (str)."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/config"})
        msg = await client.receive_json()

        for key, info in msg["result"]["layout_types"].items():
            assert isinstance(info["slots"], int), f"{key}: slots not int"
            assert isinstance(info["name"], str), f"{key}: name not str"


# =============================================================================
# View Commands
# =============================================================================


class TestViewCRUD:
    """Test view create/read/update/delete lifecycle."""

    async def test_views_list_initially_empty(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/views/list"})
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["views"] == []

    async def test_create_view(self, hass: HomeAssistant, hass_ws_client):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "Test View",
            "layout": "grid_2x2",
            "theme": "classic",
            "widgets": [],
        })
        msg = await client.receive_json()

        assert msg["success"]
        result = msg["result"]
        assert "view_id" in result
        assert result["view"]["name"] == "Test View"
        assert result["view"]["layout"] == "grid_2x2"
        assert result["view"]["theme"] == "classic"
        assert result["view"]["widgets"] == []
        assert result["view"]["id"] == result["view_id"]

    async def test_create_view_response_matches_typescript_viewconfig(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Created view must have all fields from TypeScript ViewConfig."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "Contract Test",
        })
        msg = await client.receive_json()
        view = msg["result"]["view"]

        # Required fields per ViewConfig interface
        assert "id" in view
        assert "name" in view
        assert "layout" in view
        assert "theme" in view
        assert "widgets" in view
        # Optional fields
        assert "created_at" in view
        assert "updated_at" in view

    async def test_get_view(self, hass: HomeAssistant, hass_ws_client):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        # Create
        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "Fetch Me",
        })
        create_msg = await client.receive_json()
        view_id = create_msg["result"]["view_id"]

        # Get
        await client.send_json({
            "id": 2,
            "type": "geekmagic/views/get",
            "view_id": view_id,
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["view"]["id"] == view_id
        assert msg["result"]["view"]["name"] == "Fetch Me"

    async def test_get_nonexistent_view_returns_error(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/get",
            "view_id": "nonexistent",
        })
        msg = await client.receive_json()

        assert not msg["success"]
        assert msg["error"]["code"] == "not_found"

    async def test_update_view(self, hass: HomeAssistant, hass_ws_client):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        # Create
        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "Original",
        })
        create_msg = await client.receive_json()
        view_id = create_msg["result"]["view_id"]

        # Update
        await client.send_json({
            "id": 2,
            "type": "geekmagic/views/update",
            "view_id": view_id,
            "name": "Updated",
            "layout": "grid_3x3",
            "theme": "neon",
            "widgets": [{"slot": 0, "type": "clock"}],
        })
        msg = await client.receive_json()

        assert msg["success"]
        view = msg["result"]["view"]
        assert view["name"] == "Updated"
        assert view["layout"] == "grid_3x3"
        assert view["theme"] == "neon"
        assert len(view["widgets"]) == 1
        assert view["widgets"][0]["type"] == "clock"

    async def test_update_nonexistent_view_returns_error(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/update",
            "view_id": "nonexistent",
            "name": "Nope",
        })
        msg = await client.receive_json()

        assert not msg["success"]
        assert msg["error"]["code"] == "not_found"

    async def test_delete_view(self, hass: HomeAssistant, hass_ws_client):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        # Create
        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "To Delete",
        })
        create_msg = await client.receive_json()
        view_id = create_msg["result"]["view_id"]

        # Delete
        await client.send_json({
            "id": 2,
            "type": "geekmagic/views/delete",
            "view_id": view_id,
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["success"] is True

        # Verify deleted
        await client.send_json({
            "id": 3,
            "type": "geekmagic/views/get",
            "view_id": view_id,
        })
        msg = await client.receive_json()
        assert not msg["success"]

    async def test_delete_nonexistent_view_returns_error(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/delete",
            "view_id": "nonexistent",
        })
        msg = await client.receive_json()

        assert not msg["success"]
        assert msg["error"]["code"] == "not_found"

    async def test_duplicate_view(self, hass: HomeAssistant, hass_ws_client):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        # Create original
        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "Original",
            "layout": "hero",
            "theme": "neon",
            "widgets": [{"slot": 0, "type": "clock"}],
        })
        create_msg = await client.receive_json()
        original_id = create_msg["result"]["view_id"]

        # Duplicate
        await client.send_json({
            "id": 2,
            "type": "geekmagic/views/duplicate",
            "view_id": original_id,
            "name": "My Copy",
        })
        msg = await client.receive_json()

        assert msg["success"]
        result = msg["result"]
        assert result["view_id"] != original_id
        assert result["view"]["name"] == "My Copy"
        assert result["view"]["layout"] == "hero"
        assert result["view"]["theme"] == "neon"
        assert len(result["view"]["widgets"]) == 1

    async def test_duplicate_nonexistent_view_returns_error(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/duplicate",
            "view_id": "nonexistent",
        })
        msg = await client.receive_json()

        assert not msg["success"]

    async def test_views_list_returns_created_views(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        # Create two views
        await client.send_json({
            "id": 1,
            "type": "geekmagic/views/create",
            "name": "View A",
        })
        await client.receive_json()

        await client.send_json({
            "id": 2,
            "type": "geekmagic/views/create",
            "name": "View B",
        })
        await client.receive_json()

        # List
        await client.send_json({"id": 3, "type": "geekmagic/views/list"})
        msg = await client.receive_json()

        assert msg["success"]
        views = msg["result"]["views"]
        assert len(views) == 2
        names = {v["name"] for v in views}
        assert names == {"View A", "View B"}

    async def test_full_crud_lifecycle(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Test create → list → update → get → delete → list."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)
        msg_id = 0

        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id

        # Create
        await client.send_json({
            "id": next_id(),
            "type": "geekmagic/views/create",
            "name": "Lifecycle",
        })
        create_msg = await client.receive_json()
        view_id = create_msg["result"]["view_id"]

        # List — should have 1
        await client.send_json({"id": next_id(), "type": "geekmagic/views/list"})
        list_msg = await client.receive_json()
        assert len(list_msg["result"]["views"]) == 1

        # Update
        await client.send_json({
            "id": next_id(),
            "type": "geekmagic/views/update",
            "view_id": view_id,
            "name": "Updated Lifecycle",
        })
        update_msg = await client.receive_json()
        assert update_msg["result"]["view"]["name"] == "Updated Lifecycle"

        # Get — verify update persisted
        await client.send_json({
            "id": next_id(),
            "type": "geekmagic/views/get",
            "view_id": view_id,
        })
        get_msg = await client.receive_json()
        assert get_msg["result"]["view"]["name"] == "Updated Lifecycle"

        # Delete
        await client.send_json({
            "id": next_id(),
            "type": "geekmagic/views/delete",
            "view_id": view_id,
        })
        await client.receive_json()

        # List — should be empty
        await client.send_json({"id": next_id(), "type": "geekmagic/views/list"})
        final_msg = await client.receive_json()
        assert len(final_msg["result"]["views"]) == 0


# =============================================================================
# Device Commands
# =============================================================================


class TestDeviceCommands:
    """Test device-related WebSocket commands."""

    async def test_devices_list_with_device(
        self, hass: HomeAssistant, hass_ws_client, aioclient_mock
    ):
        """Devices list should return configured devices with correct shape."""
        await _setup_with_device(hass, aioclient_mock)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/devices/list"})
        msg = await client.receive_json()

        assert msg["success"]
        devices = msg["result"]["devices"]
        assert len(devices) == 1

        device = devices[0]
        # Verify all fields that TypeScript DeviceConfig expects
        assert "entry_id" in device
        assert "name" in device
        assert "host" in device
        assert device["host"] == DEVICE_HOST
        assert "assigned_views" in device
        assert isinstance(device["assigned_views"], list)
        assert "current_view_index" in device
        assert "brightness" in device
        assert "refresh_interval" in device
        assert "cycle_interval" in device
        assert "online" in device
        assert isinstance(device["online"], bool)

    async def test_devices_list_empty_without_devices(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Devices list should return empty list when no devices configured."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/devices/list"})
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["devices"] == []

    async def test_assign_views_to_device(
        self, hass: HomeAssistant, hass_ws_client, aioclient_mock
    ):
        """Assigning views should update device's assigned_views."""
        store, entry = await _setup_with_device(hass, aioclient_mock)
        client = await hass_ws_client(hass)

        # Create a view first
        view_id = await store.async_create_view(name="Test View")

        # Assign
        await client.send_json({
            "id": 1,
            "type": "geekmagic/devices/assign_views",
            "entry_id": entry.entry_id,
            "view_ids": [view_id],
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["success"] is True

        # Verify the config entry was updated
        assert entry.options.get("assigned_views") == [view_id]

    async def test_assign_views_nonexistent_device(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/devices/assign_views",
            "entry_id": "nonexistent",
            "view_ids": [],
        })
        msg = await client.receive_json()

        assert not msg["success"]

    async def test_device_settings(
        self, hass: HomeAssistant, hass_ws_client, aioclient_mock
    ):
        """Device settings endpoint should accept valid parameters."""
        _, entry = await _setup_with_device(hass, aioclient_mock)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/devices/settings",
            "entry_id": entry.entry_id,
            "brightness": 75,
            "refresh_interval": 30,
            "cycle_interval": 60,
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert msg["result"]["success"] is True

    async def test_device_settings_nonexistent_device(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({
            "id": 1,
            "type": "geekmagic/devices/settings",
            "entry_id": "nonexistent",
            "brightness": 50,
        })
        msg = await client.receive_json()

        assert not msg["success"]


# =============================================================================
# Entity List Command
# =============================================================================


class TestEntityList:
    """Test the entity list WebSocket command."""

    async def test_entities_list_empty_hass(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Entity list should return correct shape even with no entities."""
        await _setup_domain(hass)
        client = await hass_ws_client(hass)

        await client.send_json({"id": 1, "type": "geekmagic/entities/list"})
        msg = await client.receive_json()

        assert msg["success"]
        result = msg["result"]
        # Verify shape matches TypeScript EntitiesListResponse
        assert "entities" in result
        assert "total" in result
        assert "has_more" in result
        assert isinstance(result["entities"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["has_more"], bool)

    async def test_entities_list_with_states(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Entity list should return entities with correct field shape."""
        await _setup_domain(hass)

        # Add some fake states
        hass.states.async_set(
            "sensor.temperature",
            "23.5",
            {"friendly_name": "Temperature", "unit_of_measurement": "°C"},
        )
        hass.states.async_set(
            "light.living_room",
            "on",
            {"friendly_name": "Living Room Light"},
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "geekmagic/entities/list"})
        msg = await client.receive_json()

        assert msg["success"]
        entities = msg["result"]["entities"]
        assert len(entities) == 2

        # Verify field shape matches TypeScript EntityInfo
        for entity in entities:
            assert "entity_id" in entity
            assert "name" in entity
            assert "state" in entity
            assert "domain" in entity
            # Optional fields should still be present (as None/null)
            assert "unit" in entity
            assert "device_class" in entity
            assert "area" in entity
            assert "device" in entity
            assert "icon" in entity

    async def test_entities_list_domain_filter(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Domain filter should only return matching entities."""
        await _setup_domain(hass)

        hass.states.async_set("sensor.temp", "23", {"friendly_name": "Temp"})
        hass.states.async_set("light.lamp", "on", {"friendly_name": "Lamp"})

        client = await hass_ws_client(hass)
        await client.send_json({
            "id": 1,
            "type": "geekmagic/entities/list",
            "domain": "sensor",
        })
        msg = await client.receive_json()

        assert msg["success"]
        entities = msg["result"]["entities"]
        assert len(entities) == 1
        assert entities[0]["domain"] == "sensor"

    async def test_entities_list_widget_type_filter(
        self, hass: HomeAssistant, hass_ws_client
    ):
        """Widget type filter should use domain restrictions from schema."""
        await _setup_domain(hass)

        hass.states.async_set("weather.home", "sunny", {"friendly_name": "Home"})
        hass.states.async_set("sensor.temp", "23", {"friendly_name": "Temp"})

        client = await hass_ws_client(hass)
        await client.send_json({
            "id": 1,
            "type": "geekmagic/entities/list",
            "widget_type": "weather",
        })
        msg = await client.receive_json()

        assert msg["success"]
        entities = msg["result"]["entities"]
        assert len(entities) == 1
        assert entities[0]["domain"] == "weather"

    async def test_entities_list_search_filter(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)

        hass.states.async_set("sensor.temp", "23", {"friendly_name": "Temperature"})
        hass.states.async_set("sensor.humidity", "60", {"friendly_name": "Humidity"})

        client = await hass_ws_client(hass)
        await client.send_json({
            "id": 1,
            "type": "geekmagic/entities/list",
            "search": "temp",
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert len(msg["result"]["entities"]) == 1
        assert msg["result"]["entities"][0]["entity_id"] == "sensor.temp"

    async def test_entities_list_respects_limit(
        self, hass: HomeAssistant, hass_ws_client
    ):
        await _setup_domain(hass)

        for i in range(10):
            hass.states.async_set(
                f"sensor.s{i}", str(i), {"friendly_name": f"Sensor {i}"}
            )

        client = await hass_ws_client(hass)
        await client.send_json({
            "id": 1,
            "type": "geekmagic/entities/list",
            "limit": 3,
        })
        msg = await client.receive_json()

        assert msg["success"]
        assert len(msg["result"]["entities"]) == 3
        assert msg["result"]["has_more"] is True
