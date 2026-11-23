"""Skipping views in View Cycling, and showing a view for a while (issue #160).

A skipped view stays assigned: the Display select, the panel and
``geekmagic.show_view`` still show it, but View Cycling and next/previous
step over it. ``show_view`` with a duration holds a view, then goes back
to what was on screen before.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.geekmagic.const import (
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SKIPPED_VIEWS,
    CONF_WIDGETS,
    DOMAIN,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator

VIEWS = ["view_a", "view_b", "view_c"]
INTERVAL = 30


@pytest.fixture
def store(hass):
    views = {view_id: {"name": view_id[-1].upper(), CONF_WIDGETS: []} for view_id in VIEWS}
    store = MagicMock()
    store.get_view = MagicMock(side_effect=views.get)
    hass.data.setdefault(DOMAIN, {})["store"] = store
    return store


@pytest.fixture
def device():
    device = MagicMock()
    device.host = "192.168.1.100"
    device.display_rendered_dashboard = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=None)
    device.set_theme_custom = AsyncMock()
    device.set_theme = AsyncMock()
    device.is_builtin_theme = MagicMock(return_value=False)
    return device


def _coordinator(hass, device, skipped=(), cycle=INTERVAL) -> GeekMagicCoordinator:
    coordinator = GeekMagicCoordinator(
        hass,
        device,
        {
            "assigned_views": list(VIEWS),
            CONF_SKIPPED_VIEWS: list(skipped),
            CONF_SCREEN_CYCLE_INTERVAL: cycle,
            CONF_REFRESH_INTERVAL: 10,
        },
    )
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def _cycle(coordinator) -> str | None:
    """Run one update after a full cycle interval; the view then on screen."""
    coordinator._last_screen_change -= INTERVAL + 1
    with patch.object(
        coordinator, "_render_display", return_value=(b"jpeg", b"png", "dashboard.jpg")
    ):
        await coordinator._async_update_data()
    return coordinator.current_view_id


class TestSkipping:
    async def test_cycling_steps_over_a_skipped_view(self, hass, store, device):
        coordinator = _coordinator(hass, device, skipped=["view_b"])

        assert [await _cycle(coordinator) for _ in range(3)] == ["view_c", "view_a", "view_c"]

    async def test_cycling_moves_off_a_skipped_view_shown_on_request(self, hass, store, device):
        coordinator = _coordinator(hass, device, skipped=["view_b"])
        await coordinator.async_show_view("view_b")

        assert await _cycle(coordinator) == "view_c"

    async def test_nothing_else_cycles_so_the_view_stays(self, hass, store, device):
        coordinator = _coordinator(hass, device, skipped=["view_b", "view_c"])

        assert await _cycle(coordinator) == "view_a"

    async def test_next_and_previous_step_over_skipped_views(self, hass, store, device):
        coordinator = _coordinator(hass, device, skipped=["view_b"])

        await coordinator.async_next_screen()
        assert coordinator.current_view_id == "view_c"
        await coordinator.async_previous_screen()
        assert coordinator.current_view_id == "view_a"

    async def test_next_with_nothing_to_step_to_reshows_the_view(self, hass, store, device):
        """As with a single view: the button still leaves a built-in mode."""
        coordinator = _coordinator(hass, device, skipped=["view_b", "view_c"])
        coordinator.set_display_mode("builtin", 1)

        await coordinator.async_next_screen()

        assert coordinator.display_mode == "custom"
        assert coordinator.current_view_id == "view_a"

    async def test_a_built_in_hands_back_to_the_only_cycled_view(self, hass, store, device):
        """A built-in is one stop of the rotation, even when one view cycles."""
        coordinator = _coordinator(hass, device, skipped=["view_b", "view_c"])
        coordinator.set_display_mode("builtin", 1)

        assert await _cycle(coordinator) == "view_a"
        assert coordinator.display_mode == "custom"

    def test_update_pace_ignores_cycling_when_nothing_cycles(self, hass, store, device):
        """A 5 s cycle sets the pace only while there is something to cycle."""
        assert _coordinator(hass, device, cycle=5)._tick_interval() == 5
        everything = _coordinator(hass, device, skipped=VIEWS, cycle=5)
        assert everything._tick_interval() == 10
        one_left = _coordinator(hass, device, skipped=["view_b", "view_c"], cycle=5)
        assert one_left._tick_interval() == 5

    def test_skipping_rebuilds_nothing_and_forces_no_upload(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        coordinator._last_push = ((b"jpeg", "dashboard.jpg", False, "custom"), 0.0)
        layouts = list(coordinator._layouts)

        coordinator.update_options({**coordinator.options, CONF_SKIPPED_VIEWS: ["view_b"]})

        assert coordinator.skipped_view_ids == ["view_b"]
        assert coordinator._layouts == layouts
        assert coordinator._last_push is not None

    async def test_legacy_screens_still_cycle(self, hass, device):
        """Legacy configs have no view ids: every screen cycles."""
        coordinator = GeekMagicCoordinator(
            hass,
            device,
            {
                CONF_SCREEN_CYCLE_INTERVAL: INTERVAL,
                "screens": [
                    {"name": "One", "layout": "grid_2x2", "widgets": []},
                    {"name": "Two", "layout": "grid_2x2", "widgets": []},
                ],
            },
        )
        coordinator.async_request_refresh = AsyncMock()

        await _cycle(coordinator)

        assert coordinator.current_screen == 1


async def _expire(hass, seconds: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds + 1))
    await hass.async_block_till_done()


class TestShowFor:
    async def test_holds_the_view_then_goes_back(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view("view_b")

        await coordinator.async_show_view_for("view_c", 600)

        assert coordinator.held_view_id == "view_c"
        # View Cycling waits, however long it has been
        assert await _cycle(coordinator) == "view_c"
        await _expire(hass, 600)
        assert coordinator.held_view_id is None
        assert coordinator.current_view_id == "view_b"

    async def test_without_duration_it_is_a_plain_show(self, hass, store, device):
        coordinator = _coordinator(hass, device)

        await coordinator.async_show_view_for("view_c", None)

        assert coordinator.held_view_id is None
        assert await _cycle(coordinator) == "view_a"

    async def test_a_skipped_view_can_be_held(self, hass, store, device):
        coordinator = _coordinator(hass, device, skipped=["view_c"])

        await coordinator.async_show_view_for("view_c", 600)
        assert await _cycle(coordinator) == "view_c"
        await _expire(hass, 600)

        assert coordinator.current_view_id == "view_a"

    async def test_another_choice_ends_the_hold_where_it_is(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_c", 600)

        await coordinator.async_show_view("view_b")
        await _expire(hass, 600)

        assert coordinator.held_view_id is None
        assert coordinator.current_view_id == "view_b"

    async def test_next_button_ends_the_hold(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_b", 600)

        await coordinator.async_next_screen()
        await _expire(hass, 600)

        assert coordinator.current_view_id == "view_c"

    async def test_a_new_hold_keeps_the_first_way_back(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_b", 600)

        await coordinator.async_show_view_for("view_c", 60)
        await _expire(hass, 60)

        assert coordinator.current_view_id == "view_a"
        await _expire(hass, 600)
        assert coordinator.current_view_id == "view_a"

    async def test_goes_back_to_a_built_in_mode(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        coordinator.set_display_mode("builtin", 2)

        await coordinator.async_show_view_for("view_b", 60)
        assert coordinator.display_mode == "custom"
        await _expire(hass, 60)

        device.set_theme.assert_awaited_once_with(2)
        assert coordinator.display_mode == "builtin"
        assert coordinator.builtin_theme == 2

    async def test_unassigning_the_held_view_ends_the_hold(self, hass, store, device):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_c", 600)

        coordinator.update_options({**coordinator.options, "assigned_views": ["view_a", "view_b"]})

        assert coordinator.held_view_id is None

    async def test_ends_quietly_when_the_display_is_unreachable(self, hass, store, device, caplog):
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_c", 60)
        device.set_theme_custom.side_effect = TimeoutError("unreachable")

        await _expire(hass, 60)

        assert "Failed to show the view again" in caplog.text
        assert coordinator.held_view_id is None

    async def test_ends_while_paused(self, hass, store, device):
        """The way back is taken even while paused; it shows on resume."""
        coordinator = _coordinator(hass, device)
        await coordinator.async_show_view_for("view_c", 60)
        coordinator._paused = True

        await _expire(hass, 60)

        assert coordinator.current_view_id == "view_a"
