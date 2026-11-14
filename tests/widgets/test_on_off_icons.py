"""State-specific icons: ``on_icon`` / ``off_icon`` (issue #15).

Precedence everywhere: the configured icon for the current state > the
generic ``icon`` option > the icon Home Assistant derives for the
entity. Each widget decides "on" and "off" with the verdict it already
uses for its tint, so glyph and colour always switch together.
"""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.icons import get_mdi_char
from custom_components.geekmagic.widgets import WIDGET_TYPE_SCHEMAS
from custom_components.geekmagic.widgets.base import Widget, WidgetConfig
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.helpers import get_domain_state_icon
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

ON = "mdi:lightbulb-on"
# Not HA's own light-off glyph (mdi:lightbulb-off), so a fallback to the
# HA icon can never pass for the configured one.
OFF = "mdi:lightbulb-off-outline"
GENERIC = "mdi:star"

# Every Status layout carries the glyph: stack, strip, compact.
_STATUS_CELLS = [(240, 240), (228, 74), (74, 56)]


def glyph(icon: str | None) -> str:
    """The HTML entity mdi_span emits for an icon."""
    assert icon
    return f"&#x{ord(get_mdi_char(icon)):X};"


def light(state: str, **attrs: Any) -> EntityState:
    return EntityState(
        entity_id="light.lamp", state=state, attributes={"friendly_name": "Lamp", **attrs}
    )


def ctx_for(width: int = 240, height: int = 240) -> CellContext:
    return CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)


def render(
    cls: type[Widget], entity: EntityState | None, ctx: CellContext | None = None, **options
) -> str:
    widget = cls(
        WidgetConfig(
            widget_type=cls.WIDGET_TYPE,
            slot=0,
            entity_id="light.lamp",
            options=options,
        )
    )
    return widget.render_html(ctx or ctx_for(), WidgetState(entity=entity))


def test_icons_are_distinct() -> None:
    """Guard the fixtures: every glyph used here must be its own character."""
    ha_on = get_domain_state_icon("light", "on")
    ha_off = get_domain_state_icon("light", "off")
    assert ha_on
    assert ha_off
    glyphs = {glyph(i) for i in (ON, OFF, GENERIC, ha_on, ha_off)}
    assert len(glyphs) == 5


@pytest.mark.parametrize("widget_type", ["status", "entity"])
def test_schema_exposes_icon_pickers(widget_type: str) -> None:
    options = {o["key"]: o for o in WIDGET_TYPE_SCHEMAS[widget_type]["options"]}
    assert options["on_icon"]["type"] == "icon"
    assert options["off_icon"]["type"] == "icon"
    # No default: an unset state icon must fall through to `icon`.
    assert "default" not in options["on_icon"]
    assert "default" not in options["off_icon"]


# ============================================================================
# Status
# ============================================================================


class TestStatusOnOffIcons:
    @pytest.mark.parametrize("size", _STATUS_CELLS)
    def test_on_state_uses_on_icon(self, size: tuple[int, int]) -> None:
        html = render(StatusWidget, light("on"), ctx_for(*size), on_icon=ON, off_icon=OFF)
        assert glyph(ON) in html
        assert glyph(OFF) not in html

    @pytest.mark.parametrize("size", _STATUS_CELLS)
    def test_off_state_uses_off_icon(self, size: tuple[int, int]) -> None:
        html = render(StatusWidget, light("off"), ctx_for(*size), on_icon=ON, off_icon=OFF)
        assert glyph(OFF) in html
        assert glyph(ON) not in html

    def test_icon_only_mode(self) -> None:
        html = render(StatusWidget, light("on"), on_icon=ON, off_icon=OFF, show_status_text=False)
        assert glyph(ON) in html

    @pytest.mark.parametrize("state", ["open", "home", "up", "true"])
    def test_every_on_state_counts(self, state: str) -> None:
        html = render(StatusWidget, light(state), on_icon=ON, off_icon=OFF)
        assert glyph(ON) in html

    @pytest.mark.parametrize("state", ["unavailable", "unknown"])
    def test_unavailable_follows_the_off_verdict(self, state: str) -> None:
        """The widget already shows OFF in the off tint here; the glyph agrees."""
        html = render(StatusWidget, light(state), on_icon=ON, off_icon=OFF)
        assert ">OFF<" in html
        assert glyph(OFF) in html

    def test_missing_entity_follows_the_off_verdict(self) -> None:
        html = render(StatusWidget, None, on_icon=ON, off_icon=OFF)
        assert glyph(OFF) in html

    def test_state_icon_beats_generic_icon(self) -> None:
        html = render(StatusWidget, light("on"), icon=GENERIC, on_icon=ON)
        assert glyph(ON) in html
        assert glyph(GENERIC) not in html

    def test_unset_state_icon_falls_back_to_generic_icon(self) -> None:
        html = render(StatusWidget, light("off"), icon=GENERIC, on_icon=ON)
        assert glyph(GENERIC) in html
        assert glyph(ON) not in html

    def test_unset_state_icon_falls_back_to_ha_icon(self) -> None:
        html = render(StatusWidget, light("off"), on_icon=ON)
        assert glyph(get_domain_state_icon("light", "off")) in html

    def test_cleared_picker_falls_back(self) -> None:
        """The icon picker stores "" when cleared — that is unset."""
        html = render(StatusWidget, light("on"), icon=GENERIC, on_icon="", off_icon="")
        assert glyph(GENERIC) in html

    @pytest.mark.parametrize("state", ["on", "off", "unavailable"])
    @pytest.mark.parametrize("size", _STATUS_CELLS)
    @pytest.mark.parametrize("base", [{}, {"icon": GENERIC}])
    def test_existing_configs_render_identically(
        self, state: str, size: tuple[int, int], base: dict[str, Any]
    ) -> None:
        legacy = render(StatusWidget, light(state), ctx_for(*size), **base)
        unset = render(
            StatusWidget, light(state), ctx_for(*size), **base, on_icon=None, off_icon=""
        )
        assert legacy == unset


# ============================================================================
# Entity
# ============================================================================


class TestEntityOnOffIcons:
    def test_on_state_uses_on_icon(self) -> None:
        html = render(EntityWidget, light("on"), on_icon=ON, off_icon=OFF)
        assert glyph(ON) in html
        assert glyph(OFF) not in html

    @pytest.mark.parametrize("state", ["off", "closed", "away", "idle", "paused"])
    def test_muted_states_use_off_icon(self, state: str) -> None:
        """ "Off" is exactly the set that greys the icon."""
        html = render(EntityWidget, light(state), on_icon=ON, off_icon=OFF)
        assert glyph(OFF) in html
        assert glyph(ON) not in html
        assert "var(--muted)" in html

    @pytest.mark.parametrize("state", ["playing", "heat", "42"])
    def test_other_live_states_use_on_icon(self, state: str) -> None:
        html = render(EntityWidget, light(state), on_icon=ON, off_icon=OFF)
        assert glyph(ON) in html

    @pytest.mark.parametrize("state", ["unavailable", "unknown"])
    def test_absent_states_are_neither_on_nor_off(self, state: str) -> None:
        html = render(EntityWidget, light(state), icon=GENERIC, on_icon=ON, off_icon=OFF)
        assert glyph(GENERIC) in html
        assert glyph(ON) not in html
        assert glyph(OFF) not in html

    def test_missing_entity_is_neither_on_nor_off(self) -> None:
        html = render(EntityWidget, None, icon=GENERIC, on_icon=ON, off_icon=OFF)
        assert glyph(GENERIC) in html
        assert glyph(OFF) not in html

    def test_state_icon_beats_override(self) -> None:
        html = render(EntityWidget, light("off"), icon=GENERIC, off_icon=OFF)
        assert glyph(OFF) in html
        assert glyph(GENERIC) not in html

    def test_unset_state_icon_falls_back_to_override(self) -> None:
        html = render(EntityWidget, light("on"), icon=GENERIC, off_icon=OFF)
        assert glyph(GENERIC) in html

    def test_unset_state_icon_falls_back_to_entity_icon(self) -> None:
        html = render(EntityWidget, light("on", icon="mdi:desk-lamp"), off_icon=OFF)
        assert glyph("mdi:desk-lamp") in html

    def test_state_icon_shows_like_the_override_with_show_icon_off(self) -> None:
        """A configured glyph is explicit, exactly like ``icon``."""
        html = render(EntityWidget, light("on"), on_icon=ON, show_icon=False)
        assert glyph(ON) in html

    @pytest.mark.parametrize("state", ["on", "off", "unavailable", "23.5"])
    @pytest.mark.parametrize("base", [{}, {"icon": GENERIC}, {"show_icon": False}])
    def test_existing_configs_render_identically(self, state: str, base: dict[str, Any]) -> None:
        entity = light(state, icon="mdi:desk-lamp")
        legacy = render(EntityWidget, entity, **base)
        unset = render(EntityWidget, entity, **base, on_icon="", off_icon=None)
        assert legacy == unset
