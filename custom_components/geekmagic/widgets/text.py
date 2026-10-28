"""Text widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..const import PLACEHOLDER_VALUE
from ..htmldoc import css_rgb
from ._card import Header, card_html, header_html
from ._cardfit import (
    HERO_SHARE_SOLO,
    HERO_SHARE_STACKED,
    HeroFit,
    caption_visible,
    cell_box,
    fit_hero,
    hero_block,
)
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

_MAX_HERO_PX = 124.0
_MIN_HERO_PX = 12.0

# Below this the cell has no room for a second line.
_WRAP_MIN_CELL = 100

# Below this content height even a compact caption row would crowd the
# text out entirely (matches entity.py).
_COMPACT_MIN_H = 40.0


class TextWidget(Widget):
    """Widget that displays static or dynamic text via the card pattern.

    Maps to ``card_html(caption=label, hero=text)`` — the watchOS
    caption-above-hero pattern. The hero is measured and fitted to the
    cell, so the legacy ``size`` option (small/regular/large/xlarge) is
    no longer needed and is silently ignored if present in stored
    configs. Likewise the legacy ``align`` option is ignored — text is
    centred in the watchOS contract. Sentences too long for one line
    take a second one rather than shrinking to nothing.
    """

    WIDGET_TYPE: ClassVar[str] = "text"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Text",
        "needs_entity": False,
        "options": [
            {"key": "text", "type": "text", "label": "Text Content"},
            {"key": "entity_id", "type": "entity", "label": "Entity (dynamic text)"},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the text widget."""
        super().__init__(config)
        self.text = config.options.get("text", "")
        # Entity ID for dynamic text (from options, takes precedence over widget entity_id)
        self.dynamic_entity_id = config.options.get("entity_id")

    def _fit(self, ctx: CellContext, state: WidgetState) -> tuple[str, HeroFit, Header, float]:
        """(text, fitted hero, header, gap) for this cell."""
        text = self._get_text(state)
        box_w, box_h = cell_box(ctx)
        bands_kept = caption_visible(ctx)
        # Short cells (hero-layout footers) keep a shrunk caption row
        # instead of dropping the label — an unlabeled "247" is noise.
        compact_identity = not bands_kept and box_h >= _COMPACT_MIN_H
        show_caption = bool(self.config.label) and (bands_kept or compact_identity)
        header = header_html(
            ctx,
            self.config.label if show_caption else "",
            None,
            None,
            width_px=box_w,
            hide="hide-short" if bands_kept else "",
        )
        gap = max(3.0, min(0.09 * box_h, 16.0)) if header else 0.0
        share = HERO_SHARE_STACKED if header else HERO_SHARE_SOLO
        max_px = _MAX_HERO_PX
        cap = ctx.extra.get("hero_px_cap")
        if cap:
            max_px = min(max_px, float(cap))

        hero = fit_hero(
            text,
            ctx,
            box_w,
            max(16.0, (box_h - header.band_px - gap) * share),
            # Wrapping needs WIDTH for its lines — the height cost is
            # already enforced by the band budget, so a 228x76 footer may
            # take two ~20px lines instead of one truncated 12px line.
            allow_wrap=ctx.width >= _WRAP_MIN_CELL,
            # A tall column would otherwise strand its height below two
            # short lines; a wide cell reads better in two.
            max_lines=3 if box_h > 1.5 * box_w else 2,
            max_px=max_px,
            min_px=_MIN_HERO_PX,
        )
        return text, hero, header, gap

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the text widget."""
        text, hero, header, gap = self._fit(ctx, state)
        # "--" is the absence of a value, not a value (matches entity.py).
        missing = text == PLACEHOLDER_VALUE
        hero_color = css_rgb(self.config.color) if self.config.color else None
        return card_html(
            header=header,
            hero=hero_block(hero),
            hero_is_html=True,
            hero_color="var(--text-tertiary)" if missing else hero_color,
            stack_gap_px=gap,
            ctx=ctx,
        )

    def hero_hint(self, ctx: CellContext, state: WidgetState) -> tuple[str, float] | None:
        """The size this cell's text fits at, for sibling harmony."""
        text, hero, _header, _gap = self._fit(ctx, state)
        if text == PLACEHOLDER_VALUE or hero.wrapped:
            return None
        return ("num" if any(ch.isdigit() for ch in text) else "word"), hero.px

    def _get_text(self, state: WidgetState) -> str:
        """Get the text to display.

        If entity_id is set (from options or widget config), returns the
        entity state — with absence states mapped to a dimmed "--" like
        entity.py, so a dead sensor never headlines the literal word
        "unavailable". Otherwise returns the configured static text.
        """

        def entity_text(value: str) -> str:
            return PLACEHOLDER_VALUE if value in ("unavailable", "unknown", "none", "") else value

        if state.entity:
            return entity_text(state.entity.state)
        if self.dynamic_entity_id:
            entity = state.get_entity(self.dynamic_entity_id)
            if entity:
                return entity_text(entity.state)
        return self.text

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on."""
        entities = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.dynamic_entity_id and self.dynamic_entity_id != self.config.entity_id:
            entities.append(self.dynamic_entity_id)
        return entities
