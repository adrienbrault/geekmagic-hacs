"""Climate widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import (
    COLOR_BLUE,
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_ORANGE,
)
from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
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

# HVAC action colors
HVAC_ACTION_COLORS = {
    "heating": COLOR_ORANGE,
    "cooling": COLOR_BLUE,
    "idle": COLOR_GRAY,
    "off": COLOR_GRAY,
    "drying": COLOR_CYAN,
    "fan": COLOR_CYAN,
    "preheating": COLOR_ORANGE,
}

# HVAC mode colors
HVAC_MODE_COLORS = {
    "heat": COLOR_ORANGE,
    "cool": COLOR_BLUE,
    "heat_cool": COLOR_CYAN,
    "auto": COLOR_CYAN,
    "dry": COLOR_CYAN,
    "fan_only": COLOR_CYAN,
    "off": COLOR_GRAY,
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
    """Climate display component."""

    current_temp: float | int | str | None = None
    target_temp: float | int | str | None = None
    hvac_mode: str = "off"
    hvac_action: str | None = None
    humidity: int | str | None = None
    name: str = ""
    show_target: bool = True
    show_humidity: bool = True
    show_mode: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render climate widget."""
        size = get_size_category(height)

        # Also consider width - narrow widgets need compact layouts even if tall
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
        """Get icon and color based on hvac_action or hvac_mode."""
        # Prefer action over mode if available
        if self.hvac_action and self.hvac_action != "idle":
            icon = HVAC_ACTION_ICONS.get(self.hvac_action, "thermostat")
            color = HVAC_ACTION_COLORS.get(self.hvac_action, COLOR_CYAN)
        else:
            icon = HVAC_MODE_ICONS.get(self.hvac_mode, "thermostat")
            color = HVAC_MODE_COLORS.get(self.hvac_mode, COLOR_CYAN)
        return icon, color

    def _build_full(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Build full climate layout with all details."""
        padding = int(width * 0.04)
        icon_name, color = self._get_icon_and_color()

        # Scale icon based on height - larger for fullscreen
        icon_size = max(32, int(height * 0.28))

        # Current temperature is the primary value
        current_str = _format_temp(self.current_temp)

        # Build main column with icon and current temp
        main_children: list[Component] = [
            Icon(icon_name, size=icon_size, color=color),
            Text(current_str, font="huge", color=THEME_TEXT_PRIMARY),
        ]

        # Add target temperature if enabled and available
        if self.show_target and self.target_temp is not None:
            target_str = _format_temp(self.target_temp)
            target_icon_size = max(14, int(height * 0.08))
            main_children.append(
                Row(
                    children=[
                        Icon("target", size=target_icon_size, color=THEME_TEXT_SECONDARY),
                        Text(target_str, font="regular", color=THEME_TEXT_SECONDARY),
                    ],
                    gap=6,
                    align="center",
                    justify="center",
                )
            )

        main_weather = Column(
            children=main_children,
            gap=int(height * 0.03),
            align="center",
            justify="center",
            padding=padding,
        )

        # Bottom info row with humidity and/or mode
        bottom_children: list[Component] = []

        if self.show_humidity and self.humidity is not None:
            try:
                humidity_val = int(float(self.humidity))
                humidity_icon_size = max(14, int(height * 0.08))
                bottom_children.append(
                    Row(
                        children=[
                            Icon("water-percent", size=humidity_icon_size, color=COLOR_CYAN),
                            Text(f"{humidity_val}%", font="small", color=COLOR_CYAN),
                        ],
                        gap=6,
                        align="center",
                    )
                )
            except (ValueError, TypeError):
                pass

        if self.show_mode:
            # Show hvac action if available, otherwise mode
            display_text = self.hvac_action or self.hvac_mode
            if display_text:
                bottom_children.append(
                    Text(
                        display_text.replace("_", " ").title(),
                        font="small",
                        color=color,
                    )
                )

        if bottom_children:
            bottom_row = Row(
                children=bottom_children,
                gap=int(width * 0.10),
                align="center",
                justify="center",
                padding=padding,
            )
            return Column(
                children=[main_weather, bottom_row],
                gap=int(height * 0.02),
                align="center",
                justify="space-between",
            )

        return main_weather

    def _build_medium(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Build medium climate layout."""
        padding = int(width * 0.04)
        icon_name, color = self._get_icon_and_color()

        # For narrow+tall layouts (1x2), use vertical stacking
        is_tall = height > width * 1.5

        if is_tall:
            # Vertical layout for narrow tall containers
            icon_size = max(24, int(height * 0.18))
            current_str = _format_temp(self.current_temp)

            main_children: list[Component] = [
                Icon(icon_name, size=icon_size, color=color),
                Text(current_str, font="xlarge", color=THEME_TEXT_PRIMARY),
            ]

            # Add target temperature
            if self.show_target and self.target_temp is not None:
                target_str = _format_temp(self.target_temp)
                main_children.append(
                    Row(
                        children=[
                            Icon("target", size=12, color=THEME_TEXT_SECONDARY),
                            Text(target_str, font="small", color=THEME_TEXT_SECONDARY),
                        ],
                        gap=4,
                        align="center",
                        justify="center",
                    )
                )

            # Add humidity
            if self.show_humidity and self.humidity is not None:
                try:
                    humidity_val = int(float(self.humidity))
                    main_children.append(
                        Row(
                            children=[
                                Icon("water-percent", size=12, color=COLOR_CYAN),
                                Text(f"{humidity_val}%", font="small", color=COLOR_CYAN),
                            ],
                            gap=4,
                            align="center",
                            justify="center",
                        )
                    )
                except (ValueError, TypeError):
                    pass

            # Add mode at bottom
            if self.show_mode:
                display_text = self.hvac_action or self.hvac_mode
                if display_text:
                    main_children.append(
                        Text(
                            display_text.replace("_", " ").title(),
                            font="small",
                            color=color,
                        )
                    )

            return Column(
                children=main_children,
                gap=int(height * 0.04),
                padding=padding,
                align="center",
                justify="center",
            )

        # Horizontal layout for wider containers (2x2, etc.)
        icon_size = max(20, int(height * 0.22))
        current_str = _format_temp(self.current_temp)

        top_row = Row(
            children=[
                Icon(icon_name, size=icon_size, color=color),
                Text(current_str, font="large", color=THEME_TEXT_PRIMARY),
            ],
            gap=int(width * 0.04),
            align="center",
            justify="center",
        )

        children: list[Component] = [top_row]

        # For small cells, use 2 rows: target+humidity, then mode
        # For larger cells, fit more on one row
        is_small = width < 115

        if is_small:
            # Row 1: target + humidity
            row1_parts: list[Component] = []
            if self.show_target and self.target_temp is not None:
                target_str = _format_temp(self.target_temp)
                row1_parts.append(
                    Row(
                        children=[
                            Icon("target", size=10, color=THEME_TEXT_SECONDARY),
                            Text(target_str, font="tiny", color=THEME_TEXT_SECONDARY),
                        ],
                        gap=2,
                        align="center",
                    )
                )
            if self.show_humidity and self.humidity is not None:
                try:
                    humidity_val = int(float(self.humidity))
                    row1_parts.append(
                        Row(
                            children=[
                                Icon("water-percent", size=10, color=COLOR_CYAN),
                                Text(f"{humidity_val}%", font="tiny", color=COLOR_CYAN),
                            ],
                            gap=2,
                            align="center",
                        )
                    )
                except (ValueError, TypeError):
                    pass
            if row1_parts:
                children.append(
                    Row(
                        children=row1_parts,
                        gap=8,
                        align="center",
                        justify="center",
                    )
                )

            # Row 2: mode
            if self.show_mode:
                display_text = self.hvac_action or self.hvac_mode
                if display_text:
                    children.append(
                        Text(
                            display_text.replace("_", " ").title(),
                            font="tiny",
                            color=color,
                        )
                    )
        else:
            # Single row with all info for larger cells
            bottom_parts: list[Component] = []
            if self.show_target and self.target_temp is not None:
                target_str = _format_temp(self.target_temp)
                bottom_parts.append(
                    Row(
                        children=[
                            Icon("target", size=10, color=THEME_TEXT_SECONDARY),
                            Text(target_str, font="tiny", color=THEME_TEXT_SECONDARY),
                        ],
                        gap=2,
                        align="center",
                    )
                )
            if self.show_humidity and self.humidity is not None:
                try:
                    humidity_val = int(float(self.humidity))
                    bottom_parts.append(
                        Row(
                            children=[
                                Icon("water-percent", size=10, color=COLOR_CYAN),
                                Text(f"{humidity_val}%", font="tiny", color=COLOR_CYAN),
                            ],
                            gap=2,
                            align="center",
                        )
                    )
                except (ValueError, TypeError):
                    pass
            if self.show_mode:
                display_text = self.hvac_action or self.hvac_mode
                if display_text:
                    bottom_parts.append(
                        Text(
                            display_text.replace("_", " ").title(),
                            font="tiny",
                            color=color,
                        )
                    )
            if bottom_parts:
                children.append(
                    Row(
                        children=bottom_parts,
                        gap=12,
                        align="center",
                        justify="center",
                    )
                )

        return Column(
            children=children,
            gap=int(height * 0.04),
            padding=padding,
            align="center",
            justify="center",
        )

    def _build_compact(self, ctx: RenderContext, width: int, height: int) -> Component:
        """Build compact climate layout for small spaces."""
        padding = int(width * 0.04)
        icon_name, color = self._get_icon_and_color()

        current_str = _format_temp(self.current_temp)

        # Check if we have enough height for 2 rows (2x3, 3x2, 3x3 layouts)
        has_room_for_details = height >= 65

        if has_room_for_details:
            # 2-row layout: icon+temp on top, details below
            icon_size = max(14, min(22, int(height * 0.25)))

            top_row = Row(
                children=[
                    Icon(icon_name, size=icon_size, color=color),
                    Text(current_str, font="medium", color=THEME_TEXT_PRIMARY),
                ],
                gap=4,
                align="center",
                justify="center",
            )

            # Build detail row with target and/or humidity
            detail_parts: list[Component] = []
            if self.show_target and self.target_temp is not None:
                target_str = _format_temp(self.target_temp)
                detail_parts.append(
                    Row(
                        children=[
                            Icon("target", size=8, color=THEME_TEXT_SECONDARY),
                            Text(target_str, font="tiny", color=THEME_TEXT_SECONDARY),
                        ],
                        gap=2,
                        align="center",
                    )
                )
            if self.show_humidity and self.humidity is not None:
                try:
                    humidity_val = int(float(self.humidity))
                    detail_parts.append(
                        Row(
                            children=[
                                Icon("water-percent", size=8, color=COLOR_CYAN),
                                Text(f"{humidity_val}%", font="tiny", color=COLOR_CYAN),
                            ],
                            gap=2,
                            align="center",
                        )
                    )
                except (ValueError, TypeError):
                    pass

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
                gap=2,
                padding=padding,
                align="center",
                justify="center",
            )

        # Minimal layout for very small spaces
        icon_size = max(14, min(24, int(height * 0.35)))
        return Row(
            children=[
                Icon(icon_name, size=icon_size, color=color),
                Text(current_str, font="small", color=THEME_TEXT_PRIMARY),
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
        )
