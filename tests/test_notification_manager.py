"""Tests for the notification_manager module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.hero_simple import HeroSimpleLayout
from custom_components.geekmagic.notification_manager import NotificationManager


def _make_manager():
    hass = MagicMock()
    hass.loop.call_later = MagicMock()
    hass.async_create_task = MagicMock()
    refresh = AsyncMock()
    manager = NotificationManager(hass, refresh)
    return manager, hass, refresh


class TestActiveState:
    def test_starts_inactive(self):
        manager, _, _ = _make_manager()
        assert manager.is_active is False
        assert manager.image_source is None

    @pytest.mark.asyncio
    async def test_trigger_marks_active(self):
        manager, _, refresh = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"message": "hi", "duration": 5})
        # is_active checks time.time() < expiry, so we need to be inside the window
        with patch("time.time", return_value=1004):
            assert manager.is_active is True
        refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_expiry_marks_inactive(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"message": "hi", "duration": 5})
        with patch("time.time", return_value=2000):
            assert manager.is_active is False

    @pytest.mark.asyncio
    async def test_retrigger_cancels_previous_timer(self):
        manager, hass, _ = _make_manager()
        first_handle = MagicMock()
        second_handle = MagicMock()
        hass.loop.call_later.side_effect = [first_handle, second_handle]

        await manager.trigger({"message": "first", "duration": 5})
        await manager.trigger({"message": "second", "duration": 5})

        first_handle.cancel.assert_called_once()


class TestImageSource:
    @pytest.mark.asyncio
    async def test_image_source_returned_when_active(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"image": "camera.front", "duration": 5})
        with patch("time.time", return_value=1004):
            assert manager.image_source == "camera.front"

    @pytest.mark.asyncio
    async def test_image_source_none_when_no_image(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"message": "no image", "duration": 5})
        with patch("time.time", return_value=1004):
            assert manager.image_source is None


class TestBuildLayout:
    def test_returns_none_when_inactive(self):
        manager, _, _ = _make_manager()
        assert manager.build_layout() is None

    @pytest.mark.asyncio
    async def test_message_with_image_returns_hero_simple_with_camera_hero(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"message": "Test", "image": "camera.test", "duration": 5})
        with patch("time.time", return_value=1004):
            layout = manager.build_layout()
        assert isinstance(layout, HeroSimpleLayout)
        hero = layout.get_slot(0).widget
        text = layout.get_slot(1).widget
        assert hero is not None and hero.config.widget_type == "camera"
        assert hero.config.entity_id == "camera.test"
        assert text is not None and text.config.options["text"] == "Test"

    @pytest.mark.asyncio
    async def test_message_without_image_uses_icon_hero(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"message": "Hi", "icon": "mdi:bell", "duration": 5})
        with patch("time.time", return_value=1004):
            layout = manager.build_layout()
        assert isinstance(layout, HeroSimpleLayout)
        hero = layout.get_slot(0).widget
        assert hero is not None and hero.config.widget_type == "icon"
        assert hero.config.options["icon"] == "mdi:bell"

    @pytest.mark.asyncio
    async def test_no_message_with_image_returns_fullscreen(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"image": "camera.test", "duration": 5})
        with patch("time.time", return_value=1004):
            layout = manager.build_layout()
        assert isinstance(layout, FullscreenLayout)
        hero = layout.get_slot(0).widget
        assert hero is not None and hero.config.widget_type == "camera"

    @pytest.mark.asyncio
    async def test_no_message_no_image_returns_fullscreen_icon(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"icon": "mdi:alert", "duration": 5})
        with patch("time.time", return_value=1004):
            layout = manager.build_layout()
        assert isinstance(layout, FullscreenLayout)
        hero = layout.get_slot(0).widget
        assert hero is not None and hero.config.widget_type == "icon"
        assert hero.config.options["icon"] == "mdi:alert"
        assert hero.config.options.get("show_panel") is False

    @pytest.mark.asyncio
    async def test_default_icon_when_none_provided(self):
        manager, _, _ = _make_manager()
        with patch("time.time", return_value=1000):
            await manager.trigger({"duration": 5})
        with patch("time.time", return_value=1004):
            layout = manager.build_layout()
        hero = layout.get_slot(0).widget
        assert hero is not None
        assert hero.config.options["icon"] == "mdi:bell-ring"
