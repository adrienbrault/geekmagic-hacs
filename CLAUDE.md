# GeekMagic HACS Integration

Home Assistant custom integration for GeekMagic displays (SmallTV Pro and similar ESP8266-based devices).

## Development

Use `uv` for all Python operations:

```bash
uv sync                       # Install dependencies
uv run pytest                 # Run tests
uv run pytest -v              # Run tests with verbose output
uv run ruff check .           # Lint code
uv run ruff format .          # Format code
uv run ty check               # Type check
uv run pre-commit run --all   # Run all pre-commit hooks
```

## Git Workflow

Follow **Conventional Commits** and create **atomic commits** as you work:

### Commit Types
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring (no functional change)
- `docs:` Documentation only
- `test:` Adding/updating tests
- `chore:` Maintenance (deps, config, tooling)
- `style:` Formatting, whitespace (no code change)

### Atomic Commits
Create small, focused commits that each represent a single logical change:

1. **After implementing a feature** → commit the feature
2. **After fixing a bug** → commit the fix
3. **After adding tests** → commit the tests
4. **After refactoring** → commit the refactor

**Always run pre-commit before committing**: `uv run pre-commit run --all`

This validates tests, linting, formatting, and type checking in one command.

### Examples
```bash
git commit -m "feat: add clock widget with timezone support"
git commit -m "fix: handle missing entity gracefully in EntityWidget"
git commit -m "test: add unit tests for sparkline rendering"
git commit -m "refactor: extract color parsing into helper function"
git commit -m "chore: add ty type checker and pre-commit hooks"
```

## Release Process

HACS detects new versions via GitHub releases. The user creates releases in the GitHub UI (with auto-generated notes); Claude prepares the version bump.

### When the user asks for a version bump (e.g. "bump to 1.0.1", "release a new patch")

1. Determine the new version using semver:
   - **Patch** (`1.0.0 → 1.0.1`): bug fixes only
   - **Minor** (`1.0.0 → 1.1.0`): new features, backward-compatible
   - **Major** (`1.0.0 → 2.0.0`): breaking changes
2. Update `version` in `custom_components/geekmagic/manifest.json`
3. Commit on `main` (or a `chore/bump-X.Y.Z` branch if a PR is preferred):
   ```
   chore: bump version to X.Y.Z
   ```
4. Push, then tell the user to create the release in GitHub UI:
   - Releases → "Draft a new release"
   - Tag: `vX.Y.Z` (matches `manifest.json`)
   - Target: the bump commit on `main`
   - Click "Generate release notes" → Publish

### Critical rules
- **Tag must match `manifest.json` version exactly** (HA core reads `manifest.json` and a mismatch breaks update detection)
- **Tag the bump commit, not an earlier one** — otherwise the tagged tree still has the old version
- Tag format: `vX.Y.Z` (with leading `v`)
- Never tag or create the release yourself — the user does that in GitHub UI

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
│   ├── helpers.py    # Widget helper functions
│   └── text.py       # Static/dynamic text
├── layouts/          # Layout systems
│   ├── base.py       # Layout base class
│   ├── grid.py       # 2x2, 2x3, 3x3 grids
│   ├── hero.py       # Hero + footer layout
│   └── split.py      # Split panel layouts
├── entities/         # Entity platform implementations
│   ├── entity.py     # Base GeekMagicEntity class
│   ├── number.py     # Number entities (brightness, etc.)
│   ├── select.py     # Select entities (layout, widget type)
│   ├── switch.py     # Switch entities (boolean options)
│   ├── text.py       # Text entities (names, labels)
│   ├── button.py     # Button entities (refresh, nav)
│   └── sensor.py     # Sensor entities (status, dividers)
├── number.py         # Re-export for HA platform discovery
├── select.py         # Re-export for HA platform discovery
├── switch.py         # Re-export for HA platform discovery
├── text.py           # Re-export for HA platform discovery
├── button.py         # Re-export for HA platform discovery
├── sensor.py         # Re-export for HA platform discovery
├── manifest.json     # HACS metadata
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
    def render(self, ctx: RenderContext, hass) -> None:
        """Draw widget using the render context (local coordinates)."""

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

## Font Sizing System

Fonts are automatically scaled based on container height. Two naming systems are supported:

### Semantic Sizes (Preferred)

Use these for new widgets - they scale proportionally to container height:

| Size | Ratio | Use Case |
|------|-------|----------|
| `primary` | 35% | Main value (clock time, large number) |
| `secondary` | 20% | Supporting info (date, unit) |
| `tertiary` | 12% | Labels, captions |

```python
# Get font with semantic size
font = ctx.get_font("primary", bold=True)
font = ctx.get_font("secondary")
font = ctx.get_font("tertiary", adjust=-1)  # Slightly smaller
```

### Auto-Fit Text

For text that should fill available space (like clock displays):

```python
# Get largest font that fits within bounds
font = ctx.fit_text("12:45", max_width=ctx.width * 0.95)
font = ctx.fit_text("Hello", max_width=100, max_height=50, bold=True)
```

### Relative Adjustments

Fine-tune sizes with `adjust` parameter (-2 to +2, each step is ~15%):

```python
font = ctx.get_font("secondary", adjust=+1)  # 15% larger
font = ctx.get_font("primary", adjust=-1)    # 15% smaller
```

### Legacy Sizes

Still supported for backward compatibility:

| Size Name | Use Case |
|-----------|----------|
| `tiny` | Small labels |
| `small` | Labels, status |
| `regular` | Standard text |
| `medium` | Emphasized values |
| `large` | Primary values |
| `xlarge` | Hero values |
| `huge` | Maximum emphasis |

**Best practices:**
- Prefer semantic sizes (`primary`, `secondary`, `tertiary`) for new code
- Use `ctx.fit_text()` when text should fill available space
- Add `bold=True` for values that need emphasis
- Never specify pixel sizes directly

## Testing

Tests are organized by component:
- `tests/test_device.py` - HTTP client tests
- `tests/test_renderer.py` - Pillow rendering tests
- `tests/test_config_flow.py` - Config flow and options flow tests
- `tests/test_integration.py` - Integration setup/teardown tests
- `tests/widgets/test_widgets.py` - Widget tests
- `tests/layouts/test_layouts.py` - Layout tests

All tests use mocks and don't require a real device or Home Assistant instance.

### Home Assistant Testing Best Practices

Uses `pytest-homeassistant-custom-component` for HA-specific fixtures. See:
- https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
- https://developers.home-assistant.io/docs/development_testing/

**Available fixtures**: `hass`, `aioclient_mock`, `MockConfigEntry`, etc.

**Testing principles**:
- Use core interfaces (`hass.states`, `hass.services`) instead of integration details
- Mock external dependencies (`aiohttp`, devices)
- Add regression tests when fixing bugs
- Run `pytest` and `pre-commit` before commits

## Adding New Widgets

1. Create `custom_components/geekmagic/widgets/mywidget.py`
2. Extend `Widget` base class
3. Implement `render()` and optionally `get_entities()`
4. Register in `widgets/__init__.py`
5. Add to `WIDGET_CLASSES` in `coordinator.py`
6. Add tests in `tests/widgets/`

### Widget Helper Functions

Use helper functions from `widgets/helpers.py` for common operations:

```python
from ..widgets.helpers import (
    truncate_text,       # Truncate long text with ellipsis
    extract_numeric,     # Get float from entity state
    resolve_label,       # Get label from config or friendly_name
    calculate_percent,   # Calculate percentage in range
    is_entity_on,        # Check binary state
    get_unit,            # Get unit of measurement
)
```

### Layout Helper Functions

Use `widgets/layout_helpers.py` for common rendering patterns:

```python
from ..widgets.layout_helpers import (
    layout_icon_label_value,   # [Icon] [Label] ... [Value]
    layout_centered_value,     # Centered value with label below
    layout_bar_with_label,     # Progress bar with label/value above
    layout_list_rows,          # Calculate row positions for lists
    draw_title,                # Draw title at top
)
```

## Adding New Layouts

When adding a new layout, update these files:

### 1. Backend

- `layouts/<name>.py` - Create layout class extending `Layout`
- `layouts/__init__.py` - Import and export the new class
- `const.py` - Add `LAYOUT_<NAME>` constant and add to `LAYOUT_SLOT_COUNTS`
- `coordinator.py` - Add to `LAYOUT_CLASSES` dict

### 2. Frontend

- `frontend/src/geekmagic-panel.ts`:
  - Add entry to `layoutConfig` object with CSS class and cell count
  - Add CSS grid styles for the layout icon visualization in the `<style>` section
- Run `npm run build` in `frontend/` directory to rebuild

### 3. Documentation & Samples

- `scripts/generate_samples.py` - Add layout to `generate_layout_samples()`
- Run `uv run python scripts/generate_samples.py` to generate images
- `README.md` - Add to "Layout Examples" section and "Layout Types" table

### 4. Tests

- `tests/layouts/test_layouts.py` - Add test class for the new layout

## README Image Conventions

When embedding sample/screenshot images of device renders (240x240 PNGs from `samples/`) in `README.md`:

- **Outside tables**: always use `width="200"` for consistency across Dashboard Samples, Binary Sensor States, Domain Icons, Layout Examples, etc.
- **Inside tables**: omit the `width` attribute — let the table column dictate sizing.
- UI screenshots (panel editor, device info pages) and the hero device photo are not "samples" and keep their own widths.

## Home Assistant Platform Discovery

**IMPORTANT**: Home Assistant discovers entity platforms by looking for modules at `custom_components.<domain>.<platform>`. For example, `Platform.NUMBER` looks for `custom_components.geekmagic.number`.

Entity implementations live in `entities/` subfolder for organization, but **stub modules must exist at the root level** that re-export `async_setup_entry`:

```python
# custom_components/geekmagic/number.py (stub for HA discovery)
"""Number platform - re-exports from entities submodule."""
from .entities.number import async_setup_entry
__all__ = ["async_setup_entry"]
```

### When Adding New Entity Platforms

1. Create implementation in `entities/<platform>.py`
2. Create stub at `custom_components/geekmagic/<platform>.py` that re-exports `async_setup_entry`
3. Add `Platform.<PLATFORM>` to `PLATFORMS` list in `__init__.py`

### Common Mistake to Avoid

Moving entity files to a subfolder without creating re-export stubs will cause:
```
ModuleNotFoundError: No module named 'custom_components.geekmagic.<platform>'
```

The fix is to create stub modules that re-export from the subfolder.

## Asyncio and Blocking Operations

Home Assistant runs on asyncio. Blocking operations prevent the event loop from executing other tasks and must be handled properly.

### Blocking Operations to Avoid in Async Code
- **Disk I/O**: `open()`, `glob.glob()`, `os.walk()`, `os.listdir()`, `pathlib` read/write
- **Network I/O**: urllib operations (use `aiohttp` instead)
- **Heavy computation**: CPU-intensive tasks like image rendering
- **Sleep**: Use `asyncio.sleep()` instead of `time.sleep()`

### How to Offload Blocking Work
```python
# In Home Assistant integration code:
result = await hass.async_add_executor_job(blocking_function, arg1, arg2)

# With keyword arguments:
from functools import partial
result = await hass.async_add_executor_job(
    partial(blocking_function, kwarg1=value1), arg1
)
```

### This Integration's Blocking Operations
- **Image rendering** (Pillow): CPU-intensive, runs in executor
- **JPEG/PNG encoding**: CPU-intensive, runs in executor
- **HTTP upload to device**: Uses aiohttp (async-native)

See: https://developers.home-assistant.io/docs/asyncio_blocking_operations/

## Frontend Panel

The integration includes a custom panel for configuring displays via the HA sidebar.

### Building the Frontend

After making changes to the frontend source in `custom_components/geekmagic/frontend/`:

```bash
cd custom_components/geekmagic/frontend
npm install    # First time only
npm run build  # Build production bundle
```

**Important**: The built `dist/` directory must be committed to git. Users install via HACS which clones the repo directly - there's no build step during installation.

### Cache Busting

The panel uses content-hash based cache busting. A SHA256 hash of the JS file is appended to the URL (via `?h={hash}` query parameter). When the file content changes, the hash changes, and browsers automatically fetch the new version.

### After Frontend Changes

1. Make changes in `frontend/src/`
2. Run `npm run build` to regenerate `dist/`
3. Commit both source and dist changes
