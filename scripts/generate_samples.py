#!/usr/bin/env python3
"""Generate sample dashboard images using the layout system and widgets.

This script generates sample images that represent what the integration
will actually render, using real layouts and widgets with mock Home Assistant data.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from custom_components.geekmagic.widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from custom_components.geekmagic.layouts.base import Layout

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
from custom_components.geekmagic.layouts.corner_hero import (
    HeroCornerBL,
    HeroCornerBR,
    HeroCornerTL,
    HeroCornerTR,
)
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.hero_simple import HeroSimpleLayout
from custom_components.geekmagic.layouts.sidebar import SidebarLeft, SidebarRight
from custom_components.geekmagic.layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
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
    WeatherWidget,
    WidgetConfig,
)
from custom_components.geekmagic.widgets.climate import ClimateWidget
from custom_components.geekmagic.widgets.theme import THEMES
from scripts.mock_hass import (
    MockHass,
    create_battery_states,
    create_clock_states,
    create_energy_states,
    create_fitness_states,
    create_media_player_paused_states,
    create_media_player_states,
    create_network_states,
    create_security_states,
    create_server_stats_states,
    create_smart_home_states,
    create_system_monitor_states,
    create_thermostat_states,
    create_weather_states,
)

# Fixed sample time for reproducible clock displays (Wed Jan 15, 2025 10:30 AM)
SAMPLE_TIME = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


def build_widget_states(
    layout: Layout,
    hass: MockHass,
    chart_history: dict[int, list[float]] | None = None,
    images: dict[int, Image.Image] | None = None,
    now: datetime | None = None,
) -> dict[int, WidgetState]:
    """Build WidgetState dict for all widgets in a layout.

    Args:
        layout: Layout with widgets assigned
        hass: MockHass with entity states
        chart_history: Optional dict mapping slot index to history data
        images: Optional dict mapping slot index to PIL images
        now: Optional fixed datetime for reproducible samples (defaults to current time)

    Returns:
        Dict mapping slot index to WidgetState
    """
    widget_states: dict[int, WidgetState] = {}
    chart_history = chart_history or {}
    images = images or {}

    # Use fixed time for reproducible samples (default to SAMPLE_TIME)
    sample_time = now if now is not None else SAMPLE_TIME

    for slot in layout.slots:
        if slot.widget is None:
            continue

        widget = slot.widget

        # Get primary entity
        entity_id = widget.config.entity_id
        entity: EntityState | None = None
        if entity_id:
            state = hass.states.get(entity_id)
            if state:
                entity = EntityState(
                    entity_id=entity_id,
                    state=state.state,
                    attributes=state.attributes,
                )

        # Get additional entities for multi-entity widgets
        entities: dict[str, EntityState] = {}
        try:
            entity_ids = widget.get_entities()
            for eid in entity_ids:
                if eid and eid != entity_id:
                    state = hass.states.get(eid)
                    if state:
                        entities[eid] = EntityState(
                            entity_id=eid,
                            state=state.state,
                            attributes=state.attributes,
                        )
        except AttributeError:
            pass

        # Get chart history for chart widgets
        history: list[float] = chart_history.get(slot.index, [])

        # Get forecast for weather widgets (from entity attributes for mock data)
        forecast: list[dict] = []
        if entity and widget.config.widget_type == "weather":
            forecast = entity.attributes.get("forecast", [])

        # Get image for this slot (for media/camera widgets)
        image = images.get(slot.index)

        widget_states[slot.index] = WidgetState(
            entity=entity,
            entities=entities,
            history=history,
            forecast=forecast,
            image=image,
            now=sample_time,
        )

    return widget_states


def save_image(renderer: Renderer, img: Image.Image, name: str, output_dir: Path) -> None:
    """Save the rendered image to disk."""
    final = renderer.finalize(img)
    output_path = output_dir / f"{name}.png"
    final.save(output_path)
    print(f"Generated: {output_path}")


def create_fake_album_art(size: int = 300) -> Image.Image:
    """Create a fake album art image with elegant abstract design.

    Generates a visually appealing image that looks like modern album artwork
    with smooth gradients, geometric shapes, and artistic composition.

    Args:
        size: Image size (square)

    Returns:
        PIL Image
    """
    from PIL import ImageDraw, ImageFilter

    # Create image
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)

    # Rich gradient colors (deep blue to magenta to warm coral)
    colors = [
        (15, 23, 42),  # Slate 900
        (88, 28, 135),  # Purple 900
        (157, 23, 77),  # Pink 900
        (194, 65, 12),  # Orange 800
        (251, 146, 60),  # Orange 400
    ]

    # Draw diagonal gradient for more visual interest
    for y in range(size):
        for x in range(size):
            # Diagonal position (0 to 1)
            diag_pos = (x + y) / (size * 2)

            # Map to color array
            pos = diag_pos * (len(colors) - 1)
            idx = min(int(pos), len(colors) - 2)
            t = pos - idx

            # Smooth interpolation
            c1, c2 = colors[idx], colors[idx + 1]
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            img.putpixel((x, y), (r, g, b))

    # Large soft circle (like a sun/moon)
    circle_radius = int(size * 0.35)
    circle_x = int(size * 0.55)
    circle_y = int(size * 0.45)

    # Draw circle with gradient fill
    for radius in range(circle_radius, 0, -1):
        # Fade from bright to background
        t = radius / circle_radius
        # Warm highlight color
        color = (
            int(255 * t + 194 * (1 - t)),
            int(200 * t + 65 * (1 - t)),
            int(150 * t + 12 * (1 - t)),
        )
        draw.ellipse(
            [circle_x - radius, circle_y - radius, circle_x + radius, circle_y + radius],
            fill=color,
        )

    # Add subtle arc lines for texture
    for i in range(3):
        arc_radius = int(size * (0.6 + i * 0.15))
        arc_center_x = int(size * 0.2)
        arc_center_y = int(size * 0.8)
        draw.arc(
            [
                arc_center_x - arc_radius,
                arc_center_y - arc_radius,
                arc_center_x + arc_radius,
                arc_center_y + arc_radius,
            ],
            start=-60,
            end=30,
            fill=(255, 255, 255),
            width=2,
        )

    # Apply slight blur for softness
    return img.filter(ImageFilter.GaussianBlur(radius=1))


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
    hass.states.set(
        "binary_sensor.door", "on", {"friendly_name": "Front Door", "device_class": "door"}
    )
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
    hass.states.set(
        "media_player.spotify",
        "playing",
        {
            "friendly_name": "Spotify",
            "media_title": "Bohemian Rhapsody",
            "media_artist": "Queen",
            "media_album_name": "A Night at the Opera",
            "media_position": 145,
            "media_duration": 354,
        },
    )
    hass.states.set(
        "climate.thermostat",
        "heat",
        {
            "friendly_name": "Thermostat",
            "current_temperature": 21.5,
            "temperature": 22,
            "humidity": 58,
            "hvac_action": "heating",
        },
    )

    # Create fake album art for media widget
    media_album_art = create_fake_album_art(300)

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
        return ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id="sensor.temp",
                label="Temperature",
                color=COLOR_CYAN,
                options={},
            )
        )

    def make_chart_binary(slot: int) -> ChartWidget:
        return ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id="binary_sensor.door",
                label="Door",
                color=COLOR_LIME,
                options={},
            )
        )

    def make_media(slot: int) -> MediaWidget:
        return MediaWidget(
            WidgetConfig(
                widget_type="media",
                slot=slot,
                entity_id="media_player.spotify",
                color=COLOR_CYAN,
                options={"show_album_art": True, "show_artist": True, "show_progress": True},
            )
        )

    def make_climate(slot: int) -> ClimateWidget:
        return ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=slot,
                entity_id="climate.thermostat",
                color=COLOR_ORANGE,
                options={"show_target": True, "show_humidity": True, "show_mode": True},
            )
        )

    # Chart history data - keyed by widget_name
    chart_histories: dict[str, list[float]] = {
        "chart": [20, 21, 22, 21, 23, 24, 23, 22, 21, 22, 23, 24],
        "chart_binary": [0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0],
    }

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
        ("media", make_media),
        ("climate", make_climate),
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

            # Build chart_history for all slots if this is a chart widget
            slot_chart_history: dict[int, list[float]] = {}
            if widget_name in chart_histories:
                for i in range(num_slots):
                    slot_chart_history[i] = chart_histories[widget_name]

            # Build images dict for media widgets
            slot_images: dict[int, Image.Image] = {}
            if widget_name == "media":
                for i in range(num_slots):
                    slot_images[i] = media_album_art

            layout.render(
                renderer,
                draw,
                build_widget_states(layout, hass, slot_chart_history, images=slot_images),
            )
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "04_server_stats", output_dir)


def generate_media_player(renderer: Renderer, output_dir: Path) -> None:
    """Generate media player dashboard using fullscreen layout with album art."""
    hass = MockHass()
    create_media_player_states(hass)

    layout = FullscreenLayout(padding=0)
    img, draw = renderer.create_canvas()

    # Media widget takes full screen with album art
    media = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True, "show_album_art": True},
        )
    )
    layout.set_widget(0, media)

    # Create fake album art for the sample
    album_art = create_fake_album_art(300)
    images = {0: album_art}

    layout.render(renderer, draw, build_widget_states(layout, hass, images=images))
    save_image(renderer, img, "05_media_player", output_dir)


def generate_media_player_paused(renderer: Renderer, output_dir: Path) -> None:
    """Generate paused media player dashboard showing centered pause icon."""
    hass = MockHass()
    create_media_player_paused_states(hass)

    layout = FullscreenLayout(padding=0)
    img, draw = renderer.create_canvas()

    # Media widget in paused state
    media = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True, "show_album_art": True},
        )
    )
    layout.set_widget(0, media)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "05b_media_player_paused", output_dir)


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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "09_network_monitor", output_dir)


def generate_thermostat(renderer: Renderer, output_dir: Path) -> None:
    """Generate thermostat dashboard using HeroLayout with ClimateWidget."""
    hass = MockHass()
    create_thermostat_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Climate widget showing current temp, target, and hvac status
    thermostat = ClimateWidget(
        WidgetConfig(
            widget_type="climate",
            slot=0,
            entity_id="climate.main",
            label="Thermostat",
            color=COLOR_ORANGE,
            options={
                "show_target": True,
                "show_humidity": True,
                "show_mode": True,
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "12_security", output_dir)


def generate_binary_sensor_states(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample showing binary sensor device class icons and state translations.

    Shows all common device classes with their state-specific icons:
    - Icons read from HA icons.json files
    - States translated based on device_class (e.g., door on -> "Open")
    """
    hass = MockHass()

    # Create two grids side by side for more device classes
    # Left side: "On" states, Right side: Additional device classes
    # Using 2x Grid2x3 combined horizontally

    # Grid 1: Door/Window/Motion/Presence types (common home sensors)
    sensors_grid1 = [
        ("binary_sensor.door_on", "on", "Door", "door", COLOR_RED),
        ("binary_sensor.door_off", "off", "Door", "door", COLOR_LIME),
        ("binary_sensor.window_on", "on", "Window", "window", COLOR_ORANGE),
        ("binary_sensor.motion_on", "on", "Motion", "motion", COLOR_YELLOW),
        ("binary_sensor.motion_off", "off", "Motion", "motion", COLOR_CYAN),
        ("binary_sensor.presence", "on", "Home", "presence", COLOR_PURPLE),
    ]

    # Grid 2: Lock/Connectivity/Safety/Smoke
    sensors_grid2 = [
        ("binary_sensor.lock_on", "on", "Lock", "lock", COLOR_RED),
        ("binary_sensor.lock_off", "off", "Lock", "lock", COLOR_LIME),
        ("binary_sensor.wifi", "on", "WiFi", "connectivity", COLOR_CYAN),
        ("binary_sensor.smoke", "on", "Smoke", "smoke", COLOR_RED),
        ("binary_sensor.battery", "on", "Battery", "battery", COLOR_ORANGE),
        ("binary_sensor.plug", "on", "Plug", "plug", COLOR_LIME),
    ]

    # Set up all states
    for entity_id, state, name, device_class, _ in sensors_grid1 + sensors_grid2:
        hass.states.set(
            entity_id,
            state,
            {"friendly_name": name, "device_class": device_class},
        )

    # Create first grid (2x3)
    layout1 = Grid2x3(padding=8, gap=6)
    img1, draw1 = renderer.create_canvas()

    for slot, (entity_id, _, label, _, color) in enumerate(sensors_grid1):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout1.set_widget(slot, widget)

    layout1.render(renderer, draw1, build_widget_states(layout1, hass))
    save_image(renderer, img1, "16_binary_sensors", output_dir)

    # Create second grid (2x3) with additional device classes
    layout2 = Grid2x3(padding=8, gap=6)
    img2, draw2 = renderer.create_canvas()

    for slot, (entity_id, _, label, _, color) in enumerate(sensors_grid2):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout2.set_widget(slot, widget)

    layout2.render(renderer, draw2, build_widget_states(layout2, hass))
    save_image(renderer, img2, "17_binary_sensors_more", output_dir)


def generate_domain_icons(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample showing domain-specific state icons.

    Shows how different domains display icons based on state:
    - light: lightbulb on/off
    - switch: toggle on/off
    - fan: fan on/off
    - lock: lock/unlock
    """
    hass = MockHass()

    # Set up entities with various domains and states
    domain_entities = [
        # Row 1: Lights
        ("light.living_room", "on", "Light On", COLOR_GOLD),
        ("light.bedroom", "off", "Light Off", COLOR_GRAY),
        ("switch.outlet", "on", "Switch On", COLOR_LIME),
        # Row 2: Switch/Fan
        ("switch.plug", "off", "Switch Off", COLOR_GRAY),
        ("fan.ceiling", "on", "Fan On", COLOR_CYAN),
        ("fan.desk", "off", "Fan Off", COLOR_GRAY),
    ]

    for entity_id, state, name, _ in domain_entities:
        hass.states.set(
            entity_id,
            state,
            {"friendly_name": name},
        )

    layout = Grid2x3(padding=8, gap=6)
    img, draw = renderer.create_canvas()

    for slot, (entity_id, _, label, color) in enumerate(domain_entities):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout.set_widget(slot, widget)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "18_domain_icons", output_dir)


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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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
    hass.states.set(
        "binary_sensor.motion", "off", {"friendly_name": "Motion", "device_class": "motion"}
    )
    hass.states.set("binary_sensor.door", "off", {"friendly_name": "Door", "device_class": "door"})

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Chart history data for each slot
    chart_history: dict[int, list[float]] = {
        0: [21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 23.8, 23.5, 23.0, 22.5, 23.0, 23.5],  # temp
        1: [60, 62, 65, 68, 70, 68, 65, 63, 60, 58, 60, 65],  # humidity
        2: [0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0],  # motion (binary)
        3: [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # door (binary)
    }

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
    layout.set_widget(3, door_chart)

    layout.render(renderer, draw, build_widget_states(layout, hass, chart_history))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
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

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "14_gauges_small", output_dir)


def generate_layout_samples(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample images for all layouts showing their structure.

    Each layout is rendered with numbered slots to show the layout structure.
    """

    layouts_dir = output_dir / "layouts"
    layouts_dir.mkdir(exist_ok=True)

    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})

    # Define all layouts with their classes and names
    layouts_to_generate = [
        ("fullscreen", FullscreenLayout()),
        ("grid_2x2", Grid2x2()),
        ("grid_2x3", Grid2x3()),
        ("grid_3x2", Grid3x2()),
        ("grid_3x3", Grid3x3()),
        ("split_horizontal", SplitHorizontal()),
        ("split_vertical", SplitVertical()),
        ("split_h_1_2", SplitHorizontal1To2()),
        ("split_h_2_1", SplitHorizontal2To1()),
        ("three_column", ThreeColumnLayout()),
        ("three_row", ThreeRowLayout()),
        ("hero", HeroLayout()),
        ("hero_simple", HeroSimpleLayout()),
        ("sidebar_left", SidebarLeft()),
        ("sidebar_right", SidebarRight()),
        ("hero_corner_tl", HeroCornerTL()),
        ("hero_corner_tr", HeroCornerTR()),
        ("hero_corner_bl", HeroCornerBL()),
        ("hero_corner_br", HeroCornerBR()),
    ]

    for layout_name, layout in layouts_to_generate:
        img, draw = renderer.create_canvas()

        # Add a widget to each slot showing the slot number
        slot_count = layout.get_slot_count()
        colors = [COLOR_CYAN, COLOR_LIME, COLOR_ORANGE, COLOR_PURPLE, COLOR_YELLOW, COLOR_RED]

        for i in range(slot_count):
            widget = GaugeWidget(
                WidgetConfig(
                    widget_type="gauge",
                    slot=i,
                    entity_id="sensor.cpu",
                    label=f"Slot {i}",
                    color=colors[i % len(colors)],
                    options={"style": "bar"},
                )
            )
            layout.set_widget(i, widget)

        layout.render(renderer, draw, build_widget_states(layout, hass))
        save_image(renderer, img, f"layout_{layout_name}", layouts_dir)

    print(f"Generated layout samples in {layouts_dir}")


def generate_theme_samples(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample images for each theme with varied widgets."""
    import random

    layouts_dir = output_dir / "layouts"
    layouts_dir.mkdir(exist_ok=True)

    hass = MockHass()
    hass.states.set("sensor.cpu", "42", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.memory", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "55", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set("sensor.network", "85", {"unit_of_measurement": "Mb/s", "friendly_name": "Net"})
    hass.states.set("sensor.temp", "23", {"unit_of_measurement": "°C", "friendly_name": "Temp"})
    hass.states.set(
        "sensor.humidity", "58", {"unit_of_measurement": "%", "friendly_name": "Humidity"}
    )
    hass.states.set(
        "sensor.battery", "87", {"unit_of_measurement": "%", "friendly_name": "Battery"}
    )
    hass.states.set("sensor.power", "2.4", {"unit_of_measurement": "kW", "friendly_name": "Power"})
    hass.states.set("sensor.solar", "3.2", {"unit_of_measurement": "kW", "friendly_name": "Solar"})
    hass.states.set("device_tracker.phone", "home", {"friendly_name": "Phone"})

    # Define unique widget configurations for each theme
    theme_configs: dict[str, list] = {
        "classic": [
            ("gauge", "sensor.cpu", "CPU", {"style": "ring"}),
            ("gauge", "sensor.memory", "Memory", {"style": "ring"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("gauge", "sensor.disk", "Disk", {"style": "bar"}),
        ],
        "minimal": [
            ("entity", "sensor.temp", "Temp", {}),
            ("entity", "sensor.humidity", "Humidity", {}),
            ("status", "device_tracker.phone", "Phone", {}),
            ("entity", "sensor.power", "Power", {}),
        ],
        "neon": [
            ("gauge", "sensor.cpu", "CPU", {"style": "arc"}),
            ("gauge", "sensor.memory", "MEM", {"style": "arc"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("gauge", "sensor.battery", "BAT", {"style": "ring"}),
        ],
        "retro": [
            ("gauge", "sensor.cpu", "CPU", {"style": "bar"}),
            ("gauge", "sensor.memory", "MEM", {"style": "bar"}),
            ("gauge", "sensor.disk", "DSK", {"style": "bar"}),
            ("gauge", "sensor.network", "NET", {"style": "bar"}),
        ],
        "soft": [
            ("entity", "sensor.temp", "Inside", {}),
            ("progress", "sensor.battery", "Battery", {"target": 100}),
            ("chart", "sensor.temp", "Trend", {}),
            ("entity", "sensor.humidity", "Humidity", {}),
        ],
        "light": [
            ("gauge", "sensor.cpu", "CPU", {"style": "ring"}),
            ("gauge", "sensor.memory", "Memory", {"style": "ring"}),
            ("entity", "sensor.temp", "Temp", {}),
            ("progress", "sensor.disk", "Disk", {"target": 100}),
        ],
        "ocean": [
            ("gauge", "sensor.humidity", "Humidity", {"style": "arc"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("entity", "sensor.temp", "Inside", {}),
            ("gauge", "sensor.battery", "Battery", {"style": "ring"}),
        ],
        "sunset": [
            ("gauge", "sensor.power", "Power", {"style": "arc", "max": 5}),
            ("gauge", "sensor.solar", "Solar", {"style": "arc", "max": 5}),
            ("chart", "sensor.temp", "Temp", {}),
            ("entity", "sensor.battery", "Battery", {}),
        ],
        "forest": [
            ("entity", "sensor.temp", "Outdoor", {}),
            ("gauge", "sensor.humidity", "Humidity", {"style": "bar"}),
            ("chart", "sensor.temp", "Climate", {}),
            ("progress", "sensor.solar", "Solar", {"target": 5}),
        ],
        "candy": [
            ("gauge", "sensor.battery", "Battery", {"style": "ring"}),
            ("entity", "sensor.temp", "Temp", {}),
            ("progress", "sensor.cpu", "CPU", {"target": 100}),
            ("chart", "sensor.temp", "Trend", {}),
        ],
    }

    for theme_name, theme in THEMES.items():
        layout = Grid2x2(padding=8, gap=8)
        layout.theme = theme

        accent_colors = theme.accent_colors
        configs = theme_configs.get(theme_name, theme_configs["classic"])

        chart_history: dict[int, list[float]] = {}

        for i, (widget_type, entity_id, label, options) in enumerate(configs):
            color = accent_colors[i % len(accent_colors)]
            widget: (
                ClockWidget
                | GaugeWidget
                | EntityWidget
                | ChartWidget
                | ProgressWidget
                | StatusWidget
            )

            if widget_type == "gauge":
                widget = GaugeWidget(
                    WidgetConfig(
                        widget_type="gauge",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
            elif widget_type == "entity":
                widget = EntityWidget(
                    WidgetConfig(
                        widget_type="entity",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options={"show_panel": True, **options},
                    )
                )
            elif widget_type == "chart":
                widget = ChartWidget(
                    WidgetConfig(
                        widget_type="chart",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
                rng = random.Random(42 + i)  # noqa: S311
                chart_history[i] = [20 + rng.uniform(-3, 5) for _ in range(48)]
            elif widget_type == "progress":
                widget = ProgressWidget(
                    WidgetConfig(
                        widget_type="progress",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
            elif widget_type == "status":
                widget = StatusWidget(
                    WidgetConfig(
                        widget_type="status",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options={"on_color": theme.success, "off_color": theme.error},
                    )
                )
            else:
                continue

            layout.set_widget(i, widget)

        img, draw = renderer.create_canvas(background=theme.background)
        layout.render(renderer, draw, build_widget_states(layout, hass, chart_history))
        save_image(renderer, img, f"layout_theme_{theme_name}", layouts_dir)

    print(f"Generated {len(THEMES)} theme samples in {layouts_dir}")


def generate_emoji_sample(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample showcasing Unicode emoji support in widgets.

    Demonstrates emoji rendering with font fallback in various contexts:
    - Entity labels with emoji
    - Text widgets with emoji
    - Mixed text and emoji content
    """
    from custom_components.geekmagic.widgets.text import TextWidget

    hass = MockHass()

    # Entities with emoji-friendly names
    hass.states.set(
        "sensor.temperature",
        "23.5",
        {"unit_of_measurement": "°C", "friendly_name": "🌡️ Temperature"},
    )
    hass.states.set(
        "sensor.humidity",
        "58",
        {"unit_of_measurement": "%", "friendly_name": "💧 Humidity"},
    )
    hass.states.set(
        "light.living_room",
        "on",
        {"friendly_name": "💡 Lights"},
    )
    hass.states.set(
        "lock.front_door",
        "locked",
        {"friendly_name": "🔒 Door"},
    )
    hass.states.set(
        "sensor.battery",
        "85",
        {"unit_of_measurement": "%", "friendly_name": "🔋 Battery"},
    )
    hass.states.set(
        "binary_sensor.motion",
        "off",
        {"friendly_name": "👁️ Motion", "device_class": "motion"},
    )

    # Grid layout with emoji in labels
    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Temperature with emoji label
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
            label="🌡️ Temp",
            color=COLOR_ORANGE,
            options={"show_panel": True},
        )
    )
    layout.set_widget(0, temp)

    # Humidity with emoji
    humidity = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.humidity",
            label="💧 Humid",
            color=COLOR_CYAN,
            options={"show_panel": True},
        )
    )
    layout.set_widget(1, humidity)

    # Light status with emoji
    light = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="light.living_room",
            label="💡 Light",
            color=COLOR_GOLD,
            options={"show_panel": True},
        )
    )
    layout.set_widget(2, light)

    # Lock status with emoji
    lock = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="lock.front_door",
            label="🔒 Door",
            color=COLOR_LIME,
            options={"show_panel": True},
        )
    )
    layout.set_widget(3, lock)

    # Battery with emoji
    battery = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=4,
            entity_id="sensor.battery",
            label="🔋 Battery",
            color=COLOR_LIME,
            options={"style": "bar"},
        )
    )
    layout.set_widget(4, battery)

    # Text widget with emoji
    text = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=5,
            color=COLOR_WHITE,
            options={"text": "✅ All OK"},
        )
    )
    layout.set_widget(5, text)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "19_emoji_support", output_dir)

    # Also generate a hero layout with emoji
    layout2 = HeroLayout(footer_slots=3, hero_ratio=0.65, padding=8, gap=8)
    img2, draw2 = renderer.create_canvas()

    # Hero: Clock with greeting
    clock = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            color=COLOR_WHITE,
            options={"show_date": True},
        )
    )
    layout2.set_widget(0, clock)

    # Footer with emoji labels
    temp2 = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.temperature",
            label="🏠 Inside",
            color=COLOR_ORANGE,
        )
    )
    layout2.set_widget(1, temp2)

    status = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=2,
            color=COLOR_LIME,
            options={"text": "🌤️ Sunny"},
        )
    )
    layout2.set_widget(2, status)

    mood = TextWidget(
        WidgetConfig(
            widget_type="text",
            slot=3,
            color=COLOR_CYAN,
            options={"text": "😀 Good"},
        )
    )
    layout2.set_widget(3, mood)

    layout2.render(renderer, draw2, build_widget_states(layout2, hass))
    save_image(renderer, img2, "20_emoji_hero", output_dir)


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
    generate_media_player_paused(renderer, output_dir)
    generate_energy_monitor(renderer, output_dir)
    generate_fitness(renderer, output_dir)
    generate_clock_dashboard(renderer, output_dir)
    generate_network_monitor(renderer, output_dir)
    generate_thermostat(renderer, output_dir)
    generate_batteries(renderer, output_dir)
    generate_security(renderer, output_dir)
    generate_binary_sensor_states(renderer, output_dir)
    generate_domain_icons(renderer, output_dir)
    generate_gauge_sizes_2x2(renderer, output_dir)
    generate_gauge_sizes_2x3(renderer, output_dir)
    generate_charts_dashboard(renderer, output_dir)
    generate_widget_sizes(renderer, output_dir)
    generate_layout_samples(renderer, output_dir)
    generate_theme_samples(renderer, output_dir)
    generate_emoji_sample(renderer, output_dir)

    print()
    print(f"Done! Generated all samples in {output_dir}")


if __name__ == "__main__":
    main()
