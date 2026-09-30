"""Tests for the panel bundle bootstrap (runs in the executor)."""

from pathlib import Path

from custom_components.geekmagic.panel import _ensure_panel_js


def test_ensure_panel_js_writes_placeholder_when_missing(tmp_path: Path) -> None:
    panel_js = tmp_path / "dist" / "geekmagic-panel.js"
    _ensure_panel_js(panel_js)
    assert "customElements.define('geekmagic-panel'" in panel_js.read_text()


def test_ensure_panel_js_keeps_existing_bundle(tmp_path: Path) -> None:
    panel_js = tmp_path / "geekmagic-panel.js"
    panel_js.write_text("built")
    _ensure_panel_js(panel_js)
    assert panel_js.read_text() == "built"
