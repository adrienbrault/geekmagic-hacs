# GeekMagic Display for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

<p align="center">
  <img src="https://github.com/user-attachments/assets/09890b95-8a94-4df9-bf2f-6b9a6ac0d5e9" alt="GeekMagic Display running Home Assistant dashboard" width="400">
</p>

A Home Assistant custom integration for GeekMagic displays (SmallTV Pro, Ultra, and similar ESP8266/ESP32-based devices).

> **How it works:** This integration renders dashboard images directly in Home Assistant using Python/Pillow and pushes them to your GeekMagic device over HTTP. No flashing required - works with stock firmware.

---

### Disclaimers

> **Early Software:** This project is in active development. Expect bugs, breaking changes, and incomplete features. The API and configuration format may change between versions.

> **Vibe Coded:** This integration was largely vibe-coded with AI assistance. While functional, it may contain unconventional patterns or rough edges. Contributions and feedback welcome!

---

### Background & Credits

I have a **GeekMagic Ultra** with ESP8266, which has [limited possibilities for flashing with ESPHome](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029). Instead of fighting the hardware, this integration takes a different approach: render everything server-side and push images to the device.

Special thanks to:
- The [Home Assistant Community thread](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029) for documenting GeekMagic device capabilities
- **[Aydar (@aydarik)](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029/214)** for sharing the [bash script](https://gist.github.com/aydarik/e81edaf63041a85fb0325a1c8c2e4bac) that demonstrated how to push images to these devices - the core inspiration for this integration

---

## Dashboard Samples

<p align="center">
  <img src="samples/01_system_monitor.png" alt="System Monitor" width="120">
  <img src="samples/02_smart_home.png" alt="Smart Home" width="120">
  <img src="samples/03_weather.png" alt="Weather" width="120">
  <img src="samples/04_server_stats.png" alt="Server Stats" width="120">
</p>

<p align="center">
  <img src="samples/05_media_player.png" alt="Media Player" width="120">
  <img src="samples/06_energy_monitor.png" alt="Energy Monitor" width="120">
  <img src="samples/07_fitness.png" alt="Fitness Tracker" width="120">
  <img src="samples/08_clock_dashboard.png" alt="Clock Dashboard" width="120">
</p>

<p align="center">
  <img src="samples/09_network_monitor.png" alt="Network Monitor" width="120">
  <img src="samples/10_thermostat.png" alt="Thermostat" width="120">
  <img src="samples/11_batteries.png" alt="Batteries" width="120">
  <img src="samples/12_security.png" alt="Security" width="120">
</p>

## Binary Sensor States & Icons

Binary sensors display human-readable states and state-specific icons based on their `device_class`. Icons are sourced from Home Assistant's official icon definitions.

<p align="center">
  <img src="samples/16_binary_sensors.png" alt="Binary Sensor States" width="240">
  <img src="samples/17_binary_sensors_more.png" alt="More Binary Sensors" width="240">
</p>

## Domain State Icons

Entities like lights, switches, and fans show different icons based on their state (on/off).

<p align="center">
  <img src="samples/18_domain_icons.png" alt="Domain Icons" width="240">
</p>

## Widget Gallery

| Widget | 1x1 | 1x2 | 2x1 | 2x2 | 2x3 | 3x3 |
|--------|-----|-----|-----|-----|-----|-----|
| **Gauge (Bar)** | <img src="samples/widgets/gauge_bar_1x1.png"> | <img src="samples/widgets/gauge_bar_1x2.png"> | <img src="samples/widgets/gauge_bar_2x1.png"> | <img src="samples/widgets/gauge_bar_2x2.png"> | <img src="samples/widgets/gauge_bar_2x3.png"> | <img src="samples/widgets/gauge_bar_3x3.png"> |
| **Gauge (Ring)** | <img src="samples/widgets/gauge_ring_1x1.png"> | <img src="samples/widgets/gauge_ring_1x2.png"> | <img src="samples/widgets/gauge_ring_2x1.png"> | <img src="samples/widgets/gauge_ring_2x2.png"> | <img src="samples/widgets/gauge_ring_2x3.png"> | <img src="samples/widgets/gauge_ring_3x3.png"> |
| **Gauge (Arc)** | <img src="samples/widgets/gauge_arc_1x1.png"> | <img src="samples/widgets/gauge_arc_1x2.png"> | <img src="samples/widgets/gauge_arc_2x1.png"> | <img src="samples/widgets/gauge_arc_2x2.png"> | <img src="samples/widgets/gauge_arc_2x3.png"> | <img src="samples/widgets/gauge_arc_3x3.png"> |
| **Entity (Icon)** | <img src="samples/widgets/entity_icon_1x1.png"> | <img src="samples/widgets/entity_icon_1x2.png"> | <img src="samples/widgets/entity_icon_2x1.png"> | <img src="samples/widgets/entity_icon_2x2.png"> | <img src="samples/widgets/entity_icon_2x3.png"> | <img src="samples/widgets/entity_icon_3x3.png"> |
| **Entity (Plain)** | <img src="samples/widgets/entity_plain_1x1.png"> | <img src="samples/widgets/entity_plain_1x2.png"> | <img src="samples/widgets/entity_plain_2x1.png"> | <img src="samples/widgets/entity_plain_2x2.png"> | <img src="samples/widgets/entity_plain_2x3.png"> | <img src="samples/widgets/entity_plain_3x3.png"> |
| **Clock** | <img src="samples/widgets/clock_1x1.png"> | <img src="samples/widgets/clock_1x2.png"> | <img src="samples/widgets/clock_2x1.png"> | <img src="samples/widgets/clock_2x2.png"> | <img src="samples/widgets/clock_2x3.png"> | <img src="samples/widgets/clock_3x3.png"> |
| **Text** | <img src="samples/widgets/text_1x1.png"> | <img src="samples/widgets/text_1x2.png"> | <img src="samples/widgets/text_2x1.png"> | <img src="samples/widgets/text_2x2.png"> | <img src="samples/widgets/text_2x3.png"> | <img src="samples/widgets/text_3x3.png"> |
| **Progress** | <img src="samples/widgets/progress_1x1.png"> | <img src="samples/widgets/progress_1x2.png"> | <img src="samples/widgets/progress_2x1.png"> | <img src="samples/widgets/progress_2x2.png"> | <img src="samples/widgets/progress_2x3.png"> | <img src="samples/widgets/progress_3x3.png"> |
| **Weather** | <img src="samples/widgets/weather_1x1.png"> | <img src="samples/widgets/weather_1x2.png"> | <img src="samples/widgets/weather_2x1.png"> | <img src="samples/widgets/weather_2x2.png"> | <img src="samples/widgets/weather_2x3.png"> | <img src="samples/widgets/weather_3x3.png"> |
| **Status** | <img src="samples/widgets/status_1x1.png"> | <img src="samples/widgets/status_1x2.png"> | <img src="samples/widgets/status_2x1.png"> | <img src="samples/widgets/status_2x2.png"> | <img src="samples/widgets/status_2x3.png"> | <img src="samples/widgets/status_3x3.png"> |
| **Chart** | <img src="samples/widgets/chart_1x1.png"> | <img src="samples/widgets/chart_1x2.png"> | <img src="samples/widgets/chart_2x1.png"> | <img src="samples/widgets/chart_2x2.png"> | <img src="samples/widgets/chart_2x3.png"> | <img src="samples/widgets/chart_3x3.png"> |

## Layout Examples

### Fullscreen & Grid Layouts

<p align="center">
  <img src="samples/layouts/layout_fullscreen.png" alt="Fullscreen" width="200">
  <img src="samples/layouts/layout_grid_2x2.png" alt="Grid 2x2" width="200">
  <img src="samples/layouts/layout_grid_2x3.png" alt="Grid 2x3" width="200">
  <img src="samples/layouts/layout_grid_3x2.png" alt="Grid 3x2" width="200">
  <img src="samples/layouts/layout_grid_3x3.png" alt="Grid 3x3" width="200">
</p>

### Split Layouts

<p align="center">
  <img src="samples/layouts/layout_split_horizontal.png" alt="Split Horizontal" width="200">
  <img src="samples/layouts/layout_split_vertical.png" alt="Split Vertical" width="200">
  <img src="samples/layouts/layout_split_h_1_2.png" alt="Split 1:2" width="200">
  <img src="samples/layouts/layout_split_h_2_1.png" alt="Split 2:1" width="200">
</p>

### Column & Row Layouts

<p align="center">
  <img src="samples/layouts/layout_three_column.png" alt="Three Column" width="200">
  <img src="samples/layouts/layout_three_row.png" alt="Three Row" width="200">
</p>

### Hero Layouts

<p align="center">
  <img src="samples/layouts/layout_hero.png" alt="Hero" width="200">
  <img src="samples/layouts/layout_hero_simple.png" alt="Hero Simple" width="200">
  <img src="samples/layouts/layout_hero_corner_tl.png" alt="Hero TL" width="200">
  <img src="samples/layouts/layout_hero_corner_tr.png" alt="Hero TR" width="200">
  <img src="samples/layouts/layout_hero_corner_bl.png" alt="Hero BL" width="200">
  <img src="samples/layouts/layout_hero_corner_br.png" alt="Hero BR" width="200">
</p>

### Sidebar Layouts

<p align="center">
  <img src="samples/layouts/layout_sidebar_left.png" alt="Sidebar Left" width="200">
  <img src="samples/layouts/layout_sidebar_right.png" alt="Sidebar Right" width="200">
</p>

## Themes

Choose from **10 built-in themes** that go beyond just colors - affecting typography, spacing, shapes, and visual effects.

### Dark Themes

| Classic | Minimal | Neon | Retro | Soft |
|:-------:|:-------:|:----:|:-----:|:----:|
| <img src="samples/layouts/layout_theme_classic.png" alt="Classic" width="200"> | <img src="samples/layouts/layout_theme_minimal.png" alt="Minimal" width="200"> | <img src="samples/layouts/layout_theme_neon.png" alt="Neon" width="200"> | <img src="samples/layouts/layout_theme_retro.png" alt="Retro" width="200"> | <img src="samples/layouts/layout_theme_soft.png" alt="Soft" width="200"> |
| Balanced with rounded corners | Sharp, monochrome | Cyberpunk with glow | Terminal scanlines | Cozy, very rounded |

### Colored & Light Themes

| Ocean | Sunset | Forest | Light | Candy |
|:-----:|:------:|:------:|:-----:|:-----:|
| <img src="samples/layouts/layout_theme_ocean.png" alt="Ocean" width="200"> | <img src="samples/layouts/layout_theme_sunset.png" alt="Sunset" width="200"> | <img src="samples/layouts/layout_theme_forest.png" alt="Forest" width="200"> | <img src="samples/layouts/layout_theme_light.png" alt="Light" width="200"> | <img src="samples/layouts/layout_theme_candy.png" alt="Candy" width="200"> |
| Deep blue, nautical | Warm coral/orange | Natural earth tones | Clean white background | Playful pastels |

---

## Features

- **12 widget types**: Clock, entity, media, chart, text, gauge, progress, weather, status, camera, and more
- **19 layout options**: Fullscreen, grids, splits, hero variants, sidebars, and more
- **10 visual themes**: Classic, Minimal, Neon, Retro, Soft, Light, Ocean, Sunset, Forest, Candy
- **Visual configuration**: Custom sidebar panel with live preview
- **Global views**: Create views once, assign to multiple devices
- **Multi-screen support**: Assign multiple views per device with auto-cycling
- **Pure Python rendering**: Uses Pillow for image generation (no browser required)
- **Configurable refresh**: Updates every 5-300 seconds

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Custom repositories"
3. Add this repository URL
4. Install "GeekMagic Display"
5. Restart Home Assistant

### Manual

1. Copy `custom_components/geekmagic` to your Home Assistant's `custom_components` folder
2. Restart Home Assistant

## Configuration

### Adding a Device

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "GeekMagic"
4. Enter your device's IP address

### Using the GeekMagic Panel

After installation, a **GeekMagic** item appears in your sidebar.

#### Views Tab

Create and manage display views:

- **Create views** with the "+ Add View" button
- **Edit views** by clicking on them
- **Delete views** via the menu on each card

#### View Editor

The editor provides a live preview and widget configuration:

<p align="center">
  <img src="https://github.com/user-attachments/assets/e3420b9e-a325-49ea-8ab9-2133ae7f0a20" alt="GeekMagic View Editor" width="700">
</p>

- **Preview**: See real-time rendering as you configure
- **Layout**: Choose grid size (2x2, 2x3, 3x2, hero, split, etc.)
- **Theme**: Select from 10 visual themes
- **Widgets**: Each slot shows a position grid - click cells to swap widget positions
- **Entity picker**: Native Home Assistant entity selector with filtering

#### Devices Tab

Assign views to your GeekMagic devices:

- Check which views each device should display
- Devices automatically cycle through assigned views
- Drag to reorder the rotation sequence

#### Device Info Page

Each device exposes entities for brightness, refresh interval, mode selection, and status:

<p align="center">
  <img src="https://github.com/user-attachments/assets/ddbc7f2d-2e9a-4a22-8eb8-248f26e9adf4" alt="GeekMagic Device Info" width="700">
</p>

---

## Entities

Each GeekMagic device creates the following entities for control and monitoring:

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| `number.geekmagic_brightness` | Number | Display brightness (0-100%) |
| `number.geekmagic_refresh_interval` | Number | Update interval (5-300 seconds) |
| `select.geekmagic_mode` | Select | Device mode (Custom Views, Clock, Weather, System Info) |
| `select.geekmagic_current_view` | Select | Currently displayed view (when in Custom mode) |

### Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.geekmagic_status` | Sensor | Connection status with device attributes |
| `sensor.geekmagic_storage_used` | Sensor | Device storage usage percentage |
| `sensor.geekmagic_storage_free` | Sensor | Free storage in KB |

### Buttons

| Entity | Type | Description |
|--------|------|-------------|
| `button.geekmagic_refresh` | Button | Force immediate display refresh |
| `button.geekmagic_next_screen` | Button | Switch to next view in rotation |
| `button.geekmagic_previous_screen` | Button | Switch to previous view in rotation |

---

## Widget Types

| Type | Description |
|------|-------------|
| `gauge` | Bar, ring, or arc gauge (`style: bar/ring/arc`) |
| `entity` | Any HA entity value (with optional `icon`) |
| `clock` | Time and date |
| `text` | Static or dynamic text |
| `progress` | Goal tracking with progress bar |
| `weather` | Weather with forecast |
| `status` | Binary sensor indicator |
| `chart` | Sparkline from entity history |
| `camera` | Camera snapshot display |
| `media` | Now playing from media player |
| `multi_progress` | Multiple progress items |
| `status_list` | Multiple status indicators |

## Layout Types

| Layout | Slots | Description |
|--------|-------|-------------|
| `fullscreen` | 1 | Single widget fills entire display (no padding) |
| `grid_2x2` | 4 | 2x2 grid of equal widgets |
| `grid_2x3` | 6 | 2 rows, 3 columns |
| `grid_3x2` | 6 | 3 rows, 2 columns |
| `grid_3x3` | 9 | 3x3 grid of equal widgets |
| `split_horizontal` | 2 | Left/right side by side |
| `split_vertical` | 2 | Top/bottom stacked |
| `split_h_1_2` | 2 | Narrow left (1/3), wide right (2/3) |
| `split_h_2_1` | 2 | Wide left (2/3), narrow right (1/3) |
| `three_column` | 3 | 3 vertical columns |
| `three_row` | 3 | 3 horizontal rows |
| `hero` | 4 | Large hero + 3 footer widgets |
| `hero_simple` | 2 | Large hero + 1 footer widget |
| `hero_corner_tl` | 6 | 2x2 hero top-left + 4 small widgets |
| `hero_corner_tr` | 6 | 2x2 hero top-right + 4 small widgets |
| `hero_corner_bl` | 6 | 2x2 hero bottom-left + 4 small widgets |
| `hero_corner_br` | 6 | 2x2 hero bottom-right + 4 small widgets |
| `sidebar_left` | 4 | Wide left panel + 3 right rows |
| `sidebar_right` | 4 | 3 left rows + wide right panel |

---

## Device Compatibility

Tested with:
- GeekMagic SmallTV Ultra (240x240, ESP8266)

Should work with any GeekMagic device that supports the `/doUpload` HTTP API.

**Important:** This integration works with the **stock firmware** that ships with GeekMagic devices. No custom firmware or flashing required - just connect your device to your network and add the integration.

## Development

```bash
uv sync                              # Install dependencies
uv run pytest                        # Run tests
uv run ruff check .                  # Lint
uv run pre-commit run --all-files    # Run all checks
uv run python scripts/generate_samples.py  # Generate samples
```

## License

MIT
