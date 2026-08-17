# Domain glossary

The words this codebase uses, as the code uses them. Prefer these in
code, docstrings, commits and reviews; when a term here is fuzzy,
sharpen it here first. Architecture vocabulary (module, interface,
seam, adapter, depth, leverage, locality) follows the deep-module
sense: a module is anything with an interface and an implementation;
a seam is where its interface lives.

## Screens and views

- **View** — a named, globally stored screen definition
  (`{id, name, layout, theme, widgets[]}`) kept in `GeekMagicStore`,
  assignable to many devices. The current, JSON-shaped format.
- **Screen** — what a view becomes at runtime: a `Layout` with widgets
  in its slots. Also the legacy per-device inline definition
  (`CONF_SCREENS`) and the runtime index of "which of my layouts is
  showing" (`current_screen`). All three meanings are live.
- **Assigned views** — the ordered list of view IDs one device cycles
  through (`options["assigned_views"]`).
- **View → layout factory** — `views.build_layout`: the ONE path from a
  view dict to a placed, themed `Layout`. Callers keep their own
  defaults at the seam (`default_theme`, `default_widgets`). The
  layout registry (`LAYOUT_CLASSES`) and slot counts live there too.
- **Slot** — a numbered position in a layout: `Slot(index, rect,
  widget)`. Slot index also drives accent cycling.
- **Welcome layout** — the fallback screen (clock + HA version + entity
  count) rendered when no views are configured.
- **Notification** — a time-boxed layout override that replaces the
  current view during render (`geekmagic.notify` service).
- **Preview** — two things: the PNG served to the HA image entity
  (`coordinator.last_image`) and the editor render the panel asks for
  (`ws_preview_render`). Both render through the same factory and
  resolver as the device.

## Widget data

- **WidgetState** — everything a widget needs to render, injected per
  slot: primary entity, additional entities, history, candlestick
  data, image, forecast, `now`. Rendering is a pure function of
  `(CellContext, WidgetState)`.
- **DataNeeds** — a widget's declaration of what must be fetched
  beyond entity snapshots: `history_hours`, `candles` (`CandleSpec`),
  `image_source`, `forecast`. Returned by `Widget.data_needs()`;
  default: nothing.
- **Widget data resolver** — `widget_data.WidgetDataResolver`: gathers
  every placed widget's `DataNeeds`, fetches once in the event loop
  (`async_prefetch`), then builds per-slot `WidgetState` in the
  executor (`build_states`). It never asks what class a widget is.
  Caches survive fetch failures (stale-on-failure): a camera frame
  keeps the last frame. Images are the exception — an `entity_picture`
  that fails to download is dropped and warned once per entity
  (re-armed by the next success), a missing `entity_picture` clears the
  cache, and bytes that fail to decode are evicted.
- **Entity snapshot** — `EntityState` built from `hass.states` for the
  primary entity and every entity `get_entities()` names.

## Cell and rendering

- **Cell** — one widget's pixel rectangle AND its own CSS viewport;
  `vmin`/`vw`/`@media` resolve against it.
- **Layer** — one entry in the `render_layers` list: backdrop, a cell
  document, a glow underlay, or the overlay. Painted in order, clipped
  to its rect.
- **Fluid kit** — the utility CSS injected into every cell document:
  `.cell`, `.t-hero/.t-value/.t-unit/.t-label`, `.icon`, `.hide-*`.
- **Chrome** — per-cell theme decoration painted on `.root` (padding /
  border / background) via `Theme.chrome_css`.
- **Theme facts** — what a theme declares as fields rather than leaving
  to be sniffed out of its CSS: `chrome_inset` / `chrome_inset_y` (px
  per side that `.root` chrome eats, on the width and height axes —
  `_y` is None for the symmetric majority), `uppercase_labels` (kit text
  classes are uppercased), `rounded_font` (Nunito vs DejaVu measuring
  family). `tests/test_theme_facts.py` pins each fact to the CSS it
  describes.
- **Cell geometry** — `widgets/_cellkit.py`: the one owner of "how big
  is this cell really" (`cell_box`, `cell_inner`, `cell_box_px`,
  `cell_padding`) and of the kit's Python mirrors (`label_px`,
  `chip_px`, `HIDE_SHORT_H = 100`, `HIDE_SMALL = 130`,
  `caption_visible`, `small_visible`). Mirrors are tested against the
  kit CSS they mirror.
- **Glyph-overhang floor** — the 1.5px inset a chromeless theme still
  reserves so a fitted glyph never lands on the bezel.
- **Fit** — open-loop prediction: measure in Python (`_textfit`
  metrics, engine-shaped), emit an explicit `font-size`, let the engine
  draw. Blitz paints overflow past the bezel, so nothing is verified
  after the fact; the fit contract (`tests/widgets/test_fit_contract.py`)
  is the guard.
- **Caption** — the caps label naming what a cell shows (`.t-label`).
  Fitted by `_fit.fit_caption_sized`: shrink to `CAPTION_MIN_PX` (10px)
  before truncating; a stub survives only if it keeps `min_keep`
  identity (CJK glyphs count double) AND measures inside its band —
  otherwise the caption is dropped rather than painted over the bezel.
- **Hero** — the primary value, as large as the cell allows
  (`_fit.fit_hero` / `hero_block`), with an optional smaller suffix
  (unit, AM/PM) on the same baseline. Below the 12px floor it truncates,
  and — unlike a caption, which drops to "" — it walks the stub down to
  a single glyph rather than vanish: the hero IS the cell's content.
- **Chip** — a soft pill carrying one supporting metric.
- **Band** — one horizontal row inside a `.cell` (caption band, hero
  band, chip strip, feature-icon band).
- **Band policy** — `widgets/_bands.plan_bands`: given a cell, which
  bands survive and which `.hide-*` class each row carries. Owns the
  kit breakpoints' Python side and the compact-identity floor
  (`IDENTITY_MIN_H = 40`). The gauge family keeps its own thresholds
  (`CAPTION_MIN_CELL_H = 46`, `STACK_MIN_CELL_H = 64`) because those
  cells carry a bar as well as a value.
- **Compact identity** — a cell too short for a normal caption band
  still shows a shrunk 10px name rather than an anonymous number.
- **Track / fill** — the two halves of a gauge: dimmed background and
  accent-coloured value.
- **Glow underlay** — a blurred copy of a cell layer painted beneath
  the sharp one for `glow_effect` themes.
- **Supersample scale** — the device-pixel ratio Blitz renders at
  before the Lanczos downscale.

## Device

- **Display mode** — `"custom"` (integration renders and uploads) vs
  `"builtin"` (device firmware draws its own theme; render skipped).
- **Builtin theme** — the firmware theme number in builtin mode;
  profile-specific.
- **Custom theme** — the one firmware theme number that displays an
  uploaded image (`capabilities.custom_image_theme`, default 3).
- **Firmware profile** — the adapter encapsulating one firmware
  family's HTTP quirks (`profiles.py`, four adapters); `profile_id` is
  the model key. A real seam: two-plus adapters vary behind it.
- **Live transaction** — backup/restore of device settings around a
  destructive live smoke test (`scripts/device_cli.py`); not a DB
  transaction.
- **Pause / active** — sleep-wake: brightness to 0 and the whole
  render/upload cycle skipped.
- **Managed Pro album** — destructive album-file management on Pro
  firmware, opt-in.
