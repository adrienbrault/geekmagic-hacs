"""Tests for the HTML widget and the htmldoc document assembly."""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.htmldoc import (
    HAS_ENGINE,
    CellContext,
    build_cell_document,
    render_layers_image,
)
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.html import (
    HtmlWidget,
    _render_template,
)
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME


@pytest.fixture
def widget_state():
    """Widget state with a primary entity and one extra entity."""
    return WidgetState(
        entity=EntityState(
            entity_id="sensor.temperature",
            state="21.5",
            attributes={"friendly_name": "Living Room", "unit_of_measurement": "°C"},
        ),
        entities={
            "climate.living_room": EntityState(
                entity_id="climate.living_room", state="heat", attributes={}
            ),
        },
        now=datetime.now(tz=UTC),
    )


@pytest.fixture
def ctx():
    """Standard cell context."""
    return CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


def make_widget(html: str, entity_id: str | None = "sensor.temperature") -> HtmlWidget:
    """Create an HtmlWidget with the given template."""
    return HtmlWidget(
        WidgetConfig(widget_type="html", slot=0, entity_id=entity_id, options={"html": html})
    )


class TestTemplateRendering:
    """Jinja template context and rendering."""

    def test_primary_entity_variables(self, widget_state):
        result = _render_template("{{ name }}: {{ state }}{{ unit }}", widget_state)
        assert result == "Living Room: 21.5°C"

    def test_states_function(self, widget_state):
        result = _render_template("{{ states('climate.living_room') }}", widget_state)
        assert result == "heat"

    def test_states_unknown_entity(self, widget_state):
        result = _render_template("{{ states('sensor.missing') }}", widget_state)
        assert result == "unknown"

    def test_state_attr_function(self, widget_state):
        result = _render_template(
            "{{ state_attr('sensor.temperature', 'unit_of_measurement') }}", widget_state
        )
        assert result == "°C"

    def test_is_state_function(self, widget_state):
        result = _render_template(
            "{% if is_state('climate.living_room', 'heat') %}ON{% endif %}", widget_state
        )
        assert result == "ON"

    def test_no_entity(self):
        state = WidgetState(now=datetime.now(tz=UTC))
        result = _render_template("[{{ state }}][{{ name }}]", state)
        assert result == "[][]"

    def test_options_entity_id_feeds_primary_variables(self, ctx):
        """The UI stores the selector in options.entity_id and the
        coordinator delivers that entity in state.entities — the
        convenience variables must resolve it as the primary entity."""
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={
                    "entity_id": "sensor.temp",
                    "html": "{{ name }}|{{ state }}|{{ unit }}|{{ attributes.friendly_name }}",
                },
            )
        )
        state = WidgetState(
            entity=None,
            entities={
                "sensor.temp": EntityState(
                    entity_id="sensor.temp",
                    state="21.5",
                    attributes={"friendly_name": "Room", "unit_of_measurement": "°C"},
                )
            },
            now=datetime.now(tz=UTC),
        )
        assert widget.render_html(ctx, state) == "Room|21.5|°C|Room"

    def test_top_level_entity_id_still_feeds_primary_variables(self, ctx, widget_state):
        """Traditional config.entity_id (state.entity) keeps working."""
        widget = make_widget("{{ name }}|{{ state }}{{ unit }}")
        assert widget.render_html(ctx, widget_state) == "Living Room|21.5°C"

    def test_options_entity_missing_falls_back_to_state_entity(self, ctx, widget_state):
        """An unresolvable options entity degrades to state.entity."""
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                entity_id="sensor.temperature",
                options={"entity_id": "sensor.gone", "html": "{{ state }}"},
            )
        )
        assert widget.render_html(ctx, widget_state) == "21.5"

    def test_css_braces_untouched(self, widget_state):
        css = "body { color: red; }"
        assert _render_template(css, widget_state) == css


class TestCellDocument:
    """Document assembly: theme variables and fluid kit."""

    def test_injects_theme_variables(self):
        doc = build_cell_document("<div>hi</div>", DEFAULT_THEME)
        assert "--text-primary:" in doc
        assert "--success:" in doc
        assert "--bg:" in doc
        assert "<div>hi</div>" in doc

    def test_fluid_kit_injected(self):
        doc = build_cell_document("", DEFAULT_THEME)
        for cls in (".cell", ".t-hero", ".t-value", ".t-unit", ".t-label", ".icon"):
            assert cls in doc
        for cls in (".hide-short", ".hide-narrow", ".hide-small"):
            assert cls in doc

    def test_transparent_body(self):
        doc = build_cell_document("", DEFAULT_THEME)
        assert "background: transparent" in doc


class TestGetEntities:
    """Entity dependency extraction from templates."""

    def test_config_entity_only(self):
        widget = make_widget("<div>static</div>")
        assert widget.get_entities() == ["sensor.temperature"]

    def test_extracts_states_references(self):
        widget = make_widget(
            "{{ states('climate.living_room') }} {{ state_attr(\"sensor.humidity\", 'value') }}"
        )
        assert widget.get_entities() == [
            "sensor.temperature",
            "climate.living_room",
            "sensor.humidity",
        ]

    def test_no_duplicates(self):
        widget = make_widget("{{ states('sensor.temperature') }}")
        assert widget.get_entities() == ["sensor.temperature"]

    def test_options_entity_id(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"html": "x", "entity_id": "sensor.other"},
            )
        )
        assert widget.get_entities() == ["sensor.other"]

    def test_extracts_is_state_references(self):
        widget = make_widget("{{ is_state('light.kitchen', 'on') }}", entity_id=None)
        assert widget.get_entities() == ["light.kitchen"]

    def test_extracts_is_state_double_quotes(self):
        widget = make_widget('{{ is_state("light.kitchen", "on") }}', entity_id=None)
        assert widget.get_entities() == ["light.kitchen"]

    def test_mixed_helpers_stable_order_deduped(self):
        widget = make_widget(
            "{{ states('sensor.a') }}"
            "{{ is_state('light.b', 'on') }}"
            "{{ state_attr('sensor.a', 'x') }}"
            '{{ is_state("sensor.c", "wet") }}'
            "{{ states('light.b') }}",
            entity_id=None,
        )
        assert widget.get_entities() == ["sensor.a", "light.b", "sensor.c"]


class TestRenderFragment:
    """Fragment output paths that don't require blitz-py."""

    def test_returns_rendered_template(self, ctx, widget_state):
        widget = make_widget('<div class="t-hero">{{ state }}</div>')
        assert widget.render_html(ctx, widget_state) == '<div class="t-hero">21.5</div>'

    def test_empty_html_placeholder(self, ctx, widget_state):
        """Placeholder words wrap per-word so they never bleed off panel."""
        fragment = make_widget("").render_html(ctx, widget_state)
        for word in ("NO", "HTML", "CONFIGURED"):
            assert f">{word}</span>" in fragment

    def test_invalid_template_placeholder(self, ctx, widget_state):
        fragment = make_widget("{{ unclosed").render_html(ctx, widget_state)
        for word in ("TEMPLATE", "ERROR"):
            assert f">{word}</span>" in fragment


def _render_cell(document: str, width: int, height: int, time: float | None = None):
    """Rasterize one cell document the way the pipeline ships it.

    Production never rasterizes a lone document: ``layouts.base`` hands
    every pass to ``render_layers_image`` as a layer. Tests go through
    the same seam so what they assert is what the display gets.
    """
    layer: dict = {"html": document, "width": width, "height": height, "x": 0, "y": 0}
    if time is not None:
        layer["time"] = time
    return render_layers_image([layer], width, height)


@pytest.mark.skipif(not HAS_ENGINE, reason="blitz-py >= 0.4.2 not installed")
class TestBlitzRender:
    """Real rasterization through blitz-py."""

    def test_renders_pixels(self, ctx, widget_state):
        widget = make_widget(
            "<div style='color:#fff;font-size:60px;text-align:center'>{{ state }}</div>"
        )
        doc = build_cell_document(widget.render_html(ctx, widget_state), DEFAULT_THEME)
        img = _render_cell(doc, 240, 240)
        assert img is not None
        colors = img.getcolors(maxcolors=1_000_000)
        assert colors is not None
        assert len(colors) > 1  # more than just the background

    def test_hide_short_responds_to_cell_height(self, widget_state):
        """.hide-short content disappears in cells under 100px tall."""

        def red_pixels(cell_height: int) -> int:
            widget = make_widget(
                '<div class="hide-short" style="color:#f00;font-size:40px">XXXX</div>'
            )
            ctx = CellContext(width=240, height=cell_height, theme=DEFAULT_THEME)
            doc = build_cell_document(widget.render_html(ctx, widget_state), DEFAULT_THEME)
            img = _render_cell(doc, 240, cell_height)
            assert img is not None
            rgb = img.convert("RGB")
            return sum(
                count
                for count, (r, g, b) in rgb.getcolors(maxcolors=1_000_000)
                if r > 180 and g < 80 and b < 80
            )

        assert red_pixels(240) > 0
        assert red_pixels(80) == 0

    def test_fluid_hero_scales_with_cell(self, widget_state):
        """.t-hero text occupies more pixels in a larger cell."""

        def content_pixels(size: int) -> int:
            widget = make_widget('<div class="cell"><div class="t-hero">21.5</div></div>')
            ctx = CellContext(width=size, height=size, theme=DEFAULT_THEME)
            doc = build_cell_document(widget.render_html(ctx, widget_state), DEFAULT_THEME)
            img = _render_cell(doc, size, size)
            assert img is not None
            rgb = img.convert("RGB")
            return sum(
                count
                for count, (r, g, b) in rgb.getcolors(maxcolors=1_000_000)
                if r > 100 or g > 100 or b > 100
            )

        assert content_pixels(240) > content_pixels(80) * 2


class TestAnimatedWidgets:
    """Opt-in animation contract (per-frame layer clocks)."""

    def test_default_not_animated(self):
        widget = make_widget("<div>static</div>")
        assert widget.is_animated() is False

    def test_animate_option_opts_in(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"html": "<div>x</div>", "animate": True},
            )
        )
        assert widget.is_animated() is True

    @pytest.mark.skipif(not HAS_ENGINE, reason="blitz-py >= 0.4.2 not installed")
    def test_layer_clock_animates(self):
        """A layer's ``time`` advances the document's animation clock.

        This is the seam the animated path uses: ``render_animation``
        composites one ``render_layers`` call per timestamp with the
        frame's clock on the animated layers.
        """
        doc = build_cell_document(
            "<style>@keyframes r { from { transform: rotate(0deg); } "
            "to { transform: rotate(360deg); } }"
            ".b { width: 48px; height: 10px; background: #f90; margin: 40px auto;"
            " animation: r 1s linear infinite; }</style><div class='b'></div>",
            DEFAULT_THEME,
        )
        frames = [_render_cell(doc, 120, 120, time=t) for t in (0.0, 0.11, 0.29)]
        assert all(frame is not None for frame in frames)
        assert len(frames) == 3
        assert frames[0].tobytes() != frames[1].tobytes()

    def test_loop_seconds_option(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"html": "<div>x</div>", "animate": True, "loop_seconds": 3.2},
            )
        )
        assert widget.animation_seconds() == 3.2

    def test_loop_seconds_ignored_when_static(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"html": "<div>x</div>", "loop_seconds": 3.2},
            )
        )
        assert widget.animation_seconds() is None
