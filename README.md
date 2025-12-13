# GeekMagic Display for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration for GeekMagic displays (SmallTV Pro and similar ESP8266-based devices).

## Screenshots

<p align="center">
  <img src="samples/01_system_monitor.png" alt="System Monitor">
  <img src="samples/02_smart_home.png" alt="Smart Home">
  <img src="samples/04_server_stats.png" alt="Server Stats">
  <img src="samples/07_fitness.png" alt="Fitness Tracker">
</p>

<p align="center">
  <img src="samples/06_energy_monitor.png" alt="Energy Monitor">
  <img src="samples/08_clock_dashboard.png" alt="Clock Dashboard">
  <img src="samples/09_network_monitor.png" alt="Network Monitor">
  <img src="samples/05_media_player.png" alt="Media Player">
</p>

## Features

- **Dashboard widgets**: Clock, entity values, media player, charts, and text
- **Multiple layouts**: 2x2 grid, 2x3 grid, hero layout, split panels
- **Pure Python rendering**: Uses Pillow for image generation (no browser required)
- **Configurable refresh**: Updates every 5-300 seconds
- **Easy setup**: Add device by IP address through the UI

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

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "GeekMagic"
4. Enter your device's IP address

## Widget Types

| Widget | Description |
|--------|-------------|
| `clock` | Current time and date |
| `entity` | Any Home Assistant entity value |
| `media` | Now playing information from a media player |
| `chart` | Sparkline chart from entity history |
| `text` | Static or dynamic text |

## Layouts

| Layout | Description |
|--------|-------------|
| `grid_2x2` | 2x2 grid (4 widgets) |
| `grid_2x3` | 2x3 grid (6 widgets) |
| `hero` | Large main widget + 3 footer widgets |
| `split` | Two equal panels |

## Services

| Service | Description |
|---------|-------------|
| `geekmagic.refresh` | Force immediate display update |
| `geekmagic.brightness` | Set display brightness (0-100) |

## Device Compatibility

Tested with:
- GeekMagic SmallTV Pro (240x240, ESP8266)

Should work with any GeekMagic device that supports the `/doUpload` HTTP API.

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint and type check
uv run ruff check .
uv run ty check

# Run all checks (pre-commit)
uv run pre-commit run --all-files

# Generate sample images
uv run python scripts/generate_samples.py
```

## License

MIT
