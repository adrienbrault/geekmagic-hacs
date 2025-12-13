"""Weather widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..const import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_GRAY,
    COLOR_WHITE,
)
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


# Map weather conditions to icons
WEATHER_ICONS = {
    "sunny": "sun",
    "clear-night": "moon",
    "partlycloudy": "cloud",
    "cloudy": "cloud",
    "rainy": "rain",
    "pouring": "rain",
    "snowy": "cloud",
    "fog": "cloud",
    "windy": "wind",
    "lightning": "bolt",
    "lightning-rainy": "bolt",
}


class WeatherWidget(Widget):
    """Widget that displays weather information."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the weather widget."""
        super().__init__(config)
        self.show_forecast = config.options.get("show_forecast", True)
        self.forecast_days = config.options.get("forecast_days", 3)
        self.show_humidity = config.options.get("show_humidity", True)
        self.show_wind = config.options.get("show_wind", False)

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the weather widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        center_x = ctx.width // 2

        # Get scaled fonts
        font_regular = ctx.get_font("regular")

        # Calculate relative padding
        padding = int(ctx.width * 0.04)

        # Get entity state
        state = self.get_entity_state(hass)

        if state is None:
            # Show placeholder
            ctx.draw_text(
                "No Weather Data",
                (center_x, ctx.height // 2),
                font=font_regular,
                color=COLOR_GRAY,
                anchor="mm",
            )
            return

        attrs = state.attributes
        condition = state.state
        temperature = attrs.get("temperature", "--")
        humidity = attrs.get("humidity", "--")
        forecast = attrs.get("forecast", [])

        # Get weather icon
        icon_name = WEATHER_ICONS.get(condition, "sun")

        # Layout depends on available space (use relative threshold)
        if ctx.height > 120 and self.show_forecast:
            self._render_full(ctx, icon_name, temperature, humidity, condition, forecast, padding)
        else:
            self._render_compact(ctx, icon_name, temperature, humidity, padding)

    def _render_full(
        self,
        ctx: RenderContext,
        icon_name: str,
        temperature: Any,
        humidity: Any,
        condition: str,
        forecast: list[dict],
        padding: int,
    ) -> None:
        """Render full weather with forecast."""
        center_x = ctx.width // 2

        # Get scaled fonts
        font_temp = ctx.get_font("xlarge")
        font_condition = ctx.get_font("small")
        font_tiny = ctx.get_font("tiny")

        # Current weather section
        current_y = padding

        # Weather icon (scaled to container)
        icon_size = max(24, int(ctx.height * 0.25))
        ctx.draw_icon(
            icon_name,
            (center_x - icon_size // 2, current_y),
            size=icon_size,
            color=COLOR_GOLD,
        )

        # Temperature
        temp_str = f"{temperature}°" if temperature != "--" else "--"
        ctx.draw_text(
            temp_str,
            (center_x, current_y + icon_size + int(ctx.height * 0.08)),
            font=font_temp,
            color=COLOR_WHITE,
            anchor="mm",
        )

        # Condition text
        ctx.draw_text(
            condition.replace("-", " ").title(),
            (center_x, current_y + icon_size + int(ctx.height * 0.22)),
            font=font_condition,
            color=COLOR_GRAY,
            anchor="mm",
        )

        # Humidity
        if self.show_humidity:
            humidity_icon_size = max(8, int(ctx.height * 0.07))
            humidity_y = current_y + icon_size + int(ctx.height * 0.30)
            ctx.draw_icon(
                "drop",
                (padding, humidity_y),
                size=humidity_icon_size,
                color=COLOR_CYAN,
            )
            ctx.draw_text(
                f"{humidity}%",
                (padding + humidity_icon_size + 4, humidity_y + humidity_icon_size // 2),
                font=font_tiny,
                color=COLOR_CYAN,
                anchor="lm",
            )

        # Forecast section
        if forecast and self.show_forecast:
            forecast_y = ctx.height - int(ctx.height * 0.28)
            forecast_items = forecast[: self.forecast_days]
            if forecast_items:
                item_width = (ctx.width - padding * 2) // len(forecast_items)
                forecast_icon_size = max(10, int(ctx.height * 0.10))

                for i, day in enumerate(forecast_items):
                    fx = padding + i * item_width + item_width // 2
                    day_condition = day.get("condition", "sunny")
                    day_temp = day.get("temperature", "--")
                    day_name = day.get("datetime", "")[:3] if day.get("datetime") else f"D{i + 1}"

                    # Day name
                    ctx.draw_text(
                        day_name.upper(),
                        (fx, forecast_y),
                        font=font_tiny,
                        color=COLOR_GRAY,
                        anchor="mm",
                    )

                    # Small icon
                    day_icon = WEATHER_ICONS.get(day_condition, "sun")
                    ctx.draw_icon(
                        day_icon,
                        (fx - forecast_icon_size // 2, forecast_y + int(ctx.height * 0.05)),
                        size=forecast_icon_size,
                        color=COLOR_GRAY,
                    )

                    # Temperature
                    ctx.draw_text(
                        f"{day_temp}°",
                        (fx, forecast_y + int(ctx.height * 0.20)),
                        font=font_tiny,
                        color=COLOR_WHITE,
                        anchor="mm",
                    )

    def _render_compact(
        self,
        ctx: RenderContext,
        icon_name: str,
        temperature: Any,
        humidity: Any,
        padding: int,
    ) -> None:
        """Render compact weather (for smaller slots)."""
        center_y = ctx.height // 2

        # Get scaled fonts
        font_temp = ctx.get_font("large")
        font_tiny = ctx.get_font("tiny")

        # Icon on left, temp on right - scaled to container
        icon_size = max(16, min(32, int(ctx.height * 0.40)))
        ctx.draw_icon(
            icon_name,
            (padding, center_y - icon_size // 2),
            size=icon_size,
            color=COLOR_GOLD,
        )

        # Temperature
        temp_str = f"{temperature}°" if temperature != "--" else "--"
        ctx.draw_text(
            temp_str,
            (ctx.width - padding, center_y - int(ctx.height * 0.04)),
            font=font_temp,
            color=COLOR_WHITE,
            anchor="rm",
        )

        # Humidity below temp
        if self.show_humidity:
            ctx.draw_text(
                f"{humidity}%",
                (ctx.width - padding, center_y + int(ctx.height * 0.15)),
                font=font_tiny,
                color=COLOR_CYAN,
                anchor="rm",
            )
