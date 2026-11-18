"""State-aware icons: derived by the widget, never injected by the sample mock.

Regression: ``MockStates`` injected the domain's plain default icon
(``mdi:lock`` for every lock), which shadowed the widget's own state-aware
resolution. ``samples/12_security.png`` therefore painted the garage door
standing open with a closed padlock, and the light/fan "off" cells in
``samples/18_domain_icons.png`` with their "on" glyph.

The mock no longer injects anything (a real HA state object carries an
``icon`` attribute only when set by hand), so samples exercise exactly the
resolution a real dashboard does: device-class state icon, explicit
``icon``, the domain's state→icon map, then the domain's plain glyph.
"""

from __future__ import annotations

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.icons import MDI_CODEPOINTS
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.helpers import resolve_entity_icon
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from scripts.mock_hass import MockHass, create_security_states


def _glyph(icon: str) -> str:
    """The HTML entity an MDI icon paints as."""
    return f"&#x{MDI_CODEPOINTS[icon.removeprefix('mdi:')]};"


def _entity(mock: MockHass, entity_id: str) -> EntityState:
    """The entity as a widget would see it (attributes included)."""
    state = mock.states.get(entity_id)
    assert state is not None
    return EntityState(entity_id, state.state, dict(state.attributes))


def _render_entity(
    entity_id: str,
    state: str,
    attributes: dict | None = None,
    size: tuple[int, int] = (240, 240),
) -> str:
    """Render an Entity card for this state, as the device would."""
    widget = EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id=entity_id))
    entity = EntityState(entity_id, state, attributes or {})
    ctx = CellContext(width=size[0], height=size[1], slot_index=0, theme=DEFAULT_THEME)
    return widget.render_html(ctx, WidgetState(entity=entity))


class TestResolveEntityIcon:
    """Every domain HA gives state icons gets them here too."""

    @pytest.mark.parametrize(
        ("domain", "state", "expected"),
        [
            # lock — the original regression
            ("lock", "unlocked", "mdi:lock-open-variant"),
            ("lock", "locked", "mdi:lock"),
            ("lock", "jammed", "mdi:lock-alert"),
            # alarm: the state IS the meaning (`disarmed` is not `armed_home`)
            ("alarm_control_panel", "disarmed", "mdi:shield-off"),
            ("alarm_control_panel", "armed_home", "mdi:shield-home"),
            ("alarm_control_panel", "armed_away", "mdi:shield-lock"),
            ("alarm_control_panel", "triggered", "mdi:bell-ring"),
            # valve
            ("valve", "open", "mdi:valve-open"),
            ("valve", "closed", "mdi:valve-closed"),
            ("valve", "opening", "mdi:valve"),
            # update
            ("update", "on", "mdi:package-up"),
            ("update", "off", "mdi:package"),
            # presence
            ("person", "home", "mdi:account"),
            ("person", "not_home", "mdi:account-arrow-right"),
            ("device_tracker", "not_home", "mdi:account-arrow-right"),
            # weather / calendar / remote / camera
            ("weather", "rainy", "mdi:weather-rainy"),
            ("weather", "sunny", "mdi:weather-sunny"),
            ("calendar", "off", "mdi:calendar-blank"),
            ("calendar", "on", "mdi:calendar-check"),
            ("remote", "off", "mdi:remote-off"),
            ("camera", "off", "mdi:video-off"),
            # already-covered domains still work
            ("light", "off", "mdi:lightbulb-off"),
            ("cover", "closed", "mdi:card"),  # generic cover, HA core's own default
            ("media_player", "off", "mdi:cast-off"),
            ("script", "on", "mdi:script-text-play"),
            ("switch", "off", "mdi:toggle-switch-variant-off"),
        ],
    )
    def test_domain_state_icon(self, domain: str, state: str, expected: str) -> None:
        assert resolve_entity_icon(domain, state) == expected

    def test_binary_sensor_device_class_state_icon(self) -> None:
        """A tripped motion sensor is not painted with its resting glyph."""
        assert resolve_entity_icon("binary_sensor", "off", "motion") == "mdi:motion-sensor-off"
        assert resolve_entity_icon("binary_sensor", "on", "motion") == "mdi:motion-sensor"

    def test_binary_sensor_state_icon_beats_explicit_icon(self) -> None:
        """The device-class glyph is more specific than a hand-set icon."""
        assert (
            resolve_entity_icon("binary_sensor", "on", "door", icon="mdi:home") == "mdi:door-open"
        )

    def test_explicit_icon_wins_for_other_domains(self) -> None:
        """A hand-set icon is left alone — the state never overrides it."""
        assert resolve_entity_icon("lock", "unlocked", icon="mdi:garage") == "mdi:garage"

    def test_cover_device_class_uses_its_own_glyphs(self) -> None:
        """A garage door reads as a garage, closed or open."""
        assert resolve_entity_icon("cover", "closed", "garage") == "mdi:garage"
        assert resolve_entity_icon("cover", "open", "garage") == "mdi:garage-open"

    def test_sensor_device_class_glyph(self) -> None:
        """A sensor with no state map still gets its device-class glyph."""
        assert resolve_entity_icon("sensor", "21.5", "temperature") == "mdi:thermometer"

    def test_domain_without_state_map_keeps_its_default(self) -> None:
        """No state map for this domain leaves its plain glyph."""
        assert resolve_entity_icon("scene", "on") == "mdi:palette"

    def test_unknown_icon_for_status_rows(self) -> None:
        """Status rows pass domain_default=False: no glyph means no glyph."""
        assert resolve_entity_icon("scene", "on", domain_default=False) is None


class TestEntityWidgetPaintsStateIcons:
    """The Entity card derives the glyph itself (it used to paint none)."""

    def test_unlocked_lock_renders_the_open_padlock(self) -> None:
        fragment = _render_entity("lock.garage", "unlocked")
        assert _glyph("mdi:lock-open-variant") in fragment
        assert _glyph("mdi:lock") not in fragment

    def test_locked_lock_renders_the_closed_padlock(self) -> None:
        fragment = _render_entity("lock.front_door", "locked")
        assert _glyph("mdi:lock") in fragment
        assert _glyph("mdi:lock-open-variant") not in fragment

    @pytest.mark.parametrize(
        ("entity_id", "state", "icon"),
        [
            ("alarm_control_panel.home", "disarmed", "mdi:shield-off"),
            ("alarm_control_panel.home", "triggered", "mdi:bell-ring"),
            ("valve.irrigation", "closed", "mdi:valve-closed"),
            ("update.core", "on", "mdi:package-up"),
            ("person.ada", "not_home", "mdi:account-arrow-right"),
            ("weather.home", "rainy", "mdi:weather-rainy"),
            ("camera.front", "off", "mdi:video-off"),
            ("light.bedroom", "off", "mdi:lightbulb-off"),
            ("fan.ceiling", "on", "mdi:fan"),
        ],
    )
    def test_domain_glyph_is_painted(self, entity_id: str, state: str, icon: str) -> None:
        assert _glyph(icon) in _render_entity(entity_id, state)

    def test_explicit_icon_attribute_is_painted(self) -> None:
        fragment = _render_entity(
            "lock.garage", "unlocked", {"icon": "mdi:garage", "friendly_name": "Garage"}
        )
        assert _glyph("mdi:garage") in fragment
        assert _glyph("mdi:lock-open-variant") not in fragment

    def test_configured_off_icon_still_wins(self) -> None:
        """A user's on/off icon override outranks the derived glyph."""
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="lock.garage",
                options={"on_icon": "mdi:door-open", "off_icon": "mdi:door-closed"},
            )
        )
        entity = EntityState("lock.garage", "unlocked", {"friendly_name": "Garage"})
        ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(ctx, WidgetState(entity=entity))
        assert _glyph("mdi:door-open") in fragment
        assert _glyph("mdi:lock-open-variant") not in fragment


class TestMockDoesNotInjectIcons:
    """A real state object carries ``icon`` only when someone set it."""

    def test_no_icon_attribute_is_added(self) -> None:
        hass = MockHass()
        hass.states.set("lock.garage", "unlocked", {"friendly_name": "Garage"})
        state = hass.states.get("lock.garage")
        assert state is not None
        assert "icon" not in state.attributes

    def test_explicit_icon_is_kept(self) -> None:
        hass = MockHass()
        hass.states.set("lock.garage", "unlocked", {"icon": "mdi:garage"})
        state = hass.states.get("lock.garage")
        assert state is not None
        assert state.attributes["icon"] == "mdi:garage"


class TestSecuritySampleReadsLocksStateAware:
    """The sample's door list paints each lock with its own state glyph."""

    def test_unlocked_garage_keeps_its_open_padlock(self) -> None:
        """Locked doors keep the closed padlock; the open garage gets the open one."""
        hass = MockHass()
        create_security_states(hass)
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "title": "Doors",
                    "entities": [
                        ("lock.front_door", "Front Door"),
                        ("lock.back_door", "Back Door"),
                        ("lock.garage", "Garage"),
                    ],
                    "on_color": [255, 59, 48],
                    "off_color": [52, 199, 89],
                    "on_text": "OPEN",
                    "off_text": "LOCKED",
                },
            )
        )
        ctx = CellContext(width=240, height=110, slot_index=0, theme=DEFAULT_THEME)
        state = WidgetState(
            entities={
                entity_id: _entity(hass, entity_id)
                for entity_id in ("lock.front_door", "lock.back_door", "lock.garage")
            }
        )

        rows = widget._resolve_rows(ctx, state)

        assert [row.icon for row in rows] == [
            "mdi:lock",
            "mdi:lock",
            "mdi:lock-open-variant",
        ]
        assert [row.state_text for row in rows] == ["LOCKED", "LOCKED", "OPEN"]
