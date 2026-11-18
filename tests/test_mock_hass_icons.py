"""The sample mock resolves icons the way a widget does: per state.

Regression: ``MockStates`` injected the domain's plain default icon
(``mdi:lock`` for every lock), which shadowed the widget's own state-aware
fallback. ``samples/12_security.png`` therefore painted the garage door
standing open with a closed padlock, and the light/fan "off" cells in
``samples/18_domain_icons.png`` with their "on" glyph.
"""

from __future__ import annotations

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from scripts.mock_hass import MockHass, create_security_states


def _entity(mock: MockHass, entity_id: str) -> EntityState:
    """The entity as a widget would see it (attributes included)."""
    state = mock.states.get(entity_id)
    assert state is not None
    return EntityState(entity_id, state.state, dict(state.attributes))


class TestMockStateIcons:
    """Auto-resolved icons follow the state, not just the domain."""

    def test_lock_states_get_their_own_padlock(self) -> None:
        """An unlocked lock reads as an open padlock, a locked one as closed."""
        hass = MockHass()
        hass.states.set("lock.front_door", "locked", {"friendly_name": "Front Door"})
        hass.states.set("lock.garage", "unlocked", {"friendly_name": "Garage"})

        assert _entity(hass, "lock.front_door").icon == "mdi:lock"
        assert _entity(hass, "lock.garage").icon == "mdi:lock-open-variant"

    def test_binary_sensor_states_get_their_own_icon(self) -> None:
        """A tripped motion sensor is not painted with its resting glyph."""
        hass = MockHass()
        hass.states.set("binary_sensor.quiet", "off", {"device_class": "motion"})
        hass.states.set("binary_sensor.tripped", "on", {"device_class": "motion"})

        assert _entity(hass, "binary_sensor.quiet").icon == "mdi:motion-sensor-off"
        assert _entity(hass, "binary_sensor.tripped").icon == "mdi:motion-sensor"

    def test_explicit_icon_still_wins(self) -> None:
        """A hand-set icon is left alone — the state never overrides it."""
        hass = MockHass()
        hass.states.set(
            "lock.garage", "unlocked", {"friendly_name": "Garage", "icon": "mdi:garage"}
        )

        assert _entity(hass, "lock.garage").icon == "mdi:garage"

    def test_domain_state_icon_overrides_the_domain_default(self) -> None:
        """A domain's own state glyph wins over its plain default."""
        hass = MockHass()
        hass.states.set("script.party", "on", {"friendly_name": "Party"})
        hass.states.set("script.quiet", "off", {"friendly_name": "Quiet"})

        assert _entity(hass, "script.party").icon == "mdi:script-text-play"
        assert _entity(hass, "script.quiet").icon == "mdi:script-text"

    def test_domain_without_state_icons_keeps_its_default(self) -> None:
        """No state map for this domain leaves its default icon."""
        hass = MockHass()
        hass.states.set("sensor.mystery", "42", {"friendly_name": "Mystery"})

        assert _entity(hass, "sensor.mystery").icon == "mdi:eye"


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
