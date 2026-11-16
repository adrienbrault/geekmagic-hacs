"""Preview warnings for HTML widget cells (cellcheck.py)."""

from __future__ import annotations

import pytest

from custom_components.geekmagic.cellcheck import cell_warnings, probe_text, text_overflow
from custom_components.geekmagic.const import LAYOUT_GRID_2X2
from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.websocket import async_register_websocket_commands
from custom_components.geekmagic.widgets import HtmlWidget, WidgetConfig
from custom_components.geekmagic.widgets.theme import THEMES
from scripts.generate_html_samples import (
    EXAMPLES,
    EXAMPLES_DIR,
    TAILWIND_EXAMPLES,
    widget_state,
)

requires_engine = pytest.mark.skipif(get_engine() is None, reason="blitz-py not installed")

HERO = '<div class="cell"><div style="font-size: 82px; font-weight: 800">{{ state }}</div></div>'


def html(source: str, slot: int = 0, *, tailwind: bool = False, entity: str = "") -> HtmlWidget:
    options: dict[str, object] = {"html": source, "tailwind": tailwind}
    return HtmlWidget(
        WidgetConfig(widget_type="html", slot=slot, entity_id=entity or None, options=options)
    )


class TestProbeText:
    def test_wraps_each_text_run(self) -> None:
        probed, texts = probe_text("<div>Hello <b>big</b> world</div>")
        assert list(texts.values()) == ["Hello", "big", "world"]
        assert probed.count('style="display: inline-block"') == 3

    def test_leaves_style_svg_and_icons_alone(self) -> None:
        source = (
            "<style>.a::before { content: 'x'; }</style>"
            "<svg><text>label</text></svg>"
            '<span class="icon">\U000f0335</span>'
        )
        probed, texts = probe_text(source)
        assert texts == {}
        assert probed == source

    def test_attribute_with_a_bracket(self) -> None:
        """A ``>`` inside a quoted attribute is not the end of the tag."""
        _, texts = probe_text('<div class="[&>p]:mt-1" title="a > b">text</div>')
        assert list(texts.values()) == ["text"]


@requires_engine
class TestTextOverflow:
    def test_long_text_runs_past_the_side(self) -> None:
        doc = '<div style="white-space: nowrap; font-size: 82px">unavailable</div>'
        assert text_overflow(doc, 240, 240) == ["unavailable"]

    def test_text_that_fits(self) -> None:
        doc = '<div style="font-size: 40px; text-align: center">21.5°C</div>'
        assert text_overflow(doc, 240, 240) == []

    def test_rows_clipped_off_the_bottom_are_not_reported(self) -> None:
        """A list clipped with overflow: hidden is a design, not a bleed."""
        rows = "".join(f"<div style='height: 60px'>Row {i}</div>" for i in range(8))
        doc = f"<div style='height: 240px; overflow: hidden'>{rows}</div>"
        assert text_overflow(doc, 240, 240) == []

    def test_long_text_is_shortened_in_the_report(self) -> None:
        doc = f'<div style="white-space: nowrap; font-size: 30px">{"x" * 80}</div>'
        (snippet,) = text_overflow(doc, 240, 240)
        assert len(snippet) == 32
        assert snippet.endswith("…")


@requires_engine
class TestCellWarnings:
    def test_overflow_and_unknown_classes_per_slot(self) -> None:
        layout = Grid2x2()
        layout.set_widget(0, html(HERO, 0, entity="sensor.living_temp"))
        layout.set_widget(1, html('<div class="p-2 blur-sm text-warnng">x</div>', 1, tailwind=True))
        layout.set_widget(2, html("<div>fine</div>", 2))
        states = {i: widget_state("sensor.living_temp") for i in range(3)}

        warnings = [w.as_dict() for w in cell_warnings(layout, states)]

        assert warnings == [
            {"slot": 0, "kind": "overflow", "items": ["21.5"]},
            {"slot": 1, "kind": "unknown_classes", "items": ["blur-sm", "text-warnng"]},
        ]

    def test_fit_keeps_the_same_value_inside(self) -> None:
        layout = Grid2x2()
        layout.set_widget(
            0, html('<div class="cell">{{ fit(state, max=82) }}</div>', entity="sensor.living_temp")
        )
        assert cell_warnings(layout, {0: widget_state("sensor.living_temp")}) == []

    @pytest.mark.parametrize("theme", sorted(THEMES))
    def test_no_warning_on_the_gallery(self, theme: str) -> None:
        """Every gallery template fits, in every theme: no false positives."""
        for stem, entity_id, _ in EXAMPLES:
            layout = FullscreenLayout()
            layout.theme = THEMES[theme]
            source = (EXAMPLES_DIR / f"{stem}.html").read_text()
            layout.set_widget(0, html(source, tailwind=stem in TAILWIND_EXAMPLES, entity=entity_id))
            assert cell_warnings(layout, {0: widget_state(entity_id)}) == [], stem


@requires_engine
async def test_preview_returns_warnings(hass, hass_ws_client) -> None:
    hass.states.async_set("sensor.power", "unavailable", {"friendly_name": "Power"})
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)
    widgets = [
        {"type": "html", "slot": 0, "entity_id": "sensor.power", "options": {"html": HERO}},
        {"type": "html", "slot": 1, "options": {"html": "<div>ok</div>"}},
    ]
    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/preview/render",
            "view_config": {"layout": LAYOUT_GRID_2X2, "widgets": widgets},
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    assert msg["result"]["warnings"] == [{"slot": 0, "kind": "overflow", "items": ["unavailable"]}]
