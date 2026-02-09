"""Tests for GeekMagic entity implementations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.geekmagic.const import (
    CONF_FLIP_DISPLAY,
    CONF_SCREEN_CYCLE_INTERVAL,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator for entity tests."""
    coordinator = MagicMock()
    coordinator.options = {}
    coordinator.entry = MagicMock()
    coordinator.entry.options = {}
    coordinator.entry.entry_id = "test_entry_123"
    coordinator.get_store = MagicMock(return_value=None)
    coordinator.display_mode = "custom"
    coordinator.builtin_theme = 0
    coordinator.current_screen = 0
    coordinator.device = MagicMock()
    coordinator.device.set_theme = AsyncMock()
    coordinator.set_display_mode = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_refresh_display = AsyncMock()
    return coordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


class TestDisplaySelectCoordinatorUpdate:
    """Tests for Display select entity _handle_coordinator_update behavior."""

    def test_state_written_on_first_update(self, mock_coordinator):
        """Test that state is written on first coordinator update (initialization)."""
        from custom_components.geekmagic.entities.select import GeekMagicDisplaySelect

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.async_write_ha_state = MagicMock()

        # First update - should write state
        select._handle_coordinator_update()

        select.async_write_ha_state.assert_called_once()
        assert select._last_options is not None

    def test_state_written_when_options_change(self, mock_coordinator):
        """Test that state is written when options change (views added/removed)."""
        from custom_components.geekmagic.entities.select import (
            GeekMagicDisplaySelect,
        )

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.async_write_ha_state = MagicMock()

        # First update - sets initial options
        select._handle_coordinator_update()
        initial_call_count = select.async_write_ha_state.call_count
        initial_options = select._last_options.copy()

        # Simulate adding a new view by mocking get_store
        mock_store = MagicMock()
        mock_store.get_view = MagicMock(return_value={"name": "New View"})
        mock_coordinator.get_store = MagicMock(return_value=mock_store)
        mock_coordinator.options = {"assigned_views": ["view_1"]}

        # Second update with different options - should write state
        select._handle_coordinator_update()

        assert select.async_write_ha_state.call_count == initial_call_count + 1
        assert select._last_options != initial_options

    def test_state_not_written_during_cycling(self, mock_coordinator):
        """Test that state is NOT written when only current_screen changes (cycling)."""
        from custom_components.geekmagic.entities.select import GeekMagicDisplaySelect

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.async_write_ha_state = MagicMock()

        # First update
        select._handle_coordinator_update()
        initial_call_count = select.async_write_ha_state.call_count

        # Simulate cycling - current_screen changes but options stay the same
        mock_coordinator.current_screen = 1

        # Second update - options unchanged, should NOT write state
        select._handle_coordinator_update()

        # Call count should not have increased
        assert select.async_write_ha_state.call_count == initial_call_count

    def test_state_not_written_on_multiple_cycling_updates(self, mock_coordinator):
        """Test that repeated cycling updates don't trigger state writes."""
        from custom_components.geekmagic.entities.select import GeekMagicDisplaySelect

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.async_write_ha_state = MagicMock()

        # First update
        select._handle_coordinator_update()
        initial_call_count = select.async_write_ha_state.call_count

        # Simulate multiple cycling updates
        for i in range(10):
            mock_coordinator.current_screen = i % 3
            select._handle_coordinator_update()

        # Call count should not have increased despite 10 updates
        assert select.async_write_ha_state.call_count == initial_call_count

    @pytest.mark.asyncio
    async def test_state_written_after_user_selection(self, mock_coordinator, mock_hass):
        """Test that state IS written after explicit user selection."""
        from custom_components.geekmagic.entities.select import GeekMagicDisplaySelect

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.hass = mock_hass
        select.async_write_ha_state = MagicMock()

        # User selects a built-in mode
        await select.async_select_option("Weather Clock Today")

        # State should be written after user selection
        select.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_state_written_after_custom_view_selection(self, mock_coordinator, mock_hass):
        """Test that state is written when user selects a custom view."""
        from custom_components.geekmagic.entities.select import GeekMagicDisplaySelect

        # Set up mock store with a custom view
        mock_store = MagicMock()
        mock_store.get_view = MagicMock(return_value={"name": "My Dashboard"})
        mock_coordinator.get_store = MagicMock(return_value=mock_store)
        mock_coordinator.options = {"assigned_views": ["view_1"]}

        select = GeekMagicDisplaySelect(mock_coordinator)
        select.hass = mock_hass
        select.async_write_ha_state = MagicMock()

        # User selects the custom view
        await select.async_select_option("My Dashboard")

        # State should be written
        select.async_write_ha_state.assert_called()


class TestViewCyclingSwitchIsOn:
    """Tests for ViewCyclingSwitch is_on property."""

    def test_is_on_returns_true_when_interval_greater_than_zero(self, mock_coordinator):
        """Test is_on returns True when CONF_SCREEN_CYCLE_INTERVAL > 0."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 30}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch.is_on is True

    def test_is_on_returns_false_when_interval_is_zero(self, mock_coordinator):
        """Test is_on returns False when CONF_SCREEN_CYCLE_INTERVAL == 0."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch.is_on is False

    def test_is_on_returns_false_when_interval_not_set(self, mock_coordinator):
        """Test is_on returns False when interval is not configured (defaults to 0)."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch.is_on is False


class TestViewCyclingSwitchTurnOn:
    """Tests for ViewCyclingSwitch async_turn_on."""

    @pytest.mark.asyncio
    async def test_turn_on_sets_default_interval_when_no_previous(
        self, mock_coordinator, mock_hass
    ):
        """Test async_turn_on sets interval to default (30) when no previous interval."""
        from custom_components.geekmagic.entities.switch import (
            DEFAULT_CYCLE_ON_INTERVAL,
            GeekMagicViewCyclingSwitch,
        )

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_on()

        # Should update entry with default interval
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        new_options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert new_options[CONF_SCREEN_CYCLE_INTERVAL] == DEFAULT_CYCLE_ON_INTERVAL

    @pytest.mark.asyncio
    async def test_turn_on_restores_previous_interval(self, mock_coordinator, mock_hass):
        """Test async_turn_on restores previous interval after turn_off/turn_on cycle."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        # Start with cycling enabled at 45 seconds
        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 45}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 45}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)
        switch.hass = mock_hass

        # Turn off - should store 45
        await switch.async_turn_off()

        # Update mock to reflect the turn off
        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}
        mock_hass.config_entries.async_update_entry.reset_mock()

        # Turn on - should restore 45
        await switch.async_turn_on()

        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        new_options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert new_options[CONF_SCREEN_CYCLE_INTERVAL] == 45

    @pytest.mark.asyncio
    async def test_turn_on_is_noop_when_already_on(self, mock_coordinator, mock_hass):
        """Test async_turn_on is no-op when already on."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 30}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 30}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_on()

        # Should not call update_entry since already on
        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestViewCyclingSwitchTurnOff:
    """Tests for ViewCyclingSwitch async_turn_off."""

    @pytest.mark.asyncio
    async def test_turn_off_sets_interval_to_zero(self, mock_coordinator, mock_hass):
        """Test async_turn_off sets interval to 0 and stores previous value."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 60}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 60}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_off()

        # Should update entry with interval = 0
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        new_options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert new_options[CONF_SCREEN_CYCLE_INTERVAL] == 0

        # Should store previous interval
        assert switch._last_interval == 60

    @pytest.mark.asyncio
    async def test_turn_off_is_noop_when_already_off(self, mock_coordinator, mock_hass):
        """Test async_turn_off is no-op when already off."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        mock_coordinator.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}
        mock_coordinator.entry.options = {CONF_SCREEN_CYCLE_INTERVAL: 0}

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_off()

        # Should not call update_entry since already off
        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestViewCyclingSwitchAttributes:
    """Tests for ViewCyclingSwitch entity attributes."""

    def test_switch_has_correct_name(self, mock_coordinator):
        """Test switch entity has correct name."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch._attr_name == "View Cycling"

    def test_switch_has_correct_icon(self, mock_coordinator):
        """Test switch entity has correct icon."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch._attr_icon == "mdi:view-carousel"

    def test_switch_has_unique_id(self, mock_coordinator):
        """Test switch entity has unique ID based on entry."""
        from custom_components.geekmagic.entities.switch import GeekMagicViewCyclingSwitch

        switch = GeekMagicViewCyclingSwitch(mock_coordinator)

        assert switch._attr_unique_id == "test_entry_123_view_cycling"


class TestFlipDisplaySwitchIsOn:
    """Tests for FlipDisplaySwitch is_on property."""

    def test_is_on_returns_true_when_flip_enabled(self, mock_coordinator):
        """Test is_on returns True when CONF_FLIP_DISPLAY is True."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: True}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch.is_on is True

    def test_is_on_returns_false_when_flip_disabled(self, mock_coordinator):
        """Test is_on returns False when CONF_FLIP_DISPLAY is False."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: False}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch.is_on is False

    def test_is_on_returns_false_when_not_set(self, mock_coordinator):
        """Test is_on returns False when flip is not configured (defaults to False)."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch.is_on is False


class TestFlipDisplaySwitchTurnOn:
    """Tests for FlipDisplaySwitch async_turn_on."""

    @pytest.mark.asyncio
    async def test_turn_on_sets_flip_to_true(self, mock_coordinator, mock_hass):
        """Test async_turn_on sets CONF_FLIP_DISPLAY to True."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: False}
        mock_coordinator.entry.options = {CONF_FLIP_DISPLAY: False}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_on()

        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        new_options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert new_options[CONF_FLIP_DISPLAY] is True

    @pytest.mark.asyncio
    async def test_turn_on_is_noop_when_already_on(self, mock_coordinator, mock_hass):
        """Test async_turn_on is no-op when already on."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: True}
        mock_coordinator.entry.options = {CONF_FLIP_DISPLAY: True}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_on()

        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestFlipDisplaySwitchTurnOff:
    """Tests for FlipDisplaySwitch async_turn_off."""

    @pytest.mark.asyncio
    async def test_turn_off_sets_flip_to_false(self, mock_coordinator, mock_hass):
        """Test async_turn_off sets CONF_FLIP_DISPLAY to False."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: True}
        mock_coordinator.entry.options = {CONF_FLIP_DISPLAY: True}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_off()

        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        new_options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert new_options[CONF_FLIP_DISPLAY] is False

    @pytest.mark.asyncio
    async def test_turn_off_is_noop_when_already_off(self, mock_coordinator, mock_hass):
        """Test async_turn_off is no-op when already off."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        mock_coordinator.options = {CONF_FLIP_DISPLAY: False}
        mock_coordinator.entry.options = {CONF_FLIP_DISPLAY: False}

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)
        switch.hass = mock_hass

        await switch.async_turn_off()

        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestFlipDisplaySwitchAttributes:
    """Tests for FlipDisplaySwitch entity attributes."""

    def test_switch_has_correct_name(self, mock_coordinator):
        """Test switch entity has correct name."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch._attr_name == "Flip Display"

    def test_switch_has_correct_icon(self, mock_coordinator):
        """Test switch entity has correct icon."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch._attr_icon == "mdi:phone-rotate-landscape"

    def test_switch_has_unique_id(self, mock_coordinator):
        """Test switch entity has unique ID based on entry."""
        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch._attr_unique_id == "test_entry_123_flip_display"

    def test_switch_has_config_entity_category(self, mock_coordinator):
        """Test switch entity is categorized as CONFIG."""
        from homeassistant.const import EntityCategory

        from custom_components.geekmagic.entities.switch import GeekMagicFlipDisplaySwitch

        switch = GeekMagicFlipDisplaySwitch(mock_coordinator)

        assert switch._attr_entity_category == EntityCategory.CONFIG
