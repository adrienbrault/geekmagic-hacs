"""Climate widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .base import SIZE_ADJUST_OPTION, Widget, WidgetConfig
from .components import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SUCCESS,
    THEME_TEXT_SECONDARY,
    THEME_WARNING,
    Color,
    Column,
    Component,
    Icon,
    Text,
)
from .data_card import Chip, DataCard

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


# HVAC action / mode → MDI icon (the "fire" / "snowflake" / "thermostat"
# state visual for the hero band).
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

# HVAC action / mode → theme role color sentinel. Resolves to the active
# theme's warning / info / muted at draw time so the heating flame is
# orange in watchOS, amber in retro, coral in candy, etc. — no hardcoded
# RGB leaks through to widget code.
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
    if num == int(num):
        return f"{int(num)}{unit}"
    return f"{num:.1f}{unit}"


def _hvac_visual(hvac_action: str | None, hvac_mode: str) -> tuple[str, Color]:
    """Pick the HVAC icon + theme-role color for the current state.

    ``hvac_action`` is the live action ("heating", "cooling") and wins
    when present and not ``"idle"``. ``hvac_mode`` is the configured
    mode and is the fallback (used when the unit is reporting idle or
    didn't expose ``hvac_action``).
    """
    if hvac_action and hvac_action != "idle":
        return (
            HVAC_ACTION_ICONS.get(hvac_action, "thermostat"),
            HVAC_ACTION_ROLES.get(hvac_action, THEME_PRIMARY),
        )
    return (
        HVAC_MODE_ICONS.get(hvac_mode, "thermostat"),
        HVAC_MODE_ROLES.get(hvac_mode, THEME_PRIMARY),
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
    """Widget that displays climate/thermostat information via ``DataCard``.

    Maps to:
      caption  = HVAC mode/action ("HEATING" / "COOLING" / "OFF" ...)
      icon     = state-tinted HVAC icon (fire / snowflake / fan / ...)
      hero     = current temperature ("21.5°C")
      supporting = [target chip, humidity chip]
    """

    WIDGET_TYPE: ClassVar[str] = "climate"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Climate",
        "needs_entity": True,
        "entity_domains": ["climate"],
        "options": [
            {"key": "show_target", "type": "boolean", "label": "Show Target Temp", "default": True},
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_mode", "type": "boolean", "label": "Show HVAC Mode", "default": True},
            SIZE_ADJUST_OPTION,
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

        hvac_mode = entity.state
        hvac_action = entity.get("hvac_action")
        icon_name, icon_color = _hvac_visual(hvac_action, hvac_mode)

        # Caption: caps-tracked HVAC state. Falls back to widget label
        # when show_mode is False (preserves the entity name as a
        # caption rather than dropping the band entirely).
        caption: str | None = None
        if self.show_mode:
            mode_text = hvac_action or hvac_mode
            caption = mode_text.replace("_", " ").upper() if mode_text else None
        if caption is None:
            caption = self.label_for(entity)

        unit = entity.get("temperature_unit") or "°C"
        hero = _format_temp(entity.get("current_temperature"), unit)

        # Supporting chips: target temp + humidity.
        supporting: list[Chip] = []
        if self.show_target and entity.get("temperature") is not None:
            supporting.append(Chip(_format_temp(entity.get("temperature")), icon="target"))
        if self.show_humidity and entity.get("humidity") is not None:
            try:
                humidity_val = int(float(entity.get("humidity")))
            except (ValueError, TypeError):
                pass
            else:
                supporting.append(Chip(f"{humidity_val}%", icon="water-percent", color=THEME_INFO))

        return DataCard(
            caption=caption,
            icon=icon_name,
            icon_color=icon_color,
            icon_role="feature",
            hero=hero,
            supporting=supporting,
        )
