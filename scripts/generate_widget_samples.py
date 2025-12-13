#!/usr/bin/env python3
"""Generate individual widget sample images at appropriate sizes.

This script renders each widget on a full-size canvas and then crops
to the widget's area to produce correctly-sized sample images.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from custom_components.geekmagic.const import (
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_LIME,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
)
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import (
    ChartWidget,
    ClockWidget,
    EntityWidget,
    GaugeWidget,
    MediaWidget,
    MultiProgressWidget,
    ProgressWidget,
    StatusListWidget,
    StatusWidget,
    TextWidget,
    WeatherWidget,
    WidgetConfig,
)
from scripts.mock_hass import MockHass


def render_widget_sample(
    renderer: Renderer,
    widget: Any,
    hass: MockHass,
    width: int,
    height: int,
) -> Image.Image:
    """Render a widget at specified size by rendering on full canvas and cropping.

    Args:
        renderer: Renderer instance
        widget: Widget to render
        hass: Mock Home Assistant instance
        width: Desired output width
        height: Desired output height

    Returns:
        Cropped and finalized widget image
    """
    # Create full canvas
    img, draw = renderer.create_canvas()

    # Calculate centered position for widget (in unscaled coordinates)
    # This ensures the widget renders properly with relative sizing
    x = (240 - width) // 2
    y = (240 - height) // 2
    rect = (x, y, x + width, y + height)

    # Render widget
    widget.render(renderer, draw, rect, hass)  # type: ignore[arg-type]

    # Finalize the full image
    final_full = renderer.finalize(img)

    # Crop to widget area and return
    return final_full.crop((x, y, x + width, y + height))


def save_widget(img: Image.Image, name: str, output_dir: Path) -> None:
    """Save widget image."""
    output_path = output_dir / f"widget_{name}.png"
    img.save(output_path)
    print(f"Generated: {output_path}")


def generate_clock(renderer: Renderer, output_dir: Path) -> None:
    """Generate clock widget sample."""
    hass = MockHass()
    widget = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            color=COLOR_WHITE,
            options={"show_date": True, "show_seconds": False},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 120, 80)
    save_widget(img, "clock", output_dir)


def generate_entity(renderer: Renderer, output_dir: Path) -> None:
    """Generate entity widget sample (basic)."""
    hass = MockHass()
    hass.states.set(
        "sensor.temperature",
        "23.5",
        {"unit_of_measurement": "°C", "friendly_name": "Temperature"},
    )

    widget = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
            color=COLOR_ORANGE,
            options={"show_name": True, "show_unit": True},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 100, 80)
    save_widget(img, "entity", output_dir)


def generate_entity_icon(renderer: Renderer, output_dir: Path) -> None:
    """Generate entity widget sample with icon."""
    hass = MockHass()
    hass.states.set(
        "sensor.humidity",
        "58",
        {"unit_of_measurement": "%", "friendly_name": "Humidity"},
    )

    widget = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.humidity",
            color=COLOR_CYAN,
            options={"show_name": True, "show_unit": True, "icon": "drop", "show_panel": True},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 100, 80)
    save_widget(img, "entity_icon", output_dir)


def generate_media(renderer: Renderer, output_dir: Path) -> None:
    """Generate media widget sample."""
    hass = MockHass()
    hass.states.set(
        "media_player.living_room",
        "playing",
        {
            "friendly_name": "Living Room",
            "media_title": "Bohemian Rhapsody",
            "media_artist": "Queen",
            "media_position": 145,
            "media_duration": 354,
        },
    )

    widget = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 200, 120)
    save_widget(img, "media", output_dir)


def generate_chart(renderer: Renderer, output_dir: Path) -> None:
    """Generate chart widget sample."""
    hass = MockHass()
    hass.states.set(
        "sensor.temperature",
        "23.5",
        {"unit_of_measurement": "°C", "friendly_name": "Temperature"},
    )

    widget = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
            color=COLOR_ORANGE,
            options={"show_value": True, "show_range": True},
        )
    )
    # Set mock history data using the public setter
    widget.set_history([18.5, 19.2, 20.1, 21.5, 22.3, 23.0, 23.5, 22.8, 21.5, 20.2])

    img = render_widget_sample(renderer, widget, hass, 120, 80)
    save_widget(img, "chart", output_dir)


def generate_text(renderer: Renderer, output_dir: Path) -> None:
    """Generate text widget sample."""
    hass = MockHass()

    widget = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=0,
            color=COLOR_WHITE,
            options={"text": "Hello World", "size": "large", "align": "center"},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 120, 60)
    save_widget(img, "text", output_dir)


def generate_progress(renderer: Renderer, output_dir: Path) -> None:
    """Generate progress widget sample."""
    hass = MockHass()
    hass.states.set(
        "sensor.calories",
        "680",
        {"unit_of_measurement": "cal", "friendly_name": "Calories"},
    )

    widget = ProgressWidget(
        WidgetConfig(
            widget_type="progress",
            slot=0,
            entity_id="sensor.calories",
            label="Move",
            color=COLOR_RED,
            options={"target": 800, "unit": "cal", "icon": "flame"},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 180, 60)
    save_widget(img, "progress", output_dir)


def generate_multi_progress(renderer: Renderer, output_dir: Path) -> None:
    """Generate multi-progress widget sample."""
    hass = MockHass()
    hass.states.set("sensor.move", "680", {"unit_of_measurement": "cal"})
    hass.states.set("sensor.exercise", "24", {"unit_of_measurement": "min"})
    hass.states.set("sensor.stand", "12", {"unit_of_measurement": "hr"})

    widget = MultiProgressWidget(
        WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={
                "title": "Activity",
                "items": [
                    {
                        "entity_id": "sensor.move",
                        "label": "Move",
                        "target": 800,
                        "color": COLOR_RED,
                        "icon": "flame",
                    },
                    {
                        "entity_id": "sensor.exercise",
                        "label": "Exercise",
                        "target": 40,
                        "color": COLOR_LIME,
                        "icon": "steps",
                    },
                    {
                        "entity_id": "sensor.stand",
                        "label": "Stand",
                        "target": 12,
                        "color": COLOR_CYAN,
                    },
                ],
            },
        )
    )

    img = render_widget_sample(renderer, widget, hass, 180, 140)
    save_widget(img, "multi_progress", output_dir)


def generate_weather(renderer: Renderer, output_dir: Path) -> None:
    """Generate weather widget sample."""
    hass = MockHass()
    hass.states.set(
        "weather.home",
        "sunny",
        {
            "temperature": 24,
            "humidity": 45,
            "friendly_name": "Home",
            "forecast": [
                {"datetime": "Mon", "condition": "sunny", "temperature": 26},
                {"datetime": "Tue", "condition": "partlycloudy", "temperature": 23},
                {"datetime": "Wed", "condition": "rainy", "temperature": 19},
            ],
        },
    )

    widget = WeatherWidget(
        WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
            options={"show_forecast": True, "forecast_days": 3, "show_humidity": True},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 180, 160)
    save_widget(img, "weather", output_dir)


def generate_status(renderer: Renderer, output_dir: Path) -> None:
    """Generate status widget sample."""
    hass = MockHass()
    hass.states.set("lock.front_door", "locked", {"friendly_name": "Front Door"})

    widget = StatusWidget(
        WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="lock.front_door",
            options={
                "on_color": COLOR_LIME,
                "off_color": COLOR_RED,
                "on_text": "LOCKED",
                "off_text": "OPEN",
                "icon": "lock",
            },
        )
    )

    img = render_widget_sample(renderer, widget, hass, 140, 40)
    save_widget(img, "status", output_dir)


def generate_status_list(renderer: Renderer, output_dir: Path) -> None:
    """Generate status list widget sample."""
    hass = MockHass()
    hass.states.set("device_tracker.phone", "home", {"friendly_name": "Phone"})
    hass.states.set("device_tracker.laptop", "home", {"friendly_name": "Laptop"})
    hass.states.set("device_tracker.tablet", "not_home", {"friendly_name": "Tablet"})
    hass.states.set("device_tracker.watch", "home", {"friendly_name": "Watch"})

    widget = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Devices",
                "entities": [
                    ("device_tracker.phone", "Phone"),
                    ("device_tracker.laptop", "Laptop"),
                    ("device_tracker.tablet", "Tablet"),
                    ("device_tracker.watch", "Watch"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_GRAY,
            },
        )
    )

    img = render_widget_sample(renderer, widget, hass, 160, 120)
    save_widget(img, "status_list", output_dir)


def generate_gauge_bar(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauge widget sample (bar style)."""
    hass = MockHass()
    hass.states.set("sensor.cpu", "42", {"unit_of_measurement": "%", "friendly_name": "CPU"})

    widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "bar", "max": 100, "icon": "cpu"},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 160, 60)
    save_widget(img, "gauge_bar", output_dir)


def generate_gauge_ring(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauge widget sample (ring style)."""
    hass = MockHass()
    hass.states.set(
        "sensor.memory",
        "68",
        {"unit_of_measurement": "%", "friendly_name": "Memory"},
    )

    widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.memory",
            label="Memory",
            color=COLOR_PURPLE,
            options={"style": "ring", "max": 100},
        )
    )

    img = render_widget_sample(renderer, widget, hass, 100, 100)
    save_widget(img, "gauge_ring", output_dir)


def generate_gauge_arc(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauge widget sample (arc style)."""
    hass = MockHass()
    hass.states.set(
        "climate.thermostat",
        "heat",
        {"temperature": 22, "friendly_name": "Thermostat"},
    )

    widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="climate.thermostat",
            label="Target",
            color=COLOR_ORANGE,
            options={
                "style": "arc",
                "min": 15,
                "max": 30,
                "unit": "°C",
                "attribute": "temperature",
            },
        )
    )

    img = render_widget_sample(renderer, widget, hass, 120, 100)
    save_widget(img, "gauge_arc", output_dir)


def main() -> None:
    """Generate all widget sample images."""
    output_dir = Path(__file__).parent.parent / "samples" / "widgets"
    output_dir.mkdir(parents=True, exist_ok=True)

    renderer = Renderer()

    print("Generating individual widget samples...")
    print()

    generate_clock(renderer, output_dir)
    generate_entity(renderer, output_dir)
    generate_entity_icon(renderer, output_dir)
    generate_media(renderer, output_dir)
    generate_chart(renderer, output_dir)
    generate_text(renderer, output_dir)
    generate_progress(renderer, output_dir)
    generate_multi_progress(renderer, output_dir)
    generate_weather(renderer, output_dir)
    generate_status(renderer, output_dir)
    generate_status_list(renderer, output_dir)
    generate_gauge_bar(renderer, output_dir)
    generate_gauge_ring(renderer, output_dir)
    generate_gauge_arc(renderer, output_dir)

    print()
    print(f"Done! Generated 14 widget samples in {output_dir}")


if __name__ == "__main__":
    main()
