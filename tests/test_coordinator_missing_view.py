"""A view the store lost must not shift the view of every screen after it.

``assigned_views`` is an option and can name a view that was deleted from
another display's entry (or from storage), while the layouts are only
built for the views the store still has. Every screen index past the gap
then named the neighbouring view: the Display select said "Kitchen" while
the device drew Garden, ``current_view_id`` reported a view that no
longer exists, and the panel's "show this view" landed past the end of
the list and rendered the welcome screen.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.geekmagic.const import CONF_WIDGETS
from custom_components.geekmagic.coordinator import GeekMagicCoordinator

MISSING = "view_deleted"


@pytest.fixture
def store_views(hass):
    """A store with two views, one of them deleted from an entry's list."""
    views = {
        "view_kitchen": {"name": "Kitchen", CONF_WIDGETS: []},
        "view_garden": {"name": "Garden", CONF_WIDGETS: []},
    }
    store = MagicMock()
    store.get_view = MagicMock(side_effect=views.get)
    hass.data.setdefault("geekmagic", {})["store"] = store
    return views


@pytest.fixture
def coordinator(hass, store_views):
    """A display assigned a deleted view followed by two live ones."""
    device = MagicMock()
    device.set_theme_custom = AsyncMock()
    coordinator = GeekMagicCoordinator(
        hass,
        device,
        {"assigned_views": [MISSING, "view_kitchen", "view_garden"]},
    )
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def test_one_layout_per_live_view(coordinator):
    """The deleted view gets no screen, so the list is shorter than the option."""
    assert coordinator.screen_count == 2
    assert coordinator.screen_view_ids == ["view_kitchen", "view_garden"]


def test_current_screen_name_and_view_id_agree(coordinator):
    """Screen 0 is Kitchen, not the deleted view nor the one after it."""
    assert coordinator.current_screen_name == "Kitchen"
    assert coordinator.current_view_id == "view_kitchen"


def test_second_screen_is_the_second_live_view(coordinator):
    """Screen 1 is Garden: the gap must not push every index one view back."""
    coordinator.set_current_screen(1)

    assert coordinator.current_screen_name == "Garden"
    assert coordinator.current_view_id == "view_garden"


@pytest.mark.asyncio
async def test_show_view_reaches_the_view_it_names(coordinator):
    """Showing Garden now must render Garden, not land past the last screen."""
    await coordinator.async_show_view("view_garden")

    assert coordinator.current_screen == 1
    assert 0 <= coordinator.current_screen < coordinator.screen_count
    assert coordinator.current_view_id == "view_garden"


@pytest.mark.asyncio
async def test_show_view_refuses_a_view_the_store_lost(coordinator):
    """The deleted view has no screen to show, so it is not assignable."""
    with pytest.raises(ValueError, match="is not assigned"):
        await coordinator.async_show_view(MISSING)


def test_update_options_keeps_the_view_on_screen(coordinator):
    """Re-saving the assignments keeps drawing the view that was on screen."""
    coordinator.set_current_screen(1)

    coordinator.update_options({"assigned_views": [MISSING, "view_kitchen", "view_garden"]})

    assert coordinator.screen_count == 2
    assert coordinator.current_view_id == "view_garden"
