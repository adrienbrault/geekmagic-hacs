---
name: geekmagic-views
description: Design views and HTML widgets for GeekMagic 240x240 displays (SmallTV and similar, driven by the geekmagic-hacs Home Assistant integration), and render them to PNG with the integration's own engine against demo or exported entity data. Use when the user wants to create, rework, review or preview a GeekMagic view, screen, dashboard or HTML widget, or asks how a design would look on their GeekMagic display.
---

# GeekMagic views

A view is JSON: a layout, a theme, and widgets placed in the layout's
slots. `scripts/render_view.py` renders it exactly as the display would:
it runs the integration's own engine, fonts, widgets, layouts and themes,
not a copy. Only the entity data is fake (the demo home) or a snapshot
(entity data the user exported from Home Assistant).

Paths in this file are relative to this skill's directory, the folder
holding this SKILL.md: `${CLAUDE_SKILL_DIR}` (if that shows literally,
use the folder you read this file from). Use its absolute path in
commands; write every output (views, states files, PNGs) to a working
directory, never into the skill's directory.

## Running the renderer

```sh
R="${CLAUDE_SKILL_DIR}/scripts/render_view.py"
uv run "$R" --schema          # preferred: uv reads the script's PEP 723 dependencies
python3 "$R" --schema         # without uv (Python 3.12+)
```

Without uv, the first run installs `blitz-py`, `pillow` and `jinja2` from
PyPI into a private virtualenv under `~/.cache/geekmagic-views` (never
into the system Python). `python3 "$R" -h` documents every option and
both file formats.

Exit status: `0` rendered; `1` the view has errors or a widget failed to
render (stderr says which: fix and re-run); `2` the integration or its
engine can't be loaded. On `2`, tell the user what stderr says and stop:
never describe a render you could not make. The script finds the
integration in the repository it is installed with, else downloads the
release it belongs to.

## Loop

1. `--schema` once: every layout (slot rects in px, 240x240 screen),
   theme, and widget type with its options (type, default, `visible_when`).
   Use only what it lists.
2. `--demo`: the demo home, ~45 entities with realistic states and units,
   chart history, candles, a weather forecast, album art and a camera
   picture. Build on these ids so the effort goes into the design, not into
   fake data. Full data, attributes included: `demo/home.json`.
3. Write `view.json`. If the user pasted a view from the GeekMagic panel,
   save it unchanged and render it as is first: a bare view (**Copy view
   JSON**) as `view.json`, an export with data (**Copy for AI**, a JSON
   object with a `view` key) as `export.json` (see "A panel export"
   below). Other entity data (a states file) goes in with `--states
   data.json`: renders then show the user's real ids and values.
4. `"$R" view.json -o view.png --zoom 2`, then LOOK at the PNG and fix
   what reads badly. Show the user the image.
5. Check edge cases and themes in ONE render. Write small override files
   (same format as `demo/home.json`, only the entities that change; an
   override replaces the whole entity, so copy its attributes), then
   `"$R" view.json --scenario unlocked.json --scenario unavailable.json
   --theme watchos --theme night -o sheet.png` renders a labelled grid
   (rows: base + each scenario; columns: themes). Cover what real data
   will do: `unavailable`, long names, 5-digit values, night and day (a
   scenario can set `"now"`). One sheet beats many single renders.
6. Hand over (below).

Formats, in short (`-h` has them in full):

```
view.json   {"name", "layout", "theme", "widgets": [{"type", "slot",
            "entity_id", "label", "color": [r, g, b], "options": {...}}]}
states.json {"version": 1, "now": "2026-11-16T08:30:00+01:00",
             "timezone": "Europe/Paris",
             "entities": {"sensor.x": {"state": "21.5", "attributes": {...},
                 "history": [...] | {"24": [...]},
                 "candles": [[o, h, l, c], ...] | {"3600x20": [...]},
                 "forecast": [{"datetime": "+1", ...}], "picture": "cover.jpg"}},
             "templates": {"<slot>": {"<label template>": "<rendered>"}}}
export.json a states file plus "integration_version" and the view under
            "view": the panel's "Copy for AI"
```

Working examples: `examples/*.json` (`morning`, `front-door`, and three
HTML widgets, `html-*`), all on the demo home.

## A panel export ("Copy for AI")

The panel's **Copy for AI (includes entity data)** copies ONE JSON
document: a states file with the view inside it, as Home Assistant had
them when the user copied it.

```
{"version": 1, "integration_version": "1.9.5",
 "now": "2026-11-16T08:30:00+01:00", "timezone": "Europe/Paris",
 "view": {"name", "layout", "theme", "widgets": [...]},
 "entities": {"sensor.x": {"state", "attributes", "history": {"6": [...]},
                           "candles": [...], "forecast": [...]}},
 "templates": {"2": {"{{ states('sensor.y') }} W": "340 W"}}}
```

- Save the pasted text to `export.json` exactly (drop a surrounding code
  fence, change nothing else) and render it as is: `"$R" export.json -o
  now.png --zoom 2`. That is the user's screen as their display showed
  it: their ids, values, history, forecast, rendered label templates, and
  clocks at the export's `now` in its `timezone`. Show it to the user
  before changing anything.
- Edit the view in place (the `view` key) and render `export.json` again.
  Or split it: `"$R" export.json --save-view view.json --check` writes
  the bare view, and `"$R" view.json --states export.json` renders the
  same picture.
- Entity data stacks: the demo home, then the export, then each `--states`
  file (later wins, per entity, and replaces the entity whole: copy its
  attributes). `--scenario` files go on top of all of it.
- No pictures, ever: an exported camera, media player or Image widget
  shows its placeholder (a "no picture for" warning). To see one, add a `--states` file giving that
  entity a demo picture by absolute path, `demo/front_door.jpg` (camera)
  or `demo/album.jpg` (album art), with the entity's state and attributes
  copied from the export: `{"version": 1, "entities": {"camera.porch":
  {"state": "idle", "attributes": {...}, "picture": "/abs/.../front_door.jpg"}}}`.
- The export holds only what the view read when it was copied: history
  for those chart windows (`"6"` = 6 hours), candles for those candlestick
  settings, and each label template's output for its slot. Change a
  chart's period and it shows "No data" ("no history for sensor.x over
  6h (has 24h)" warning: the windows it has); move a templated
  widget to another slot or edit its template and it shows the template
  as written ("has no rendered output" warning); a new entity reads
  unknown ("no state for" warning) unless it is a demo id. Use demo
  entities for what you add, and tell the user what will only show right
  on the device.

## Hand over

1. Swap in the user's real entity ids, if they named them, and check the
   result: `"$R" view.json --map sensor.co2=sensor.office_co2 --map ...
   --save-view final.json --check` rewrites every reference (entity
   fields, options, ids quoted inside HTML and label templates) without
   rendering. Don't hand-edit ids. Without ids to swap: `"$R" view.json
   --check`. Add `--states` with the user's data when you have it. `ok`
   means the view is valid; fix every error, and expect "no state for"
   warnings only for real ids the demo lacks.
2. Give the user the final view JSON, the bare view `--save-view` wrote
   (as a file and in a code block). They add it in Home Assistant:
   GeekMagic panel → **Import view** → paste → pick a replacement for any
   entity id their Home Assistant doesn't have → save as a new view, or
   over an existing one (replace the one they exported to rework it).
   Import view also takes a whole edited `export.json`: it reads the view
   from its `view` key and ignores the data.

## Design rules (the screen is 27 mm wide, read from 0.6-1 m)

- The value is the widget: big hero text, few words. Captions are support.
- Fewer, bigger cells beat dense grids: a 2x2 cell is 114x114 px, a 3x3
  cell 73x73 (`--schema` has every rect).
- Colour comes from the theme. In HTML widgets use CSS variables
  (`var(--text-primary)`, `var(--warning)`, ...), never hex, so every theme
  works. Inside SVG `fill`/`stroke`, `var()` does not resolve: use the
  drawing helpers or `{{ color('warning') }}`.
- One accent per cell; tint icons and gauges rather than hero text.

## Built-in or HTML?

Use a **built-in widget** when one fits the job: it fits its text to any
cell size, follows every theme, matches its neighbours' type size, and the
user can edit it later in the panel's forms.

Use an **HTML widget** for what built-ins can't express: several entities
composed in one cell, state-driven designs (the whole cell changes when a
door unlocks), custom layouts of a forecast or a history, typographic
clocks, lists built from attributes (departures, prices), decorative
backgrounds. HTML widgets get the same data and the same drawing helpers
as built-ins, so a custom cell sits next to built-in ones without looking
foreign. Mix freely.

## HTML widgets

**Start from a working template.** `examples/html-*.json` (bedside, power
trend, front door) use the data functions and drawing helpers below and
render against the demo home as is. When the repository is installed
with this skill, `../../scripts/html_examples/*.html` holds the whole
gallery (dials, rings, sun arc, departures, price chart, presence, room
bars, watch face, animated `anim_*`); those use their own entity ids, so
swap in demo ids. Pick the closest, put it in the widget's
`options.html`, then adapt. Full reference: `../../docs/html-widget.md`.

What a template sees:
- `state`, `name`, `unit`, `attributes`, `entity`: the widget's `entity_id`
- `states('sensor.x')`, `state_attr('sensor.x', 'attr')`,
  `is_state('sensor.x', 'on')`: any entity
- `forecast('weather.home')`: daily entries (`datetime`, `condition`,
  `temperature`, `templow`, `precipitation_probability`, ...) plus `day`
  (`Mon`), `icon` (`mdi:weather-...`) and `color` (a theme role)
- `history('sensor.x', hours=24)`: up to 96 numbers, oldest first
  (`hours` above 0, up to 24)
- `picture('camera.x')`: a `data:` URI for `<img src>` (camera snapshot,
  media player album art, image entity); `''` when there is none
- `now`: timezone-aware datetime (`now.strftime('%H:%M')`)
- Entity ids (and `hours`) MUST be quoted literals: only those are fetched.
  `states(var)` reads `unknown`, `forecast(var)` returns `[]`.

Drawing helpers (output with `{{ }}`), the built-in widgets' own markup:
- `ring(value, color, min=0, max=100, size=None)`, `arc(...)`: gauge ring /
  270° arc; `bar(value, color, min, max, vertical=False, thickness=None)`
- `sparkline(values, color, width=None, height=None, fill=True, dot=True,
  min=None, max=None)`: the chart widget's line; fewer than 2 values: `''`
- `icon('mdi:lock', color, size)`: any Material Design Icons glyph
- `color('warning')`: the concrete colour, for your own SVG/CSS
- Colours are theme roles: `primary`, `secondary`, `success`, `warning`,
  `error`, `info`, `muted`, `text-primary|secondary|tertiary`, `accent`
  (the cell's own), `accent-0..N`. They resolve per theme, also inside SVG.
  Prefer roles to literal colours so every theme works.
- Values can be state strings: `ring(states('sensor.battery'))`;
  `unavailable` reads as 0, so branch on it when it matters.

Patterns that work:
- **Numbers are strings.** `{% set p = states('sensor.solar_power') | float(0) %}`
  before math; the fallback covers `unavailable`.
- **Branch the whole design on state**, not only a colour:
  `{% if is_state('lock.front_door', 'unlocked') %}...{% endif %}`, and
  give `unavailable`/`unknown` its own honest look (never "secure").
- **Theme colours**: `var(--text-primary|secondary|tertiary)`,
  `var(--primary|success|warning|error|info|muted)`, `var(--bg)`,
  `var(--chip-bg)`, `var(--track)`, `var(--hairline)`, `var(--radius)`.
  On `night` (monochrome) every role is a shade of red, so encode state
  with size/shape/fill too, not colour alone.
- **Fluid kit classes** scale with the cell: `.t-hero` (big value),
  `.t-value`, `.t-unit`, `.t-label` (caps caption), `.t-date`; `.icon` +
  an MDI codepoint (`<span class="icon">&#xF050F;</span>` =
  mdi:thermometer); `.hide-short` / `.hide-narrow` / `.hide-small` shed
  bands in small cells.
- **Layout**: a root `<div style="height:100%; display:flex; ...">`; px
  sizes are cell pixels (fullscreen 240x240, a 2x2 cell 114x114, a 3x3
  cell 73x73). `<style>` blocks and `@media (max-height: 100px)` work.
- **SVG**: `var()` does NOT resolve in `fill`/`stroke`; use the helpers
  or `color('role')`. Size inline SVG with `viewBox` aspect.
- **Labels inside a ring**: a `position: relative` box holding the ring and
  an absolutely positioned label (see `examples/html-power-trend.json`).
- **Text**: no ellipsis painting, so cut in Jinja:
  `{{ name | truncate(12, true, '…', 0) }}`. No `text-shadow`, `filter`,
  container queries, `background-clip: text`.

Every built-in widget's options, at every cell size:
`../../docs/widgets.md`. Every layout: `../../docs/layouts.md`.

## Limits of the offline render

- Templates in a built-in widget's label or a Text widget (`{{ ... }}`)
  are rendered by Home Assistant, not here: they show as written (with a
  warning) unless the states file carries their output under `templates`,
  as exported data does. HTML widget templates are rendered here.
- An animated HTML widget (`"animate": true`) renders one still frame;
  the device animates it only when its Animations switch is on.
- `history()` and charts read the entity's `history`: a list serves any
  window, `{"24": [...], "6": [...]}` one series per window.
- Camera snapshots and album art come from the demo home's entities.
  Exported data never includes pictures; to show one, set `"picture":
  "file.jpg"` on the entity in a `--states` file, and an Image widget's
  picture with `"images": {"<its source>": "file.png"}` (paths relative
  to that file).
- "no state for ..." warnings: the view reads an entity the data lacks;
  it renders as unknown. Use demo ids, or add the entity to a states file.
- "no history for ... over 6h", "no candles for", "no forecast for",
  "no picture for" warnings: the entity is there but not what this cell
  draws from it, so the cell shows "No data" or its placeholder. Give
  the entity that data in a `--states` file (a history list serves any
  window), or pick a window the data has.
