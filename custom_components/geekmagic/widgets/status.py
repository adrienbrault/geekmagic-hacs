"""Status widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import PLACEHOLDER_NAME
from ..htmldoc import css_rgb, mdi_span
from ._cardfit import CAPTION_MIN_PX, fit_caption_sized
from ._cellkit import cell_box_px, cell_padding, hairline_css, label_px, tint_css
from ._textfit import HERO_TRACKING, TextMetrics, metrics_for
from .base import Widget, WidgetConfig
from .helpers import (
    ON_STATES,
    get_binary_sensor_icon,
    get_domain_state_icon,
    translate_binary_state,
)

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import EntityState, WidgetState

# Indicator chip: the icon sits in a soft lozenge tinted with the state
# colour — an iOS status-tile lamp. Sizes are em-relative to the icon's
# own font-size, so the chip scales with whatever the kit picks.
# MDI glyphs carry generous internal padding, so the lozenge only needs
# a little more than the em box to look optically centred.
_CHIP_SIZE_EM = 1.38
_CHIP_FILL_ALPHA = 0.17
_CHIP_RING_ALPHA = 0.26
# Same tint, used to fill the state pills in the list variant.
_PILL_FILL_ALPHA = 0.16

# Content height below which even a 10px identity row would crowd the
# state out of the cell. Mirrors the card family's compact-identity gate.
_IDENTITY_MIN_H = 34.0
# The same gate for the icon-only variant, which has no hero to protect —
# only the chip, and a chip a few pixels smaller still reads.
_ICON_ONLY_CAPTION_MIN_H = 40.0


def _is_entity_on(entity: EntityState | None) -> bool:
    """Check if entity is in 'on' state."""
    if entity is None:
        return False
    return entity.state.lower() in ON_STATES


def _css_color(value: object, fallback: str) -> str:
    """Coerce a stored RGB option (JSON list/tuple) to CSS, else a palette var."""
    if isinstance(value, list | tuple) and len(value) == 3:
        try:
            return css_rgb((int(value[0]), int(value[1]), int(value[2])))
        except (TypeError, ValueError):
            return fallback
    return fallback


def _tint_rgb(value: object, ctx: CellContext, role: str) -> tuple[int, int, int]:
    """Resolve a state colour to concrete RGB for rgba() tints.

    ``var(--success)`` cannot be faded with ``rgba()``, so the halo behind
    the icon needs real channel values: the user's configured colour when
    there is one, otherwise the active theme's semantic role.
    """
    if isinstance(value, list | tuple) and len(value) == 3:
        try:
            return (int(value[0]), int(value[1]), int(value[2]))
        except (TypeError, ValueError):
            pass
    theme = ctx.theme
    if theme is None:  # pragma: no cover - ctx always carries a theme
        return (128, 128, 128)
    return getattr(theme, role)


@dataclass(frozen=True)
class _Indicator:
    """Everything the state resolves to, ready to render."""

    name: str
    icon: str
    color: str  # CSS colour: a theme var() or the user's rgb()
    fill: str  # the same colour at _CHIP_FILL_ALPHA, flattened
    ring: str  # the same colour at _CHIP_RING_ALPHA, flattened
    text: str

    def chip_html(self, *, size_class: str, px: float | None = None) -> str:
        """Icon inside a tinted indicator lozenge.

        ``px`` overrides the kit size class when the band has a measured
        height budget; otherwise the class (``i-lg``/``i-md``) drives it
        and the chip follows in ``em``.
        """
        style = [
            f"color: {self.color}",
            f"background: {self.fill}",
            f"border: 1px solid {self.ring}",
            f"width: {_CHIP_SIZE_EM}em",
            f"height: {_CHIP_SIZE_EM}em",
            "display: inline-flex",
            "align-items: center",
            "justify-content: center",
            "border-radius: 999px",
            "box-sizing: border-box",
            "flex: none",
        ]
        if px is not None:
            style.insert(0, f"font-size: {px:.1f}px")
        return mdi_span(self.icon, f"icon {size_class}", "; ".join(style))


@dataclass(frozen=True)
class _Row:
    """One resolved list row, before it knows how much space it gets."""

    label: str
    state_text: str
    icon: str | None
    color: str  # CSS colour for the icon and the pill's text
    fill: str  # the same colour at _PILL_FILL_ALPHA, flattened

    def _lead_html(self, icon_px: float, icon_col: float) -> str:
        """The fixed-width indicator column that names align against."""
        if self.icon:
            return mdi_span(
                self.icon,
                "icon",
                f"font-size: {icon_px:.1f}px; color: {self.color}; flex: none; "
                f"width: {icon_col:.1f}px; text-align: center",
            )
        # No icon known — a tinted lamp still reads as a status.
        dot = max(6.0, icon_px * 0.5)
        return (
            f'<span style="flex: none; width: {icon_col:.1f}px; display: flex; '
            'align-items: center; justify-content: center">'
            f'<span style="width: {dot:.1f}px; height: {dot:.1f}px; '
            f'border-radius: 50%; background: {self.color}"></span></span>'
        )

    def _state_html(self, px: float, *, filled: bool) -> str:
        """The row's state text, as a tinted pill or bare when it must be.

        The pill's own padding is ~1.7em of the row's width; a narrow
        column that cannot spare it keeps the state as bare tinted text
        rather than losing the word.
        """
        if filled:
            return (
                f'<span class="chip" style="flex: none; font-size: {px:.1f}px; '
                f"font-weight: 700; color: {self.color}; "
                f'background: {self.fill}">{escape(self.state_text)}</span>'
            )
        return (
            f'<span style="flex: none; font-size: {px:.1f}px; font-weight: 700; '
            f'line-height: 1; color: {self.color}">{escape(self.state_text)}</span>'
        )

    def html(
        self,
        tm: TextMetrics,
        *,
        index: int,
        row_h: float,
        name_px: float,
        name_budget: float,
        icon_px: float,
        icon_col: float,
        gap: float,
        pill_px: float | None,
        pill_filled: bool = True,
        hairline: str,
    ) -> str:
        """Icon column, name, and (when it fits) the tinted state pill."""
        pill_html = "" if pill_px is None else self._state_html(pill_px, filled=pill_filled)
        # A long name gets one shrink step (down to 88%) before the
        # ellipsis — "Kitchen Window" whole at 13px beats "Kitchen …"
        # at 15px. The step is bounded so rows stay visually uniform.
        if tm.width(self.label, name_px, "semibold") > name_budget:
            shrunk = tm.fit_font_size(
                self.label, name_budget, name_px, "semibold", min_px=name_px * 0.88
            )
            name_px = shrunk
        name = tm.truncate(self.label, name_px, name_budget, "semibold", min_chars=3)
        sep = f"border-top: 1px solid {hairline}; " if index > 0 else ""
        return (
            f'<div style="{sep}height: {row_h:.1f}px; flex: none; display: flex; '
            f'align-items: center; gap: {gap:.1f}px">'
            f"{self._lead_html(icon_px, icon_col)}"
            f'<span style="flex: 1; min-width: 0; font-size: {name_px:.1f}px; '
            "font-weight: 600; line-height: 1.05; white-space: nowrap; "
            f'color: var(--text-primary)">{escape(name)}</span>'
            f"{pill_html}"
            "</div>"
        )


def _entity_status_icon(entity: EntityState | None) -> str | None:
    """Derive an icon for an entity: device_class state icon > explicit icon > domain icon."""
    if entity is None:
        return None
    domain = entity.entity_id.split(".")[0]
    if domain == "binary_sensor":
        icon = get_binary_sensor_icon(entity.state, entity.device_class)
        if icon:
            return icon
    if entity.icon:
        return entity.icon
    return get_domain_state_icon(domain, entity.state, entity.device_class)


class StatusWidget(Widget):
    """Widget that displays a binary sensor status with colored indicator.

    Reads as a physical indicator: the device icon sits in a lozenge
    tinted with the state colour (iOS status tile), and the ON/OFF hero
    carries the same tint — the documented exception where colour *is*
    the meaning.

    Three layouts, chosen from the cell's aspect at render time:

    - **strip** (wide and short): chip on the left, name + state stacked
      beside it, so a 228x74 slot spends its width instead of its height.
    - **stack** (square-ish and roomy): chip / name / state bands.
    - **compact** (either side under ~90px): state only, sized as large
      as the cell allows.
    """

    WIDGET_TYPE: ClassVar[str] = "status"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Status",
        "needs_entity": True,
        "entity_domains": None,  # Any entity (interprets state as on/off)
        "options": [
            {"key": "on_text", "type": "text", "label": "On Text", "default": "On"},
            {"key": "off_text", "type": "text", "label": "Off Text", "default": "Off"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [50, 215, 75],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [110, 110, 114],
            },
            {"key": "icon", "type": "icon", "label": "Icon"},
            {
                "key": "show_status_text",
                "type": "boolean",
                "label": "Show Status Text",
                "default": True,
            },
            {
                "key": "show_name",
                "type": "boolean",
                "label": "Show Name",
                "default": True,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status widget."""
        super().__init__(config)
        self._on_option = config.options.get("on_color")
        self._off_option = config.options.get("off_color")
        self.on_color = _css_color(self._on_option, "var(--success)")
        self.off_color = _css_color(self._off_option, "var(--muted)")
        self.on_text = config.options.get("on_text", "ON")
        self.off_text = config.options.get("off_text", "OFF")
        self.icon = config.options.get("icon")
        self.show_status_text = config.options.get("show_status_text", True)
        self.show_name = config.options.get("show_name", True)

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the status widget."""
        entity = state.entity
        is_on = _is_entity_on(entity)
        color = self.on_color if is_on else self.off_color
        tint = _tint_rgb(
            self._on_option if is_on else self._off_option,
            ctx,
            "success" if is_on else "muted",
        )
        ind = _Indicator(
            name=self.label_for(entity, fallback=PLACEHOLDER_NAME) if self.show_name else "",
            icon=self.icon or _entity_status_icon(entity) or "circle",
            color=color,
            fill=tint_css(tint, ctx.theme, _CHIP_FILL_ALPHA),
            ring=tint_css(tint, ctx.theme, _CHIP_RING_ALPHA),
            text=self.on_text if is_on else self.off_text,
        )

        if not self.show_status_text:
            return self._render_icon_only(ctx, ind)

        # Wide slots read far better as a row: the chip anchors the left
        # edge and the name/state stack spends the width instead of
        # stranding it either side of a centred column.
        if ctx.width >= 150 and ctx.width >= ctx.height * 1.7:
            return self._render_strip(ctx, ind)
        # The stacked chip/name/state fits from ~64px of height — even a
        # 3x3 tile (the old design stacked those too). The inline compact
        # row is only for cells with no vertical room at all.
        if ctx.height < 64 or ctx.width < 48:
            return self._render_compact(ctx, ind)
        return self._render_stack(ctx, ind)

    # ------------------------------------------------------------------
    # Layouts
    # ------------------------------------------------------------------

    @staticmethod
    def _caption_html(
        ctx: CellContext,
        text: str,
        max_width: float,
        align: str,
        *,
        icon_html: str = "",
        max_px: float | None = None,
    ) -> str:
        """A caps-tracked name band, shrunk to the width it actually has.

        Size is given up before letters (the shared ``fit_caption_sized``
        policy): a whole "FRONT DOOR" at 10px names the cell where
        "FRON…" at 12px names nothing. Visibility is the caller's
        decision, so the band never carries ``hide-short`` — the kit's
        media rule would re-hide the row the widget shrank for.
        """
        fitted, px = fit_caption_sized(text, ctx, max_width, reserve_em=1.5 if icon_html else 0.0)
        if max_px is not None:
            px = min(px, max_px)
        if not (fitted or icon_html):
            return ""
        classes = "t-label caption-row" if icon_html else "t-label"
        return (
            f'<div class="{classes}" style="text-align: {align}; font-size: {px:.1f}px">'
            f"{icon_html}{escape(fitted)}</div>"
        )

    def _render_stack(self, ctx: CellContext, ind: _Indicator) -> str:
        """Chip / name / state, spread evenly down the cell."""
        tm = metrics_for(ctx.theme)
        pad_x, pad_y = cell_padding(ctx)
        usable_w, usable_h = cell_box_px(ctx, pad_x, pad_y)
        caption_px = label_px(ctx)

        # A hidden name frees its band for the other two: the chip and
        # the hero split what the caption would have taken.
        caption_h = caption_px * 1.2 if ind.name else 0.0
        chip_outer = min(max(0.36 * usable_h, 26.0), 104.0, 0.55 * usable_w)
        hero_px = tm.fit_font_size(
            ind.text,
            usable_w * 0.94,
            (0.38 if ind.name else 0.44) * usable_h,
            "extrabold",
            tracking=HERO_TRACKING,
            min_px=14.0,
        )
        # Short values leave the height budget unspent — give the slack
        # back to the indicator so the cell never reads half-empty.
        slack = usable_h - (chip_outer + caption_h + hero_px)
        if slack > 0.22 * usable_h:
            chip_outer = min(chip_outer + slack * 0.45, 104.0, 0.55 * usable_w)

        # No hide-short on either band: this layout only runs in cells at
        # least 90px on their short side, which the chip and the caption
        # were just sized against — the kit's 100px rule would blank the
        # top two thirds of a 96px cell it has no say over.
        chip = ind.chip_html(size_class="i-md", px=chip_outer / _CHIP_SIZE_EM)
        return (
            f'<div class="cell" style="padding: {pad_y:.1f}px {pad_x:.1f}px">'
            f'<div class="card-icon">{chip}</div>'
            f"{self._caption_html(ctx, ind.name, usable_w, 'center')}"
            f'<div class="t-hero" style="color: {ind.color}; font-size: {hero_px:.1f}px">'
            f"{escape(ind.text)}</div>"
            "</div>"
        )

    def _render_strip(self, ctx: CellContext, ind: _Indicator) -> str:
        """Chip on the left, name over state on the right."""
        tm = metrics_for(ctx.theme)
        pad_x, pad_y = cell_padding(ctx)
        usable_w, usable_h = cell_box_px(ctx, pad_x, pad_y)
        caption_px = label_px(ctx)

        chip_outer = min(max(0.60 * usable_h, 24.0), 104.0, 0.34 * usable_w)
        gap = max(7.0, chip_outer * 0.20)
        text_w = usable_w - chip_outer - gap
        inner_gap = max(2.0, usable_h * 0.05)
        # No name band: the hero gets its height back.
        caption_h = caption_px * 1.15 + inner_gap if ind.name else 0.0
        hero_px = tm.fit_font_size(
            ind.text,
            text_w,
            usable_h - caption_h,
            "extrabold",
            tracking=HERO_TRACKING,
            min_px=14.0,
        )

        chip = ind.chip_html(size_class="i-md", px=chip_outer / _CHIP_SIZE_EM)
        return (
            f'<div class="cell row" style="padding: {pad_y:.1f}px {pad_x:.1f}px; '
            f'justify-content: center; gap: {gap:.1f}px">'
            f"{chip}"
            '<div style="display: flex; flex-direction: column; align-items: flex-start; '
            f'justify-content: center; gap: {inner_gap:.1f}px">'
            f"{self._caption_html(ctx, ind.name, text_w, 'left')}"
            f'<div class="t-hero" style="color: {ind.color}; font-size: {hero_px:.1f}px">'
            f"{escape(ind.text)}</div>"
            "</div></div>"
        )

    def _render_compact(self, ctx: CellContext, ind: _Indicator) -> str:
        """3x3-grid slot: an inline identity row over the state.

        A bare "OPEN" says nothing about *what* is open, so the chip and
        the name collapse into one 10px row — the compact-identity rule
        the card widgets follow — and the state keeps the rest.
        """
        tm = metrics_for(ctx.theme)
        pad_x, pad_y = cell_padding(ctx)
        usable_w, usable_h = cell_box_px(ctx, pad_x, pad_y)

        identity = ""
        if usable_h >= _IDENTITY_MIN_H:
            icon_html = mdi_span(
                ind.icon,
                "icon",
                f"font-size: {CAPTION_MIN_PX * 1.15:.1f}px; color: {ind.color}; flex: none",
            )
            identity = self._caption_html(
                ctx, ind.name, usable_w, "center", icon_html=icon_html, max_px=CAPTION_MIN_PX
            )
        hero_px = tm.fit_font_size(
            ind.text,
            usable_w,
            (usable_h - (CAPTION_MIN_PX * 1.5 if identity else 0.0)) * 0.78,
            "extrabold",
            tracking=HERO_TRACKING,
            min_px=12.0,
        )
        return (
            f'<div class="cell" style="padding: {pad_y:.1f}px {pad_x:.1f}px; '
            f'justify-content: center; gap: {CAPTION_MIN_PX * 0.4:.1f}px">{identity}'
            f'<div class="t-hero" style="color: {ind.color}; font-size: {hero_px:.1f}px">'
            f"{escape(ind.text)}</div></div>"
        )

    def _render_icon_only(self, ctx: CellContext, ind: _Indicator) -> str:
        """The tinted chip *is* the state — promoted to the hero band."""
        pad_x, pad_y = cell_padding(ctx)
        usable_w, usable_h = cell_box_px(ctx, pad_x, pad_y)
        caption_px = label_px(ctx)
        # An unnamed lozenge is a lamp with no label on it. The caption
        # shrinks instead of disappearing, so it survives every cell with
        # room for a chip and a 10px word above it — unless the user
        # hid the name outright (issue #180), which leaves the chip the
        # whole cell.
        show_caption = bool(ind.name) and usable_h >= _ICON_ONLY_CAPTION_MIN_H
        chip_outer = min(
            usable_h - (caption_px * 1.9 if show_caption else 0.0),
            usable_w * 0.72,
            132.0,
        )
        chip = ind.chip_html(size_class="i-lg", px=max(14.0, chip_outer / _CHIP_SIZE_EM))
        caption = self._caption_html(ctx, ind.name, usable_w, "center") if show_caption else ""
        # Two bands only: space-evenly would fling the caption and the
        # chip to opposite ends of a tall cell. Centre them as one unit.
        return (
            f'<div class="cell" style="padding: {pad_y:.1f}px {pad_x:.1f}px; '
            f'justify-content: center; gap: {caption_px * 0.8:.1f}px">{caption}'
            f'<div class="card-icon">{chip}</div></div>'
        )


class StatusListWidget(Widget):
    """Widget that displays a list of binary sensors with status indicators.

    watchOS list pattern: caps-tracked title, then evenly-pitched rows
    separated by hairlines. Each row is a fixed-width icon column (so
    names start on a common left edge), the name, and the state in a
    small pill tinted with the state colour. Rows keep a maximum pitch,
    so a two-item list in a 240px cell stays a tight centred block
    instead of two items marooned at opposite edges.
    """

    WIDGET_TYPE: ClassVar[str] = "status_list"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Status List",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "entities", "type": "status_entities", "label": "Status Entities"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [50, 215, 75],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [110, 110, 114],
            },
        ],
    }

    # Row pitch bounds. The floor keeps a 10px name legible on a 2"
    # panel; the ceiling stops a two-item list from sprawling across a
    # 240px cell, and the width term keeps the pitch proportional in
    # narrow slots (a 46px row in a 114px column reads as a poster, not
    # a list).
    _ROW_MIN = 10.5
    _ROW_MAX = 58.0

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status list widget."""
        super().__init__(config)
        self.entities = config.options.get("entities", [])
        self._on_option = config.options.get("on_color")
        self._off_option = config.options.get("off_color")
        self.on_color = _css_color(self._on_option, "var(--success)")
        self.off_color = _css_color(self._off_option, "var(--muted)")
        self.on_text = config.options.get("on_text")
        self.off_text = config.options.get("off_text")
        self.title = config.options.get("title")

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on."""
        return [e[0] if isinstance(e, list | tuple) else e for e in self.entities]

    def _state_text(self, entity: EntityState | None, is_on: bool) -> str:
        """Right-hand state text: configured on/off text > device_class translation."""
        configured = self.on_text if is_on else self.off_text
        if configured:
            return configured
        if entity is not None and entity.entity_id.startswith("binary_sensor."):
            translated = translate_binary_state(entity.state, entity.device_class)
            if translated != entity.state:
                return translated
        return "On" if is_on else "Off"

    def _resolve_rows(self, ctx: CellContext, state: WidgetState) -> list[_Row]:
        """Turn the configured entries into everything a row needs."""
        rows: list[_Row] = []
        for entry in list(self.entities) or [None]:
            if isinstance(entry, list | tuple):
                entity_id, label = entry[0], entry[1]
            elif entry is None:
                entity_id, label = "", PLACEHOLDER_NAME
            else:
                entity_id, label = entry, None

            entity = state.get_entity(entity_id) if entity_id else None
            is_on = _is_entity_on(entity)
            tint = _tint_rgb(
                self._on_option if is_on else self._off_option,
                ctx,
                "success" if is_on else "muted",
            )
            if entity and not label:
                label = entity.friendly_name
            rows.append(
                _Row(
                    label=str(label or entity_id or PLACEHOLDER_NAME),
                    state_text=self._state_text(entity, is_on),
                    icon=_entity_status_icon(entity),
                    color=self.on_color if is_on else self.off_color,
                    fill=tint_css(tint, ctx.theme, _PILL_FILL_ALPHA),
                )
            )
        return rows

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the status list widget."""
        tm = metrics_for(ctx.theme)
        rows = self._resolve_rows(ctx, state)
        pad_x, pad_y = cell_padding(ctx)
        avail, usable_h = cell_box_px(ctx, pad_x, pad_y)

        # A row's pitch answers to both axes: tall enough to breathe,
        # never taller than the cell is wide would make sensible.
        row_max = min(self._ROW_MAX, ctx.width * 0.30)

        # The title earns its band on the height budget alone — a narrow
        # column still has to say what it is listing, and the title
        # shrinks to the 10px floor before it costs a row its pitch.
        title_text, title_px = (
            fit_caption_sized(self.title, ctx, avail) if self.title else ("", 0.0)
        )
        title_h = title_px * 1.9 if title_text else 0.0
        show_title = bool(title_text) and (usable_h - title_h) / len(rows) >= self._ROW_MIN
        rows_h = usable_h - (title_h if show_title else 0.0)

        # Past a point there is no legible pitch left; showing fewer rows
        # beats stacking unreadable ones.
        if rows_h / len(rows) < self._ROW_MIN:
            rows = rows[: max(1, int(rows_h // self._ROW_MIN))]
        row_h = min(rows_h / len(rows), row_max)

        icon_px = max(12.0, min(row_h * 0.78, 28.0))
        icon_col = icon_px * 1.25
        gap = max(4.0, row_h * 0.16)
        pill_px = max(10.0, min(row_h * 0.44, 18.0))

        # The state is all-or-nothing across rows — a list where only some
        # rows carry one loses its right-hand edge — but it shrinks before
        # it goes, so a mid-size cell keeps "Closed" instead of leaving
        # the state to the icon's tint alone. It is set as bare tinted
        # text at nearly the name's size (a pill's padding costs width a
        # 2" panel does not have, and the colour already says "badge");
        # every step is sized off the widest state and kept only if the
        # names still get a readable share.
        name_budget = avail - icon_col - gap
        keep = max(0.30 * avail, 55.0)
        state_px: float | None = None
        pill_filled = False
        for px, filled in ((pill_px, False), (max(9.0, pill_px * 0.8), False), (9.0, False)):
            # Twice the gap: one the flex row consumes, one kept clear so
            # a name that fills its budget still breathes off the state.
            cost = (
                max(tm.width(r.state_text, px, "bold") for r in rows)
                + (px * 1.7 if filled else 0.0)
                + gap * 2
            )
            if name_budget - cost >= keep:
                state_px, pill_filled = px, filled
                name_budget -= cost
                break

        name_px = self._name_px(tm, rows, row_h, name_budget)

        body = "".join(
            row.html(
                tm,
                index=i,
                row_h=row_h,
                name_px=name_px,
                name_budget=name_budget,
                icon_px=icon_px,
                icon_col=icon_col,
                gap=gap,
                pill_px=state_px,
                pill_filled=pill_filled,
                hairline=hairline_css(ctx.theme),
            )
            for i, row in enumerate(rows)
        )

        title_html = ""
        if show_title:
            title_html = (
                '<div class="t-label" style="text-align: left; flex: none; '
                f"font-size: {title_px:.1f}px; "
                f'padding-bottom: {title_px * 0.55:.1f}px">{escape(title_text)}</div>'
            )

        return (
            f'<div class="cell" style="padding: {pad_y:.1f}px {pad_x:.1f}px; '
            'align-items: stretch; justify-content: center; text-align: left">'
            f"{title_html}"
            '<div style="flex: none; display: flex; flex-direction: column">'
            f"{body}</div></div>"
        )

    @staticmethod
    def _name_px(tm: TextMetrics, rows: list[_Row], row_h: float, budget: float) -> float:
        """One name size for every row, sized so a *typical* label fits.

        Fitting the longest label would punish four short names for one
        long one; fitting the median keeps the common case whole and lets
        the outlier truncate, which is how a system list behaves.
        """
        ideal = max(10.0, min(row_h * 0.50, 24.0))
        units = sorted(tm.width(r.label, 1.0, "semibold") for r in rows)
        median = units[len(units) // 2]
        if median <= 0:  # pragma: no cover - empty labels are placeholder-filled
            return ideal
        return max(10.0, min(ideal, budget / median))
