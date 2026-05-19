"""Tests for the display_state module."""

from __future__ import annotations

from custom_components.geekmagic.display_state import DisplayState


class TestInitial:
    def test_starts_custom_not_paused(self):
        d = DisplayState()
        assert d.mode == "custom"
        assert d.is_paused is False
        assert d.is_active is True


class TestModeTransitions:
    def test_set_builtin_records_theme(self):
        d = DisplayState()
        d.set_builtin(2)
        assert d.mode == "builtin"
        assert d.builtin_theme == 2

    def test_set_custom_does_not_clear_recorded_theme(self):
        # `builtin_theme` is meaningless when mode != builtin; we don't promise to clear it.
        d = DisplayState()
        d.set_builtin(1)
        d.set_custom()
        assert d.mode == "custom"


class TestSyncFromDeviceTheme:
    def test_flips_to_builtin_when_custom_and_device_theme_low(self):
        d = DisplayState()
        flipped = d.sync_from_device_theme(1)
        assert flipped is True
        assert d.mode == "builtin"
        assert d.builtin_theme == 1

    def test_no_flip_when_device_theme_is_3_or_higher(self):
        # Themes >= 3 are the integration's own "custom image" slot
        d = DisplayState()
        flipped = d.sync_from_device_theme(3)
        assert flipped is False
        assert d.mode == "custom"

    def test_no_flip_when_already_builtin(self):
        d = DisplayState()
        d.set_builtin(2)
        flipped = d.sync_from_device_theme(0)
        assert flipped is False
        # mode stays builtin, theme not overwritten by sync
        assert d.mode == "builtin"
        assert d.builtin_theme == 2


class TestPauseLifecycle:
    def test_enter_pause_remembers_brightness(self):
        d = DisplayState()
        d.enter_pause(75)
        assert d.is_paused is True
        restore = d.exit_pause()
        assert restore == 75
        assert d.is_paused is False

    def test_exit_pause_clears_brightness(self):
        d = DisplayState()
        d.enter_pause(50)
        d.exit_pause()
        # second exit returns None
        assert d.exit_pause() is None

    def test_double_enter_pause_keeps_first_brightness(self):
        d = DisplayState()
        d.enter_pause(80)
        d.enter_pause(10)  # called while already paused — should not overwrite
        assert d.exit_pause() == 80

    def test_enter_pause_with_none_brightness(self):
        d = DisplayState()
        d.enter_pause(None)
        assert d.is_paused is True
        assert d.exit_pause() is None
