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
import threading
from dataclasses import dataclass, field
from html import unescape
from typing import TYPE_CHECKING, Any

from .engine import get_engine
from .htmldoc import CellContext, font_param
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


# Elements with no closing tag: they never hold text
_VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
_PROBE_STYLE = "all: unset; display: inline-block"


@dataclass
class _Open:
    """An element still open while scanning: its text runs and child count."""

    name: str
    texts: list[int] = field(default_factory=list)
    elements: int = 0


def probe_text(document: str) -> tuple[str, dict[str, str]]:
    """``document`` with text that fills an element wrapped in an id'd probe.

    Only an element whose whole content is one run of text (``<div>23.5°C
    </div>``, ``fit()``'s span) is probed: wrapping text that sits beside
    other elements would add a child and change what ``> *``,
    ``:last-child`` and ``space-x-*`` match, moving the very layout being
    measured. The probe is ``all: unset``, so rules aimed at spans don't
    reach it, while inherited font, case and spacing still do. Returns the
    probed document and ``{probe id: text}``; text inside ``<style>``,
    ``<svg>`` and the like is left alone.
    """
    parts = [part for part in _TOKEN_RE.split(document) if part]
    wrap: list[int] = []
    stack: list[_Open] = []
    opaque_depth = 0

    def close(element: _Open) -> None:
        if element.elements == 0 and len(element.texts) == 1:
            wrap.append(element.texts[0])

    for index, part in enumerate(parts):
        if not part.startswith("<"):
            if stack and not opaque_depth and _PUA_RE.sub("", part).strip():
                stack[-1].texts.append(index)
            continue
        if part.startswith("<!"):
            continue  # a comment or doctype
        tag = _TAG_RE.match(part)
        if tag is None:
            continue
        closing, name = tag.group(1) == "/", tag.group(2).lower()
        if name in _OPAQUE:
            if closing:
                opaque_depth = max(0, opaque_depth - 1)
            elif not part.rstrip(">").endswith("/"):
                opaque_depth += 1
            if stack and not closing:
                stack[-1].elements += 1
            continue
        if opaque_depth:
            continue
        if closing:
            # Close up to the matching element (browsers forgive the rest)
            for depth in range(len(stack) - 1, -1, -1):
                if stack[depth].name == name:
                    while len(stack) > depth:
                        close(stack.pop())
                    break
            continue
        if stack:
            stack[-1].elements += 1
        if name not in _VOID and not part.rstrip(">").endswith("/"):
            stack.append(_Open(name))
    while stack:
        close(stack.pop())

    texts: dict[str, str] = {}
    for index in sorted(wrap):
        probe = _PROBE_ID.format(len(texts))
        visible = _PUA_RE.sub("", unescape(parts[index]))
        texts[probe] = " ".join(visible.split())
        parts[index] = f'<span id="{probe}" style="{_PROBE_STYLE}">{parts[index]}</span>'
    return "".join(parts), texts


# One long-lived Template per cell size, refilled for every check: each
# new Template starts a native worker thread, and Stylo leaks ~34 KB per
# thread that styles a document (blitz-py docs/UPSTREAM.md), so a
# Template per check leaked on every preview and thumbnail refresh.
_HOST_ID = "gm-cellcheck-host"
_TEMPLATES: dict[tuple[int, int], Any] = {}
_TEMPLATES_LOCK = threading.Lock()
_MAX_TEMPLATES = 16


def _layout_boxes(document: str, width: int, height: int) -> dict[str, tuple]:
    """``Template.boxes()`` for ``document`` laid out in a ``width`` x ``height`` cell."""
    engine = get_engine()
    if engine is None:
        return {}
    with _TEMPLATES_LOCK:
        template = _TEMPLATES.get((width, height))
        if template is None:
            if len(_TEMPLATES) >= _MAX_TEMPLATES:
                _TEMPLATES.clear()
            template = engine.Template(
                f'<body id="{_HOST_ID}"></body>',
                width=width,
                height=height,
                fonts=font_param(),
            )
            _TEMPLATES[(width, height)] = template
        template.set_html(_HOST_ID, document)
        return template.boxes()


def text_overflow(document: str, width: int, height: int) -> list[str]:
    """The texts of ``document`` that run past the sides of a ``width`` x ``height`` cell."""
    probed, texts = probe_text(document)
    if not texts:
        return []
    boxes = _layout_boxes(probed, width, height)
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
    so what is measured is what the device shows. Never raises: a failure
    costs the warnings, never the preview.
    """
    if not any(isinstance(slot.widget, HtmlWidget) for slot in layout.slots):
        return []  # nothing to check: skip re-rendering the other widgets
    try:
        return _cell_warnings(layout, widget_states)
    except Exception:
        _LOGGER.debug("Cell checks failed", exc_info=True)
        return []


def _cell_warnings(layout: Layout, widget_states: dict[int, WidgetState]) -> list[CellWarning]:
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
