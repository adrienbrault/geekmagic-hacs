# GeekMagic HACS Integration

Home Assistant custom integration for GeekMagic displays (SmallTV Pro and similar ESP8266-based devices).

## Development

Use `uv` for all Python operations:

```bash
uv sync              # Install dependencies
uv run pytest        # Run tests
uv run pytest -v     # Run tests with verbose output
uv run ruff check .  # Lint code
uv run ruff format . # Format code
```

## Project Structure

```
custom_components/geekmagic/
├── __init__.py       # Integration entry, services
├── config_flow.py    # Device setup + options flow
├── coordinator.py    # Data update coordinator
├── device.py         # HTTP API client for GeekMagic
├── renderer.py       # Pillow image generation
├── const.py          # Constants and config keys
├── widgets/          # Widget components
│   ├── base.py       # Widget base class
│   ├── clock.py      # Clock widget
│   ├── entity.py     # HA entity display
│   ├── media.py      # Media player widget
│   ├── chart.py      # Sparkline chart
│   └── text.py       # Static/dynamic text
├── layouts/          # Layout systems
│   ├── base.py       # Layout base class
│   ├── grid.py       # 2x2, 2x3, 3x3 grids
│   ├── hero.py       # Hero + footer layout
│   └── split.py      # Split panel layouts
├── manifest.json     # HACS metadata
├── services.yaml     # Service definitions
└── strings.json      # UI translations
```

## Key Concepts

### Rendering Pipeline
1. Coordinator triggers update on interval
2. Layout calculates widget rectangles (slots)
3. Each widget renders into its slot using Pillow
4. Image converted to JPEG and uploaded to device

### Widget Interface
```python
class Widget(ABC):
    def render(self, renderer, draw, rect, hass) -> None:
        """Draw widget in the given rectangle."""

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on."""
```

### Layout Interface
```python
class Layout(ABC):
    def _calculate_slots(self) -> None:
        """Calculate slot rectangles."""

    def render(self, renderer, draw, hass) -> None:
        """Render all widgets in their slots."""
```

## Device API

GeekMagic devices use a simple HTTP API:

```
POST /doUpload?dir=/image/   # Upload image (multipart form)
GET  /set?img=/image/{file}  # Display image
GET  /set?theme=3            # Set custom image mode
GET  /set?brt={0-100}        # Set brightness
GET  /app.json               # Get device state
```

## Display Constraints

- Resolution: 240x240 pixels
- Physical size: ~4cm diagonal
- Minimum font size: 10-12px for readability
- Use high contrast colors (light on dark)
- JPEG upload is faster than PNG (~2.5s vs ~5.8s)

## Testing

Tests are organized by component:
- `tests/test_device.py` - HTTP client tests
- `tests/test_renderer.py` - Pillow rendering tests
- `tests/widgets/test_widgets.py` - Widget tests
- `tests/layouts/test_layouts.py` - Layout tests

All tests use mocks and don't require a real device or Home Assistant instance.

## Adding New Widgets

1. Create `custom_components/geekmagic/widgets/mywidget.py`
2. Extend `Widget` base class
3. Implement `render()` and optionally `get_entities()`
4. Register in `widgets/__init__.py`
5. Add to `WIDGET_CLASSES` in `coordinator.py`
6. Add tests in `tests/widgets/`

## Adding New Layouts

1. Create layout class extending `Layout`
2. Implement `_calculate_slots()` to define slot rectangles
3. Register in `layouts/__init__.py`
4. Add to `LAYOUT_CLASSES` in `coordinator.py`
5. Add to config flow options
