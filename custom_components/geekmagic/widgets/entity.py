"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import (
    PLACEHOLDER_NAME,
    PLACEHOLDER_VALUE,
)
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
from .helpers import get_binary_sensor_icon, translate_binary_state

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# The card's anatomy is the iOS widget's: one HEADER (a tinted icon
# beside — or, in narrow cells, above — the caption) and the value
# underneath, as large as the cell allows. See ``_card.header_html``.
_MAX_HERO_PX = 124.0
_MIN_HERO_PX = 12.0

# Below this content height even a compact caption row would crowd the
# value out entirely.
_COMPACT_MIN_H = 40.0

# Only wrap a value onto two lines in cells with room to spare.
_WRAP_MIN_CELL = 130


@dataclass(frozen=True)
class _Plan:
    """Everything render_html needs, resolved once per cell."""

    value: str
    unit: str
    missing: bool
    header: Header
    gap: float
    hero: HeroFit


def _get_entity_icon(entity_state) -> str | None:
    """Get icon from entity state, handling MDI format and state-specific icons."""
    if entity_state is None:
        return None

    # For binary sensors, get state-specific icon
    if entity_state.entity_id.startswith("binary_sensor."):
        icon = get_binary_sensor_icon(entity_state.state, entity_state.device_class)
        if icon:
            return icon.removeprefix("mdi:")

    # Check explicit icon attribute
    icon = entity_state.icon
    if icon and icon.startswith("mdi:"):
        return icon.removeprefix("mdi:")
    return None


class EntityWidget(Widget):
    """Widget that displays a Home Assistant entity state."""

    WIDGET_TYPE: ClassVar[str] = "entity"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Entity",
        "needs_entity": True,
        "entity_domains": None,  # All domains
        "options": [
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_unit", "type": "boolean", "label": "Show Unit", "default": True},
            {"key": "show_icon", "type": "boolean", "label": "Show Icon", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon Override"},
            {
                "key": "precision",
                "type": "number",
                "label": "Decimal Places",
                "min": 0,
                "max": 5,
            },
            {"key": "attribute", "type": "text", "label": "Entity Attribute"},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the entity widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_unit = config.options.get("show_unit", True)
        self.show_icon = config.options.get("show_icon", True)
        self.icon = config.options.get("icon")  # Explicit icon override
        self.precision = config.options.get("precision")  # Decimal places for numeric values
        # Attribute to read value from (instead of state)
        self.attribute = config.options.get("attribute")

    def _plan(self, ctx: CellContext, state: WidgetState) -> _Plan:
        """Resolve value, identity, and the fitted hero for this cell."""
        entity = state.entity

        if entity is None:
            value = PLACEHOLDER_VALUE
            unit = ""
            name = self.label_for(None, fallback=self.config.entity_id or PLACEHOLDER_NAME)
        else:
            # Get value from attribute or state
            if self.attribute:
                raw_value = entity.get(self.attribute)
                # Containers must not headline their Python repr —
                # lists join readably, mappings read as absent.
                if isinstance(raw_value, list | tuple):
                    value = ", ".join(map(str, raw_value)) or PLACEHOLDER_VALUE
                elif isinstance(raw_value, dict) or raw_value is None:
                    value = PLACEHOLDER_VALUE
                else:
                    value = str(raw_value)
            else:
                value = entity.state
                if value in ("unavailable", "unknown", "none", ""):
                    # Absence reads as absence — a quiet dimmed marker,
                    # not a truncated "Unavail…" headline.
                    value = PLACEHOLDER_VALUE
                elif entity.entity_id.startswith("binary_sensor."):
                    value = translate_binary_state(value, entity.device_class)
                elif isinstance(value, str) and value.isalpha() and len(value) <= 16:
                    # Title-case short alpha flag states ('on'→'On', 'home'→'Home')
                    # to match binary-sensor 'Open'/'Closed' style.
                    value = value.title()
            # Apply precision formatting if specified and value is numeric
            if self.precision is not None:
                try:
                    numeric_value = float(value)
                    formatted = f"{numeric_value:.{self.precision}f}"
                    # "1e-9" at precision 3 rounds to "0.000", which reads
                    # as zero — keep the original for tiny non-zero values.
                    if numeric_value == 0.0 or float(formatted) != 0.0:
                        value = formatted
                except (ValueError, TypeError):
                    pass  # Keep original value if not numeric
            unit = entity.unit if self.show_unit else ""
            name = self.label_for(entity)

        # Narrow columns: long word units (km/h, kWh) cost the digits
        # their size — drop them before the value has to shrink or
        # mangle. Short suffixes (°, %, °C) are cheap and keep their
        # meaning; a bare "22" in a footer cell reads as noise.
        if unit and len(unit) > 2 and ctx.width < 100:
            unit = ""

        # Determine icon to use
        icon = self.icon
        if not icon and self.show_icon:
            icon = _get_entity_icon(entity)

        box_w, box_h = cell_box(ctx)
        # "--" is the absence of a value, not a value: it reads as a
        # dimmed marker rather than a headline set in 100px dashes.
        missing = value == PLACEHOLDER_VALUE
        bands_kept = caption_visible(ctx)
        # Short cells (hero-layout footers, ~65px) still owe the value
        # its identity — a bare "85" reads as noise. The header row
        # shrinks instead of disappearing.
        compact_identity = not bands_kept and box_h >= _COMPACT_MIN_H
        show_caption = bool(name) and self.show_name and (bands_kept or compact_identity)
        show_icon = bool(icon) and (bands_kept or compact_identity)

        tint = css_rgb(self.config.color) if self.config.color else ctx.accent()
        header = header_html(
            ctx,
            name if show_caption else "",
            icon if show_icon else None,
            tint,
            width_px=box_w,
            # Compact cells manage the header's visibility themselves —
            # the kit's hide-short must not re-hide the row it shrank for.
            hide="hide-short" if bands_kept else "",
        )

        # Header and hero are one centred block: the gap between them
        # scales with the cell, and the hero gets everything else.
        gap = max(3.0, min(0.09 * box_h, 16.0)) if header else 0.0
        share = HERO_SHARE_STACKED if header else HERO_SHARE_SOLO
        free_h = box_h - header.band_px - gap

        max_hero = min(_MAX_HERO_PX, 0.34 * box_h) if missing else _MAX_HERO_PX
        # Sibling cells in the same layout may have agreed on a common
        # size (see Layout._hero_caps) — never exceed it.
        cap = ctx.extra.get("hero_px_cap")
        if cap:
            max_hero = min(max_hero, float(cap))

        hero = fit_hero(
            value,
            ctx,
            box_w,
            max(16.0, free_h * share),
            suffix=unit,
            allow_wrap=min(ctx.width, ctx.height) >= _WRAP_MIN_CELL,
            max_px=max_hero,
            min_px=_MIN_HERO_PX,
        )
        return _Plan(
            value=value,
            unit=unit,
            missing=missing,
            header=header,
            gap=gap,
            hero=hero,
        )

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the entity widget."""
        p = self._plan(ctx, state)
        return card_html(
            header=p.header,
            hero=hero_block(p.hero, suffix=p.unit),
            hero_color="var(--text-tertiary)" if p.missing else None,
            hero_is_html=True,
            stack_gap_px=p.gap,
            ctx=ctx,
        )

    def hero_hint(self, ctx: CellContext, state: WidgetState) -> tuple[str, float] | None:
        """The size this cell's hero fits at, for sibling harmony.

        Numbers and words are harmonised separately: a grid of readings
        should share one size, and so should a row of "On" / "Off" /
        "Locked" — but a long word must not shrink the numbers beside it.
        """
        p = self._plan(ctx, state)
        if p.missing or p.hero.wrapped:
            return None
        kind = "num" if any(ch.isdigit() for ch in p.value) else "word"
        return kind, p.hero.px
