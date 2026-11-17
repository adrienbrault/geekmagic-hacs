"""Preview warnings for HTML widget cells (cellcheck.py)."""

from __future__ import annotations

import copy

import pytest

from custom_components.geekmagic import cellcheck
from custom_components.geekmagic.cellcheck import cell_warnings, probe_text, text_overflow
from custom_components.geekmagic.const import LAYOUT_GRID_2X2
from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.websocket import async_register_websocket_commands
from custom_components.geekmagic.widgets import HtmlWidget, WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import THEMES
from scripts.generate_html_samples import (
    ENTITIES,
    EXAMPLE_ENTITIES,
    EXAMPLE_FORECASTS,
    EXAMPLE_HISTORIES,
    EXAMPLE_PICTURES,
    EXAMPLES,
    EXAMPLES_DIR,
    NOW,
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


def fullscreen(source: str, *, tailwind: bool = False, entity: str = "", theme: str = "watchos"):
    layout = FullscreenLayout()
    layout.theme = THEMES[theme]
    layout.set_widget(0, html(source, tailwind=tailwind, entity=entity))
    return layout


class TestProbeText:
    def test_probes_text_that_fills_its_element(self) -> None:
        """Text beside other elements isn't wrapped: a probe would be a new child."""
        probed, texts = probe_text("<div>Hello <b>big</b> world</div><p>alone</p>")
        assert list(texts.values()) == ["big", "alone"]
        assert probed.count('style="all: unset; display: inline-block"') == 2

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

    def test_void_elements_and_entities(self) -> None:
        _, texts = probe_text("<div>a<br>b</div><p>&nbsp;x &amp; y</p>")
        assert list(texts.values()) == ["x & y"]


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

    def test_one_template_per_cell_size(self) -> None:
        """A new Template per check leaked ~34 KB (a native thread each)."""
        cellcheck._TEMPLATES.clear()
        text_overflow("<div>a</div>", 120, 90)
        first = cellcheck._TEMPLATES[(120, 90)]
        text_overflow("<div>b</div>", 120, 90)
        assert cellcheck._TEMPLATES[(120, 90)] is first
        assert len(cellcheck._TEMPLATES) == 1

    def test_probe_ignores_styles_aimed_at_spans(self) -> None:
        doc = "<style>span { padding: 0 200px }</style><div><span>fits</span></div>"
        assert text_overflow(doc, 240, 240) == []


@requires_engine
class TestCellWarnings:
    def test_overflow_and_unknown_classes_per_slot(self) -> None:
        layout = Grid2x2()
        layout.set_widget(0, html(HERO, 0, entity="sensor.living_temp"))
        layout.set_widget(
            1, html('<div class="p-2 backdrop-blur-sm text-warnng">x</div>', 1, tailwind=True)
        )
        layout.set_widget(2, html("<div>fine</div>", 2))
        states = {i: widget_state("sensor.living_temp") for i in range(3)}

        warnings = [w.as_dict() for w in cell_warnings(layout, states)]

        assert warnings == [
            {"slot": 0, "kind": "overflow", "items": ["21.5"]},
            {"slot": 1, "kind": "unknown_classes", "items": ["backdrop-blur-sm", "text-warnng"]},
        ]

    def test_the_templates_own_classes_are_not_unknown(self) -> None:
        source = "<style>.big { font-size: 40px }</style><div class='big p-2'>hi</div>"
        layout = fullscreen(source, tailwind=True)
        assert cell_warnings(layout, {0: WidgetState()}) == []

    @pytest.mark.parametrize(
        "source",
        [
            # Probes beside an icon used to shift space-x/*: rules
            '<div class="flex items-center space-x-20 text-6xl font-bold">'
            "{{ icon('thermometer') }}21.5°</div>",
            '<div class="flex justify-center *:px-12 text-xl"><span>A</span>Temperature</div>',
        ],
    )
    def test_no_false_positive_from_child_selectors(self, source: str) -> None:
        layout = fullscreen(source, tailwind=True)
        assert cell_warnings(layout, {0: WidgetState()}) == []

    def test_no_html_widget_no_work(self, monkeypatch) -> None:
        layout = Grid2x2()
        calls: list[object] = []
        monkeypatch.setattr(layout, "cell_documents", calls.append)
        assert cell_warnings(layout, {}) == []
        assert calls == []  # the other widgets weren't rendered again

    def test_fit_keeps_the_same_value_inside(self) -> None:
        layout = Grid2x2()
        layout.set_widget(
            0, html('<div class="cell">{{ fit(state, max=82) }}</div>', entity="sensor.living_temp")
        )
        assert cell_warnings(layout, {0: widget_state("sensor.living_temp")}) == []

    @pytest.mark.parametrize("theme", ["minimal", "neon", "retro", "watchos"])
    def test_fit_ignores_a_caps_parent(self, theme: str) -> None:
        """fit() sets its own case and spacing: a .t-label parent can't widen it."""
        fitted = '{{ fit("unavailable state here", max=200) }}'
        source = f'<div class="cell"><div class="t-label">{fitted}</div></div>'
        assert cell_warnings(fullscreen(source, theme=theme), {0: WidgetState()}) == []

    @pytest.mark.parametrize("theme", sorted(THEMES))
    def test_no_warning_on_the_gallery(self, theme: str) -> None:
        """Every gallery template fits, in every theme: no false positives."""
        for stem, entity_id, _ in EXAMPLES:
            source = (EXAMPLES_DIR / f"{stem}.html").read_text()
            layout = fullscreen(
                source, tailwind=stem in TAILWIND_EXAMPLES, entity=entity_id, theme=theme
            )
            assert cell_warnings(layout, {0: widget_state(entity_id)}) == [], stem


def _stressed_entities(kind: str) -> dict[str, EntityState]:
    """The gallery's mock entities with the long values real ones have."""
    entities = {}
    for entity_id, (mock_state, mock_attributes) in {**ENTITIES, **EXAMPLE_ENTITIES}.items():
        state, attributes = mock_state, copy.deepcopy(mock_attributes)
        if kind == "unavailable":
            state = "unavailable"
        elif kind == "long names":
            attributes["friendly_name"] = "Downstairs living room sensor"
        else:  # long text: string attributes, list items and non-numeric states
            long_text = "An unusually long piece of text from Home Assistant"
            for key, value in list(attributes.items()):
                if key in ("unit_of_measurement", "friendly_name"):
                    continue
                if isinstance(value, str) and not value[:1].isdigit():
                    attributes[key] = long_text
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            item.update(
                                {k: long_text for k, v in item.items() if isinstance(v, str)}
                            )
            if not state.replace(".", "", 1).replace("-", "", 1).isdigit():
                state = "an_unusually_long_state_value"
        entities[entity_id] = EntityState(entity_id, state, attributes)
    return entities


@requires_engine
@pytest.mark.parametrize("kind", ["unavailable", "long names", "long text"])
@pytest.mark.parametrize(("stem", "entity_id", "animated"), EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_gallery_survives_real_world_values(
    stem: str, entity_id: str, animated: bool, kind: str
) -> None:
    """Copied with real entities, a gallery template must not run off the cell.

    Entity-driven text goes through fit(); the rest is numbers formatted in
    Jinja. Checked in the default theme and the widest face (minimal).
    """
    entities = _stressed_entities(kind)
    state = WidgetState(
        entity=entities[entity_id],
        entities=entities,
        forecasts=EXAMPLE_FORECASTS,
        histories=EXAMPLE_HISTORIES,
        pictures=EXAMPLE_PICTURES,
        now=NOW,
    )
    source = (EXAMPLES_DIR / f"{stem}.html").read_text()
    for theme in ("watchos", "minimal"):
        layout = fullscreen(
            source, tailwind=stem in TAILWIND_EXAMPLES, entity=entity_id, theme=theme
        )
        assert cell_warnings(layout, {0: state}) == [], theme


async def _preview(hass, hass_ws_client, **extra) -> dict:
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
            **extra,
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]


@requires_engine
async def test_preview_returns_warnings_when_asked(hass, hass_ws_client) -> None:
    result = await _preview(hass, hass_ws_client, warnings=True)
    assert result["warnings"] == [{"slot": 0, "kind": "overflow", "items": ["unavailable"]}]


@requires_engine
async def test_thumbnails_skip_the_checks(hass, hass_ws_client) -> None:
    """Thumbnails refresh every minute: they don't pay for the checks."""
    assert (await _preview(hass, hass_ws_client))["warnings"] == []
