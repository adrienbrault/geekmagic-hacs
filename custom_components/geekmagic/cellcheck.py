"""What the panel preview warns about in user-written HTML widgets.

Two problems a template author can't see coming, because the data
changes after the template is written:

- **Text running past the side of the cell.** A template sized for
  "21.5°C" meets "unavailable" or a long friendly name, and Blitz neither
  clips nor ellipsizes it: the text runs across the bezel. Found by
  laying the cell out once more with every run of text wrapped in an
  ``inline-block`` probe (a block's box keeps the block's width, and an
  inline span reports no box, but an inline-block reports the text's real
  extent), then reading the probes' boxes with ``Template.boxes()``.
  Only the sides: rows past the bottom are usually a list clipped on
  purpose (``overflow: hidden``), and the engine doesn't report clipping.
- **Utility classes the widget doesn't generate** (with the Tailwind
  option on): a typo, a utility the engine can't paint (``blur``), or a
  Tailwind name from another version, all of which leave an element
  silently unstyled.

HA-free (``view.py`` hands it a layout); preview only, never the device
loop: it costs one extra layout pass per HTML cell.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .engine import get_engine
from .htmldoc import CellContext
from .widgets._tailwind import compile_utilities
from .widgets.html import HtmlWidget

if TYPE_CHECKING:
    from .layouts.base import Layout
    from .widgets.state import WidgetState

_LOGGER = logging.getLogger(__name__)

# Tags whose text isn't laid out as HTML text (or can't hold a span)
_OPAQUE = {"style", "script", "svg", "title", "textarea"}
_TOKEN_RE = re.compile(r"""(<!--.*?-->|<(?:[^>"']|"[^"]*"|'[^']*')*>)""", re.DOTALL)
_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][\w-]*)")
_PROBE_ID = "gm-probe-{}"
# Material Design Icons glyphs live in the Private Use Area: an icon is
# not text a reader can be told about
_PUA_RE = re.compile("[-\U000f0000-\U000ffffd]")
_TOLERANCE_PX = 1.0
_BEARING_SHARE = 0.06
_SNIPPET_CHARS = 32


@dataclass(frozen=True)
class CellWarning:
    """One problem in one slot, as the preview reports it."""

    slot: int
    kind: str  # "overflow" | "unknown_classes"
    items: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"slot": self.slot, "kind": self.kind, "items": list(self.items)}


def probe_text(document: str) -> tuple[str, dict[str, str]]:
    """``document`` with each run of visible text in an id'd inline-block.

    Returns the probed document and ``{probe id: text}``. Text inside
    ``<style>``, ``<svg>`` and the like is left alone.
    """
    out: list[str] = []
    texts: dict[str, str] = {}
    opaque_depth = 0
    for part in _TOKEN_RE.split(document):
        if not part:
            continue
        if part.startswith("<"):
            if (tag := _TAG_RE.match(part)) and tag.group(2).lower() in _OPAQUE:
                closing = tag.group(1) == "/"
                self_closing = part.rstrip(">").endswith("/")
                if closing:
                    opaque_depth = max(0, opaque_depth - 1)
                elif not self_closing:
                    opaque_depth += 1
            out.append(part)
            continue
        visible = _PUA_RE.sub("", part).strip()
        if opaque_depth or not visible:
            out.append(part)
            continue
        probe = _PROBE_ID.format(len(texts))
        texts[probe] = " ".join(visible.split())
        out.append(f'<span id="{probe}" style="display: inline-block">{part}</span>')
    return "".join(out), texts


def text_overflow(document: str, width: int, height: int) -> list[str]:
    """The texts of ``document`` that run past a ``width`` x ``height`` cell."""
    engine = get_engine()
    if engine is None:
        return []
    probed, texts = probe_text(document)
    if not texts:
        return []
    boxes = engine.Template(probed, width=width, height=height).boxes()
    overflowing = []
    for probe, text in texts.items():
        x, y, w, h = boxes.get(probe, (0.0, 0.0, 0.0, 0.0))
        if w <= 0 or h <= 0 or y >= height or y + h <= 0:
            continue  # not displayed, or a row clipped off the top or bottom
        # The box is the text's advance, wider than its ink by the glyphs'
        # side bearings, which grow with the type
        slack = _TOLERANCE_PX + _BEARING_SHARE * h
        if x < -slack or x + w > width + slack:
            snippet = text if len(text) <= _SNIPPET_CHARS else text[: _SNIPPET_CHARS - 1] + "…"
            overflowing.append(snippet)
    return list(dict.fromkeys(overflowing))


def cell_warnings(layout: Layout, widget_states: dict[int, WidgetState]) -> list[CellWarning]:
    """Warnings for the layout's HTML widget cells (blocking: run in the executor).

    Lays out the very documents the frame renders (``Layout.cell_documents``),
    so what is measured is what the device shows. A failure here only
    costs the warnings, never the preview.
    """
    warnings: list[CellWarning] = []
    for slot, document, _ in layout.cell_documents(widget_states):
        widget = slot.widget
        if not isinstance(widget, HtmlWidget):
            continue
        x1, y1, x2, y2 = slot.rect
        try:
            overflow = text_overflow(document, x2 - x1, y2 - y1)
        except Exception:  # pragma: no cover - engine failure: no warning, still a preview
            _LOGGER.debug("Overflow check failed for slot %s", slot.index, exc_info=True)
            overflow = []
        if overflow:
            warnings.append(CellWarning(slot.index, "overflow", tuple(overflow)))
        if widget.tailwind:
            ctx = CellContext(x2 - x1, y2 - y1, slot.index, layout.theme)
            _, unknown = compile_utilities(document, ctx)
            if unknown:
                warnings.append(CellWarning(slot.index, "unknown_classes", tuple(unknown)))
    return warnings
