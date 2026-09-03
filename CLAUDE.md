# GeekMagic HACS Integration

Home Assistant custom integration for GeekMagic displays (SmallTV Pro and similar ESP8266-based devices).

## Development

Use `uv` for all Python operations:

```bash
uv sync                       # Install dependencies (blitz-py comes as a
                              # prebuilt wheel from PyPI)
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
├── htmldoc.py        # Blitz document assembly, fluid kit, SVG helpers
├── renderer.py       # Canvas compositing + JPEG/PNG encoding
├── const.py          # Constants and config keys
├── fonts/            # Embedded fonts (Nunito, DejaVu, MDI)
├── widgets/          # Widget components (HTML fragments)
│   ├── base.py       # Widget base class (render_html contract)
│   ├── _card.py      # card_html/chip_html three-band primitives
│   ├── theme.py      # Themes: palette + CSS (chrome/backdrop/overlay)
│   ├── clock.py      # Clock widget
│   ├── entity.py     # HA entity display
│   ├── media.py      # Media player widget
│   ├── chart.py      # Sparkline chart (SVG)
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

### Rendering Pipeline (Blitz engine)

All drawing happens in the **Blitz HTML/CSS engine** via the `blitz-py`
package (Stylo CSS + Taffy layout + Parley text + Vello raster — no
browser). Pillow only composites passes and encodes JPEG/PNG.

1. Coordinator triggers update on interval
2. Layout calculates widget rectangles (slots) — pure geometry
3. **One `render_layers` call** composites the whole screen
   engine-side: the theme backdrop layer (`theme.backdrop_css`), one
   layer per widget cell (each widget's `render_html` fragment wrapped
   by `htmldoc.build_cell_document` — theme CSS variables + fluid kit +
   `theme.chrome_css`), and the optional `theme.overlay_css` layer
   (scanlines, vignettes) on top. Each cell layer keeps its own CSS
   viewport (`vmin`/`vw` and `@media` respond to the CELL size) and is
   CLIPPED to its rect by the engine. Themes with `glow_effect` (neon)
   paint each cell once blurred beneath its sharp pass (per-layer
   `blur`/`opacity`).
4. Image converted to JPEG and uploaded to device. Fonts are
   registered process-wide once, under a lock (`register_fonts`,
   htmldoc's `font_param()`) — no per-call font bytes. If
   registration ever fails, the same embedded font bytes ride every
   measurement call AND every render layer, so measurement and
   rendering can never resolve different fonts (that divergence is how
   fitted text overflows the panel).

`manifest.json` installs blitz-py >= 0.5.0 (a pure engine bump over
0.4.2: Stylo 0.20 / Taffy 0.13 / parley 0.11.1 / vello_cpu 0.16, crash
and layout robustness fixes, no Python API change; renders shift only
at the glyph-antialiasing level). The pipeline's functional floor stays
0.4.2 (`htmldoc._ENGINE_FLOOR`) — a working older install keeps
rendering rather than getting the install-hint screen, which only an
engine below the floor (or missing) paints. The pre-0.4.2 fallback
paths (per-document renders + Pillow premultiplied compositing) were
removed — do not reintroduce version-gated pipelines.

**Animated path (opt-in):** when the device's Animations switch is on
and a placed widget returns ``is_animated() == True``, the coordinator
calls ``layout.render_animation`` instead: each frame is ONE
``render_layers`` call with the frame's clock on animated layers (and
their glow underlays). Frames are encoded with ``Renderer.to_gif``
(1.6s @ 10fps, palette quantized without dithering) and
``dashboard.gif`` is uploaded in place of the JPEG.

blitz-py capabilities adopted so far: ``measure_text`` (0.3.0) and
``ellipsize`` (0.4.0) drive ``widgets/_textfit.py`` — engine-native
shaping over the embedded fonts, including the system fallback for
CJK; ``register_fonts`` (0.4.0) makes fonts process-wide;
``render_layers`` (0.4.0) composites the screen engine-side. Still
available but not yet adopted: ``fit_font_size`` / ``line_clamp`` /
``wrap_balanced`` (the Python fitters in ``_cardfit``/``media`` carry
extra semantics — suffix reserve, identity rules — that need mapping
first), ``Template.get_box``/``boxes()`` (could replace the CSS-math
mirrors like ``label_px``), the ``Template`` mutate-and-re-render fast
path, and native ``render_layers_jpeg`` encode (encoding stays in
``renderer.py`` while supersample-then-Lanczos remains the quality
baseline). The true fix for truncation remains ``text-overflow:
ellipsis`` in blitz-dom, tracked in the blitz-py repo's
docs/UPSTREAM.md.

`blitz-py` is REQUIRED for rendering — it's in `manifest.json`
requirements (PyPI wheels for Linux glibc/musl x86_64 + aarch64, macOS,
Windows), so HA installs it automatically. Without it the display shows
an install-hint error screen.

Blitz engine gotchas (verified on 0.4.2, re-verified on 0.5.0 — the
engine bump fixed none of these, keep every workaround):
- `var(--x)` does NOT resolve inside SVG paint attributes — pass
  concrete colors (`css_rgb(theme.x)`) to the SVG helpers.
- `text-overflow: ellipsis` paints no "…" (the engine clips the text
  but draws no mark), and `overflow: hidden` cuts glyphs mid-stroke — on
  tight line-heights (`.t-hero`'s 0.85) it also crops
  ascenders/descenders, and `overflow-x` clips BOTH axes. So CSS can
  contain overflow but never resolve it nicely: keep truncating long
  strings in Python (`helpers.truncate_text`, or the measured
  `_textfit` metrics for design-critical text).
- All Python-side fitting is open-loop (predict, then draw) and funnels
  through `_textfit._ref_width`, which sanitizes degenerate engine
  measurements (NaN/<= 0 fall back to a conservative estimate). A NaN
  that leaks into `fit_hero` disables the width bound AND truncation
  (every comparison is False) and paints the value at the height cap
  across the bezel — the "massive text" field bug. Keep that choke
  point intact.
- Inline `style="display: flex"` beats the kit's `.hide-*` media rules —
  put hide classes on a wrapper div without inline display.
- Inline `<svg>` is sized from its viewBox ASPECT RATIO, not from
  `height:100%` against a flex parent — measure the plot box in Python
  and pass a matching `aspect`/viewBox.
- Percentage padding resolves against the cell WIDTH on both axes —
  use px padding when vertical space is tight.
- `<style>` blocks inside a widget fragment work, including media
  queries — a clean lever for widget-scoped responsive rules. But an
  element carrying both `.hide-*` and your own breakpoint loses to the
  kit's `display:none !important`; drop the `.hide-*` class when
  self-managing visibility.
- Blitz paints non-positioned subtrees BEFORE absolutely-positioned
  siblings. A `.hide-*` wrapper around overlay text puts it under the
  scrim unless the wrapper itself is `position:absolute; inset:0` (and
  it must fill the cell — absolute boxes resolve against the parent, so
  a zero-height wrapper collapses the overlay).
- Fixed-height flex children shrink when the column overflows — give
  bars/tracks `flex: none` or they collapse to hairlines.
- `white-space: normal` wrapping is not clipped by `.cell`'s
  percentage padding — engine-wrapped text bleeds into the margin.
  Emit one block div per line (see `_cardfit`).
- Text measured for fitting must use the theme's real face and case —
  `widgets/_textfit.py` (`metrics_for(theme)`) is the canonical
  measurer; `_cardfit.py` builds card geometry on top of it.
- No container queries, no `background-clip: text`, no `text-shadow`,
  no `filter`. Gradients (linear/radial/conic), `box-shadow`, borders,
  `object-fit`, SVG (incl. `linearGradient`, bezier paths, `stroke-dasharray`),
  and CSS math (`clamp`/`min`/nested) all work.

### Widget Interface
```python
class Widget(ABC):
    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Return an HTML fragment rasterized at the cell size."""

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on."""
```

`CellContext` (from `htmldoc.py`) carries `width`, `height`,
`slot_index`, `theme`, plus `accent()` (slot-cycled theme accent as a
CSS color) and `is_compact`.

### Layout Interface
```python
class Layout(ABC):
    def _calculate_slots(self) -> None:
        """Calculate slot rectangles (pure geometry)."""

    def render(self, renderer, draw, widget_states) -> None:
        """Composite backdrop + widget cells + overlay onto the canvas."""
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

## Design System (watchOS-inspired) — rules for widget authors

The default theme (`watchos`) is modelled on Apple's watchOS HIG: true-black
background, system colours, opacity-based text hierarchy, tinted Activity-ring
gauges, no card chrome. `standby` is the same system on translucent white
cards (iOS StandBy / Smart Stack); `night` is StandBy's bedside mode, one
warm red ramp on black — a **monochrome** theme (`Theme.monochrome`), so the
layout strips per-widget colours (`config.color`, `on_color`/`off_color`,
thresholds, item colours) before rendering. **Every widget should follow these rules so themes
stay consistent.** When in doubt, look at how Entity / Clock / BarGauge
handle the same thing — they're the canonical references.

### The viewing distance rule (read this first)

The panel is ~27mm wide and is read from **0.6 to 1 m** away — a
nightstand, a desk edge, a shelf. At 1 m a 12px caption subtends about
3 arcminutes, well under comfortable reading; a 40px value, a 20px tinted
icon, and a colour fill are what actually register. So the design is
modelled on Apple's **StandBy** and Smart Stack widgets, not on a
dashboard:

- **The value is the widget.** Every cell spends its height on the hero.
- **The icon carries identity and state.** A tinted glyph reads from a
  metre away where a word does not; an entity that is off/closed/away
  renders its icon in `var(--muted)` (`entity._MUTED_STATES`).
- **Captions are support, not structure.** Secondary tone, 10-18px, one
  line, shrink-then-truncate (`_cardfit.fit_caption_sized`).
- **Colour is restrained.** One accent per cell, the theme's rotation
  across cells, semantic tints only where colour IS the meaning.
- **Edge to edge.** Themes keep a 2-3px outer margin and an 8px gap
  between widgets; the gap does the separating.

### Card anatomy (entity / gauge / progress / clock / text)

One shared **header** (`_card.header_html`) and one **hero**:

```
┌──────────────┐   ┌──────────────┐
│  ◉ CAPTION   │   │      ◉       │   header: tinted icon + caps caption,
│              │   │   CAPTION    │   inline — or STACKED in narrow, tall
│    23.5°C    │   │    23.5°C    │   cells (`header_stacks(ctx)`)
└──────────────┘   └──────────────┘
```

- Inline vs stacked is decided from **cell geometry only**
  (`_card.header_stacks`), never from the content, so every cell of a
  grid carries the same header shape.
- **The glyph is big.** 2.3x the caption inline, 3x stacked
  (`HEADER_ICON_EM` / `STACK_ICON_EM`), floored at a share of the cell's
  short side and capped at 24% of the cell height so it never costs the
  hero. When the caption would truncate beside it, the glyph gives up
  size first (1.5x), then the caption shortens by word.
- Header and hero are centred as one block with a gap that scales with
  the cell (`card_html(stack_gap_px=…)`); three-band cards (with a chip
  strip) keep the kit's `space-evenly`.
- **Sibling harmony.** Widgets report `hero_hint(ctx, state) -> (kind,
  px)`; `Layout._hero_caps` caps equal-sized cells whose heroes are of
  the same kind ("num" / "word") to the smallest fitted size, floored at
  half a cell's own size. A grid of readings shares one type size; a row
  of "On / Off / Heat" shares another. Read the cap from
  `ctx.extra["hero_px_cap"]` in any widget that fits a hero.

### Goals

1. **Information density first.** A 240×240 cell is tiny. Use every pixel —
   `justify="space-evenly"` to spread content top-to-bottom (equal gaps
   before/between/after each band reads more balanced than pinning the
   first/last items flush to the cell edges). Never leave the bottom half
   of a cell empty if there's data to show. Three-band layout (caption /
   hero / supporting strip) is the default for cells ≥100×100.
2. **Hierarchy via size + weight + colour.** A glance must surface the
   primary metric instantly: bold + large for the hero, secondary for
   supporting data, tertiary for captions. Don't make everything the same
   size.
3. **Theme consistency.** A user moving between widgets in the same theme
   should never see an unexplained colour shift. Colour comes from the
   theme, not from the widget.
4. **Adapt to cell shape.** Pick layout from `(width, height)` at render
   time — a hero ring should spread across a fullscreen cell but stay tight
   in a 3×3 grid; a vertical bar should stack everything when the cell is
   very narrow.

### Colour rules — pick by intent, not by RGB

Widgets MUST use **theme CSS variables** in markup, never hardcoded hex
colors. The variables resolve to the active theme's palette when the
cell document is built.

Available CSS variables (resolve to `theme.<role>`):

| CSS variable            | Use for                                              |
|-------------------------|------------------------------------------------------|
| `var(--text-primary)`   | Default for hero values (white-ish on dark themes)   |
| `var(--text-secondary)` | Supporting info (dates, units, "Sunny" condition)    |
| `var(--text-tertiary)`  | Caps captions, very-low-priority text                |
| `var(--primary)`        | Brand accent — fallback for chart / progress         |
| `var(--secondary)`      | Night, lightning, less-prominent accents             |
| `var(--success)`        | ON / connected / wind                                |
| `var(--warning)`        | Sunny / hot temp / heating / caution                 |
| `var(--error)`          | Problems: disconnected / extreme / alarm                  |
| `var(--info)`           | Cool / cold / water / rain / cooling / humidity      |
| `var(--muted)`          | Off / closed / away / idle / fog / disabled                            |

Also: `var(--bg)`, `var(--surface)`, `var(--surface-variant)`,
`var(--border)`, `var(--accent-0..N)`, `var(--radius)`. For the
slot-cycled accent use `ctx.accent()`. Inside **SVG paint attributes**
`var()` does not resolve — pass concrete colors via
`css_rgb(ctx.theme.success)` etc.

**Rule of thumb for hero value colour:**

- Default: no explicit color (body text is `var(--text-primary)`). Use
  this for entity value, clock time, weather temp, climate temp,
  multi-progress hero.
- Use a role tint **only** when one of these narrow exceptions applies:
  1. **Gauge family** (Bar/Ring/Arc) where the value matches the gauge's
     own accent — value + fill read as one visual unit (Apple Activity-ring
     style). E.g. ring `73%` in the ring's tint.
  2. **Status state** where the colour IS the meaning — `ON` in success
     green, `OFF` in the muted tone (red is for problems the user chose
     to paint red, never the default off state).
  3. **Mode chip** where the tint reinforces an explicit mode label
     (climate `HEATING` chip in warning).

**The icon, ring fill, bar fill, and dot indicators carry the semantic
tint.** That's where the colour lives.

### Don't

- Don't hardcode `SYSTEM_*` colors or hex literals in widget code — the
  regression test `tests/test_watchos_design_system.py` guards this.
  (Neutral `rgba(255,255,255,0.x)` tracks/overlays are the exception.)
- Don't `import` from `widgets/theme.py` for colour values in widgets.
- Don't tint a hero value just because it "looks nice" — follow the rule
  above. If you're tempted, the icon should probably be tinted instead.
- Don't put `style="display: flex"` inline on an element that carries a
  `.hide-*` class — inline styles defeat the media-query hide. Wrap it.
- Don't rely on `text-overflow: ellipsis` or `overflow: hidden` for
  text — the engine clips without painting "…" and crops glyph
  ascenders/descenders on tight line-heights. Truncate long strings in
  Python (`helpers.truncate_text`).
- Don't spread two bands with `space-evenly` — a header and a hero are
  one block, centred with a scaled gap (`card_html(stack_gap_px=…)`).
  Three or more bands keep `space-evenly`; tall columns group their
  bands (see progress) rather than fling them to the cell's ends.

### Do

- Read `tests/test_watchos_design_system.py` before adding a widget — it
  documents the contract.
- Use `card_html()` from `widgets/_card.py` for the standard
  caption/hero/chips card — consistency for free.
- Tint gauge tracks with `css_rgba(accent, theme.tint_track_opacity)`
  when `theme.tint_track` is set (see gauge.py).
- Attach `.hide-short` / `.hide-small` to optional bands so cells
  degrade gracefully — that's the fluid system.

## Typography — the fluid kit

Type is CSS-driven. The fluid kit (injected into every cell document by
`htmldoc.py`) scales text with the CELL via `clamp()` + `vmin`/`vw`
(width-capped so ~5-char values never overflow), and sheds optional
bands via media queries:

| Class | Role |
|-------|------|
| `.t-hero` | Primary value — as big as the cell allows (weight 700, -0.02em) |
| `.t-value` | Secondary emphasized value |
| `.t-unit` | Unit suffix (secondary color) |
| `.t-label` | Caps caption (secondary color, 0.05em tracking) |
| `.t-date` | Plain secondary line (the clock's date) |
| `.caption-row` / `.card-head` | Inline / stacked header (see `_card.header_html`) |
| `.icon` + `.i-lg/.i-md/.i-sm` | MDI glyphs (embedded font) |
| `.hide-short` | Hidden when cell < 100px tall |
| `.hide-narrow` | Hidden when cell < 100px wide |
| `.hide-small` | Hidden when either dimension < 130px |
| `.cell` / `.cell.row` | Flex scaffold, space-evenly |
| `.chips` / `.chip` / `.caption-row` | Supporting strip (see `_card.py`) |

Fonts embedded in every render: **Nunito** (400/600/700/800),
**DejaVu Sans**, **Material Design Icons**. Themes pick families via
`theme.font_stack`.

**Best practices:**
- Use kit classes; add inline `style` only for widget-specific layout.
- TEXT AS BIG AS POSSIBLE — this is a 2" display.
- One fragment for all sizes: hide bands with `.hide-*` instead of
  branching in Python where possible (`ctx.is_compact` exists for the
  cases CSS can't express).

## Testing

Tests are organized by component:
- `tests/test_device.py` - HTTP client tests
- `tests/test_renderer.py` - Canvas/encoding tests
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
- **Never reach into `hass.data` by string key, and never call a core API the
  release notes mark deprecated.** Both work right up until they don't: HA's
  `hass.data` keys are `HassKey` objects that only happen to subclass `str`, so
  a raw lookup returns `None` and silently drops data instead of raising.
  `dr.async_get(hass)` / `ar.async_get(hass)` / `er.async_get(hass)`, and
  `dr.async_entries_for_config_entry` over `async_get_device`.

### The CI matrix is an HA matrix

`uv.lock` is gitignored on purpose, so CI resolves fresh on every run. Each
`pytest-homeassistant-custom-component` release pins one **exact** HA version
and raises its own `requires-python` in lockstep, which means the Python
version alone decides which core the suite runs against:

| Job | Resolves to | As of 2026-09 |
|-----|-------------|---------------|
| Python 3.12 | oldest ptc that still supports it | HA 2025.1.4 |
| Python 3.13 | a ptc a few months back | HA 2026.2.3 (stable) |
| Python 3.14 | the newest ptc | HA 2026.9.0b6 (**beta**) |

That mapping moves on its own. The `Resolved Home Assistant version` step in
each leg prints what a given run actually got.

**The newest leg is deliberately merge-blocking.** Resolving unpinned is how
the 2026.9 deprecation of `device_registry.async_get_device` surfaced months
before it would have reached users, and a red check is what got it fixed the
same day. The accepted cost: an upstream beta can turn an unrelated PR red.
When that happens the fix belongs on `main`, not in the contributor's branch.

## Adding New Widgets

1. Create `custom_components/geekmagic/widgets/mywidget.py`
2. Extend `Widget` base class
3. Implement `render_html()` and optionally `get_entities()`
4. Register in `widgets/__init__.py` (`_ALL_WIDGETS` — WIDGET_CLASSES
   and schemas derive from it)
5. Add tests in `tests/widgets/`

### Widget Helper Functions

Use helper functions from `widgets/helpers.py` for common operations:

```python
from ..widgets.helpers import (
    truncate_text,  # Truncate long text with ellipsis
    estimate_max_chars,  # Estimate max chars that fit in pixel width
    format_number,  # Format with optional 1k/1M abbreviation
    format_value_with_unit,  # Format "23°C" / "1.5k views"
    calculate_percent,  # Clamp value to 0..100 over a min/max range
    parse_color,  # Coerce JSON list/tuple to RGB
    get_binary_sensor_icon,  # MDI icon by binary_sensor device_class
    get_domain_state_icon,  # MDI icon by domain + state
    translate_binary_state,  # Localized "Open"/"Closed" etc.
)
```

### Markup Helpers

Build fragments with `card_html`/`chip_html` (`widgets/_card.py`) for
the standard three-band card, and `mdi_span` / `svg_sparkline` /
`svg_ring` / `svg_arc` / `image_data_uri` from `htmldoc.py`. The fluid
kit classes handle size adaptation; themes restyle everything through
`chrome_css`.

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

result = await hass.async_add_executor_job(partial(blocking_function, kwarg1=value1), arg1)
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
