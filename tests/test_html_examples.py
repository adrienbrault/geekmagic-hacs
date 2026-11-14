"""The HTML widget gallery in docs/html-widget.md stays honest.

Each template in scripts/html_examples/ is rendered into samples/html/
by scripts/generate_html_samples.py and shown in the doc next to its
source. These tests keep the three in sync and catch templates that
would work on the mock data but not in a real Home Assistant.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from custom_components.geekmagic.widgets import HtmlWidget, WidgetConfig
from custom_components.geekmagic.widgets.html import _render_template
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from scripts.generate_html_samples import EXAMPLE_ENTITIES, EXAMPLES, EXAMPLES_DIR, NOW

DOC = Path(__file__).parent.parent / "docs" / "html-widget.md"
TEMPLATES = sorted(EXAMPLES_DIR.glob("*.html"))

# states(eid) / state_attr(eid, ...) / is_state(eid, ...) with a VARIABLE
# instead of a quoted entity id: the widget only pre-fetches literal
# references, so these read "unknown" in a real Home Assistant.
_NON_LITERAL_REF = re.compile(r"""\b(?:states|state_attr|is_state)\(\s*(?!['"])""")


def test_every_template_is_registered() -> None:
    assert sorted(stem for stem, _, _ in EXAMPLES) == sorted(t.stem for t in TEMPLATES)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.stem)
def test_doc_shows_template_verbatim(template: Path) -> None:
    doc = DOC.read_text()
    assert f"```html\n{template.read_text().strip()}\n```" in doc
    animated = {stem for stem, _, anim in EXAMPLES if anim}
    ext = "gif" if template.stem in animated else "png"
    assert f"samples/html/{template.stem}.{ext}" in doc


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.stem)
def test_template_references_entities_literally(template: Path) -> None:
    assert not _NON_LITERAL_REF.search(template.read_text())


@pytest.mark.parametrize(("stem", "entity_id", "animated"), EXAMPLES)
def test_template_renders_with_only_its_declared_entities(
    stem: str, entity_id: str, animated: bool
) -> None:
    """Render with exactly what the coordinator would pre-fetch."""
    source = (EXAMPLES_DIR / f"{stem}.html").read_text()
    widget = HtmlWidget(
        WidgetConfig(widget_type="html", slot=0, entity_id=entity_id, options={"html": source})
    )
    fetched = {
        eid: EntityState(eid, *EXAMPLE_ENTITIES[eid])
        for eid in widget.get_entities()
        if eid in EXAMPLE_ENTITIES
    }
    assert set(widget.get_entities()) <= set(EXAMPLE_ENTITIES)
    state = WidgetState(entity=fetched[entity_id], entities=fetched, now=NOW)

    html = _render_template(source, state)

    assert "unknown" not in html
