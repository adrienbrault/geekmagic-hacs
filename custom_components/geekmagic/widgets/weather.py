"""Weather widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SECONDARY,
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


WEATHER_ICONS = {
    "sunny": "weather-sunny",
    "clear-night": "weather-night",
    "partlycloudy": "weather-partly-cloudy",
    "cloudy": "weather-cloudy",
    "rainy": "weather-rainy",
    "pouring": "weather-pouring",
    "snowy": "weather-snowy",
    "snowy-rainy": "weather-snowy-rainy",
    "fog": "weather-fog",
    "hail": "weather-hail",
    "windy": "weather-windy",
    "windy-variant": "weather-windy-variant",
    "lightning": "weather-lightning",
    "lightning-rainy": "weather-lightning-rainy",
    "exceptional": "alert-circle",
}

# Condition → theme role-color sentinel mapping. Each weather condition
# resolves to a role on the active theme so candy/retro/neon/etc. show
# tints from their own palette, not hardcoded watchOS-system colors.
#
# Mapping rationale:
#   sunny / hot      → warning  (orange-ish on most themes)
#   clear-night      → secondary
#   cloudy / partly  → primary  (uses the theme's brand accent)
#   rain / snow / hail → info   (cool/water/data role — themes that
#                                 lack blue map this to mint/cyan/etc.)
#   wind             → success
#   lightning        → secondary
#   exceptional      → error
#   fog              → muted
WEATHER_ROLES: dict[str, Color] = {
    "sunny": THEME_WARNING,
    "clear-night": THEME_SECONDARY,
    "partlycloudy": THEME_PRIMARY,
    "cloudy": THEME_PRIMARY,
    "rainy": THEME_INFO,
    "pouring": THEME_INFO,
    "snowy": THEME_INFO,
    "snowy-rainy": THEME_INFO,
    "fog": THEME_MUTED,
    "hail": THEME_INFO,
    "windy": THEME_SUCCESS,
    "windy-variant": THEME_SUCCESS,
    "lightning": THEME_SECONDARY,
    "lightning-rainy": THEME_SECONDARY,
    "exceptional": THEME_ERROR,
}


# Weekday abbreviations
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _parse_forecast_day_name(datetime_str: str, fallback: str) -> str:
    """Parse datetime string and return weekday abbreviation.

    Args:
        datetime_str: ISO format datetime string (e.g., "2025-12-29T00:00:00+00:00")
        fallback: Fallback string if parsing fails

    Returns:
        Weekday abbreviation (Mon, Tue, etc.) or fallback
    """
    if not datetime_str:
        return fallback

    try:
        # Try parsing ISO format (with or without timezone)
        # Remove timezone suffix for simpler parsing
        dt_str = datetime_str.split("+", 1)[0].split("Z", 1)[0]
        dt = datetime.fromisoformat(dt_str)
        return WEEKDAY_NAMES[dt.weekday()]
    except (ValueError, IndexError):
        # If parsing fails, try to use first 3 chars as fallback
        # (might be already a day name like "Mon")
        if len(datetime_str) >= 3 and datetime_str[:3].isalpha():
            return datetime_str[:3]
        return fallback


@dataclass
class WeatherDisplay(Component):
    """Weather display component."""

    temperature: Any = "--"
    humidity: Any = "--"
    condition: str = "sunny"
    forecast: list[dict] = field(default_factory=list)
    show_forecast: bool = True
    show_humidity: bool = True
    show_high_low: bool = True
    forecast_days: int = 3
    forecast_start_tomorrow: bool = False

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def _visible_forecast(self) -> list[dict]:
        """Return the forecast list to display.

        Daily forecasts include today as the first entry. When
        ``forecast_start_tomorrow`` is set we drop it so the row begins
        at tomorrow instead.
        """
        if self.forecast_start_tomorrow:
            return self.forecast[1:]
        return self.forecast

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render weather."""
        icon_name = WEATHER_ICONS.get(self.condition, "weather-sunny")
        icon_tint = WEATHER_ROLES.get(self.condition, THEME_WARNING)

        size = get_size_category(height)

        if size in (SizeCategory.MEDIUM, SizeCategory.LARGE) and self.show_forecast:
            component = self._build_full(width, height, icon_name, icon_tint)
        elif size == SizeCategory.SMALL and self.show_forecast and self._visible_forecast():
            component = self._build_semi_compact(width, height, icon_name, icon_tint)
        else:
            component = self._build_compact(width, height, icon_name, icon_tint)

        component.render(ctx, x, y, width, height)

    def _build_full(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Build full weather layout with forecast (hero + meta strip + forecast row)."""
        padding = int(width * 0.04)
        icon_size = max(24, int(height * 0.25))

        # Hero block: icon → big temp → condition+humidity strip.
        temp_str = f"{self.temperature}°" if self.temperature != "--" else "--"

        # Build the condition+humidity meta-strip. When humidity is
        # available we put it on the same line as the condition (e.g.
        # "Sunny   💧 45%") — both are caption-tier metadata about the
        # temp. Centred horizontally so the strip mirrors the centred
        # temp above it instead of left-anchored against the cell edge.
        meta_children: list[Component] = [
            Text(
                self.condition.replace("-", " ").title(),
                font="small",
                color=THEME_TEXT_SECONDARY,
            ),
        ]
        if self.show_humidity:
            humidity_icon_size = max(10, int(height * 0.05))
            meta_children.extend(
                [
                    Icon("water-percent", size=humidity_icon_size, color=THEME_INFO),
                    Text(f"{self.humidity}%", font="tiny", color=THEME_INFO),
                ]
            )
        meta_strip = Row(
            children=meta_children,
            gap=8,
            align="center",
            justify="center",
            padding=padding,
        )

        main_weather = Column(
            children=[
                Icon(icon_name, size=icon_size, color=icon_tint),
                Text(temp_str, font="xlarge", bold=True, color=THEME_TEXT_PRIMARY),
                meta_strip,
            ],
            gap=int(height * 0.02),
            align="center",
            justify="start",
            padding=padding,
        )

        # Forecast items
        forecast_component = None
        if self.forecast and self.show_forecast:
            forecast_items = self._visible_forecast()[: self.forecast_days]
            if forecast_items:
                forecast_icon_size = max(10, int(height * 0.10))
                forecast_columns = []

                for i, day in enumerate(forecast_items):
                    day_condition = day.get("condition", "sunny")
                    day_temp = day.get("temperature", "--")
                    day_temp_low = day.get("templow")
                    day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{i + 1}")
                    day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")

                    if self.show_high_low and day_temp_low is not None:
                        temp_str = f"{day_temp}°/{day_temp_low}°"
                    else:
                        temp_str = f"{day_temp}°"

                    day_tint = WEATHER_ROLES.get(day_condition, THEME_WARNING)
                    forecast_columns.append(
                        Column(
                            children=[
                                Text(day_name.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                                Icon(day_icon, size=forecast_icon_size, color=day_tint),
                                Text(temp_str, font="tiny", bold=True, color=THEME_TEXT_PRIMARY),
                            ],
                            gap=int(height * 0.02),
                            align="center",
                            justify="center",
                        )
                    )

                forecast_component = Row(
                    children=forecast_columns,
                    gap=0,
                    align="center",
                    justify="space-around",
                    padding=padding,
                )

        # Final layout: hero (icon + temp + condition/humidity strip)
        # above the forecast row, both centred as a group rather than
        # pinned to opposite cell edges. ``space-evenly`` puts equal
        # gap before / between / after the bands so the current-day
        # group sits near the forecast group instead of being pushed
        # apart by a Spacer.
        if forecast_component:
            return Column(
                children=[main_weather, forecast_component],
                gap=int(height * 0.04),
                align="stretch",
                justify="space-evenly",
            )
        # No forecast — just the centred hero block.
        return main_weather

    def _build_semi_compact(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Build semi-compact layout: icon + temp on top, mini forecast
        on the bottom.

        In wide cells (>= 200 px), the top row also includes the
        condition text + humidity, and the forecast strip shows day
        labels + temperatures. In narrow cells (e.g. 80x120 grid
        squares), only the temp is shown on top and the forecast is
        icon-only — otherwise the text crashes into itself.
        """
        padding = int(width * 0.04)
        icon_size = max(16, min(28, int(height * 0.28)))
        mini_icon_size = max(10, int(height * 0.18))
        temp_str = f"{self.temperature}°" if self.temperature != "--" else "--"
        is_wide = width >= 200

        # Top row: always icon + temp; only add condition + humidity in
        # wide cells.
        top_children: list[Component] = [
            Icon(icon_name, size=icon_size, color=icon_tint),
            Text(temp_str, font="large", bold=True, color=THEME_TEXT_PRIMARY),
        ]
        if is_wide:
            top_children.append(
                Text(
                    self.condition.replace("-", " ").title(),
                    font="tiny",
                    color=THEME_TEXT_SECONDARY,
                )
            )
            if self.show_humidity and self.humidity != "--":
                top_children.append(
                    Text(f"{self.humidity}%", font="tiny", color=THEME_INFO),
                )
        top_row = Row(
            children=top_children,
            gap=6,
            align="center",
            justify="center",
        )

        # Bottom row: forecast columns. Wide cells get day labels + temps;
        # narrow cells get icons only (forecast columns become Icons,
        # space-around).
        bottom_row: Component | None = None
        forecast_items = self._visible_forecast()[: min(3, self.forecast_days)]
        if forecast_items:
            if is_wide:
                forecast_columns: list[Component] = []
                for i, day in enumerate(forecast_items):
                    day_condition = day.get("condition", "sunny")
                    day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
                    day_tint = WEATHER_ROLES.get(day_condition, THEME_WARNING)
                    day_temp = day.get("temperature", "--")
                    day_temp_low = day.get("templow")
                    day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{i + 1}")
                    if self.show_high_low and day_temp_low is not None:
                        day_temp_str = f"{day_temp}°/{day_temp_low}°"
                    else:
                        day_temp_str = f"{day_temp}°"
                    forecast_columns.append(
                        Column(
                            children=[
                                Text(
                                    day_name.upper(),
                                    font="tiny",
                                    color=THEME_TEXT_SECONDARY,
                                ),
                                Icon(day_icon, size=mini_icon_size, color=day_tint),
                                Text(
                                    day_temp_str,
                                    font="tiny",
                                    bold=True,
                                    color=THEME_TEXT_PRIMARY,
                                ),
                            ],
                            gap=2,
                            align="center",
                            justify="center",
                        )
                    )
                bottom_row = Row(
                    children=forecast_columns,
                    gap=0,
                    align="center",
                    justify="space-around",
                )
            else:
                forecast_icons: list[Component] = []
                for day in forecast_items:
                    day_condition = day.get("condition", "sunny")
                    day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
                    day_tint = WEATHER_ROLES.get(day_condition, THEME_WARNING)
                    forecast_icons.append(Icon(day_icon, size=mini_icon_size, color=day_tint))
                bottom_row = Row(
                    children=forecast_icons,
                    gap=int(width * 0.06),
                    align="center",
                    justify="center",
                )

        children: list[Component] = [top_row]
        if bottom_row:
            children.append(bottom_row)

        return Column(
            children=children,
            gap=int(height * 0.04),
            padding=padding,
            align="stretch",
            justify="space-evenly",
        )

    def _build_compact(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Build compact weather layout."""
        padding = int(width * 0.04)
        icon_size = max(16, min(32, int(height * 0.40)))
        temp_str = f"{self.temperature}°" if self.temperature != "--" else "--"

        # Left side: icon (tinted by condition)
        left_side = Icon(icon_name, size=icon_size, color=icon_tint)

        # Right side: temperature and optionally humidity
        right_children: list[Component] = [
            Text(temp_str, font="large", bold=True, color=THEME_TEXT_PRIMARY, align="end")
        ]

        if self.show_humidity:
            right_children.append(
                Text(f"{self.humidity}%", font="tiny", color=THEME_INFO, align="end")
            )

        right_side = Column(
            children=right_children,
            gap=int(height * 0.08),
            align="end",
            justify="center",
        )

        return Row(
            children=[left_side, right_side],
            gap=padding,
            align="center",
            justify="space-evenly",
            padding=padding,
        )


def _weather_placeholder() -> Component:
    """Create placeholder component when no weather data."""
    return Column(
        children=[
            Icon("weather-cloudy", color=THEME_TEXT_SECONDARY, max_size=48),
            Text("No Weather Data", font="small", color=THEME_TEXT_SECONDARY),
        ],
        gap=8,
        align="center",
        justify="center",
    )


class WeatherWidget(Widget):
    """Widget that displays weather information."""

    WIDGET_TYPE: ClassVar[str] = "weather"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Weather",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [
            {"key": "show_forecast", "type": "boolean", "label": "Show Forecast", "default": True},
            {
                "key": "forecast_days",
                "type": "number",
                "label": "Forecast Days",
                "default": 3,
                "min": 1,
                "max": 5,
            },
            {
                "key": "forecast_start_tomorrow",
                "type": "boolean",
                "label": "Forecast Starts Tomorrow",
                "default": False,
            },
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_high_low", "type": "boolean", "label": "Show High/Low", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the weather widget."""
        super().__init__(config)
        self.show_forecast = config.options.get("show_forecast", True)
        self.forecast_days = config.options.get("forecast_days", 3)
        self.forecast_start_tomorrow = config.options.get("forecast_start_tomorrow", False)
        self.show_humidity = config.options.get("show_humidity", True)
        self.show_high_low = config.options.get("show_high_low", True)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the weather widget."""
        entity = state.entity

        if entity is None:
            return _weather_placeholder()

        return WeatherDisplay(
            temperature=entity.get("temperature", "--"),
            humidity=entity.get("humidity", "--"),
            condition=entity.state,
            forecast=state.forecast,  # Use pre-fetched forecast from coordinator
            show_forecast=self.show_forecast,
            show_humidity=self.show_humidity,
            show_high_low=self.show_high_low,
            forecast_days=self.forecast_days,
            forecast_start_tomorrow=self.forecast_start_tomorrow,
        )
