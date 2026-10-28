#!/usr/bin/env python3
# ruff: noqa: S311, DTZ005
"""Debug script to render dashboards and upload to a GeekMagic device.

This simulates Home Assistant coordinator updates without needing HA
installed: each dashboard builds a layout with widgets, injects simulated
WidgetState data, and renders through the Blitz pipeline exactly like the
coordinator does.

Usage:
    uv run python scripts/debug_render.py <device_ip> [--cycle] [--interval 5]

Examples:
    # Render once and upload
    uv run python scripts/debug_render.py 192.168.1.100

    # Cycle through all dashboards every 5 seconds
    uv run python scripts/debug_render.py 192.168.1.100 --cycle --interval 5

    # Upload a specific dashboard
    uv run python scripts/debug_render.py 192.168.1.100 --dashboard system_monitor
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Add the custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.device import GeekMagicDevice, RenderedDashboardRequest
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.split import SplitVertical
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import WIDGET_CLASSES
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from custom_components.geekmagic.layouts.base import Layout


def _print_pro_picture_note(device: GeekMagicDevice) -> None:
    """Tell Pro users how to make the uploaded image visible."""
    if device.capabilities.requires_managed_album:
        print("For Pro devices, manually select the Picture app if the image is not visible.")


async def _display_debug_image(device: GeekMagicDevice, jpeg_data: bytes) -> None:
    """Upload the debug render through the same profile-backed display flow as HA."""
    await device.display_rendered_dashboard(
        RenderedDashboardRequest(
            image_data=jpeg_data,
            filename="debug.jpg",
            allow_destructive_album_management=False,
            try_menu_navigation=False,
        )
    )


def _widget(widget_type: str, slot: int, **kwargs) -> object:
    """Create a widget instance from its type string."""
    options = kwargs.pop("options", {})
    config = WidgetConfig(widget_type=widget_type, slot=slot, options=options, **kwargs)
    return WIDGET_CLASSES[widget_type](config)


def _sensor(entity_id: str, state: object, name: str, unit: str | None = None) -> EntityState:
    """Create a simulated sensor EntityState."""
    attributes: dict[str, object] = {"friendly_name": name}
    if unit:
        attributes["unit_of_measurement"] = unit
    return EntityState(entity_id=entity_id, state=str(state), attributes=attributes)


def _state(entity: EntityState | None = None, history: list[float] | None = None) -> WidgetState:
    """Create a WidgetState with the current time."""
    return WidgetState(entity=entity, history=history or [], now=datetime.now(tz=UTC))


def _render_layout(renderer: Renderer, layout: Layout, states: dict[int, WidgetState]) -> bytes:
    """Render a layout with per-slot states and encode as JPEG."""
    img, draw = renderer.create_canvas()
    layout.render(renderer, draw, states)
    return renderer.to_jpeg(img)


def render_system_monitor(renderer: Renderer) -> bytes:
    """Render a system monitor dashboard with live-ish data."""
    cpu = random.randint(15, 85)
    mem = random.randint(40, 90)
    disk = random.randint(30, 70)
    net_data = [float(random.randint(20, 100)) for _ in range(25)]

    layout = Grid2x2()
    layout.set_widget(0, _widget("gauge", 0, options={"style": "ring"}))
    layout.set_widget(1, _widget("gauge", 1, options={"style": "ring"}))
    layout.set_widget(2, _widget("gauge", 2, options={"style": "bar"}))
    layout.set_widget(3, _widget("chart", 3, label="Network"))

    states = {
        0: _state(_sensor("sensor.cpu", cpu, "CPU", "%")),
        1: _state(_sensor("sensor.mem", mem, "Memory", "%")),
        2: _state(_sensor("sensor.disk", disk, "Disk", "%")),
        3: _state(_sensor("sensor.net", net_data[-1], "Network", "MB/s"), history=net_data),
    }
    return _render_layout(renderer, layout, states)


def render_clock(renderer: Renderer) -> bytes:
    """Render a clock dashboard."""
    layout = SplitVertical(ratio=0.6)
    layout.set_widget(0, _widget("clock", 0, options={"show_seconds": True}))
    layout.set_widget(1, _widget("entity", 1, label="Sunny"))

    states = {
        0: _state(),
        1: _state(_sensor("sensor.outdoor_temp", 21, "Sunny", "°C")),
    }
    return _render_layout(renderer, layout, states)


def render_fitness(renderer: Renderer) -> bytes:
    """Render a fitness dashboard."""
    move = random.randint(60, 95)
    exercise = random.randint(40, 80)
    stand = random.randint(70, 100)
    steps = random.randint(5000, 12000)

    layout = Grid2x2()
    layout.set_widget(0, _widget("gauge", 0, options={"style": "ring"}))
    layout.set_widget(1, _widget("gauge", 1, options={"style": "ring"}))
    layout.set_widget(2, _widget("gauge", 2, options={"style": "ring"}))
    layout.set_widget(3, _widget("entity", 3, options={"icon": "walk"}))

    states = {
        0: _state(_sensor("sensor.move", move, "Move", "%")),
        1: _state(_sensor("sensor.exercise", exercise, "Exercise", "%")),
        2: _state(_sensor("sensor.stand", stand, "Stand", "%")),
        3: _state(_sensor("sensor.steps", steps, "Steps")),
    }
    return _render_layout(renderer, layout, states)


def render_server_stats(renderer: Renderer) -> bytes:
    """Render a server stats dashboard."""
    cpu = random.randint(20, 90)
    mem = random.randint(40, 85)
    disk = random.randint(30, 60)
    temp = random.randint(45, 75)
    cpu_history = [float(random.randint(20, 90)) for _ in range(25)]

    layout = HeroLayout(footer_slots=3)
    layout.set_widget(0, _widget("chart", 0, label="CPU"))
    layout.set_widget(1, _widget("gauge", 1, options={"style": "bar", "show_name": False}))
    layout.set_widget(2, _widget("gauge", 2, options={"style": "bar", "show_name": False}))
    layout.set_widget(3, _widget("entity", 3, options={"show_name": False}))

    states = {
        0: _state(_sensor("sensor.cpu", cpu, "CPU", "%"), history=cpu_history),
        1: _state(_sensor("sensor.mem", mem, "Memory", "%")),
        2: _state(_sensor("sensor.disk", disk, "Disk", "%")),
        3: _state(_sensor("sensor.temp", temp, "Temp", "°C")),
    }
    return _render_layout(renderer, layout, states)


def render_energy(renderer: Renderer) -> bytes:
    """Render an energy monitor dashboard."""
    current_power = random.uniform(0.5, 4.0)
    solar = random.uniform(2.0, 5.0)
    usage_data = [random.uniform(0.5, 4.0) for _ in range(30)]

    layout = SplitVertical(ratio=0.5)
    layout.set_widget(0, _widget("entity", 0, options={"icon": "lightning-bolt", "precision": 1}))
    layout.set_widget(1, _widget("chart", 1, label="Today"))

    states = {
        0: _state(_sensor("sensor.power", f"{current_power:.1f}", "Power", "kW")),
        1: _state(_sensor("sensor.solar", f"{solar:.1f}", "Solar", "kW"), history=usage_data),
    }
    return _render_layout(renderer, layout, states)


DASHBOARDS = {
    "system_monitor": ("System Monitor", render_system_monitor),
    "clock": ("Clock", render_clock),
    "fitness": ("Fitness", render_fitness),
    "server_stats": ("Server Stats", render_server_stats),
    "energy": ("Energy", render_energy),
}


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug render to GeekMagic device")
    parser.add_argument("device_ip", help="IP address of the GeekMagic device")
    parser.add_argument("--cycle", action="store_true", help="Cycle through all dashboards")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between updates")
    parser.add_argument(
        "--dashboard", choices=list(DASHBOARDS.keys()), help="Render a specific dashboard"
    )
    parser.add_argument("--list", action="store_true", help="List available dashboards")

    args = parser.parse_args()

    if args.list:
        print("Available dashboards:")
        for key, (name, _) in DASHBOARDS.items():
            print(f"  {key}: {name}")
        return

    renderer = Renderer()
    device = GeekMagicDevice(args.device_ip)

    print(f"Connecting to device at {args.device_ip}...")

    try:
        # Test connection
        if not await device.test_connection():
            print(f"Error: Could not connect to device at {args.device_ip}")
            return

        await device.detect_model()
        identity = device.model_name or device.model
        if device.firmware_version:
            identity = f"{identity} ({device.firmware_version})"
        print(f"Connected! Detected: {identity}")

        try:
            brightness = await device.get_brightness()
            print(f"Current brightness: {brightness}")
        except Exception as err:
            print(f"Brightness unavailable: {err}")

        try:
            state = await device.get_state()
            print(f"Current theme: {state.theme}, current image: {state.current_image}")
        except Exception as err:
            print(f"State unavailable: {err}")

        if args.dashboard:
            # Single dashboard
            name, render_func = DASHBOARDS[args.dashboard]
            print(f"Rendering {name}...")
            jpeg_data = render_func(renderer)
            print(f"Uploading ({len(jpeg_data)} bytes)...")
            await _display_debug_image(device, jpeg_data)
            _print_pro_picture_note(device)
            print("Done!")

        elif args.cycle:
            # Cycle through all dashboards
            print(f"Cycling through dashboards every {args.interval}s (Ctrl+C to stop)")
            dashboard_keys = list(DASHBOARDS.keys())
            idx = 0

            while True:
                key = dashboard_keys[idx % len(dashboard_keys)]
                name, render_func = DASHBOARDS[key]

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering {name}...")
                jpeg_data = render_func(renderer)
                await _display_debug_image(device, jpeg_data)
                print(f"  Uploaded {len(jpeg_data)} bytes")
                _print_pro_picture_note(device)

                idx += 1
                await asyncio.sleep(args.interval)

        else:
            # Default: render system monitor once
            print("Rendering System Monitor...")
            jpeg_data = render_system_monitor(renderer)
            print(f"Uploading ({len(jpeg_data)} bytes)...")
            await _display_debug_image(device, jpeg_data)
            _print_pro_picture_note(device)
            print("Done!")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        await device.close()


if __name__ == "__main__":
    asyncio.run(main())
