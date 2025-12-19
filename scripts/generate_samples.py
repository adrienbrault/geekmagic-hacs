#!/usr/bin/env python3
"""Generate sample dashboard images using the layout system and widgets.

This script generates sample images that represent what the integration
will actually render, using real layouts and widgets with mock Home Assistant data.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from custom_components.geekmagic.const import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_GRAY,
    COLOR_LIME,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
    COLOR_YELLOW,
)
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid2x3, Grid3x2
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.split import SplitHorizontal, SplitVertical
from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import (
    ClockWidget,
    EntityWidget,
    GaugeWidget,
    MediaWidget,
    MultiProgressWidget,
    StatusListWidget,
    WeatherWidget,
    WidgetConfig,
)
from scripts.mock_hass import (
    MockHass,
    create_battery_states,
    create_clock_states,
    create_energy_states,
    create_fitness_states,
    create_media_player_states,
    create_network_states,
    create_security_states,
    create_server_stats_states,
    create_smart_home_states,
    create_system_monitor_states,
    create_thermostat_states,
    create_weather_states,
)


def save_image(renderer: Renderer, img: Image.Image, name: str, output_dir: Path) -> None:
    """Save the rendered image to disk."""
    final = renderer.finalize(img)
    output_path = output_dir / f"{name}.png"
    final.save(output_path)
    print(f"Generated: {output_path}")


def generate_widget_sizes(renderer: Renderer, output_dir: Path) -> None:
    """Generate full 240x240 layouts showing each widget type in different grid sizes."""
    from custom_components.geekmagic.layouts.grid import Grid3x3
    from custom_components.geekmagic.widgets.chart import ChartWidget
    from custom_components.geekmagic.widgets.clock import ClockWidget
    from custom_components.geekmagic.widgets.progress import ProgressWidget
    from custom_components.geekmagic.widgets.status import StatusWidget
    from custom_components.geekmagic.widgets.text import TextWidget
    from custom_components.geekmagic.widgets.weather import WeatherWidget

    widgets_dir = output_dir / "widgets"
    widgets_dir.mkdir(exist_ok=True)

    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU Usage"})
    hass.states.set(
        "sensor.temp", "23.5", {"unit_of_measurement": "°C", "friendly_name": "Temperature"}
    )
    hass.states.set(
        "sensor.steps", "8542", {"unit_of_measurement": "steps", "friendly_name": "Steps"}
    )
    hass.states.set("binary_sensor.door", "on", {"friendly_name": "Front Door"})
    hass.states.set(
        "weather.home",
        "sunny",
        {
            "friendly_name": "Weather",
            "temperature": 24,
            "temperature_unit": "°C",
            "humidity": 45,
            "forecast": [
                {"datetime": "2024-01-15", "condition": "sunny", "temperature": 26},
                {"datetime": "2024-01-16", "condition": "cloudy", "temperature": 23},
                {"datetime": "2024-01-17", "condition": "rainy", "temperature": 19},
            ],
        },
    )

    def make_gauge_bar(slot: int) -> GaugeWidget:
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id="sensor.cpu",
                label="CPU",
                color=COLOR_CYAN,
                options={"style": "bar", "icon": "chip"},
            )
        )

    def make_gauge_ring(slot: int) -> GaugeWidget:
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id="sensor.cpu",
                label="CPU",
                color=COLOR_LIME,
                options={"style": "ring"},
            )
        )

    def make_gauge_arc(slot: int) -> GaugeWidget:
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id="sensor.temp",
                label="Temp",
                color=COLOR_ORANGE,
                options={"style": "arc"},
            )
        )

    def make_entity_icon(slot: int) -> EntityWidget:
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id="sensor.temp",
                label="Temperature",
                color=COLOR_ORANGE,
                options={"icon": "thermometer"},
            )
        )

    def make_entity_plain(slot: int) -> EntityWidget:
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id="sensor.temp",
                label="Temperature",
                color=COLOR_CYAN,
                options={},
            )
        )

    def make_clock(slot: int) -> ClockWidget:
        return ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=slot,
                color=COLOR_WHITE,
                options={"show_date": True, "time_format": "24h"},
            )
        )

    def make_text(slot: int) -> TextWidget:
        return TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=slot,
                color=COLOR_CYAN,
                options={"text": "Hello"},
            )
        )

    def make_progress(slot: int) -> ProgressWidget:
        return ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=slot,
                entity_id="sensor.steps",
                label="Steps",
                color=COLOR_LIME,
                options={"target": 10000, "icon": "heart"},
            )
        )

    def make_weather(slot: int) -> WeatherWidget:
        return WeatherWidget(
            WidgetConfig(
                widget_type="weather",
                slot=slot,
                entity_id="weather.home",
                color=COLOR_YELLOW,
                options={"show_forecast": True, "forecast_days": 3},
            )
        )

    def make_status(slot: int) -> StatusWidget:
        return StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=slot,
                entity_id="binary_sensor.door",
                label="Door",
                color=COLOR_LIME,
                options={"icon": "lock"},
            )
        )

    def make_chart(slot: int) -> ChartWidget:
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id="sensor.temp",
                label="Temperature",
                color=COLOR_CYAN,
                options={},
            )
        )
        # Set mock history data
        widget.set_history([20, 21, 22, 21, 23, 24, 23, 22, 21, 22, 23, 24])
        return widget

    def make_chart_binary(slot: int) -> ChartWidget:
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id="binary_sensor.door",
                label="Door",
                color=COLOR_LIME,
                options={},
            )
        )
        # Set mock binary history data (0=off/closed, 1=on/open)
        # Simulates door opening and closing over time
        widget.set_history([0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0])
        return widget

    def make_fullscreen(slot: int):
        from custom_components.geekmagic.widgets.fullscreen import FullscreenWidget

        return FullscreenWidget(
            WidgetConfig(
                widget_type="fullscreen",
                slot=slot,
                label="Image",
                color=COLOR_CYAN,
                options={},
            )
        )

    # Widget configs: (name, factory)
    widget_types = [
        ("gauge_bar", make_gauge_bar),
        ("gauge_ring", make_gauge_ring),
        ("gauge_arc", make_gauge_arc),
        ("entity_icon", make_entity_icon),
        ("entity_plain", make_entity_plain),
        ("clock", make_clock),
        ("text", make_text),
        ("progress", make_progress),
        ("weather", make_weather),
        ("status", make_status),
        ("chart", make_chart),
        ("chart_binary", make_chart_binary),
        ("fullscreen", make_fullscreen),
    ]

    # Layout configs: (suffix, layout_class, num_slots, padding, gap)
    layouts = [
        ("1x1", None, 1, 8, 8),  # Single widget
        ("1x2", SplitHorizontal, 2, 8, 8),  # 2 side-by-side
        ("2x1", SplitVertical, 2, 8, 8),  # 2 stacked
        ("2x2", Grid2x2, 4, 8, 8),
        ("2x3", Grid2x3, 6, 8, 8),
        ("3x2", Grid3x2, 6, 8, 8),  # 3 rows, 2 columns
        ("3x3", Grid3x3, 9, 6, 6),
    ]

    for widget_name, make_widget in widget_types:
        for layout_suffix, layout_class, num_slots, padding, gap in layouts:
            img, draw = renderer.create_canvas()

            if layout_suffix == "1x1":
                # Single widget using hero layout with minimal footer
                layout = HeroLayout(footer_slots=1, hero_ratio=1.0, padding=padding, gap=gap)
                layout.set_widget(0, make_widget(0))
            elif layout_class is not None and num_slots == 2:
                # Split layouts
                layout = layout_class(ratio=0.5, padding=padding, gap=gap)
                for i in range(2):
                    layout.set_widget(i, make_widget(i))
            else:
                assert layout_class is not None
                layout = layout_class(padding=padding, gap=gap)
                for i in range(num_slots):
                    layout.set_widget(i, make_widget(i))

            layout.render(renderer, draw, hass)  # type: ignore[arg-type]
            save_image(renderer, img, f"{widget_name}_{layout_suffix}", widgets_dir)

    print(f"Generated widget size samples in {widgets_dir}")


def generate_system_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate system monitor dashboard using Grid2x2 layout with GaugeWidgets."""
    hass = MockHass()
    create_system_monitor_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # CPU gauge (slot 0 - top left)
    cpu_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu_usage",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "ring", "max": 100, "icon": "chip"},
        )
    )
    layout.set_widget(0, cpu_widget)

    # Memory gauge (slot 1 - top right)
    mem_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.memory_usage",
            label="Memory",
            color=COLOR_PURPLE,
            options={"style": "ring", "max": 100, "icon": "memory"},
        )
    )
    layout.set_widget(1, mem_widget)

    # Disk gauge (slot 2 - bottom left)
    disk_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.disk_usage",
            label="Disk",
            color=COLOR_ORANGE,
            options={"style": "bar", "max": 100, "icon": "harddisk"},
        )
    )
    layout.set_widget(2, disk_widget)

    # Network gauge (slot 3 - bottom right)
    net_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=3,
            entity_id="sensor.network_throughput",
            label="Network",
            color=COLOR_LIME,
            options={"style": "bar", "max": 100, "icon": "network"},
        )
    )
    layout.set_widget(3, net_widget)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "01_system_monitor", output_dir)


def generate_smart_home(renderer: Renderer, output_dir: Path) -> None:
    """Generate smart home dashboard using Grid2x3 layout."""
    hass = MockHass()
    create_smart_home_states(hass)

    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Row 1: Device status widgets
    # Living Room Light (slot 0)
    light1 = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="light.living_room",
            label="Lights",
            color=COLOR_GOLD,
            options={"show_name": True, "icon": "lightbulb", "show_panel": True},
        )
    )
    layout.set_widget(0, light1)

    # Kitchen Light (slot 1)
    light2 = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="light.kitchen",
            label="Kitchen",
            color=COLOR_GRAY,
            options={"show_name": True, "icon": "lightbulb", "show_panel": True},
        )
    )
    layout.set_widget(1, light2)

    # AC status (slot 2)
    ac = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="climate.thermostat",
            label="AC",
            color=COLOR_CYAN,
            options={"show_name": True, "show_panel": True},
        )
    )
    layout.set_widget(2, ac)

    # Row 2: Sensors
    # Temperature (slot 3)
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.temperature",
            color=COLOR_ORANGE,
            options={"show_name": True, "show_unit": True, "show_panel": True},
        )
    )
    layout.set_widget(3, temp)

    # Humidity (slot 4)
    humidity = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=4,
            entity_id="sensor.humidity",
            color=COLOR_CYAN,
            options={"show_name": True, "show_unit": True, "icon": "water", "show_panel": True},
        )
    )
    layout.set_widget(4, humidity)

    # Lock status (slot 5)
    lock = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=5,
            entity_id="lock.front_door",
            label="Door",
            color=COLOR_LIME,
            options={"show_name": True, "icon": "lock", "show_panel": True},
        )
    )
    layout.set_widget(5, lock)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "02_smart_home", output_dir)


def generate_weather(renderer: Renderer, output_dir: Path) -> None:
    """Generate weather dashboard using HeroLayout."""
    hass = MockHass()
    create_weather_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.75, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Weather widget with forecast
    weather = WeatherWidget(
        WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
            options={"show_forecast": True, "forecast_days": 3, "show_humidity": True},
        )
    )
    layout.set_widget(0, weather)

    # Footer slots can show additional info if needed
    # For now, leave them empty to let the weather widget shine

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "03_weather", output_dir)


def generate_server_stats(renderer: Renderer, output_dir: Path) -> None:
    """Generate server stats dashboard using Grid2x3 layout."""
    hass = MockHass()
    create_server_stats_states(hass)

    # Use 2x3 grid for better spacing (6 widgets instead of 9)
    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Row 1: CPU, Memory, Disk
    cpu = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.server_cpu",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "bar", "icon": "chip"},
        )
    )
    layout.set_widget(0, cpu)

    mem = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.server_memory",
            label="MEM",
            color=COLOR_PURPLE,
            options={"style": "bar", "icon": "memory"},
        )
    )
    layout.set_widget(1, mem)

    disk = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.server_disk",
            label="DISK",
            color=COLOR_ORANGE,
            options={"style": "bar", "icon": "harddisk"},
        )
    )
    layout.set_widget(2, disk)

    # Row 2: Temp, Upload, Download
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.server_temp",
            label="Temp",
            color=COLOR_RED,
            options={"show_panel": True},
        )
    )
    layout.set_widget(3, temp)

    upload = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=4,
            entity_id="sensor.server_upload",
            label="Upload",
            color=COLOR_LIME,
            options={"icon": "arrow_up", "show_panel": True},
        )
    )
    layout.set_widget(4, upload)

    download = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=5,
            entity_id="sensor.server_download",
            label="Down",
            color=COLOR_RED,
            options={"icon": "arrow_down", "show_panel": True},
        )
    )
    layout.set_widget(5, download)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "04_server_stats", output_dir)


def generate_media_player(renderer: Renderer, output_dir: Path) -> None:
    """Generate media player dashboard using single-slot layout."""
    hass = MockHass()
    create_media_player_states(hass)

    img, draw = renderer.create_canvas()

    # Media widget takes full screen
    media = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True},
        )
    )

    # Draw media widget in full canvas area using RenderContext
    rect = (8, 8, 232, 232)
    ctx = RenderContext(draw, rect, renderer)
    media.render(ctx, hass)  # type: ignore[arg-type]

    save_image(renderer, img, "05_media_player", output_dir)


def generate_energy_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate energy monitor dashboard using Grid2x2 layout."""
    hass = MockHass()
    create_energy_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Consumption (slot 0)
    consumption = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.energy_consumption",
            label="Using",
            color=COLOR_ORANGE,
            options={"icon": "lightning-bolt", "show_panel": True},
        )
    )
    layout.set_widget(0, consumption)

    # Solar (slot 1)
    solar = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.solar_production",
            label="Solar",
            color=COLOR_GOLD,
            options={"icon": "weather-sunny", "show_panel": True},
        )
    )
    layout.set_widget(1, solar)

    # Grid export (slot 2)
    grid = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.grid_export",
            label="Export",
            color=COLOR_LIME,
            options={"icon": "power", "show_panel": True},
        )
    )
    layout.set_widget(2, grid)

    # Today total (slot 3)
    today = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.energy_today",
            label="Today",
            color=COLOR_CYAN,
            options={"icon": "lightning-bolt", "show_panel": True},
        )
    )
    layout.set_widget(3, today)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "06_energy_monitor", output_dir)


def generate_fitness(renderer: Renderer, output_dir: Path) -> None:
    """Generate fitness dashboard using HeroLayout with MultiProgressWidget."""
    hass = MockHass()
    create_fitness_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Multi-progress for activity rings replacement
    progress = MultiProgressWidget(
        WidgetConfig(
            widget_type="progress",
            slot=0,
            options={
                "title": "Activity",
                "items": [
                    {
                        "entity_id": "sensor.move_calories",
                        "label": "Move",
                        "target": 800,
                        "color": COLOR_RED,
                        "unit": "cal",
                        "icon": "fire",
                    },
                    {
                        "entity_id": "sensor.exercise_minutes",
                        "label": "Exercise",
                        "target": 40,
                        "color": COLOR_LIME,
                        "unit": "min",
                        "icon": "walk",
                    },
                    {
                        "entity_id": "sensor.stand_hours",
                        "label": "Stand",
                        "target": 12,
                        "color": COLOR_CYAN,
                        "unit": "hr",
                    },
                ],
            },
        )
    )
    layout.set_widget(0, progress)

    # Footer: Steps, Distance, Heart Rate (no units to save space)
    steps = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.steps",
            label="Steps",
            color=COLOR_WHITE,
            options={"show_name": True, "show_unit": False},
        )
    )
    layout.set_widget(1, steps)

    distance = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.distance",
            label="Dist",
            color=COLOR_WHITE,
            options={"show_name": True, "show_unit": False},
        )
    )
    layout.set_widget(2, distance)

    heart = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.heart_rate",
            label="BPM",
            color=COLOR_RED,
            options={"show_name": True, "show_unit": False, "icon": "heart"},
        )
    )
    layout.set_widget(3, heart)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "07_fitness", output_dir)


def generate_clock_dashboard(renderer: Renderer, output_dir: Path) -> None:
    """Generate clock dashboard using HeroLayout."""
    hass = MockHass()
    create_clock_states(hass)

    layout = HeroLayout(footer_slots=2, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Clock widget
    clock = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            color=COLOR_WHITE,
            options={"show_date": True, "show_seconds": False},
        )
    )
    layout.set_widget(0, clock)

    # Footer: Temperature and Calendar
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.outdoor_temp",
            label="Outside",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(1, temp)

    calendar = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="calendar.personal",
            label="Next",
            color=COLOR_GOLD,
        )
    )
    layout.set_widget(2, calendar)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "08_clock_dashboard", output_dir)


def generate_network_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate network monitor dashboard using HeroLayout with StatusListWidget."""
    hass = MockHass()
    create_network_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Device status list
    devices = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Devices",
                "entities": [
                    ("device_tracker.phone", "Phone"),
                    ("device_tracker.laptop", "Laptop"),
                    ("device_tracker.tablet", "Tablet"),
                    ("device_tracker.tv", "Smart TV"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_GRAY,
            },
        )
    )
    layout.set_widget(0, devices)

    # Footer: Download, Upload, Total devices (no units to save space)
    download = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.router_download",
            label="Down",
            color=COLOR_LIME,
            options={"show_unit": False},
        )
    )
    layout.set_widget(1, download)

    upload = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.router_upload",
            label="Up",
            color=COLOR_ORANGE,
            options={"show_unit": False},
        )
    )
    layout.set_widget(2, upload)

    total = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.devices_online",
            label="Online",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(3, total)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "09_network_monitor", output_dir)


def generate_thermostat(renderer: Renderer, output_dir: Path) -> None:
    """Generate thermostat dashboard using HeroLayout."""
    hass = MockHass()
    create_thermostat_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Temperature gauge (using arc style for thermostat look)
    # Read from "temperature" attribute since climate entity state is HVAC mode
    thermostat = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="climate.main",
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
    layout.set_widget(0, thermostat)

    # Footer: Room temperatures
    living = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.living_temp",
            label="Living",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(1, living)

    bedroom = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.bedroom_temp",
            label="Bedroom",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(2, bedroom)

    bathroom = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.bathroom_temp",
            label="Bath",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(3, bathroom)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "10_thermostat", output_dir)


def generate_batteries(renderer: Renderer, output_dir: Path) -> None:
    """Generate battery status dashboard using Grid2x2 layout."""
    hass = MockHass()
    create_battery_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Phone battery
    phone = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.phone_battery",
            label="Phone",
            color=COLOR_LIME,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(0, phone)

    # Tablet battery
    tablet = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.tablet_battery",
            label="Tablet",
            color=COLOR_GOLD,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(1, tablet)

    # Watch battery (low - red)
    watch = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.watch_battery",
            label="Watch",
            color=COLOR_RED,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(2, watch)

    # AirPods battery
    airpods = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=3,
            entity_id="sensor.earbuds_battery",
            label="AirPods",
            color=COLOR_LIME,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(3, airpods)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "11_batteries", output_dir)


def generate_security(renderer: Renderer, output_dir: Path) -> None:
    """Generate security dashboard using SplitLayout."""
    hass = MockHass()
    create_security_states(hass)

    layout = SplitVertical(ratio=0.5, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Top: Door status list
    doors = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Doors",
                "entities": [
                    ("lock.front_door", "Front Door"),
                    ("lock.back_door", "Back Door"),
                    ("lock.garage", "Garage"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_RED,
                "on_text": "LOCKED",
                "off_text": "OPEN",
            },
        )
    )
    layout.set_widget(0, doors)

    # Bottom: Motion sensor status list
    motion = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=1,
            options={
                "title": "Motion",
                "entities": [
                    ("binary_sensor.living_motion", "Living Room"),
                    ("binary_sensor.kitchen_motion", "Kitchen"),
                    ("binary_sensor.backyard_motion", "Backyard"),
                ],
                "on_color": COLOR_RED,
                "off_color": COLOR_LIME,
                "on_text": "MOTION",
                "off_text": "Clear",
            },
        )
    )
    layout.set_widget(1, motion)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "12_security", output_dir)


def generate_welcome_screen(renderer: Renderer, output_dir: Path) -> None:
    """Generate welcome screen shown when device has no configuration.

    This mimics the dynamic welcome layout with clock, HA version, and entity count.
    """
    from custom_components.geekmagic.layouts.hero import HeroLayout
    from custom_components.geekmagic.widgets.clock import ClockWidget
    from custom_components.geekmagic.widgets.text import TextWidget

    hass = MockHass()

    layout = HeroLayout(footer_slots=3, hero_ratio=0.65, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Clock widget showing current time
    clock = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            color=COLOR_WHITE,
            options={"show_date": True, "show_seconds": False},
        )
    )
    layout.set_widget(0, clock)

    # Footer slot 1: HA version
    ha_version = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=1,
            label="HA",
            color=COLOR_CYAN,
            options={
                "text": "2024.12.1",
                "size": "small",
                "align": "center",
            },
        )
    )
    layout.set_widget(1, ha_version)

    # Footer slot 2: Entity count
    entity_count = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=2,
            label="Entities",
            color=COLOR_LIME,
            options={
                "text": "247",
                "size": "small",
                "align": "center",
            },
        )
    )
    layout.set_widget(2, entity_count)

    # Footer slot 3: Setup hint
    setup_hint = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=3,
            color=COLOR_GRAY,
            options={
                "text": "Configure →",
                "size": "small",
                "align": "center",
            },
        )
    )
    layout.set_widget(3, setup_hint)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "00_welcome_screen", output_dir)


def generate_charts_dashboard(renderer: Renderer, output_dir: Path) -> None:
    """Generate charts dashboard showing numeric and binary sensor history."""
    from custom_components.geekmagic.widgets.chart import ChartWidget

    hass = MockHass()
    hass.states.set(
        "sensor.temperature", "23.5", {"unit_of_measurement": "°C", "friendly_name": "Temperature"}
    )
    hass.states.set(
        "sensor.humidity", "65", {"unit_of_measurement": "%", "friendly_name": "Humidity"}
    )
    hass.states.set("binary_sensor.motion", "off", {"friendly_name": "Motion"})
    hass.states.set("binary_sensor.door", "off", {"friendly_name": "Door"})

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Temperature chart (numeric)
    temp_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
            label="Temperature",
            color=COLOR_ORANGE,
            options={},
        )
    )
    temp_chart.set_history([21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 23.8, 23.5, 23.0, 22.5, 23.0, 23.5])
    layout.set_widget(0, temp_chart)

    # Humidity chart (numeric)
    humid_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=1,
            entity_id="sensor.humidity",
            label="Humidity",
            color=COLOR_CYAN,
            options={},
        )
    )
    humid_chart.set_history([60, 62, 65, 68, 70, 68, 65, 63, 60, 58, 60, 65])
    layout.set_widget(1, humid_chart)

    # Motion sensor chart (binary)
    motion_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=2,
            entity_id="binary_sensor.motion",
            label="Motion",
            color=COLOR_RED,
            options={},
        )
    )
    # Binary: 0=no motion, 1=motion detected
    motion_chart.set_history([0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0])
    layout.set_widget(2, motion_chart)

    # Door sensor chart (binary)
    door_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=3,
            entity_id="binary_sensor.door",
            label="Door",
            color=COLOR_LIME,
            options={},
        )
    )
    # Binary: 0=closed, 1=open
    door_chart.set_history([0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    layout.set_widget(3, door_chart)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "15_charts_dashboard", output_dir)


def generate_gauge_sizes_2x2(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauges in 2x2 layout (large cells) to show responsive behavior."""
    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.mem", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "45", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set("sensor.net", "82", {"unit_of_measurement": "%", "friendly_name": "Network"})

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    widgets = [
        ("sensor.cpu", "CPU", "cpu", COLOR_LIME),
        ("sensor.mem", "Memory", "memory", COLOR_PURPLE),
        ("sensor.disk", "Disk", "disk", COLOR_ORANGE),
        ("sensor.net", "Network", "network", COLOR_CYAN),
    ]

    for i, (entity, label, icon, color) in enumerate(widgets):
        gauge = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=i,
                entity_id=entity,
                label=label,
                color=color,
                options={"style": "bar", "icon": icon},
            )
        )
        layout.set_widget(i, gauge)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "13_gauges_large", output_dir)


def generate_gauge_sizes_2x3(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauges in 2x3 layout (small cells) to show responsive behavior."""
    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.mem", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "45", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set("sensor.net", "82", {"unit_of_measurement": "%", "friendly_name": "Network"})
    hass.states.set("sensor.gpu", "55", {"unit_of_measurement": "%", "friendly_name": "GPU"})
    hass.states.set("sensor.swap", "30", {"unit_of_measurement": "%", "friendly_name": "Swap"})

    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    widgets = [
        ("sensor.cpu", "CPU", "cpu", COLOR_LIME),
        ("sensor.mem", "Memory", "memory", COLOR_PURPLE),
        ("sensor.disk", "Disk", "disk", COLOR_ORANGE),
        ("sensor.net", "Network", "network", COLOR_CYAN),
        ("sensor.gpu", "GPU", "temp", COLOR_RED),
        ("sensor.swap", "Swap", "memory", COLOR_TEAL),
    ]

    for i, (entity, label, icon, color) in enumerate(widgets):
        gauge = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=i,
                entity_id=entity,
                label=label,
                color=color,
                options={"style": "bar", "icon": icon},
            )
        )
        layout.set_widget(i, gauge)

    layout.render(renderer, draw, hass)  # type: ignore[arg-type]
    save_image(renderer, img, "14_gauges_small", output_dir)


def main() -> None:
    """Generate all sample images."""
    output_dir = Path(__file__).parent.parent / "samples"
    output_dir.mkdir(exist_ok=True)

    renderer = Renderer()

    print("Generating sample dashboards using layout system...")
    print()

    generate_welcome_screen(renderer, output_dir)
    generate_system_monitor(renderer, output_dir)
    generate_smart_home(renderer, output_dir)
    generate_weather(renderer, output_dir)
    generate_server_stats(renderer, output_dir)
    generate_media_player(renderer, output_dir)
    generate_energy_monitor(renderer, output_dir)
    generate_fitness(renderer, output_dir)
    generate_clock_dashboard(renderer, output_dir)
    generate_network_monitor(renderer, output_dir)
    generate_thermostat(renderer, output_dir)
    generate_batteries(renderer, output_dir)
    generate_security(renderer, output_dir)
    generate_gauge_sizes_2x2(renderer, output_dir)
    generate_gauge_sizes_2x3(renderer, output_dir)
    generate_charts_dashboard(renderer, output_dir)
    generate_widget_sizes(renderer, output_dir)

    print()
    print(f"Done! Generated samples in {output_dir}")


if __name__ == "__main__":
    main()
