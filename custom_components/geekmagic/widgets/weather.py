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
    THEME_TEXT_TERTIARY,
    THEME_WARNING,
    Color,
    Column,
    Component,
    Flex,
    Icon,
    Row,
    Spacer,
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


def _temp_str(value: Any) -> str:
    """Format a temperature value as ``"22°"`` (or ``"--"`` when missing)."""
    if value is None or value == "--":
        return "--"
    return f"{value}°"


@dataclass
class WeatherDisplay(Component):
    """Adaptive weather display.

    Picks one of five layouts from the cell's ``(width, height)`` so space
    is used well at every size:

    - **vertical** — tall & narrow cells (sidebars, split panels): current
      conditions on top, the forecast as a stacked list of ``DAY · icon ·
      hi/lo`` rows so nothing overflows the narrow width.
    - **strip** — wide & short cells: current conditions on the left, a
      compact forecast column-row filling the otherwise-empty right side.
    - **full** — roomy square-ish cells: a big auto-scaling hero
      temperature beside the condition icon, a condition/hi-lo/humidity
      meta strip, and a forecast row along the bottom.
    - **semi_compact** — medium cells: icon + temp on top, mini forecast
      below.
    - **compact** — micro/tiny grid cells: icon + temp (+ humidity).
    """

    temperature: Any = "--"
    humidity: Any = "--"
    condition: str = "sunny"
    forecast: list[dict] = field(default_factory=list)
    show_forecast: bool = True
    show_humidity: bool = True
    show_high_low: bool = True
    forecast_days: int = 3
    forecast_start_tomorrow: bool = False

    @property
    def _want_forecast(self) -> bool:
        """True when the user enabled the forecast AND there's data to show."""
        return self.show_forecast and bool(self._visible_forecast())

    @staticmethod
    def select_layout(width: int, height: int) -> str:
        """Pick the layout name for a cell shape.

        Aspect-aware: the old code keyed only on ``height``, which sent
        tall+narrow cells (sidebars/splits) into the wide ``full`` layout
        and overflowed the forecast off the edge. Returns one of
        ``"vertical"``, ``"strip"``, ``"full"``, ``"semi_compact"``,
        ``"compact"``. Pure/static so it can be unit-tested directly.
        """
        size = get_size_category(height)
        is_tall = height >= 150 and width < height * 0.85
        is_wide_short = width >= 200 and width >= height * 2.3

        if is_tall:
            # Vertical handles narrow cells with or without a forecast; the
            # full layout's meta strip overflows a ~110 px width.
            return "vertical"
        if is_wide_short:
            return "strip"
        if size in (SizeCategory.MEDIUM, SizeCategory.LARGE):
            # Roomy cells always get the hero layout; the forecast row is
            # added only when there's data, but even without it the big
            # hero + meta strip fill the cell far better than compact.
            return "full"
        if size == SizeCategory.SMALL:
            return "semi_compact"
        return "compact"

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
        """Render weather, picking the layout from the cell shape."""
        icon_name = WEATHER_ICONS.get(self.condition, "weather-sunny")
        icon_tint = WEATHER_ROLES.get(self.condition, THEME_WARNING)

        builders = {
            "vertical": self._build_vertical,
            "strip": self._build_strip,
            "full": self._build_full,
            "semi_compact": self._build_semi_compact,
            "compact": self._build_compact,
        }
        component = builders[self.select_layout(width, height)](width, height, icon_name, icon_tint)
        component.render(ctx, x, y, width, height)

    # ------------------------------------------------------------------
    # Shared building blocks
    # ------------------------------------------------------------------

    def _today_high_low(self) -> tuple[Any, Any]:
        """Return ``(high, low)`` from the first forecast day, if available."""
        if not self.forecast:
            return (None, None)
        day = self.forecast[0]
        return (day.get("temperature"), day.get("templow"))

    def _high_low_chips(self, icon_size: int, font: str = "tiny") -> list[Component]:
        """Build ``↑high ↓low`` chips for the current-conditions meta strip.

        Returns an empty list when there's no forecast or the user turned
        the high/low option off — callers ``extend`` with it so the strip
        collapses cleanly.
        """
        if not self.show_high_low:
            return []
        high, low = self._today_high_low()
        chips: list[Component] = []
        if high is not None:
            chips.append(Icon("arrow-up-thin", size=icon_size, color=THEME_WARNING))
            chips.append(Text(f"{high}°", font=font, color=THEME_TEXT_SECONDARY))
        if low is not None:
            chips.append(Icon("arrow-down-thin", size=icon_size, color=THEME_INFO))
            chips.append(Text(f"{low}°", font=font, color=THEME_TEXT_SECONDARY))
        return chips

    def _condition_label(self) -> str:
        return self.condition.replace("-", " ").title()

    def _forecast_column(
        self, day: dict, index: int, icon_size: int, high_only: bool = False
    ) -> Component:
        """One vertical forecast cell: ``DAY`` / icon / ``hi°/lo°`` (or ``hi°``).

        ``high_only`` forces a single temperature — used by the wide-short
        strip where each column shares a tight slice of the cell width and
        ``"26°/14°"`` would collide with its neighbours.
        """
        day_condition = day.get("condition", "sunny")
        day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
        day_tint = WEATHER_ROLES.get(day_condition, THEME_WARNING)
        day_temp = day.get("temperature", "--")
        day_low = day.get("templow")
        day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}")

        if self.show_high_low and not high_only and day_low is not None:
            temp_text = f"{day_temp}°/{day_low}°"
        else:
            temp_text = _temp_str(day_temp)

        return Column(
            children=[
                Text(day_name.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                Icon(day_icon, size=icon_size, color=day_tint),
                Text(temp_text, font="tiny", bold=True, color=THEME_TEXT_PRIMARY, auto_fit=True),
            ],
            gap=2,
            align="center",
            justify="center",
        )

    def _forecast_row(
        self,
        width: int,
        height: int,
        icon_size: int,
        max_days: int | None = None,
        high_only: bool = False,
    ) -> Component | None:
        """Horizontal strip of forecast columns, or ``None`` when not shown."""
        if not self._want_forecast:
            return None
        days = self.forecast_days if max_days is None else min(self.forecast_days, max_days)
        items = self._visible_forecast()[:days]
        if not items:
            return None
        columns = [
            self._forecast_column(day, i, icon_size, high_only=high_only)
            for i, day in enumerate(items)
        ]
        return Row(children=columns, gap=0, align="center", justify="space-around")

    def _forecast_list_row(self, day: dict, index: int, icon_size: int) -> Component:
        """One horizontal forecast row for the vertical layout:
        ``DAY  [icon]`` on the left, ``hi°  lo°`` pinned right.
        """
        day_condition = day.get("condition", "sunny")
        day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
        day_tint = WEATHER_ROLES.get(day_condition, THEME_WARNING)
        day_temp = day.get("temperature", "--")
        day_low = day.get("templow")
        day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}")

        right: list[Component] = [
            Text(_temp_str(day_temp), font="tiny", bold=True, color=THEME_TEXT_PRIMARY)
        ]
        if self.show_high_low and day_low is not None:
            right.append(Text(_temp_str(day_low), font="tiny", color=THEME_TEXT_TERTIARY))

        return Row(
            children=[
                Text(day_name.upper(), font="tiny", color=THEME_TEXT_SECONDARY, align="start"),
                Icon(day_icon, size=icon_size, color=day_tint),
                Spacer(),
                Row(children=right, gap=4, align="center", justify="end"),
            ],
            gap=6,
            align="center",
            justify="start",
        )

    # ------------------------------------------------------------------
    # Layout builders
    # ------------------------------------------------------------------

    def _build_full(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Roomy square-ish cells: hero temp + meta strip + forecast row.

        The hero temperature auto-scales (``primary`` font) so it fills the
        cell instead of being pinned to a fixed ``xlarge``. In landscape
        cells the icon sits beside the temp (using the width); in portrait
        cells it stacks above (the classic weather look).
        """
        padding = max(4, int(min(width, height) * 0.05))
        side_by_side = width >= height * 1.2
        icon_size = max(28, int(min(width, height) * (0.30 if side_by_side else 0.26)))

        temp_text = Text(
            _temp_str(self.temperature),
            font="primary",
            bold=True,
            color=THEME_TEXT_PRIMARY,
            auto_fit=True,
        )
        icon = Icon(icon_name, size=icon_size, color=icon_tint)
        if side_by_side:
            hero: Component = Row(
                children=[icon, temp_text],
                gap=int(width * 0.03),
                align="center",
                justify="center",
            )
        else:
            hero = Column(children=[icon, temp_text], gap=2, align="center", justify="center")

        # Meta strip: condition + today's hi/lo + humidity. All caption-tier
        # metadata about the hero, centred to mirror it.
        chip_icon = max(10, int(height * 0.06))
        meta_children: list[Component] = [
            Text(self._condition_label(), font="small", color=THEME_TEXT_SECONDARY)
        ]
        meta_children.extend(self._high_low_chips(chip_icon))
        if self.show_humidity and self.humidity != "--":
            meta_children.append(Icon("water-percent", size=chip_icon, color=THEME_INFO))
            meta_children.append(Text(f"{self.humidity}%", font="tiny", color=THEME_INFO))
        meta_strip = Row(children=meta_children, gap=6, align="center", justify="center")

        bands: list[Component] = [hero, meta_strip]
        forecast_row = self._forecast_row(width, height, max(14, int(height * 0.11)))
        if forecast_row is not None:
            bands.append(forecast_row)

        return Column(
            children=bands,
            gap=int(height * 0.03),
            padding=padding,
            align="stretch",
            justify="space-evenly",
        )

    def _build_vertical(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Tall & narrow cells: current conditions stacked over a forecast list.

        The forecast is laid out as one row per day (``DAY [icon]  hi° lo°``)
        which fits a ~110 px width cleanly — the horizontal column layout
        used elsewhere overflows here.
        """
        padding = max(4, int(width * 0.06))
        icon_size = max(28, int(width * 0.34))

        current = Column(
            children=[
                Icon(icon_name, size=icon_size, color=icon_tint),
                Text(
                    _temp_str(self.temperature),
                    font="primary",
                    bold=True,
                    color=THEME_TEXT_PRIMARY,
                    auto_fit=True,
                ),
                Text(
                    self._condition_label(),
                    font="tiny",
                    color=THEME_TEXT_SECONDARY,
                    truncate=True,
                ),
            ],
            gap=2,
            align="center",
            justify="center",
        )

        bands: list[Component] = [current]

        if self.show_humidity and self.humidity != "--":
            bands.append(
                Row(
                    children=[
                        Icon("water-percent", size=max(11, int(width * 0.10)), color=THEME_INFO),
                        Text(f"{self.humidity}%", font="tiny", color=THEME_INFO),
                    ],
                    gap=4,
                    align="center",
                    justify="center",
                )
            )

        if self._want_forecast:
            items = self._visible_forecast()[: self.forecast_days]
            list_icon = max(12, int(width * 0.14))
            forecast_rows = [
                self._forecast_list_row(day, i, list_icon) for i, day in enumerate(items)
            ]
            # The forecast list grows to absorb the remaining height so the
            # rows spread down the cell rather than clustering under the hero.
            bands.append(
                Flex(
                    Column(
                        children=forecast_rows,
                        gap=int(height * 0.01),
                        align="stretch",
                        justify="space-evenly",
                    )
                )
            )

        return Column(
            children=bands,
            gap=int(height * 0.02),
            padding=padding,
            align="stretch",
            justify="space-evenly",
        )

    def _build_strip(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Wide & short cells: current conditions left, forecast columns right.

        Fills the horizontal space that the old compact layout left empty
        on either side of a centred icon+temp.
        """
        padding = max(4, int(height * 0.08))
        icon_size = max(20, min(40, int(height * 0.50)))

        current = Row(
            children=[
                Icon(icon_name, size=icon_size, color=icon_tint),
                Column(
                    children=[
                        Text(
                            _temp_str(self.temperature),
                            font="large",
                            bold=True,
                            color=THEME_TEXT_PRIMARY,
                            align="start",
                            auto_fit=True,
                        ),
                        Text(
                            self._condition_label(),
                            font="tiny",
                            color=THEME_TEXT_SECONDARY,
                            align="start",
                            truncate=True,
                        ),
                    ],
                    gap=2,
                    align="start",
                    justify="center",
                ),
            ],
            gap=6,
            align="center",
            justify="start",
        )

        # Forecast shares the cell width with the current block, so cap it
        # to 3 days and a single temperature — five hi/lo columns collide
        # in the ~half-width slice that's left.
        forecast_row = self._forecast_row(
            width, height, max(14, int(height * 0.30)), max_days=3, high_only=True
        )
        if forecast_row is None:
            return Row(
                children=[current],
                padding=padding,
                align="center",
                justify="center",
            )
        return Row(
            children=[current, Spacer(), forecast_row],
            gap=int(width * 0.04),
            padding=padding,
            align="center",
            justify="space-between",
        )

    def _build_semi_compact(
        self,
        width: int,
        height: int,
        icon_name: str,
        icon_tint: Color,
    ) -> Component:
        """Medium cells: icon + temp on top, mini forecast on the bottom.

        Wide cells (>= 200 px) also show condition + humidity on the top
        row and day labels + temps in the forecast. Narrow grid squares
        keep the top row to icon + temp and the forecast to icons only so
        text never collides.
        """
        padding = max(4, int(width * 0.04))
        icon_size = max(16, min(28, int(height * 0.28)))
        mini_icon_size = max(10, int(height * 0.18))
        is_wide = width >= 200

        top_children: list[Component] = [
            Icon(icon_name, size=icon_size, color=icon_tint),
            Text(
                _temp_str(self.temperature),
                font="large",
                bold=True,
                color=THEME_TEXT_PRIMARY,
                auto_fit=True,
            ),
        ]
        if is_wide:
            top_children.append(
                Text(self._condition_label(), font="tiny", color=THEME_TEXT_SECONDARY)
            )
            if self.show_humidity and self.humidity != "--":
                top_children.append(Text(f"{self.humidity}%", font="tiny", color=THEME_INFO))
        top_row = Row(children=top_children, gap=6, align="center", justify="center")

        bottom_row: Component | None = None
        forecast_items = (
            self._visible_forecast()[: min(3, self.forecast_days)] if self._want_forecast else []
        )
        if forecast_items:
            if is_wide:
                bottom_row = Row(
                    children=[
                        self._forecast_column(day, i, mini_icon_size)
                        for i, day in enumerate(forecast_items)
                    ],
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
        """Compact weather layout."""
        padding = int(width * 0.04)
        icon_size = max(16, min(32, int(height * 0.40)))

        # Left side: icon (tinted by condition)
        left_side = Icon(icon_name, size=icon_size, color=icon_tint)

        # Right side: temperature and optionally humidity
        right_children: list[Component] = [
            Text(
                _temp_str(self.temperature),
                font="large",
                bold=True,
                color=THEME_TEXT_PRIMARY,
                align="end",
                auto_fit=True,
            )
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
