"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..const import (
    PLACEHOLDER_NAME,
    PLACEHOLDER_VALUE,
)
from ..htmldoc import css_rgb
from ._bands import plan_bands
from ._card import card_html
from ._cellkit import cell_box, label_px
from ._fit import (
    HERO_SHARE_SOLO,
    HERO_SHARE_STACKED,
    fit_hero,
    hero_block,
)
from .base import Widget, WidgetConfig
from .helpers import get_binary_sensor_icon, translate_binary_state

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# The feature icon reads as the cell's identifier, not its message. Its
# size comes from the CELL geometry alone, never the value length —
# neighbouring grid cells must carry equal icons even when one value is
# "On" and the next is "Locked". Tall cells get a bonus: their heroes
# are width-bound, and a fixed-ratio icon would strand the extra height
# as empty gaps. The ratio is deliberately generous (a 2" panel is read
# from across the room); the 0.32*height / 0.5*width caps below keep it
# from crowding the value.
_ICON_VMIN = 0.32
_ICON_TALL_BONUS = 0.15
_ICON_MIN_PX = 13.0
_MAX_HERO_PX = 124.0
_MIN_HERO_PX = 12.0

# Content height at which icon-band + caption + value stack (the old
# design's tile anatomy). Below it the icon drops inline with the
# caption; below the band plan's identity floor identity goes entirely.
_FEATURE_MIN_H = 54.0

# Only wrap a value onto two lines in cells with room to spare.
_WRAP_MIN_CELL = 130


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

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the entity widget."""
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
        # Short cells (hero-layout footers, ~65px) still owe the value
        # its identity — a bare "85" reads as noise. The shared band plan
        # decides that: the caption and icon collapse into one compact
        # inline row instead of disappearing.
        plan = plan_bands(ctx, has_name=bool(name) and self.show_name, box_h=box_h)
        show_caption = plan.show_caption
        show_icon = bool(icon) and (plan.caption or plan.compact_identity)
        # The icon rides its own band above the caption whenever the
        # stack fits (icon + 10px caption + value need ~54px) — the old
        # design stacked even 3x3 tiles, and it reads far better than an
        # inline speck. The inline chip row is only for the very
        # shortest bands.
        feature_icon = show_icon and box_h >= _FEATURE_MIN_H

        caption_band = label_px(ctx) * 1.25 if show_caption else 0.0
        share = HERO_SHARE_SOLO if not (show_caption or feature_icon) else HERO_SHARE_STACKED
        free_h = box_h - caption_band

        max_hero = min(_MAX_HERO_PX, 0.34 * box_h) if missing else _MAX_HERO_PX

        icon_px = min(
            _ICON_VMIN * min(box_w, box_h) + _ICON_TALL_BONUS * max(0.0, box_h - box_w),
            0.32 * box_h,
            0.5 * box_w,
        )
        icon_px = max(icon_px, _ICON_MIN_PX)

        hero = fit_hero(
            value,
            ctx,
            box_w,
            max(16.0, (free_h - (icon_px if feature_icon else 0.0)) * share),
            suffix=unit,
            allow_wrap=min(ctx.width, ctx.height) >= _WRAP_MIN_CELL,
            max_px=max_hero,
            min_px=_MIN_HERO_PX,
        )

        tint = css_rgb(self.config.color) if self.config.color else ctx.accent()

        return card_html(
            # card_html measures and truncates the caption itself (with
            # the chip icon's reserve in compact mode).
            caption=name if show_caption else None,
            icon=icon if show_icon else None,
            icon_color=tint,
            icon_size=icon_px if feature_icon else None,
            # The entity icon is the cell's primary visual identifier —
            # its own band when there's room, inline with the caption in
            # compact cells.
            icon_role="feature" if feature_icon else "chip",
            hero=hero_block(hero, suffix=unit),
            hero_color="var(--text-tertiary)" if missing else None,
            hero_is_html=True,
            plan=plan,
            ctx=ctx,
        )
