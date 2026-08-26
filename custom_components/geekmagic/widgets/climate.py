"""Climate widget for GeekMagic displays."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import css_rgba, mdi_span
from ._card import chip_html
from ._cardfit import (
    HERO_SHARE_STACKED,
    caption_visible,
    cell_box,
    chip_band_px,
    chip_px,
    fit_caption_sized,
    fit_hero,
    hero_block,
    label_px,
)
from ._textfit import metrics_for
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ._textfit import TextMetrics
    from .state import WidgetState


# HVAC action / mode → MDI icon (the "fire" / "snowflake" / "thermostat"
# state visual for the caption band).
HVAC_ACTION_ICONS = {
    "heating": "fire",
    "cooling": "snowflake",
    "idle": "thermostat",
    "off": "power-standby",
    "drying": "water-percent",
    "fan": "fan",
    "preheating": "fire",
}

HVAC_MODE_ICONS = {
    "heat": "fire",
    "cool": "snowflake",
    "heat_cool": "sun-snowflake-variant",
    "auto": "thermostat-auto",
    "dry": "water-percent",
    "fan_only": "fan",
    "off": "power-standby",
}

# HVAC action / mode → theme palette *role*. The role name is both the
# CSS variable suffix (``var(--warning)``) and the ``Theme`` attribute
# (``theme.warning``), so the same mapping drives the markup tint and
# the concrete RGBA used for the cell wash (SVG/gradient color stops
# can't resolve ``var()``).
#
#   heating / preheating → warning / error   (warm)
#   cooling / drying     → info              (cool)
#   fan                  → success
#   idle                 → muted
#   off                  → error
HVAC_ACTION_ROLES: dict[str, str] = {
    "heating": "warning",
    "cooling": "info",
    "idle": "muted",
    "off": "error",
    "drying": "info",
    "fan": "success",
    "preheating": "error",
}

HVAC_MODE_ROLES: dict[str, str] = {
    "heat": "warning",
    "cool": "info",
    "heat_cool": "primary",
    "auto": "primary",
    "dry": "info",
    "fan_only": "success",
    "off": "error",
}

# Public CSS-variable views of the role maps — resolve to the active
# theme's palette at raster time so the heating flame is orange in
# watchOS, amber in retro, coral in candy, etc.
HVAC_ACTION_COLORS: dict[str, str] = {k: f"var(--{v})" for k, v in HVAC_ACTION_ROLES.items()}
HVAC_MODE_COLORS: dict[str, str] = {k: f"var(--{v})" for k, v in HVAC_MODE_ROLES.items()}

# Actions that earn the cell wash. Idle/off stay neutral — a red glow on
# a switched-off thermostat reads as an alarm, and a grey wash on idle is
# just noise.
_ACTIVE_ACTIONS = frozenset({"heating", "cooling", "drying", "fan", "preheating"})

# Smallest cell that gets the wash + hairline. Below this the cell is a
# grid tile and any backdrop treatment reads as dirt.
_WASH_MIN_PX = 170

# CARD_CSS ``.chips`` gap between pills.
_CHIP_GAP_PX = 5.0

# Width safety margin handed to ``fit_hero``. It solves for the size at
# which value+suffix exactly fills the budget, so its own truncation
# check lands on float equality and can cut a value that does fit.
_FIT_SLACK = 0.99


# Placeholder shown when the thermostat reports no reading.
_NO_VALUE = "--"


def _format_temp(value: float | str | None, unit: str = "°") -> str:
    """Format temperature value for display."""
    if value is None:
        return _NO_VALUE
    try:
        num = float(value)
    except (ValueError, TypeError):
        return _NO_VALUE
    if num == int(num):
        return f"{int(num)}{unit}"
    return f"{num:.1f}{unit}"


def _hvac_visual(hvac_action: str | None, hvac_mode: str) -> tuple[str, str]:
    """Pick the HVAC icon + theme-role CSS color for the current state.

    ``hvac_action`` is the live action ("heating", "cooling") and wins
    when present and not ``"idle"``. ``hvac_mode`` is the configured
    mode and is the fallback (used when the unit is reporting idle or
    didn't expose ``hvac_action``).
    """
    if hvac_action and hvac_action != "idle":
        return (
            HVAC_ACTION_ICONS.get(hvac_action, "thermostat"),
            HVAC_ACTION_COLORS.get(hvac_action, "var(--primary)"),
        )
    return (
        HVAC_MODE_ICONS.get(hvac_mode, "thermostat"),
        HVAC_MODE_COLORS.get(hvac_mode, "var(--primary)"),
    )


def _hvac_role(hvac_action: str | None, hvac_mode: str) -> str:
    """Theme attribute name for the current HVAC state's tint."""
    if hvac_action and hvac_action != "idle":
        return HVAC_ACTION_ROLES.get(hvac_action, "primary")
    return HVAC_MODE_ROLES.get(hvac_mode, "primary")


def _chip_width_px(text: str, has_icon: bool, font_px: float, metrics: TextMetrics) -> float:
    """Rendered width of a chip pill: text + 0.85em padding each side.

    An icon adds its own em plus the pill's 0.35em gap.
    """
    width = metrics.width(text, font_px, "semibold") + 1.7 * font_px
    if has_icon:
        width += 1.35 * font_px
    return width


def _row_width_px(
    specs: list[tuple[str, str | None, str | None]], font_px: float, metrics: TextMetrics
) -> float:
    """Width of a chip row including the inter-chip gaps."""
    if not specs:
        return 0.0
    chips = sum(_chip_width_px(t, i is not None, font_px, metrics) for t, i, _ in specs)
    return chips + _CHIP_GAP_PX * (len(specs) - 1)


def _chip_rows(
    specs: list[tuple[str, str | None, str | None]], ctx: CellContext
) -> list[list[tuple[str, str | None, str | None]]]:
    """Pack chip specs into rows that fit the cell width.

    Blitz has no ellipsis and does not clip text, so a chip strip that
    overflows simply bleeds past both cell edges. Measuring with the
    theme's real face keeps every pill inside the cell at any size.

    When everything fits, one row. When it doesn't, the leading (mode)
    chip takes a line of its own and the metric chips share the next —
    a 1+2 split reads as "status, then details", where the greedy 2+1
    split would orphan a single metric pill under a full row.
    """
    if not specs:
        return []
    metrics = metrics_for(ctx.theme)
    font_px = chip_px(ctx)
    usable = cell_box(ctx)[0]
    if _row_width_px(specs, font_px, metrics) <= usable:
        return [specs]

    rows: list[list[tuple[str, str | None, str | None]]] = [[specs[0]]]
    for spec in specs[1:]:
        candidate = [*rows[-1], spec]
        if len(rows) > 1 and _row_width_px(candidate, font_px, metrics) <= usable:
            rows[-1] = candidate
        else:
            rows.append([spec])
    return rows


# Widget-scoped CSS. Injected with the fragment (Blitz honours <style>
# in the body, including media queries, and the cell document only ever
# contains this one widget).
_CLIMATE_CSS = """
<style>
.clim-stack { display: flex; flex-direction: column; align-items: center;
              gap: 4px; width: 100%; }
/* Wide strip cells are too short for stacked bands but far too wide for
   a lone hero, so they lay the same content out horizontally instead. */
.clim-strip { display: flex; align-items: center; gap: 0.2em; }
.clim-strip .icon { font-size: clamp(13px, 26vmin, 32px); }
</style>
"""


def _climate_placeholder() -> str:
    """Placeholder fragment when no climate data is available."""
    icon = mdi_span("thermostat", "icon i-md", "color: var(--text-secondary)")
    return f'<div class="cell">{icon}<div class="t-label hide-short">NO CLIMATE DATA</div></div>'


class ClimateWidget(Widget):
    """Widget that displays climate/thermostat information.

    watchOS-style thermostat card:
      caption = state-tinted HVAC icon + room name (one line)
      hero    = current temperature, big numerals + smaller degree unit
      chips   = [mode chip (state-tinted), target chip, humidity chip],
                wrapped to a second row when they don't fit the width
      wash    = in fullscreen cells, a soft radial tint of the running
                action (warm when heating, cool when cooling)
    """

    WIDGET_TYPE: ClassVar[str] = "climate"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Climate",
        "needs_entity": True,
        "entity_domains": ["climate"],
        "options": [
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_target", "type": "boolean", "label": "Show Target Temp", "default": True},
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_mode", "type": "boolean", "label": "Show HVAC Mode", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the climate widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_target = config.options.get("show_target", True)
        self.show_humidity = config.options.get("show_humidity", True)
        self.show_mode = config.options.get("show_mode", True)

    # ------------------------------------------------------------------
    # Fragment builders
    # ------------------------------------------------------------------

    @staticmethod
    def _wash_style(ctx: CellContext, hvac_action: str | None, role: str) -> str:
        """Inline style for the cell: rounded corners + optional action wash.

        A radial tint of the running action, peaking around 10% alpha at
        the top of the cell and gone by two thirds down — enough to read
        as warmth/coolness at a glance without competing with the hero.
        """
        style = "border-radius: var(--radius);"
        theme = ctx.theme
        if theme is None or hvac_action not in _ACTIVE_ACTIONS:
            return style
        if min(ctx.width, ctx.height) < _WASH_MIN_PX:
            return style
        color = getattr(theme, role, None) or theme.primary
        return (
            f"{style} background: radial-gradient(120% 78% at 50% 4%, "
            f"{css_rgba(color, 0.13)}, {css_rgba(color, 0.0)} 70%);"
        )

    @staticmethod
    def _caption_html(
        ctx: CellContext,
        label: str,
        icon: str,
        tint: str,
        *,
        with_icon: bool,
        hide_short: bool = True,
    ) -> str:
        """Tinted state icon + room name, measured against the real face.

        ``with_icon`` is decided by the caller: when the chip strip shows
        the running mode the caption can spend the icon's width on the
        room name instead — but when the chips are shed (small cells)
        the caption icon is the ONLY carrier of the hvac state, so it
        must ride along. Narrow cells STACK the icon on its own line
        above the name — inline, the icon's reserve starved the room
        name into "LIV… RO…" stubs. ``hide_short=False`` lets short
        cells keep the rows the widget deliberately built for them.
        """
        stack = with_icon and ctx.width < 150
        icon_html = ""
        if with_icon:
            classes = "icon i-md" if stack else "icon i-sm"
            icon_html = mdi_span(icon, classes, f"color: {tint}")
        text, px = fit_caption_sized(
            label, ctx, cell_box(ctx)[0], reserve_em=0.0 if stack or not with_icon else 1.5
        )
        if not (text or icon_html):
            return ""
        hide = " hide-short" if hide_short else ""
        if stack:
            label_row = (
                f'<div class="t-label{hide}" style="font-size: {px:.1f}px">{escape(text)}</div>'
                if text
                else ""
            )
            return f'<div class="card-icon{hide}">{icon_html}</div>{label_row}'
        size = f' style="font-size: {px:.1f}px"'
        return f'<div class="t-label caption-row{hide}"{size}>{icon_html}{escape(text)}</div>'

    @staticmethod
    def _hero_html(ctx: CellContext, value: str, unit: str, avail_w: float, avail_h: float) -> str:
        """Big numerals with the degree unit smaller, on the same baseline.

        Sized with :func:`fit_hero` rather than the kit's ``clamp()`` so
        a short reading like ``21`` fills the cell while ``-10.5`` still
        fits — the clamp has to assume the worst case for every value.
        """
        missing = value == _NO_VALUE
        # A 3x3 tile has no width to spare: the reading is unambiguous
        # without "°C", and dropping it buys the numerals ~20% more size.
        suffix = unit if not missing and ctx.width >= 100 else ""
        # An absent reading must not shout: fitted to the band, "--" is
        # two bars the size of the temperature it stands in for.
        max_px = min(46.0, avail_h * 0.5) if missing else 128.0
        # fit_hero sizes the value so text+suffix exactly equals the width
        # budget, which leaves its own truncation check sitting on float
        # equality — a hair of slack keeps a fitting value from being cut.
        fit = fit_hero(value, ctx, avail_w * _FIT_SLACK, avail_h, suffix=suffix, max_px=max_px)
        style = ' style="color: var(--text-secondary)"' if missing else ""
        return f'<div class="t-hero"{style}>{hero_block(fit.text, fit.px, suffix=suffix)}</div>'

    @staticmethod
    def _is_strip(ctx: CellContext) -> bool:
        """True for wide, short cells (footer strips, 228x74).

        Too short for the kit's caption/chip bands, but leaving a lone
        hero floating in 228px of width wastes most of the cell.
        """
        return ctx.height < 100 and ctx.width >= 2.2 * ctx.height

    def _strip_html(
        self,
        ctx: CellContext,
        hero: tuple[str, str],
        state_icon: tuple[str, str],
        specs: list[tuple[str, str | None, str | None]],
    ) -> str:
        """Horizontal treatment: state icon + hero, then the mode pill."""
        value, unit = hero
        icon, tint = state_icon
        avail_w, avail_h = cell_box(ctx)
        icon_html = mdi_span(icon, "icon i-sm", f"color: {tint}")
        chips = ""
        # The pill and the icon share the row with the hero, so take
        # their width out of the hero's budget before fitting it.
        reserved = 1.6 * label_px(ctx)
        if specs:
            text, chip_icon, color = specs[0]
            reserved += _chip_width_px(
                text, chip_icon is not None, chip_px(ctx), metrics_for(ctx.theme)
            )
            chips = f'<div class="chips">{chip_html(text, icon=chip_icon, color=color)}</div>'
        hero_html = self._hero_html(ctx, value, unit, max(24.0, avail_w - reserved), avail_h * 0.86)
        return (
            f'{_CLIMATE_CSS}<div class="cell row" style="border-radius: var(--radius)">'
            f'<div class="clim-strip">{icon_html}{hero_html}</div>{chips}</div>'
        )

    def _chip_specs(
        self, entity: Any, hvac_action: str | None, hvac_mode: str
    ) -> list[tuple[str, str | None, str | None]]:
        """(text, icon, color) for each supporting pill, in priority order."""
        specs: list[tuple[str, str | None, str | None]] = []
        if self.show_mode:
            mode_key = hvac_action or hvac_mode
            if mode_key:
                # Mode chip tint keys on the *displayed* state, so "IDLE"
                # is muted even when the configured mode would tint the
                # icon (mode-chip text tint is an allowed exception).
                mode_color = (
                    HVAC_ACTION_COLORS.get(mode_key)
                    or HVAC_MODE_COLORS.get(mode_key)
                    or "var(--primary)"
                )
                specs.append((mode_key.replace("_", " ").upper(), None, mode_color))
        if self.show_target and entity.get("temperature") is not None:
            specs.append((_format_temp(entity.get("temperature")), "target", None))
        if self.show_humidity and entity.get("humidity") is not None:
            try:
                humidity_val = int(float(entity.get("humidity")))
            except (ValueError, TypeError):
                pass
            else:
                specs.append((f"{humidity_val}%", "water-percent", "var(--info)"))
        return specs

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the climate widget."""
        entity = state.entity
        if entity is None:
            return _climate_placeholder()

        hvac_mode = entity.state
        hvac_action = entity.get("hvac_action")
        icon_name, icon_color = _hvac_visual(hvac_action, hvac_mode)
        role = _hvac_role(hvac_action, hvac_mode)

        unit = entity.get("temperature_unit") or "°C"
        value = _format_temp(entity.get("current_temperature"), "")
        specs = self._chip_specs(entity, hvac_action, hvac_mode)

        if self._is_strip(ctx):
            return self._strip_html(ctx, (value, unit), (icon_name, icon_color), specs)

        avail_w, avail_h = cell_box(ctx)
        bands: list[str] = []
        spent = 0.0

        bands_kept = caption_visible(ctx)
        # Short non-strip cells keep a shrunk caption row instead of an
        # anonymous temperature (same compact-identity rule as entity).
        compact_identity = not bands_kept and avail_h >= 40.0
        show_caption = bands_kept or compact_identity

        # Width decides how the pills pack; height decides how many rows
        # the cell can afford. A 2x2 tile keeps only the running state, a
        # split-v column stacks all three, a wide cell fits one row.
        # Chips survive to 100px rather than the kit's 130px: a
        # thermostat without its running state is worth much less.
        rows: list[list[tuple[str, str | None, str | None]]] = []
        if min(ctx.width, ctx.height) >= 100:
            rows = _chip_rows(specs, ctx)[: 1 if ctx.height < 150 else 3]
            spent += len(rows) * chip_band_px(ctx)

        if show_caption:
            # The caption icon rides along whenever the chips (which
            # otherwise show the mode) are shed or the cell is wide
            # enough to afford both.
            mode_in_chips = bool(rows) and self.show_mode
            with_icon = ctx.width >= 150 or not mode_in_chips
            # A hidden name leaves the band to the state icon alone —
            # and when the chips already carry the mode, drops it
            # entirely so the hero gets the height.
            name = self.label_for(entity, state=state) if self.show_name else ""
            show_caption = bool(name) or with_icon
        if show_caption:
            spent += label_px(ctx)
            if with_icon and ctx.width < 150:
                # The stacked state icon takes its own band (i-md clamp
                # mirror) — budget it or the hero eats its room.
                spent += max(14.0, min(0.20 * min(ctx.width, ctx.height), 48.0))
            bands.append(
                self._caption_html(
                    ctx,
                    name,
                    icon_name,
                    icon_color,
                    with_icon=with_icon,
                    hide_short=bands_kept,
                )
            )
        bands.append(
            self._hero_html(
                ctx, value, unit, avail_w, max(24.0, avail_h - spent) * HERO_SHARE_STACKED
            )
        )
        if rows:
            strip = "".join(
                '<div class="chips">'
                + "".join(chip_html(t, icon=i, color=c) for t, i, c in row)
                + "</div>"
                for row in rows
            )
            bands.append(f'<div class="clim-stack">{strip}</div>')

        cell_style = self._wash_style(ctx, hvac_action, role)
        return f'{_CLIMATE_CSS}<div class="cell" style="{cell_style}">{"".join(bands)}</div>'
