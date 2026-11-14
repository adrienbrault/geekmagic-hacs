"""The panel's device controls: what is on screen, and showing a view now.

Driven through the websocket API on a real (mocked-HTTP) integration, the
way the panel calls it.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from tests.test_ha_integration import setup_integration


class _Panel:
    def __init__(self, client) -> None:
        self.client = client

    async def call(self, **message) -> dict:
        await self.client.send_json_auto_id(message)
        msg = await self.client.receive_json()
        assert msg["success"], msg
        return msg["result"]

    async def error(self, **message) -> dict:
        await self.client.send_json_auto_id(message)
        msg = await self.client.receive_json()
        assert not msg["success"], msg
        return msg["error"]

    async def create_view(self, name: str) -> str:
        result = await self.call(type="geekmagic/views/create", name=name, widgets=[])
        return result["view"]["id"]

    async def device(self) -> dict:
        return (await self.call(type="geekmagic/devices/list"))["devices"][0]


async def _setup(hass, aioclient_mock, hass_ws_client) -> tuple[_Panel, list[str], str]:
    """A device rotating through four views, two of them named alike and
    one named like a built-in mode."""
    # As the config flow creates entries (without "screens", options read as
    # the legacy single-screen format and assigned views are ignored).
    await setup_integration(hass, aioclient_mock, theme=3, options={"screens": []})
    panel = _Panel(await hass_ws_client(hass))
    views = [
        await panel.create_view("Clock"),  # also an Ultra built-in mode name
        await panel.create_view("Same"),
        await panel.create_view("Same"),
        await panel.create_view("Other"),
    ]
    entry_id = (await panel.device())["entry_id"]
    await panel.call(type="geekmagic/devices/assign_views", entry_id=entry_id, view_ids=views)
    await hass.async_block_till_done()
    return panel, views, entry_id


async def test_devices_list_reports_screen_and_controls(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    panel, views, _ = await _setup(hass, aioclient_mock, hass_ws_client)
    device = await panel.device()

    assert device["display_mode"] == "custom"
    assert device["current_view_id"] == views[0]
    assert device["builtin_mode"] is None
    entities = device["entities"]
    assert set(entities) == {
        "display",
        "brightness",
        "cycle_interval",
        "view_cycling",
        "active",
        "status",
        "preview",
    }
    for entity_id in entities.values():
        assert hass.states.get(entity_id) is not None, entity_id


async def test_devices_list_follows_renamed_entities(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    from homeassistant.helpers import entity_registry as er

    panel, _, _ = await _setup(hass, aioclient_mock, hass_ws_client)
    old = (await panel.device())["entities"]["brightness"]
    er.async_get(hass).async_update_entity(old, new_entity_id="number.desk_brightness")
    await hass.async_block_till_done()

    assert (await panel.device())["entities"]["brightness"] == "number.desk_brightness"


async def test_show_view_by_id_picks_that_exact_view(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    """By name, the second "Same" is unreachable and "Clock" is a built-in."""
    panel, views, entry_id = await _setup(hass, aioclient_mock, hass_ws_client)

    for view_id in (views[2], views[0]):
        result = await panel.call(
            type="geekmagic/devices/show_view", entry_id=entry_id, view_id=view_id
        )
        await hass.async_block_till_done()
        assert result["current_view_id"] == view_id
        device = await panel.device()
        assert device["display_mode"] == "custom"
        assert device["current_view_id"] == view_id


async def test_show_view_updates_the_display_select(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    panel, views, entry_id = await _setup(hass, aioclient_mock, hass_ws_client)
    select = (await panel.device())["entities"]["display"]
    assert hass.states.get(select).state == "Clock"

    await panel.call(type="geekmagic/devices/show_view", entry_id=entry_id, view_id=views[3])
    await hass.async_block_till_done()

    assert hass.states.get(select).state == "Other"


async def test_show_view_refuses_an_unassigned_view(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    panel, views, entry_id = await _setup(hass, aioclient_mock, hass_ws_client)
    stray = await panel.create_view("Not assigned")

    error = await panel.error(type="geekmagic/devices/show_view", entry_id=entry_id, view_id=stray)

    assert error["code"] == "not_assigned"
    assert (await panel.device())["current_view_id"] == views[0]


async def test_reordering_keeps_the_view_on_screen(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    """Reordering used to keep the index, so the screen jumped to another view."""
    panel, views, entry_id = await _setup(hass, aioclient_mock, hass_ws_client)
    await panel.call(type="geekmagic/devices/show_view", entry_id=entry_id, view_id=views[3])
    await hass.async_block_till_done()

    reordered = [views[3], views[0], views[1], views[2]]
    await panel.call(type="geekmagic/devices/assign_views", entry_id=entry_id, view_ids=reordered)
    await hass.async_block_till_done()

    assert (await panel.device())["current_view_id"] == views[3]


async def test_removing_the_view_on_screen_moves_on(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    panel, views, entry_id = await _setup(hass, aioclient_mock, hass_ws_client)
    await panel.call(type="geekmagic/devices/show_view", entry_id=entry_id, view_id=views[3])
    await hass.async_block_till_done()

    await panel.call(type="geekmagic/devices/assign_views", entry_id=entry_id, view_ids=views[:3])
    await hass.async_block_till_done()

    assert (await panel.device())["current_view_id"] in views[:3]
