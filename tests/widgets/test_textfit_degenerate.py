"""Degenerate-measurement regression tests (the "massive text" bug).

Field report: on some installs the engine's text measurement came back
degenerate (NaN / zero) while rendering still drew real glyphs. Every
comparison against NaN is False, so ``fit_hero`` skipped both its width
bound and its truncation pass and sized the hero to the HEIGHT budget
alone — values painted at ~45px across the full panel and clipped at
the bezel. These tests pin the choke-point fallback in
``_textfit._ref_width``: a broken measurement must degrade to the
conservative per-character estimate, never to an overflow.
"""

from __future__ import annotations

import math

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets import _textfit
from custom_components.geekmagic.widgets._cellkit import cell_box
from custom_components.geekmagic.widgets._fit import fit_hero
from custom_components.geekmagic.widgets._textfit import TextMetrics
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME


@pytest.fixture(params=[float("nan"), 0.0, -1.0], ids=["nan", "zero", "negative"])
def broken_measurer(request, monkeypatch):
    """measure_text returning a degenerate width, as seen in the field."""

    def _measure(text, **kwargs):
        return (request.param, 40.0)

    monkeypatch.setattr(_textfit, "_measure_text", _measure)
    _textfit._ref_width.cache_clear()
    _textfit._warn_measurement_broken.cache_clear()
    yield request.param
    _textfit._ref_width.cache_clear()
    _textfit._warn_measurement_broken.cache_clear()


class TestDegenerateMeasurementFallback:
    """_ref_width must never propagate NaN/non-positive widths."""

    def test_width_falls_back_to_estimate(self, broken_measurer):
        metrics = TextMetrics()
        width = metrics.width("1am Wet tray", 33.2, "extrabold")
        estimate = len("1am Wet tray") * 0.60 * 33.2
        assert math.isfinite(width)
        assert width == pytest.approx(estimate)

    def test_fit_hero_stays_width_bound(self, broken_measurer):
        """The photo scenario: 228x111 split cell, 12-char value.

        With a sane measurement the hero is width-bound around 30-36px.
        With a degenerate one it must NOT jump to the ~45px height cap —
        the fallback estimate keeps the width bound in force.
        """
        ctx = CellContext(width=228, height=111, slot_index=0, theme=DEFAULT_THEME)
        box_w, _box_h = cell_box(ctx)
        fit = fit_hero("1am Wet tray", ctx, box_w, 38.0, max_px=124.0, min_px=12.0)
        assert math.isfinite(fit.px)
        # Fallback estimate: 12 chars * 0.6em -> box_w / 7.2em ~= 29px.
        assert fit.px <= box_w / (len("1am Wet tray") * 0.60) + 0.1

    def test_entity_widget_emits_bounded_hero(self, broken_measurer):
        """End to end: the rendered fragment carries a width-safe size."""
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                entity_id="sensor.feed",
                label="Steve's next feed",
                options={"icon": "cat"},
            )
        )
        ctx = CellContext(width=228, height=111, slot_index=0, theme=DEFAULT_THEME)
        state = WidgetState(entity=EntityState(entity_id="sensor.feed", state="1am Wet tray"))
        fragment = widget.render_html(ctx, state)
        sizes = [
            float(chunk.split("px")[0])
            for chunk in fragment.split("font-size: ")[1:]
            if chunk.split("px")[0].replace(".", "").isdigit()
        ]
        hero_px = max(sizes)
        # box_w ~= 212; the fallback estimate allows at most ~29px for a
        # 12-char value. The broken-measurement failure mode was ~45px
        # (the height cap); anything close to it means the width bound
        # was skipped again.
        assert hero_px < 32.0

    def test_warns_once(self, broken_measurer, caplog):
        with caplog.at_level("DEBUG", logger=_textfit.__name__):
            TextMetrics().width("first string", 20.0)
            TextMetrics().width("second string", 20.0)
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
