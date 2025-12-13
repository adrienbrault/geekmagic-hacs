#!/usr/bin/env python3
"""Generate layout sample images showing each layout type."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from custom_components.geekmagic.const import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_LIME,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
)
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid2x3, Grid3x3
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.split import SplitLayout, ThreeColumnLayout
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import (
    ClockWidget,
    EntityWidget,
    GaugeWidget,
    StatusListWidget,
    WeatherWidget,
    WidgetConfig,
)
from scripts.mock_hass import MockHass


def save_layout(renderer: Renderer, img: Image.Image, name: str, output_dir: Path) -> None:
    """Save layout image."""
    final = renderer.finalize(img)
    output_path = output_dir / f"layout_{name}.png"
    final.save(output_path)
    print(f"Generated: {output_path}")


def create_mock_hass() -> MockHass:
    """Create mock hass with common entities."""
    hass = MockHass()
    # Sensors
    hass.states.set("sensor.temp", "23", {"unit_of_measurement": "°C", "friendly_name": "Temp"})
    hass.states.set(
        "sensor.humidity", "58", {"unit_of_measurement": "%", "friendly_name": "Humidity"}
    )
    hass.states.set("sensor.cpu", "42", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.memory", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "55", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set(
        "sensor.network", "85", {"unit_of_measurement": "Mb/s", "friendly_name": "Network"}
    )
    hass.states.set("sensor.power", "2.4", {"unit_of_measurement": "kW", "friendly_name": "Power"})
    hass.states.set("sensor.solar", "3.2", {"unit_of_measurement": "kW", "friendly_name": "Solar"})
    hass.states.set(
        "sensor.battery", "87", {"unit_of_measurement": "%", "friendly_name": "Battery"}
    )
    # Weather
    hass.states.set(
        "weather.home",
        "sunny",
        {
            "temperature": 24,
            "humidity": 45,
            "friendly_name": "Weather",
            "forecast": [
                {"datetime": "Mon", "condition": "sunny", "temperature": 26},
                {"datetime": "Tue", "condition": "cloudy", "temperature": 22},
                {"datetime": "Wed", "condition": "rainy", "temperature": 18},
            ],
        },
    )
    # Devices
    hass.states.set("device_tracker.phone", "home", {"friendly_name": "Phone"})
    hass.states.set("device_tracker.laptop", "home", {"friendly_name": "Laptop"})
    hass.states.set("device_tracker.tablet", "not_home", {"friendly_name": "Tablet"})
    hass.states.set("device_tracker.watch", "home", {"friendly_name": "Watch"})
    return hass


def generate_grid_2x2(renderer: Renderer, output_dir: Path) -> None:
    """Generate Grid 2x2 layout sample."""
    hass = create_mock_hass()
    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # 4 gauge widgets
    widgets = [
        GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                label="CPU",
                color=COLOR_TEAL,
                options={"style": "ring"},
            )
        ),
        GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=1,
                entity_id="sensor.memory",
                label="Memory",
                color=COLOR_PURPLE,
                options={"style": "ring"},
            )
        ),
        GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=2,
                entity_id="sensor.disk",
                label="Disk",
                color=COLOR_ORANGE,
                options={"style": "ring"},
            )
        ),
        GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=3,
                entity_id="sensor.battery",
                label="Battery",
                color=COLOR_LIME,
                options={"style": "ring"},
            )
        ),
    ]
    for i, w in enumerate(widgets):
        layout.set_widget(i, w)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "grid_2x2", output_dir)


def generate_grid_2x3(renderer: Renderer, output_dir: Path) -> None:
    """Generate Grid 2x3 layout sample."""
    hass = create_mock_hass()
    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # 6 entity widgets
    configs = [
        ("sensor.temp", "Temp", COLOR_ORANGE),
        ("sensor.humidity", "Humidity", COLOR_CYAN),
        ("sensor.cpu", "CPU", COLOR_TEAL),
        ("sensor.memory", "Memory", COLOR_PURPLE),
        ("sensor.power", "Power", COLOR_GOLD),
        ("sensor.solar", "Solar", COLOR_LIME),
    ]
    for i, (entity_id, label, color) in enumerate(configs):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=i,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_panel": True},
            )
        )
        layout.set_widget(i, widget)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "grid_2x3", output_dir)


def generate_grid_3x3(renderer: Renderer, output_dir: Path) -> None:
    """Generate Grid 3x3 layout sample."""
    hass = create_mock_hass()
    # Add more sensors for 9 slots
    hass.states.set("sensor.s1", "21", {"unit_of_measurement": "°C", "friendly_name": "Living"})
    hass.states.set("sensor.s2", "19", {"unit_of_measurement": "°C", "friendly_name": "Bedroom"})
    hass.states.set("sensor.s3", "23", {"unit_of_measurement": "°C", "friendly_name": "Kitchen"})
    hass.states.set("sensor.s4", "22", {"unit_of_measurement": "°C", "friendly_name": "Office"})
    hass.states.set("sensor.s5", "20", {"unit_of_measurement": "°C", "friendly_name": "Bath"})
    hass.states.set("sensor.s6", "18", {"unit_of_measurement": "°C", "friendly_name": "Garage"})
    hass.states.set("sensor.s7", "24", {"unit_of_measurement": "°C", "friendly_name": "Attic"})
    hass.states.set("sensor.s8", "17", {"unit_of_measurement": "°C", "friendly_name": "Basement"})
    hass.states.set("sensor.s9", "22", {"unit_of_measurement": "°C", "friendly_name": "Patio"})

    layout = Grid3x3(padding=6, gap=6)
    img, draw = renderer.create_canvas()

    colors = [
        COLOR_ORANGE,
        COLOR_CYAN,
        COLOR_TEAL,
        COLOR_PURPLE,
        COLOR_GOLD,
        COLOR_LIME,
        COLOR_RED,
        COLOR_WHITE,
        COLOR_ORANGE,
    ]
    for i in range(9):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=i,
                entity_id=f"sensor.s{i+1}",
                color=colors[i],
                options={"show_name": True},
            )
        )
        layout.set_widget(i, widget)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "grid_3x3", output_dir)


def generate_hero(renderer: Renderer, output_dir: Path) -> None:
    """Generate Hero layout sample."""
    hass = create_mock_hass()
    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Weather as hero
    weather = WeatherWidget(
        WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
            options={"show_forecast": True, "forecast_days": 3},
        )
    )
    layout.set_widget(0, weather)

    # Footer entities
    footer_configs = [
        ("sensor.temp", "Inside", COLOR_ORANGE),
        ("sensor.humidity", "Humidity", COLOR_CYAN),
        ("sensor.power", "Power", COLOR_GOLD),
    ]
    for i, (entity_id, label, color) in enumerate(footer_configs):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=i + 1,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_unit": False},
            )
        )
        layout.set_widget(i + 1, widget)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "hero", output_dir)


def generate_split_vertical(renderer: Renderer, output_dir: Path) -> None:
    """Generate Split Vertical layout sample (left/right)."""
    hass = create_mock_hass()
    layout = SplitLayout(horizontal=False, ratio=0.5, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Clock on left
    clock = ClockWidget(
        WidgetConfig(widget_type="clock", slot=0, color=COLOR_WHITE, options={"show_date": True})
    )
    layout.set_widget(0, clock)

    # Gauge on right
    gauge = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.cpu",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "ring"},
        )
    )
    layout.set_widget(1, gauge)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "split_vertical", output_dir)


def generate_split_horizontal(renderer: Renderer, output_dir: Path) -> None:
    """Generate Split Horizontal layout sample (top/bottom)."""
    hass = create_mock_hass()
    layout = SplitLayout(horizontal=True, ratio=0.5, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Clock on top
    clock = ClockWidget(
        WidgetConfig(widget_type="clock", slot=0, color=COLOR_WHITE, options={"show_date": True})
    )
    layout.set_widget(0, clock)

    # Status list on bottom
    status = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=1,
            options={
                "title": "Devices",
                "entities": [
                    ("device_tracker.phone", "Phone"),
                    ("device_tracker.laptop", "Laptop"),
                    ("device_tracker.tablet", "Tablet"),
                    ("device_tracker.watch", "Watch"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_RED,
            },
        )
    )
    layout.set_widget(1, status)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "split_horizontal", output_dir)


def generate_three_column(renderer: Renderer, output_dir: Path) -> None:
    """Generate Three Column layout sample."""
    hass = create_mock_hass()
    layout = ThreeColumnLayout(ratios=(0.33, 0.34, 0.33), padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # 3 gauge widgets
    configs = [
        ("sensor.cpu", "CPU", COLOR_TEAL),
        ("sensor.memory", "MEM", COLOR_PURPLE),
        ("sensor.disk", "DISK", COLOR_ORANGE),
    ]
    for i, (entity_id, label, color) in enumerate(configs):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=i,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"style": "bar"},
            )
        )
        layout.set_widget(i, widget)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_layout(renderer, img, "three_column", output_dir)


def main() -> None:
    """Generate all layout sample images."""
    output_dir = Path(__file__).parent.parent / "samples" / "layouts"
    output_dir.mkdir(parents=True, exist_ok=True)

    renderer = Renderer()

    print("Generating layout samples...")
    print()

    generate_grid_2x2(renderer, output_dir)
    generate_grid_2x3(renderer, output_dir)
    generate_grid_3x3(renderer, output_dir)
    generate_hero(renderer, output_dir)
    generate_split_vertical(renderer, output_dir)
    generate_split_horizontal(renderer, output_dir)
    generate_three_column(renderer, output_dir)

    print()
    print(f"Done! Generated 7 layout samples in {output_dir}")


if __name__ == "__main__":
    main()
