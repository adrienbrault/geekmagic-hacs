"""Climate widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING,
    Color,
    Column,
    Component,
    Icon,
    Row,
    Text,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


# HVAC action to icon mapping
HVAC_ACTION_ICONS = {
    "heating": "fire",
    "cooling": "snowflake",
    "idle": "thermostat",
    "off": "power-standby",
    "drying": "water-percent",
    "fan": "fan",
    "preheating": "fire",
}

# HVAC mode to icon mapping (used when action is not available)
HVAC_MODE_ICONS = {
    "heat": "fire",
    "cool": "snowflake",
    "heat_cool": "sun-snowflake-variant",
    "auto": "thermostat-auto",
    "dry": "water-percent",
    "fan_only": "fan",
    "off": "power-standby",
}

# HVAC action / mode → theme role color sentinel.
# Resolved at draw time so heating shows in the theme's warning colour
# (orange on watchOS, amber on retro, coral on candy, etc.) and cooling
# in the theme's info colour. No more hardcoded SYSTEM_* leaking through.
HVAC_ACTION_ROLES: dict[str, Color] = {
    "heating": THEME_WARNING,
    "cooling": THEME_INFO,
    "idle": THEME_MUTED,
    "off": THEME_MUTED,
    "drying": THEME_INFO,
    "fan": THEME_SUCCESS,
    "preheating": THEME_ERROR,
}

HVAC_MODE_ROLES: dict[str, Color] = {
    "heat": THEME_WARNING,
    "cool": THEME_INFO,
    "heat_cool": THEME_PRIMARY,
    "auto": THEME_PRIMARY,
    "dry": THEME_INFO,
    "fan_only": THEME_SUCCESS,
    "off": THEME_MUTED,
}


def _format_temp(value: float | str | None, unit: str = "°") -> str:
    """Format temperature value for display."""
    if value is None:
        return "--"
    try:
        num = float(value)
    except (ValueError, TypeError):
        return "--"
    # Show decimal only if meaningful
    if num == int(num):
        return f"{int(num)}{unit}"
    return f"{num:.1f}{unit}"


@dataclass
class ClimateDisplay(Component):
    """Climate display component with cell-shape-aware layouts.

    Three layouts:
      - full: hero temp dominates the cell, mode label caps-tracked at
        top, target + humidity row pinned to the bottom — fills the cell.
      - medium: caps mode label top, bold hero temp middle (auto-fit),
        single-line summary at the bottom (target / humidity).
      - compact: tight 2-row layout for small grid cells.

    All variants use justify="space-evenly" to spread content across the cell.
    """

    current_temp: float | int | str | None = None
    target_temp: float | int | str | None = None
    hvac_mode: str = "off"
    hvac_action: str | None = None
    humidity: int | str | None = None
    name: str = ""
    show_target: bool = True
    show_humidity: bool = True
    show_mode: bool = True
    temp_unit: str = "°C"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render climate widget — picks layout from cell shape."""
        size = get_size_category(height)
        is_very_narrow = width < 90  # 3-column grids
        is_narrow = width < 130  # 2-column side-by-side

        if is_very_narrow or size in (SizeCategory.MICRO, SizeCategory.TINY):
            component = self._build_compact(ctx, width, height)
        elif is_narrow or size == SizeCategory.SMALL:
            component = self._build_medium(ctx, width, height)
        else:
            component = self._build_full(ctx, width, height)

        component.render(ctx, x, y, width, height)

    def _get_icon_and_color(self) -> tuple[str, tuple[int, int, int]]:
        """Get icon + theme-role color sentinel based on hvac_action/mode."""
        if self.hvac_action and self.hvac_action != "idle":
            icon = HVAC_ACTION_ICONS.get(self.hvac_action, "thermostat")
            color = HVAC_ACTION_ROLES.get(self.hvac_action, THEME_PRIMARY)
        else:
            icon = HVAC_MODE_ICONS.get(self.hvac_mode, "thermostat")
            color = HVAC_MODE_ROLES.get(self.hvac_mode, THEME_PRIMARY)
        return icon, color

    def _mode_label(self) -> str | None:
        """Return the HVAC mode/action as a display string, or None."""
        if not self.show_mode:
            return None
        text = self.hvac_action or self.hvac_mode
        if not text:
            return None
        return text.replace("_", " ").upper()

    def _humidity_chip(self, icon_size: int, font: str = "small") -> Component | None:
        """Build a humidity icon+value chip, or None if disabled/unset."""
        if not self.show_humidity or self.humidity is None:
            return None
        try:
            humidity_val = int(float(self.humidity))
        except (ValueError, TypeError):
            return None
        return Row(
            children=[
                Icon("water-percent", size=icon_size, color=THEME_INFO),
                Text(f"{humidity_val}%", font=font, color=THEME_INFO),
            ],
            gap=4,
            align="center",
        )

    def _target_chip(self, icon_size: int, font: str = "small") -> Component | None:
        """Build a target-temperature chip, or None if disabled/unset."""
        if not self.show_target or self.target_temp is None:
            return None
        target_str = _format_temp(self.target_temp)
        return Row(
            children=[
                Icon("target", size=icon_size, color=THEME_TEXT_SECONDARY),
                Text(target_str, font=font, color=THEME_TEXT_SECONDARY),
            ],
            gap=4,
            align="center",
        )

    def _build_full(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Hero layout for cells >=130x130: caps mode label + icon at top,
        bold huge temperature middle (auto-fit), target+humidity bottom.
        Three bands distributed via justify=space-between so the cell is
        completely filled.
        """
        padding = int(width * 0.04)
        icon_name, color = self._get_icon_and_color()
        icon_size = max(28, int(height * 0.20))
        current_str = _format_temp(self.current_temp, self.temp_unit)
        mode_label = self._mode_label()

        # ── Top band: caps mode label + tinted icon ──────────────────
        top_children: list[Component] = []
        if mode_label and self.show_mode:
            top_children.append(Text(mode_label, font="tiny", color=color, truncate=True))
        top_children.append(Icon(icon_name, size=icon_size, color=color))
        top_band = Column(
            children=top_children,
            gap=int(height * 0.02),
            align="center",
            justify="start",
        )

        # ── Middle: hero temperature (auto-fit to fill the band) ─────
        # Use font="huge" + auto_fit so the temp dominates the cell.
        hero = Row(
            children=[
                Text(
                    current_str,
                    font="huge",
                    bold=True,
                    color=THEME_TEXT_PRIMARY,
                    align="center",
                    auto_fit=True,
                )
            ],
            justify="center",
            align="center",
        )

        # ── Bottom band: target + humidity, side by side ─────────────
        bottom_chips: list[Component] = []
        target_chip = self._target_chip(max(12, int(height * 0.06)), font="small")
        humid_chip = self._humidity_chip(max(12, int(height * 0.06)), font="small")
        if target_chip:
            bottom_chips.append(target_chip)
        if humid_chip:
            bottom_chips.append(humid_chip)
        bottom_band: Component
        if bottom_chips:
            bottom_band = Row(
                children=bottom_chips,
                gap=int(width * 0.10),
                align="center",
                justify="center",
            )
        else:
            bottom_band = Row(children=[], align="center", justify="center")

        return Column(
            children=[top_band, hero, bottom_band],
            padding=padding,
            align="stretch",
            justify="space-evenly",
        )

    def _build_medium(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Layout for 2x2-ish cells (~100-140px in both axes).

        Three rows distributed top-to-bottom:
          1. caps mode label + tinted icon (compact row)
          2. bold hero temperature (auto-fit, dominates)
          3. target + humidity chips (single line)

        Uses justify=space-between so all three bands stretch to fill the
        cell — the previous justify=center left ~50% of the cell empty.
        """
        padding = int(width * 0.04)
        icon_name, color = self._get_icon_and_color()
        icon_size = max(16, min(24, int(height * 0.18)))
        current_str = _format_temp(self.current_temp, self.temp_unit)
        mode_label = self._mode_label()

        # Top: caps mode + small icon, centred horizontally.
        top_pieces: list[Component] = [Icon(icon_name, size=icon_size, color=color)]
        if mode_label and self.show_mode:
            top_pieces.append(Text(mode_label, font="tiny", color=color, truncate=True))
        top_band = Row(
            children=top_pieces,
            gap=6,
            align="center",
            justify="center",
        )

        # Middle: hero temp.
        hero = Row(
            children=[
                Text(
                    current_str,
                    font="xlarge",
                    bold=True,
                    color=THEME_TEXT_PRIMARY,
                    align="center",
                    auto_fit=True,
                )
            ],
            justify="center",
            align="center",
        )

        # Bottom: chips
        chip_size = max(10, int(height * 0.07))
        bottom_chips: list[Component] = []
        target_chip = self._target_chip(chip_size, font="tiny")
        humid_chip = self._humidity_chip(chip_size, font="tiny")
        if target_chip:
            bottom_chips.append(target_chip)
        if humid_chip:
            bottom_chips.append(humid_chip)
        bottom_band: Component
        if bottom_chips:
            bottom_band = Row(
                children=bottom_chips,
                gap=10,
                align="center",
                justify="center",
            )
        else:
            bottom_band = Row(children=[], align="center", justify="center")

        return Column(
            children=[top_band, hero, bottom_band],
            padding=padding,
            align="stretch",
            justify="space-evenly",
        )

    def _build_compact(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Tight 2-row layout for small grid cells (3x2, 3x3, MICRO/TINY).

        Top: icon + bold tinted temp on one row.
        Bottom: target + humidity on one row (drops if the cell is too
        short — has_room_for_details gate).
        Uses justify=space-between to spread the rows top/bottom even in
        small cells.
        """
        padding = max(2, int(width * 0.04))
        icon_name, color = self._get_icon_and_color()
        current_str = _format_temp(self.current_temp, self.temp_unit)

        has_room_for_details = height >= 65

        if has_room_for_details:
            icon_size = max(14, min(22, int(height * 0.25)))
            top_row = Row(
                children=[
                    Icon(icon_name, size=icon_size, color=color),
                    Text(current_str, font="medium", bold=True, color=THEME_TEXT_PRIMARY),
                ],
                gap=4,
                align="center",
                justify="center",
            )

            chip_size = 10
            detail_parts: list[Component] = []
            target_chip = self._target_chip(chip_size, font="tiny")
            humid_chip = self._humidity_chip(chip_size, font="tiny")
            if target_chip:
                detail_parts.append(target_chip)
            if humid_chip:
                detail_parts.append(humid_chip)

            children: list[Component] = [top_row]
            if detail_parts:
                children.append(
                    Row(
                        children=detail_parts,
                        gap=6,
                        align="center",
                        justify="center",
                    )
                )

            return Column(
                children=children,
                padding=padding,
                align="stretch",
                justify="space-evenly" if detail_parts else "center",
            )

        # Minimal layout for very short cells (under 65px height): one row.
        icon_size = max(14, min(24, int(height * 0.35)))
        return Row(
            children=[
                Icon(icon_name, size=icon_size, color=color),
                Text(current_str, font="small", bold=True, color=THEME_TEXT_PRIMARY),
            ],
            gap=padding,
            align="center",
            justify="center",
            padding=padding,
        )


def _climate_placeholder() -> Component:
    """Create placeholder component when no climate data."""
    return Column(
        children=[
            Icon("thermostat", color=THEME_TEXT_SECONDARY, max_size=48),
            Text("No Climate Data", font="small", color=THEME_TEXT_SECONDARY),
        ],
        gap=8,
        align="center",
        justify="center",
    )


class ClimateWidget(Widget):
    """Widget that displays climate/thermostat information."""

    WIDGET_TYPE: ClassVar[str] = "climate"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Climate",
        "needs_entity": True,
        "entity_domains": ["climate"],
        "options": [
            {"key": "show_target", "type": "boolean", "label": "Show Target Temp", "default": True},
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_mode", "type": "boolean", "label": "Show HVAC Mode", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the climate widget."""
        super().__init__(config)
        self.show_target = config.options.get("show_target", True)
        self.show_humidity = config.options.get("show_humidity", True)
        self.show_mode = config.options.get("show_mode", True)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the climate widget."""
        entity = state.entity

        if entity is None:
            return _climate_placeholder()

        return ClimateDisplay(
            current_temp=entity.get("current_temperature"),
            target_temp=entity.get("temperature"),
            hvac_mode=entity.state,
            hvac_action=entity.get("hvac_action"),
            humidity=entity.get("humidity"),
            name=self.config.label or entity.friendly_name,
            show_target=self.show_target,
            show_humidity=self.show_humidity,
            show_mode=self.show_mode,
            temp_unit=entity.get("temperature_unit") or "°C",
        )
