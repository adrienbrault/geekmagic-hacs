"""Tests for Jinja template support in widget labels and text content.

Regression tests for issue #73: widget labels evaluate the same
sandboxed Jinja subset as the HTML widget, with referenced entities
pre-fetched automatically by ``build_entity_states``.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.icon import IconWidget
from custom_components.geekmagic.widgets.state import (
    EntityState,
    WidgetState,
    build_entity_states,
)
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

BIRD_SENSOR = "sensor.birdnet_go_last_detection"


@pytest.fixture
def widget_state():
    """State with a primary camera entity and the bird sensor (issue #73)."""
    return WidgetState(
        entity=EntityState(
            entity_id="camera.birdnet_vogelbild",
            state="idle",
            attributes={"friendly_name": "Bird Cam"},
        ),
        entities={
            BIRD_SENSOR: EntityState(entity_id=BIRD_SENSOR, state="Great Tit", attributes={}),
        },
        # A Wednesday, for the weekday template test.
        now=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )


@pytest.fixture
def ctx():
    """Standard cell context."""
    return CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


def make_camera(label: str | None) -> CameraWidget:
    return CameraWidget(
        WidgetConfig(
            widget_type="camera",
            slot=0,
            entity_id="camera.birdnet_vogelbild",
            label=label,
        )
    )


class TestResolvedLabel:
    """Widget.resolved_label — the template-aware label accessor."""

    def test_static_label_passthrough(self, widget_state):
        widget = make_camera("Birds")
        assert widget.resolved_label(widget_state) == "Birds"

    def test_no_label_returns_none(self, widget_state):
        widget = make_camera(None)
        assert widget.resolved_label(widget_state) is None

    def test_issue_73_states_template(self, widget_state):
        """The exact example from the issue: camera label showing a sensor."""
        widget = make_camera("{{ states('" + BIRD_SENSOR + "') }}")
        assert widget.resolved_label(widget_state) == "Great Tit"

    def test_weekday_set_block_template(self, widget_state):
        """The abbreviated-weekday template from the issue thread —
        ``{% set %}`` blocks and a callable ``now()`` both work."""
        widget = make_camera(
            "{% set days = ['ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС'] %}"  # noqa: RUF001
            "{{ days[now().weekday()] }}"
        )
        assert widget.resolved_label(widget_state) == "СР"  # noqa: RUF001

    def test_primary_entity_variables(self, widget_state):
        widget = make_camera("{{ name }} ({{ state }})")
        assert widget.resolved_label(widget_state) == "Bird Cam (idle)"

    def test_broken_template_falls_back_to_raw_source(self, widget_state):
        """A syntax error shows the literal label (legacy behavior) so
        the mistake is visible on the panel instead of a blank."""
        widget = make_camera("{{ nope(")
        assert widget.resolved_label(widget_state) == "{{ nope("

    def test_whitespace_result_hides_label(self, widget_state):
        """A template evaluating to whitespace behaves like no label."""
        widget = make_camera("{% if false %}x{% endif %}")
        assert widget.resolved_label(widget_state) is None

    def test_without_state_returns_raw(self):
        """No state to render against — the raw label is preserved."""
        widget = make_camera("{{ states('sensor.x') }}")
        assert widget.resolved_label(None) == "{{ states('sensor.x') }}"


class TestLabelForChain:
    """label_for keeps its fallback chain with templates in the mix."""

    def test_template_label_wins(self, widget_state):
        widget = make_camera("{{ states('" + BIRD_SENSOR + "') }}")
        assert widget.label_for(widget_state.entity, state=widget_state) == "Great Tit"

    def test_empty_template_falls_back_to_friendly_name(self, widget_state):
        widget = make_camera("{% if false %}x{% endif %}")
        assert widget.label_for(widget_state.entity, state=widget_state) == "Bird Cam"

    def test_fallback_when_nothing_resolves(self, widget_state):
        widget = make_camera("{% if false %}x{% endif %}")
        assert widget.label_for(None, state=widget_state, fallback="Camera") == "Camera"


class TestEntityPrefetch:
    """build_entity_states snapshots entities referenced in label templates."""

    def test_label_refs_prefetched(self):
        widget = make_camera("{{ states('" + BIRD_SENSOR + "') }}")

        def get_state(entity_id):
            if entity_id != BIRD_SENSOR:
                return None
            return SimpleNamespace(entity_id=entity_id, state="Great Tit", attributes={})

        _primary, additional = build_entity_states(get_state, widget)
        assert BIRD_SENSOR in additional
        assert additional[BIRD_SENSOR].state == "Great Tit"

    def test_static_label_adds_nothing(self):
        widget = make_camera("Birds")
        _primary, additional = build_entity_states(lambda _eid: None, widget)
        assert additional == {}


class TestRenderedFragments:
    """Templates resolve end-to-end inside rendered widget fragments."""

    def test_entity_widget_label_template(self, ctx, widget_state):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="camera.birdnet_vogelbild",
                label="{{ states('" + BIRD_SENSOR + "') }}",
            )
        )
        html = widget.render_html(ctx, widget_state)
        assert "great tit" in html.lower()
        assert "states(" not in html

    def test_icon_widget_caption_template(self, ctx, widget_state):
        widget = IconWidget(
            WidgetConfig(
                widget_type="icon",
                slot=0,
                label="{{ states('" + BIRD_SENSOR + "') }}",
                options={"icon": "mdi:bird"},
            )
        )
        html = widget.render_html(ctx, widget_state)
        assert "great tit" in html.lower()


class TestTextWidgetTemplates:
    """Text widget content evaluates templates like labels do."""

    def test_templated_text_content(self, ctx, widget_state):
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                options={"text": "{{ states('" + BIRD_SENSOR + "') }}"},
            )
        )
        state = WidgetState(entities=dict(widget_state.entities), now=widget_state.now)
        html = widget.render_html(ctx, state)
        # The hero fitter may wrap the two words onto separate lines.
        assert "great" in html.lower()
        assert "tit" in html.lower()
        assert "states(" not in html

    def test_static_text_unchanged(self, ctx):
        widget = TextWidget(WidgetConfig(widget_type="text", slot=0, options={"text": "Hello"}))
        assert "Hello" in widget.render_html(ctx, WidgetState(now=datetime.now(tz=UTC)))

    def test_broken_text_template_shows_source(self, ctx):
        widget = TextWidget(WidgetConfig(widget_type="text", slot=0, options={"text": "{{ bad("}))
        html = widget.render_html(ctx, WidgetState(now=datetime.now(tz=UTC)))
        assert "bad(" in html

    def test_text_template_refs_declared(self):
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                options={"text": "{{ states('sensor.a') }} {{ is_state('sensor.b', 'on') }}"},
            )
        )
        assert widget.get_entities() == ["sensor.a", "sensor.b"]

    def test_entity_state_beats_text_template(self, ctx, widget_state):
        """An entity-driven text widget keeps showing the entity state."""
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                entity_id="camera.birdnet_vogelbild",
                options={"text": "{{ states('" + BIRD_SENSOR + "') }}"},
            )
        )
        html = widget.render_html(ctx, widget_state)
        assert "idle" in html
        assert "great tit" not in html.lower()
