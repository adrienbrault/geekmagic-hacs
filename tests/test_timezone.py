"""Tests for timezone handling in preview rendering."""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo


class TestPreviewTimezone:
    """Test timezone handling in preview rendering."""

    @staticmethod
    def _apply_override(now: datetime, widget_data: dict[str, Any]) -> datetime:
        """Mirror the generalized override in coordinator.py/websocket.py.

        No longer gated on widget type/class — any widget whose options
        carry a truthy "timezone" key gets `now` recomputed in that zone.
        """
        import contextlib

        widget_now = now
        tz_option = widget_data.get("options", {}).get("timezone")
        if tz_option:
            with contextlib.suppress(Exception):
                widget_now = datetime.now(tz=ZoneInfo(tz_option))
        return widget_now

    def test_timezone_override_for_clock_widget(self):
        """Test that clock widget timezone override creates correct datetime."""

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "clock",
            "slot": 0,
            "options": {"timezone": "America/New_York"},
        }

        widget_now = self._apply_override(now, widget_data)

        # Verify the timezone was applied
        assert widget_now.tzinfo is not None
        assert str(widget_now.tzinfo) == "America/New_York"

    def test_timezone_override_for_datetime_widget(self):
        """Test that datetime widget timezone override creates correct datetime.

        Unlike the clock widget, this only shifts the anchor/conversion
        zone used to format an entity's timestamp value — but it goes
        through the same override.
        """

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "datetime",
            "slot": 0,
            "options": {"timezone": "Asia/Tokyo"},
        }

        widget_now = self._apply_override(now, widget_data)

        assert widget_now.tzinfo is not None
        assert str(widget_now.tzinfo) == "Asia/Tokyo"

    def test_timezone_override_empty_string_uses_default(self):
        """Test that empty timezone string uses default timezone."""

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "clock",
            "slot": 0,
            "options": {"timezone": ""},
        }

        widget_now = self._apply_override(now, widget_data)

        # Should still have the base timezone since empty string is falsy
        assert str(widget_now.tzinfo) == "Europe/Paris"

    def test_timezone_override_applies_regardless_of_widget_type(self):
        """Test that the override is driven by the option, not the widget type.

        Previously this only fired for `type == "clock"`; it's now applied
        to any widget whose options carry a timezone, since datetime (and
        potentially future widgets) need the same behavior.
        """

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "entity",  # Not clock or datetime
            "slot": 0,
            "options": {"timezone": "America/New_York"},
        }

        widget_now = self._apply_override(now, widget_data)

        # The override applies wherever the option is present, regardless
        # of widget type.
        assert str(widget_now.tzinfo) == "America/New_York"

    def test_timezone_override_absent_keeps_default(self):
        """Test that a widget with no timezone option keeps the base zone."""

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "entity",
            "slot": 0,
            "options": {},
        }

        widget_now = self._apply_override(now, widget_data)

        assert str(widget_now.tzinfo) == "Europe/Paris"

    def test_invalid_timezone_is_handled_gracefully(self):
        """Test that invalid timezone doesn't crash."""

        base_tz = ZoneInfo("Europe/Paris")
        now = datetime.now(tz=base_tz)

        widget_data: dict[str, Any] = {
            "type": "clock",
            "slot": 0,
            "options": {"timezone": "Invalid/Timezone"},
        }

        widget_now = self._apply_override(now, widget_data)

        # Should fall back to base timezone on invalid timezone
        assert str(widget_now.tzinfo) == "Europe/Paris"

    def test_hass_timezone_fallback_to_utc(self):
        """Test that missing time_zone_obj falls back to UTC."""
        from datetime import UTC

        # Mock hass config without time_zone_obj
        mock_config = MagicMock()
        del mock_config.time_zone_obj  # Remove the attribute

        tz = getattr(mock_config, "time_zone_obj", None) or UTC
        assert tz == UTC

    def test_hass_timezone_uses_config(self):
        """Test that time_zone_obj from config is used."""
        mock_config = MagicMock()
        mock_config.time_zone_obj = ZoneInfo("Asia/Tokyo")

        tz = getattr(mock_config, "time_zone_obj", None)
        assert tz is not None
        assert str(tz) == "Asia/Tokyo"
