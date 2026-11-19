# HTML widget

Design your own cells with HTML/CSS + Jinja. A 240×240 cell renders in ~20-40ms.

| [Radar sweep](#radar-sweep) | [Now playing](#now-playing) | [Thunderstorm](#thunderstorm) | [Doorbell](#doorbell) |
|:-:|:-:|:-:|:-:|
| <img src="../samples/html/anim_radar.gif" alt="Radar sweep"> | <img src="../samples/html/anim_vinyl.gif" alt="Now playing"> | <img src="../samples/html/anim_rain.gif" alt="Thunderstorm"> | <img src="../samples/html/anim_doorbell.gif" alt="Doorbell"> |
| [Washing machine](#washing-machine) | [Wind turbine](#wind-turbine) | [Lava lamp](#lava-lamp) | [Watch face](#watch-face) |
| <img src="../samples/html/anim_washer.gif" alt="Washing machine"> | <img src="../samples/html/anim_turbine.gif" alt="Wind turbine"> | <img src="../samples/html/anim_lava.gif" alt="Lava lamp"> | <img src="../samples/html/watch_face.png" alt="Watch face"> |
| [Thermostat dial](#thermostat-dial) | [Glass weather card](#glass-weather-card) | [Energy flow](#energy-flow) | [Activity rings](#activity-rings) |
| <img src="../samples/html/thermostat_dial.png" alt="Thermostat dial"> | <img src="../samples/html/weather_glass.png" alt="Glass weather card"> | <img src="../samples/html/energy_orbit.png" alt="Energy flow"> | <img src="../samples/html/activity_rings.png" alt="Activity rings"> |
| [Electricity prices](#electricity-prices) | [Sun arc](#sun-arc) | [EV charging ring](#ev-charging-ring) | [Power dial (SVG)](#power-dial-svg) |
| <img src="../samples/html/price_chart.png" alt="Electricity prices"> | <img src="../samples/html/sun_arc.png" alt="Sun arc"> | <img src="../samples/html/ev_charge.png" alt="EV charging ring"> | <img src="../samples/html/power_dial.png" alt="Power dial (SVG)"> |
| [Departure board](#departure-board) | [Room temperatures](#room-temperatures) | [Who's home](#whos-home) | [Air quality](#air-quality) |
| <img src="../samples/html/departures.png" alt="Departure board"> | <img src="../samples/html/room_bars.png" alt="Room temperatures"> | <img src="../samples/html/presence.png" alt="Who's home"> | <img src="../samples/html/air_quality.png" alt="Air quality"> |
| [Bedside](#bedside) | [Power trend](#power-trend) | [Front door camera](#front-door-camera) | [Synthwave clock](#synthwave-clock) |
| <img src="../samples/html/bedside.png" alt="Bedside"> | <img src="../samples/html/power_trend.png" alt="Power trend"> | <img src="../samples/html/front_door.png" alt="Front door camera"> | <img src="../samples/html/tw_synthwave.gif" alt="Synthwave clock"> |
| [Control center](#control-center) | [Home battery](#home-battery) | [Alarm](#alarm) | |
| <img src="../samples/html/tw_control_center.png" alt="Control center"> | <img src="../samples/html/tw_battery.png" alt="Home battery"> | <img src="../samples/html/tw_alarm.gif" alt="Alarm"> | |

**Contents:** [Rendering engine](#rendering-engine) · [Templates](#templates) · [Data](#data-from-home-assistant) · [Drawing helpers](#drawing-helpers) · [Tailwind utility classes](#tailwind-utility-classes) · [Examples](#examples) · [Fluid templates](#fluid-templates) · [Animated widgets](#animated-widgets-opt-in) · [Limitations](#limitations)

## Rendering engine

All rendering, built-in widgets included, is powered by the [Blitz](https://github.com/DioxusLabs/blitz) HTML/CSS engine via [blitz-py](https://github.com/adrienbrault/blitz-py) (Stylo + Taffy + Parley + Vello, no browser). Every widget is an HTML fragment rasterized per cell, so real CSS drives the design: flexbox, gradients, glows, border-radius, media queries, SVG charts, embedded fonts. Themes are full stylesheets (fonts, chrome, backdrops, overlay effects like CRT scanlines), not just palettes.

`blitz-py` ships prebuilt wheels on PyPI (Linux glibc/musl x86_64 + aarch64, macOS, Windows) and installs automatically with the integration.

Modern CSS works: gradients (linear/radial/conic, including `repeating-*`), `transform` (rotate/translate/scale with `transform-origin`), `clip-path`, `border-radius`, `box-shadow` glows (inset too), translucent `rgba()` fills and borders, flexbox, CSS grid, absolute positioning, media queries, viewport units, and inline SVG with gradient fills and strokes.

## Templates

The **HTML Template** option is a Jinja template with access to entity data:

```html
<style>
.screen { height: 100%; display: flex; flex-direction: column;
          align-items: center; justify-content: space-evenly; }
.hero { font-size: 64px; font-weight: 700; color: var(--warning); }
.label { color: var(--text-secondary); }
</style>
<div class="screen">
  <div class="label">{{ name | upper }}</div>
  <div class="hero">{{ state }}{{ unit }}</div>
  <div class="label">HVAC {{ states('climate.living_room') | upper }}</div>
</div>
```

- `state`, `name`, `unit`, `attributes`: the widget's configured entity
- `states('sensor.x')`, `state_attr('sensor.x', 'attr')`, `is_state('sensor.x', 'on')`: any referenced entity is tracked and pre-fetched automatically
- `now`: timezone-aware current datetime
- `forecast()`, `history()` and `picture()`: what the Weather, Chart, Camera and Media widgets draw (see [Data from Home Assistant](#data-from-home-assistant))
- `ring()`, `arc()`, `bar()`, `sparkline()`, `icon()` and `color()`: the built-in widgets' drawing helpers (see [Drawing helpers](#drawing-helpers))
- Theme colors as CSS variables: `var(--text-primary)`, `var(--text-secondary)`, `var(--text-tertiary)`, `var(--primary)`, `var(--success)`, `var(--warning)`, `var(--error)`, `var(--info)`, `var(--muted)`, `var(--bg)`, plus `var(--chip-bg)`, `var(--hairline)` and `var(--track)` (neutral fills and strokes that work on light themes too), `var(--accent-0)`…`var(--accent-N)` and `var(--radius)`
- Standard Jinja: `{% set %}`, `{% for %}`, `{% if %}`, and filters like `float`, `int`, `round`, `abs`, `min`, `max`, `selectattr`, `truncate`. Home Assistant's own template extensions (`| as_timestamp`, `relative_time`, …) aren't available here.

### Data from Home Assistant

The data the built-in widgets draw, fetched before each render for the device and the panel preview alike:

| Function | Returns | Missing or failed |
|---|---|---|
| `forecast('weather.home')` | The daily forecast the Weather widget shows: a list of the entries `weather.get_forecasts` returns (`datetime`, `condition`, `temperature`, `templow`, `precipitation_probability`, …), each with three extras: `day` (`Mon`, in Home Assistant's timezone), `icon` (`mdi:weather-rainy`) and `color` (the Weather widget's colour for the condition) | `[]` |
| `history('sensor.power', hours=24)` | The Chart widget's series: up to 96 numbers, oldest first, each the time-weighted average of one equal slice of the window (fewer when the entity's history starts inside the window). On/off states read as `1.0`/`0.0`. `hours` (also positional: `history('sensor.power', 6)`) defaults to 24, and goes from just above 0 to 24 | `[]` |
| `picture('camera.front_door')` | A `data:` URI for `<img src>`: a camera's snapshot, a media player's album art, an `image` entity's picture, or another entity's `entity_picture` when Home Assistant serves it (a `/api/…` or `/local/…` path, such as a person's photo). It is scaled down to what covering the cell needs (twice the cell size, for the supersampled render) | `''` |

Only literal arguments are fetched, exactly like `states('…')`: the entity ID must be a quoted string and `hours` a plain number. `forecast(eid)`, `picture(eid)` or `history('sensor.power', hours=h)` with a variable return the empty value. Forecasts are shared with the Weather widget's cache (refreshed every 30 minutes), and each history window costs one recorder query per refresh, however many widgets read it.

```html
{% set day = history('sensor.power') %}
{% if day %}{{ sparkline(day, 'warning') }}{% endif %}
{% for d in forecast('weather.home')[:3] %}{{ d.day }} {{ icon(d.icon, d.color) }} {{ d.temperature }}°{% endfor %}
{% set snapshot = picture('camera.front_door') %}
{% if snapshot %}<img src="{{ snapshot }}" style="width: 100%; height: 100%; object-fit: cover">{% endif %}
```

### Drawing helpers

The built-in widgets' markup, so a custom cell sits next to them without looking foreign. Each returns HTML to output with `{{ … }}`:

| Helper | Draws |
|---|---|
| `ring(value, color, min=0, max=100, size=None)` | The Gauge widget's ring, filled to `value` on `min`…`max` |
| `arc(value, color, min=0, max=100, size=None)` | The Gauge widget's 270° arc |
| `bar(value, color, min=0, max=100, vertical=False, thickness=None)` | The Gauge widget's pill bar; fills its parent's width (or height when vertical) |
| `sparkline(values, color, width=None, height=None, fill=True, dot=True, smooth=None, min=None, max=None)` | The Chart widget's line with its gradient fill and end dot. `min`/`max` pin the vertical scale; `smooth` defaults to on except for on/off series. Fewer than two values draw nothing |
| `icon('mdi:lock', color, size)` | A Material Design Icons glyph |
| `color('warning')` | The colour itself, e.g. `rgb(255, 159, 10)`, for your own SVG or CSS |

- **Colours** are theme roles: `primary`, `secondary`, `success`, `warning`, `error`, `info`, `muted`, `text-primary`, `text-secondary`, `text-tertiary`, `accent` (the cell's own accent, which gauges and sparklines use by default; an icon without a colour takes the text's) and `accent-0`…`accent-N`. `var(--warning)` works too. The helpers resolve them to the current theme's colour, which is what lets them paint SVG, where `var()` doesn't resolve. A literal CSS colour (`'#30d158'`, `'rgb(48, 209, 88)'`) is used as is, except on monochrome themes (Night), where it becomes the cell's accent, as colour options do on built-in widgets.
- **Sizes** are numbers (px) or CSS lengths (`'40%'`). `ring()`/`arc()` without `size`, and `sparkline()` without `width`/`height` (2:1), fill their parent's width.
- **Values** can be state strings: `ring(states('sensor.battery'))` works, and `unavailable` reads as 0.
- **Labels inside a ring:** wrap it with a `position: relative` box and lay an absolutely positioned label over it (see [Power trend](#power-trend)).

### Template tips

- **Reference entities literally.** Only entity IDs written as quoted strings in `states('…')`, `state_attr('…', …)`, `is_state('…', …)` and the [data functions](#data-from-home-assistant) are fetched for the widget. `states(eid)` with a variable reads `unknown`, so to loop over entities, build the list from the calls themselves: `{% set rooms = [(states('sensor.living_temp'), 'Living'), …] %}`.
- **Icons:** `{{ icon('mdi:thermometer', 'warning', 24) }}` draws any [Material Design Icons](https://pictogrammers.com/library/mdi/) glyph from the embedded font. By hand, the kit's `icon` class takes the codepoint: `<span class="icon">&#xF050F;</span>`.
- **Numbers:** states are strings. Convert with `| float(0)` before doing math or comparisons; the `0` is the fallback for `unavailable`.
- **Truncating:** `truncate` has a 5-character leeway by default, so pass all four arguments to cut exactly: `{{ name | truncate(12, true, '…', 0) }}`.
- **SVG colours:** `var(--x)` doesn't resolve inside SVG `fill`/`stroke` attributes. Use the helpers, or `{{ color('warning') }}` for a concrete theme colour (or pick one in Jinja, as the [power dial](#power-dial-svg) does).

## Tailwind utility classes

Turn on the widget's **Tailwind utility classes** option and style with classes instead of a `<style>` block:

```html
<div class="h-full flex flex-col items-center justify-evenly">
  <div class="text-fg-2">{{ name | upper }}</div>
  <div class="text-[64px] font-bold text-warning">{{ state }}{{ unit }}</div>
  <div class="text-fg-2">HVAC {{ states('climate.living_room') | upper }}</div>
</div>
```

The classes are read after Jinja runs, so classes built in the template work: `class="{{ 'text-success' if on else 'text-muted' }}"`, `h-[{{ pct }}%]`. Only the classes a template uses are turned into CSS. The option is off by default because a template written without it may use a utility's name as its own class (`.ring`, `.grid`). A template's own `<style>` still works next to utilities and wins over them.

The names and values are [Tailwind CSS v4](https://tailwindcss.com/docs)'s, so its docs (and AI assistants, who write it fluently) apply:

- **Layout:** `flex`, `grid`, `grid-cols-3`, `col-span-2`, `items-center`, `justify-between`, `absolute`, `inset-0`, `z-10`, `overflow-hidden`, `aspect-square`, `w-1/2`, `size-12`, `space-y-2`, `divide-y`.
- **Spacing:** the 4px scale, in steps of 0.25: `p-4` is 16px and `gap-0.75` is 3px. Negative margins and offsets too (`-mt-2`, `-translate-x-1/2`).
- **Type:** `text-xs`…`text-9xl` (with their line heights; `text-sm/6` sets one), `font-bold`, `tracking-widest`, `leading-none`, `uppercase`, `tabular-nums`, `text-center`, `whitespace-nowrap`.
- **Effects:** `rounded-2xl`, `border-2`, `ring-1`, `inset-ring-2`, `outline-2 outline-offset-2`, `shadow-lg`, coloured glows (`shadow-[0_0_24px] shadow-warning/60`), `opacity-50`, gradients (`bg-linear-to-r from-info via-primary to-secondary`, `bg-linear-45`, `bg-radial`, `bg-conic`), transforms (`rotate-12`, `scale-110`, `translate-y-2`, `origin-bottom`).
- **Filters and text effects:** `blur-sm`, `drop-shadow-lg` (and a coloured one: `drop-shadow-[0_0_8px] drop-shadow-warning/70`, which follows a shape, unlike a box `shadow`), `text-shadow-md`, glowing text (`text-shadow-[0_0_12px] text-shadow-info`), gradient text (`bg-linear-to-r from-warning to-error bg-clip-text text-transparent`). The engine applies only the first function of a `filter`, so an element with both `blur-*` and `drop-shadow-*` is only blurred, and an arbitrary drop shadow keeps its first shadow. Under an `overflow-hidden` ancestor, a text or drop shadow is cut off at the element's own box (an engine bug): give the element padding, or drop the `overflow-hidden`.
- **SVG:** `fill-warning`, `stroke-info/60`, `stroke-2`, on the shapes inside an inline `<svg>`. The engine paints SVG apart from the page's styles, so these rules are repeated inside each `<svg>`, where media variants (`small:`), `odd:`/`even:` and `fill-current` don't apply: for the text colour, write `fill="currentColor"` on the shape.
- **Animation** (with [Animate](#animated-widgets-opt-in) on): `animate-spin`, `animate-ping`, `animate-pulse`, `animate-bounce`. They last 1s or 2s, so they loop seamlessly in a 1s or 2s loop.
- **Arbitrary values and properties:** `text-[82px]`, `tracking-[0.08em]`, `bg-[#1d2836]`, `rounded-[28px]`, and any CSS property as `[mask-image:linear-gradient(#000,transparent)]` or `[animation-delay:-0.5s]`. Underscores are spaces, and math gets its spaces back (`w-[calc(100%-20px)]`). `(--name)` is short for `var(--name)`: `bg-(--my-colour)`, `rounded-(--r)`. Add `!` at the end for `!important`.

**Colours** are the theme's, so a template follows whichever theme the view uses:

| Class part | Colour |
|---|---|
| `primary`, `secondary`, `success`, `warning`, `error`, `info`, `muted` | The theme's roles (`secondary` is an accent, not a text tone) |
| `fg`, `fg-2`, `fg-3` | Primary, secondary and tertiary text |
| `bg`, `surface`, `surface-variant`, `border` | Background and surfaces |
| `chip`, `hairline`, `track` | The neutral fills and strokes that work on light themes too |
| `accent`, `accent-0`…`accent-N` | The cell's accent, or one of the theme's |
| `sky-400`, `white`, `[#30d158]`, … | Tailwind's palette and literal colours |

Any colour takes an opacity: `bg-warning/20`, `ring-fg/[0.15]`. Colours are concrete values, not `var()`, so they paint SVG too. On a monochrome theme (Night), palette and literal colours (also inside arbitrary shadows, gradients and properties) map onto the theme's warm ramp and keep their lightness, so `bg-slate-900` stays a dark fill and `text-white` becomes the theme's brightest tone.

**Variants:**

| Variant | Applies |
|---|---|
| `short:`, `narrow:`, `small:` | Cell under 100px tall, under 100px wide, either under 130px: the fluid kit's `.hide-*` thresholds (`small:hidden`, `short:text-xs`) |
| `not-short:`, `not-narrow:`, `not-small:` | The opposite (`not-small:flex`) |
| `landscape:`, `portrait:`, `min-[130px]:`, `max-[99px]:` | Cell orientation or width |
| `first:`, `last:`, `odd:`, `even:`, `only:`, `*:`, `before:`, `after:`, `[&_span]:` | As in a browser. A `before:`/`after:` box without text needs `absolute` or `block` (`before:absolute before:inset-0`): an empty inline one blanks the cell (an engine bug) |
| `dark:` | On a dark theme |
| `sm:` … `2xl:` | Never: a cell is at most 240px wide, as in a browser that small |
| `data-[state=on]:`, `data-active:`, `aria-checked:`, `has-[img]:` | When the template sets the attribute, or has the child |
| `hover:`, `focus:`, `group-*:`, `print:`, … | Never: the display has no pointer (`not-hover:` always) |

**Not available**, because the engine can't paint them: the colour filters (`grayscale`, `brightness-*`, `sepia`, …), `backdrop-*` and `line-clamp-*`. They are ignored (logged at debug level as unknown classes), like any class that isn't a utility, and so is a class whose arbitrary value isn't self-contained (an unclosed `[`, `(` or quote, a `;` or `}`), as in Tailwind.

The reset is light: border-box sizing, and no default margins on headings, paragraphs and lists. It doesn't touch the [drawing helpers](#drawing-helpers): the [Bedside](#bedside) and [Power trend](#power-trend) examples rewritten with utility classes ([`tests/fixtures/tailwind/`](../tests/fixtures/tailwind/)) render exactly the same pixels as the originals, and a test checks it.

## Examples

Every example below is a real template, rendered by the integration's own pipeline from the mock entities in `scripts/generate_html_samples.py`. Paste one into a widget's **HTML Template** and swap in your own entity IDs. The animated ones are in [Animated widgets](#animated-widgets-opt-in).

### Built-in data and helpers

Cards that read forecasts, history and pictures, and draw with the built-in widgets' helpers, so they match the rest of the screen in every theme.

#### Bedside

A nightstand clock: the time, whether the front door is locked, and the next three days from `forecast()`, each day's glyph and tint coming with the forecast entry.

<img src="../samples/html/bedside.png" alt="Bedside" width="200">

```html
{% set locked = is_state('lock.front_door', 'locked') %}
<style>
.bed { height: 100%; display: flex; flex-direction: column; align-items: center;
       justify-content: space-between; padding: 12px 8px 10px; box-sizing: border-box; }
.time { font-size: 82px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; text-align: center; }
.date { font-size: 14px; font-weight: 700; letter-spacing: 0.1em; color: var(--text-secondary);
        text-align: center; margin-top: 4px; }
.lock { display: flex; align-items: center; gap: 6px; font-size: 15px; font-weight: 700;
        color: {{ 'var(--text-secondary)' if locked else 'var(--warning)' }}; }
.days { width: 100%; display: flex; justify-content: space-around; }
.day { display: flex; flex-direction: column; align-items: center; gap: 3px; line-height: 1; }
.day .n { font-size: 12px; font-weight: 800; letter-spacing: 0.08em; color: var(--text-tertiary); }
.day .t { font-size: 17px; font-weight: 700; }
.day .t small { font-size: 13px; color: var(--text-tertiary); }
</style>
<div class="bed">
  <div>
    <div class="time">{{ now.strftime('%H:%M') }}</div>
    <div class="date">{{ now.strftime('%A %d %B').upper() }}</div>
  </div>
  <div class="lock">
    {{ icon('mdi:lock' if locked else 'mdi:lock-open-variant', 'success' if locked else 'warning', 20) }}
    Front door {{ 'locked' if locked else 'unlocked' }}
  </div>
  <div class="days">
    {% for d in forecast('weather.home')[:3] %}
    <div class="day">
      <span class="n">{{ d.day | upper }}</span>
      {{ icon(d.icon, d.color, 28) }}
      <span class="t">{{ d.temperature | round | int }}°{% if d.templow is defined %}<small> {{ d.templow | round | int }}°</small>{% endif %}</span>
    </div>
    {% endfor %}
  </div>
</div>
```

#### Power trend

The house's power now as a `ring()`, with the last 24 hours from `history()` as a `sparkline()` and the peak and average computed from the same series.

<img src="../samples/html/power_trend.png" alt="Power trend" width="200">

```html
{% set kw = states('sensor.house_power') | float(0) %}
{% set day = history('sensor.house_power', hours=24) %}
{% set peak = day | max if day else 0 %}
{% set avg = (day | sum) / (day | length) if day else 0 %}
<style>
.pw { height: 100%; display: flex; flex-direction: column; justify-content: space-between;
      padding: 10px 12px 8px; box-sizing: border-box; }
.top { display: flex; align-items: center; gap: 14px; }
.dial { position: relative; flex: none; }
.dial .in { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex;
            flex-direction: column; align-items: center; justify-content: center; line-height: 1; }
.dial .v { font-size: 30px; font-weight: 800; letter-spacing: -0.02em; }
.dial .u { font-size: 11px; font-weight: 800; letter-spacing: 0.08em; color: var(--text-secondary); margin-top: 2px; }
.stat { line-height: 1; margin: 6px 0; }
.stat .l { font-size: 11px; font-weight: 800; letter-spacing: 0.08em; color: var(--text-tertiary); }
.stat .n { font-size: 22px; font-weight: 700; margin-top: 3px; }
.stat .n small { font-size: 13px; color: var(--text-secondary); }
.axis { display: flex; justify-content: space-between; margin-top: 2px; font-size: 11px;
        font-weight: 700; color: var(--text-tertiary); }
</style>
<div class="pw">
  <div class="top">
    <div class="dial">
      {{ ring(kw, 'warning', max=6, size=104) }}
      <div class="in"><span class="v">{{ kw }}</span><span class="u">KW NOW</span></div>
    </div>
    <div>
      <div class="stat"><div class="l">{{ icon('mdi:flash', 'warning', 12) }} PEAK 24H</div>
        <div class="n">{{ '%.1f' | format(peak) }}<small> kW</small></div></div>
      <div class="stat"><div class="l">AVERAGE</div>
        <div class="n">{{ '%.1f' | format(avg) }}<small> kW</small></div></div>
    </div>
  </div>
  <div>
    {{ sparkline(day, 'warning', width=216, height=76) }}
    <div class="axis"><span>-24h</span><span>-12h</span><span>now</span></div>
  </div>
</div>
```

#### Front door camera

A camera snapshot from `picture()`, edge to edge, with a scrim, a live badge and the lock's state. Without a snapshot it shows a placeholder glyph instead.

<img src="../samples/html/front_door.png" alt="Front door camera" width="200">

```html
{% set snapshot = picture('camera.front_door') %}
{% set locked = is_state('lock.front_door', 'locked') %}
<style>
.door { position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 22px;
        overflow: hidden; background: var(--surface); }
.door img { width: 100%; height: 100%; object-fit: cover; display: block; }
.scrim { position: absolute; left: 0; right: 0; bottom: 0; height: 50%;
         background: linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0.85)); }
.live { position: absolute; top: 10px; left: 10px; display: flex; align-items: center; gap: 5px;
        padding: 5px 9px; border-radius: 999px; background: rgba(0,0,0,0.55);
        font-size: 11px; font-weight: 800; letter-spacing: 0.1em; color: #fff; }
.foot { position: absolute; left: 14px; right: 12px; bottom: 12px; display: flex;
        align-items: flex-end; justify-content: space-between; color: #fff; line-height: 1; }
.name { font-size: 22px; font-weight: 800; }
.when { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.7); margin-top: 5px; }
.badge { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center;
         justify-content: center; background: rgba(0,0,0,0.55); }
</style>
<div class="door">
  {% if snapshot %}
  <img src="{{ snapshot }}">
  {% else %}
  <div class="cell">{{ icon('mdi:cctv-off', 'muted', 48) }}</div>
  {% endif %}
  <div class="scrim"></div>
  <div class="live">{{ icon('mdi:record', 'error', 12) }} LIVE</div>
  <div class="foot">
    <div>
      <div class="name">Front door</div>
      <div class="when">{{ now.strftime('%H:%M') }} · {{ 'Locked' if locked else 'Unlocked' }}</div>
    </div>
    <div class="badge">
      {{ icon('mdi:lock' if locked else 'mdi:lock-open-variant', 'success' if locked else 'warning', 24) }}
    </div>
  </div>
</div>
```

### Showcase

How far one cell can go: transforms placing things on circles, layered and conic gradients, glass, glows, and SVG with gradient strokes. These use their own colours rather than the theme's, like a watch face would.

#### Watch face

An analog face from 60 rotated ticks, a brushed-metal conic-gradient bezel, a date window and a phone-battery subdial. Hands are `rotate()`d from `now`; numerals use `rotate() translateY() rotate(-)` to sit upright on the circle.

<img src="../samples/html/watch_face.png" alt="Watch face" width="200">

```html
{% set h = now.hour % 12 %}{% set m = now.minute %}{% set s = now.second %}
{% set batt = states('sensor.phone_battery') | float(0) %}
<style>
.bezel { position: absolute; top: 2px; left: 2px; right: 2px; bottom: 2px; border-radius: 50%;
         background: conic-gradient(#3a3f47, #d9dde3, #4a4f57, #aab0b8, #3a3f47, #c8ccd2, #3a3f47);
         box-shadow: 0 6px 18px rgba(0,0,0,0.8); }
.dial { position: absolute; top: 7px; left: 7px; right: 7px; bottom: 7px; border-radius: 50%;
        background: radial-gradient(circle at 50% 30%, #23324a 0%, #0c1220 62%, #05070c 100%);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08), inset 0 10px 30px rgba(0,0,0,0.7); }
.c { position: absolute; left: 50%; top: 50%; }
.tick { width: 2px; height: 7px; margin: -3.5px 0 0 -1px; background: rgba(255,255,255,0.35); }
.tick.hr { width: 4px; height: 15px; margin: -7.5px 0 0 -2px; background: #f2f4f7; border-radius: 2px; }
.tick.q { background: #ff9f0a; }
.num { width: 30px; margin: -10px 0 0 -15px; text-align: center; font-size: 17px;
       font-weight: 800; color: #f2f4f7; line-height: 20px; }
.brand { width: 120px; margin-left: -60px; top: 27%; text-align: center; font-size: 9px;
         font-weight: 800; letter-spacing: 0.35em; color: rgba(255,255,255,0.55); }
.date { left: 69%; top: 50%; margin-top: -10px; padding: 2px 5px; border-radius: 4px;
        background: #f2f4f7; color: #0c1220; font-size: 12px; font-weight: 800; line-height: 16px; }
.sub { width: 50px; height: 50px; margin-left: -25px; top: 60%; border-radius: 50%;
       background: conic-gradient(#30d158 0deg {{ batt * 3.6 }}deg, rgba(255,255,255,0.10) {{ batt * 3.6 }}deg);
       box-shadow: 0 0 12px rgba(48,209,88,0.35); }
.sub-in { position: absolute; top: 5px; left: 5px; right: 5px; bottom: 5px; border-radius: 50%;
          background: #0b111d; display: flex; flex-direction: column; align-items: center;
          justify-content: center; line-height: 1; }
.sub-in b { font-size: 13px; font-weight: 800; color: #f2f4f7; }
.sub-in span { font-size: 7px; font-weight: 800; letter-spacing: 0.12em; color: #30d158; margin-top: 2px; }
.hand { transform-origin: 50% 100%; border-radius: 4px; }
.hour { width: 8px; height: 58px; margin: -58px 0 0 -4px; background: linear-gradient(#ffffff, #c9ced6);
        box-shadow: 0 2px 6px rgba(0,0,0,0.6); }
.min { width: 6px; height: 88px; margin: -88px 0 0 -3px; background: linear-gradient(#ffffff, #c9ced6);
       box-shadow: 0 2px 6px rgba(0,0,0,0.6); }
.sec { width: 2px; height: 104px; margin: -88px 0 0 -1px; background: #ff9f0a; transform-origin: 50% 84.6%; }
.pin { width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: #ff9f0a;
       box-shadow: 0 0 0 3px #0c1220; }
</style>
<div class="bezel"></div>
<div class="dial">
  {% for i in range(60) %}
  <div class="c tick {{ 'hr' if i % 5 == 0 }} {{ 'q' if i % 15 == 0 }}"
       style="transform: rotate({{ i * 6 }}deg) translateY(-100px)"></div>
  {% endfor %}
  {% for n in [12, 6, 9] %}
  <div class="c num" style="transform: rotate({{ n * 30 }}deg) translateY(-78px) rotate({{ -n * 30 }}deg)">{{ n }}</div>
  {% endfor %}
  <div class="c brand">GEEKMAGIC</div>
  <div class="c date">{{ now.strftime('%a').upper() }} {{ now.day }}</div>
  <div class="c sub"><div class="sub-in"><b>{{ batt | int }}</b><span>PHONE</span></div></div>
  <div class="c hand hour" style="transform: rotate({{ (h + m / 60) * 30 }}deg)"></div>
  <div class="c hand min" style="transform: rotate({{ m * 6 + s / 10 }}deg)"></div>
  <div class="c hand sec" style="transform: rotate({{ s * 6 }}deg)"></div>
  <div class="c pin"></div>
</div>
```

#### Thermostat dial

A climate entity as a glowing dial: 55 ticks across a 270° arc, the ones between the current and target temperature lit, with a dot for the room's reading. The disc's glow switches between heating and idle.

<img src="../samples/html/thermostat_dial.png" alt="Thermostat dial" width="200">

```html
{% set cur = state_attr('climate.living_room', 'current_temperature') | float(0) %}
{% set target = state_attr('climate.living_room', 'temperature') | float(0) %}
{% set heating = state_attr('climate.living_room', 'hvac_action') == 'heating' %}
{# 10-30 °C spread over a 270° arc: angle = -135 + (t - 10) * 13.5 #}
<style>
.disc { position: absolute; top: 6px; left: 6px; right: 6px; bottom: 6px; border-radius: 50%;
        background: radial-gradient(circle at 50% 28%, {{ '#5a2a10' if heating else '#1d2733' }} 0%,
                    #120c0a 58%, #050404 100%);
        box-shadow: 0 0 34px {{ 'rgba(255,120,30,0.45)' if heating else 'rgba(10,132,255,0.25)' }},
                    inset 0 2px 1px rgba(255,255,255,0.12), inset 0 -8px 24px rgba(0,0,0,0.8); }
.c { position: absolute; left: 50%; top: 50%; }
.t { width: 2px; height: 12px; margin: -6px 0 0 -1px; border-radius: 1px; background: rgba(255,255,255,0.22); }
.t.on { height: 18px; margin-top: -9px; width: 3px; margin-left: -1.5px; background: #ff8a1f;
        box-shadow: 0 0 6px rgba(255,138,31,0.9); }
.cur { width: 10px; height: 10px; margin: -5px 0 0 -5px; border-radius: 50%; background: #fff;
       box-shadow: 0 0 10px #fff; }
.mid { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column;
       align-items: center; justify-content: center; line-height: 1; }
.mode { font-size: 12px; font-weight: 800; letter-spacing: 0.22em;
        color: {{ '#ff8a1f' if heating else '#5ac8f5' }}; }
.set { font-size: 76px; font-weight: 800; letter-spacing: -0.04em; color: #fff; margin: 4px 0 2px; }
.set sup { font-size: 26px; letter-spacing: 0; vertical-align: top; position: relative; top: 8px; }
.now { font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.6); }
.leaf { margin-top: 8px; font-size: 18px; color: #30d158; }
</style>
<div class="disc">
  {% for i in range(0, 55) %}
    {% set t = 10 + i * 20 / 54 %}
    {% set on = (cur <= t <= target) or (target <= t <= cur) %}
    <div class="c t {{ 'on' if on }}" style="transform: rotate({{ -135 + (t - 10) * 13.5 }}deg) translateY(-96px)"></div>
  {% endfor %}
  <div class="c cur" style="transform: rotate({{ -135 + (cur - 10) * 13.5 }}deg) translateY(-80px)"></div>
  <div class="mid">
    <div class="mode">{{ 'HEATING' if heating else 'IDLE' }}</div>
    <div class="set">{{ target | int }}<sup>.{{ ((target * 10) | int) % 10 }}°</sup></div>
    <div class="now">Inside {{ cur }}°</div>
    <span class="icon leaf">&#xF032A;</span>
  </div>
</div>
```

#### Glass weather card

Layered radial gradients paint a sunset sky behind a glowing sun, and a frosted-glass panel (translucent gradient, hairline border, inset highlight) holds the details.

<img src="../samples/html/weather_glass.png" alt="Glass weather card" width="200">

```html
{% set t = state_attr('weather.nice', 'temperature') | float(0) %}
<style>
.scene { position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 26px;
         background:
           radial-gradient(circle at 78% 22%, rgba(255,214,10,0.95) 0%, rgba(255,159,10,0.55) 14%, transparent 34%),
           radial-gradient(circle at 15% 85%, rgba(191,90,242,0.75) 0%, transparent 45%),
           radial-gradient(circle at 90% 90%, rgba(255,69,58,0.55) 0%, transparent 40%),
           linear-gradient(160deg, #1b2a6b 0%, #5b2a86 55%, #c2410c 100%); }
.sun { position: absolute; top: 24px; right: 30px; width: 56px; height: 56px; border-radius: 50%;
       background: radial-gradient(circle at 40% 35%, #fff7cc, #ffd60a 55%, #ff9f0a 100%);
       box-shadow: 0 0 30px 10px rgba(255,214,10,0.55), 0 0 80px 30px rgba(255,159,10,0.35); }
.head { position: absolute; top: 16px; left: 18px; color: #fff; line-height: 1; }
.city { font-size: 13px; font-weight: 800; letter-spacing: 0.14em; opacity: 0.8; }
.temp { font-size: 76px; font-weight: 800; letter-spacing: -0.04em; margin-top: 4px; }
.cond { font-size: 16px; font-weight: 700; opacity: 0.9; margin-top: 2px; }
.glass { position: absolute; left: 12px; right: 12px; bottom: 12px; height: 70px; border-radius: 20px;
         background: linear-gradient(160deg, rgba(255,255,255,0.30) 0%, rgba(255,255,255,0.10) 60%);
         border: 1px solid rgba(255,255,255,0.45);
         box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 10px 30px rgba(0,0,0,0.35);
         display: flex; align-items: center; justify-content: space-around; }
.stat { display: flex; flex-direction: column; align-items: center; gap: 3px; color: #fff; line-height: 1; }
.stat .icon { font-size: 18px; opacity: 0.9; }
.stat b { font-size: 17px; font-weight: 800; }
.stat span { font-size: 9px; font-weight: 800; letter-spacing: 0.14em; opacity: 0.75; }
</style>
<div class="scene"></div>
<div class="sun"></div>
<div class="head">
  <div class="city">{{ name | upper }}</div>
  <div class="temp">{{ t | round | int }}&deg;</div>
  <div class="cond">{{ states('weather.nice') | capitalize }} · feels {{ state_attr('weather.nice', 'apparent_temperature') | round | int }}&deg;</div>
</div>
<div class="glass">
  <div class="stat"><span class="icon">&#xF058E;</span><b>{{ state_attr('weather.nice', 'humidity') }}%</b><span>HUMID</span></div>
  <div class="stat"><span class="icon">&#xF059D;</span><b>{{ state_attr('weather.nice', 'wind_speed') | round | int }}</b><span>KM/H</span></div>
  <div class="stat"><span class="icon">&#xF0599;</span><b>{{ states('sensor.uv_index') }}</b><span>UV</span></div>
</div>
```

#### Energy flow

Solar, home, grid and battery as glowing nodes joined by SVG bezier curves whose stroke width follows the power on each branch. The battery node is a conic-gradient ring.

<img src="../samples/html/energy_orbit.png" alt="Energy flow" width="200">

```html
{% set solar = states('sensor.solar_power') | float(0) %}
{% set home = states('sensor.home_power') | float(0) %}
{% set grid = states('sensor.grid_power') | float(0) %}
{% set batt = states('sensor.home_battery') | float(0) %}
{% set batt_kw = states('sensor.home_battery_power') | float(0) %}
<style>
.c { position: absolute; }
.node { width: 64px; height: 64px; margin: -32px 0 0 -32px; border-radius: 50%; display: flex;
        flex-direction: column; align-items: center; justify-content: center; line-height: 1;
        background: radial-gradient(circle at 50% 30%, #1d2230, #0b0d13); }
.node .icon { font-size: 20px; }
.node b { font-size: 14px; font-weight: 800; color: #fff; margin-top: 2px; }
.node span { font-size: 8px; font-weight: 800; letter-spacing: 0.1em; color: rgba(255,255,255,0.55); margin-top: 2px; }
.hub { width: 84px; height: 84px; margin: -42px 0 0 -42px; }
.hub b { font-size: 20px; }
.inner { width: 52px; height: 52px; border-radius: 50%; background: #0b0d13; display: flex;
         flex-direction: column; align-items: center; justify-content: center; }
.glow { top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 50% 58%, rgba(10,132,255,0.28), transparent 55%),
                    radial-gradient(circle at 50% 10%, rgba(255,214,10,0.18), transparent 40%); }
</style>
<div class="c glow"></div>
<svg class="c" style="top: 0; left: 0; width: 240px" viewBox="0 0 240 240">
  <defs>
    <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd60a"/><stop offset="1" stop-color="#0a84ff"/></linearGradient>
    <linearGradient id="out" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#30d158"/><stop offset="1" stop-color="#ffd60a"/></linearGradient>
    <linearGradient id="bat" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#bf5af2"/><stop offset="1" stop-color="#ffd60a"/></linearGradient>
  </defs>
  {# Line width follows the power on each branch. #}
  <path d="M120 66 C 120 90, 120 100, 120 118" stroke="url(#sun)" stroke-width="{{ 4 + solar * 2.2 }}" fill="none" stroke-linecap="round"/>
  <path d="M42 164 C 70 164, 90 140, 104 130" stroke="url(#out)" stroke-width="{{ 4 + (grid | abs) * 2.2 }}" fill="none" stroke-linecap="round"/>
  <path d="M198 164 C 170 164, 150 140, 136 130" stroke="url(#bat)" stroke-width="{{ 4 + (batt_kw | abs) * 2.2 }}" fill="none" stroke-linecap="round"/>
</svg>
<div class="c node" style="left: 120px; top: 38px; box-shadow: 0 0 0 2px #ffd60a, 0 0 22px rgba(255,214,10,0.55)">
  <span class="icon" style="color: #ffd60a">&#xF0A72;</span><b>{{ solar }}</b><span>KW</span></div>
<div class="c node hub" style="left: 120px; top: 138px; box-shadow: 0 0 0 2px #0a84ff, 0 0 26px rgba(10,132,255,0.55)">
  <span class="icon" style="color: #0a84ff; font-size: 24px">&#xF02DC;</span><b>{{ home }}</b><span>KW HOME</span></div>
<div class="c node" style="left: 40px; top: 194px; box-shadow: 0 0 0 2px #30d158, 0 0 22px rgba(48,209,88,0.5)">
  <span class="icon" style="color: #30d158">&#xF0D3E;</span><b>{{ grid | abs }}</b><span>{{ 'EXPORT' if grid < 0 else 'IMPORT' }}</span></div>
<div class="c node" style="left: 200px; top: 194px;
     background: conic-gradient(#bf5af2 0deg {{ batt * 3.6 }}deg, #2a2233 {{ batt * 3.6 }}deg);
     box-shadow: 0 0 22px rgba(191,90,242,0.5)">
  <div class="inner"><b>{{ batt | int }}%</b><span>{{ 'CHARGE' if batt_kw > 0 else 'DRAIN' }}</span></div></div>
```

#### Activity rings

Three nested conic-gradient rings with rounded end caps (two dots: one at the start, one rotated to the current angle) and a colour-keyed legend.

<img src="../samples/html/activity_rings.png" alt="Activity rings" width="200">

```html
{% set rings = [
  (states('sensor.move_calories') | float(0) / 600, '#fa114f', '#ff6b8b', 'MOVE', states('sensor.move_calories') ~ ' kcal'),
  (states('sensor.exercise_minutes') | float(0) / 30, '#92e82a', '#c7ff7a', 'EXERCISE', states('sensor.exercise_minutes') ~ ' min'),
  (states('sensor.stand_hours') | float(0) / 12, '#1eeaef', '#8ff8fa', 'STAND', states('sensor.stand_hours') ~ ' / 12 h'),
] %}
<style>
.wrap { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center;
        padding-left: 10px; gap: 12px; }
.rings { position: relative; width: 132px; height: 132px; flex: none; }
.ring { position: absolute; border-radius: 50%; }
.hole { position: absolute; border-radius: 50%; background: #000; }
.cap { position: absolute; left: 50%; top: 50%; border-radius: 50%; }
.legend { display: flex; flex-direction: column; gap: 12px; line-height: 1; }
.legend span { font-size: 10px; font-weight: 800; letter-spacing: 0.12em; }
.legend b { display: block; font-size: 19px; font-weight: 800; color: #fff; margin-top: 3px; white-space: nowrap; }
</style>
<div class="wrap">
  <div class="rings">
  {% for frac, color, light, label, text in rings %}
    {% set inset = loop.index0 * 22 %}
    {% set deg = [frac, 1] | min * 360 %}
    {% set radius = 66 - inset - 9 %}
    <div class="ring" style="top: {{ inset }}px; left: {{ inset }}px; right: {{ inset }}px; bottom: {{ inset }}px;
         background: conic-gradient({{ color }} 0deg, {{ light }} {{ deg }}deg, {{ color }}33 {{ deg }}deg 360deg);
         box-shadow: 0 0 14px {{ color }}66;"></div>
    <div class="hole" style="top: {{ inset + 18 }}px; left: {{ inset + 18 }}px; right: {{ inset + 18 }}px; bottom: {{ inset + 18 }}px"></div>
    {# Rounded ends: a dot at the start and one at the current angle. #}
    <div class="cap" style="width: 18px; height: 18px; margin: -9px 0 0 -9px; background: {{ color }};
         transform: rotate(0deg) translateY(-{{ radius }}px)"></div>
    <div class="cap" style="width: 18px; height: 18px; margin: -9px 0 0 -9px; background: {{ light }};
         box-shadow: 0 0 8px rgba(0,0,0,0.6); transform: rotate({{ deg }}deg) translateY(-{{ radius }}px)"></div>
  {% endfor %}
  </div>
  <div class="legend">
  {% for frac, color, light, label, text in rings %}
    <div><span style="color: {{ color }}">{{ label }}</span><b>{{ text }}</b></div>
  {% endfor %}
  </div>
</div>
```

#### Electricity prices

Today's hourly prices as SVG bars filled with a green-to-red gradient. Past hours are dimmed, the current hour is outlined, and a Jinja `namespace` loop finds the cheapest three-hour window and highlights it.

<img src="../samples/html/price_chart.png" alt="Electricity prices" width="200">

```html
{% set prices = state_attr('sensor.nordpool', 'today') %}
{% set lo, hi = prices | min, prices | max %}
{% set hour = now.hour %}
{# Cheapest 3-hour window: the start index with the lowest sum. #}
{% set ns = namespace(best=0, best_sum=999) %}
{% for i in range(prices | length - 2) %}
  {% set s = prices[i] + prices[i + 1] + prices[i + 2] %}
  {% if s < ns.best_sum %}{% set ns.best, ns.best_sum = i, s %}{% endif %}
{% endfor %}
<style>
.wrap { position: absolute; top: 0; left: 0; right: 0; bottom: 0; padding: 14px 12px;
        background: radial-gradient(circle at 50% 0%, #1b2440 0%, #07090f 70%); }
.top { display: flex; justify-content: space-between; align-items: flex-end; line-height: 1; }
.lbl { font-size: 10px; font-weight: 800; letter-spacing: 0.16em; color: rgba(255,255,255,0.5); }
.now b { display: block; font-size: 40px; font-weight: 800; color: #fff; margin-top: 4px; white-space: nowrap; }
.now b small { font-size: 13px; color: rgba(255,255,255,0.6); }
.cheap { text-align: right; }
.cheap b { display: block; font-size: 17px; font-weight: 800; color: #30d158; margin-top: 4px; white-space: nowrap; }
.axis { display: flex; justify-content: space-between; font-size: 10px; font-weight: 700;
        color: rgba(255,255,255,0.45); margin-top: 4px; }
</style>
<div class="wrap">
  <div class="top">
    <div class="now"><div class="lbl">NOW · €/KWH</div><b>{{ '%.2f' | format(prices[hour]) }}<small> €</small></b></div>
    <div class="cheap"><div class="lbl">CHEAPEST 3H</div><b>{{ '%02d' | format(ns.best) }}–{{ '%02d' | format(ns.best + 3) }}h</b></div>
  </div>
  <svg viewBox="0 0 216 130" style="width: 216px; height: 130px; margin-top: 12px">
    <defs>
      <linearGradient id="hot" x1="0" y1="1" x2="0" y2="0">
        <stop offset="0" stop-color="#30d158"/><stop offset="0.55" stop-color="#ffd60a"/><stop offset="1" stop-color="#ff453a"/>
      </linearGradient>
    </defs>
    <rect x="{{ ns.best * 9 }}" y="0" width="27" height="130" rx="6" fill="rgba(48,209,88,0.14)"/>
    {% for p in prices %}
      {% set h = 8 + (p - lo) / (hi - lo) * 112 %}
      <rect x="{{ loop.index0 * 9 + 1 }}" y="{{ 130 - h }}" width="7" height="{{ h }}" rx="3.5"
            fill="url(#hot)" opacity="{{ 1 if loop.index0 == hour else (0.85 if loop.index0 > hour else 0.35) }}"/>
    {% endfor %}
    <rect x="{{ hour * 9 - 1 }}" y="{{ 130 - (8 + (prices[hour] - lo) / (hi - lo) * 112) - 6 }}" width="11"
          height="{{ 8 + (prices[hour] - lo) / (hi - lo) * 112 + 6 }}" rx="5.5" fill="none" stroke="#ffffff" stroke-width="2"/>
  </svg>
  <div class="axis"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>
</div>
```

#### Sun arc

Sunrise to sunset as a dashed SVG arc, with the elapsed part traced by `stroke-dasharray` and the sun placed on the curve with `rotate()`. Times are parsed from `sun.sun`'s attributes.

<img src="../samples/html/sun_arc.png" alt="Sun arc" width="200">

```html
{% set rise = state_attr('sun.sun', 'next_rising')[11:16] %}
{% set set_ = state_attr('sun.sun', 'next_setting')[11:16] %}
{% set r_min = (rise[:2] | int) * 60 + (rise[3:] | int) %}
{% set s_min = (set_[:2] | int) * 60 + (set_[3:] | int) %}
{% set n_min = now.hour * 60 + now.minute %}
{% set p = [[(n_min - r_min) / (s_min - r_min), 0] | max, 1] | min %}
{% set left = s_min - n_min %}
<style>
.sky { position: absolute; top: 0; left: 0; right: 0; bottom: 0;
       background: linear-gradient(180deg, #120b2e 0%, #4a1d5c 45%, #c2410c 82%, #f59e0b 100%); }
.c { position: absolute; left: 120px; top: 150px; }
/* No trig in Jinja: rotate + translate puts the sun on the arc. */
.sun { width: 26px; height: 26px; margin: -13px 0 0 -13px; border-radius: 50%;
       background: radial-gradient(circle at 40% 35%, #fff7cc, #ffd60a 60%, #ff9f0a);
       box-shadow: 0 0 18px 6px rgba(255,214,10,0.6), 0 0 50px 16px rgba(255,159,10,0.35); }
.ground { position: absolute; left: 0; right: 0; top: 150px; bottom: 0;
          background: linear-gradient(180deg, rgba(10,6,20,0.85), #05030a); }
.times { position: absolute; left: 14px; right: 14px; top: 160px; display: flex; justify-content: space-between;
         line-height: 1; color: #fff; }
.times span { display: block; font-size: 10px; font-weight: 800; letter-spacing: 0.14em; opacity: 0.6; }
.times b { font-size: 18px; font-weight: 800; }
.left { position: absolute; left: 0; right: 0; bottom: 16px; text-align: center; font-size: 15px;
        font-weight: 700; color: #ffb340; }
</style>
<div class="sky"></div>
<svg style="position: absolute; top: 0; left: 0; width: 240px" viewBox="0 0 240 240">
  <defs>
    <linearGradient id="done" x1="0" x2="1"><stop offset="0" stop-color="#ffd60a" stop-opacity="0.9"/>
      <stop offset="1" stop-color="#ff9f0a" stop-opacity="0.9"/></linearGradient>
  </defs>
  {# Half circle of radius 96 around (120, 150): length 3.1416 * 96 = 301.6 #}
  <path d="M24 150 A 96 96 0 0 1 216 150" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2" stroke-dasharray="4 6"/>
  <path d="M24 150 A 96 96 0 0 1 216 150" fill="none" stroke="url(#done)" stroke-width="4" stroke-linecap="round"
        stroke-dasharray="{{ 301.6 * p }} 400"/>
</svg>
<div class="ground"></div>
<div class="c sun" style="transform: rotate({{ -90 + p * 180 }}deg) translateY(-96px)"></div>
<div class="times"><div><span>SUNRISE</span><b>{{ rise }}</b></div>
  <div style="text-align: right"><span>SUNSET</span><b>{{ set_ }}</b></div></div>
<div class="left">{{ left // 60 }}h {{ '%02d' | format(left % 60) }}m of daylight left</div>
```

### Everyday cards

Simpler cards built on the theme's CSS variables, so they follow whichever theme the view uses.

#### EV charging ring

A `conic-gradient` ring whose angle comes from the battery percentage, a centered MDI icon, and text that switches with `is_state()`.

<img src="../samples/html/ev_charge.png" alt="EV charging ring" width="200">

```html
{% set pct = states('sensor.car_battery') | float(0) %}
{% set charging = is_state('binary_sensor.car_charging', 'on') %}
<style>
.ev { height: 100%; display: flex; flex-direction: column;
      align-items: center; justify-content: center; gap: 10px; }
.ring { width: 160px; height: 160px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        background: conic-gradient(var(--success) 0deg {{ pct * 3.6 }}deg,
                                   var(--track) {{ pct * 3.6 }}deg 360deg); }
.hole { width: 136px; height: 136px; border-radius: 50%; background: var(--bg);
        display: flex; flex-direction: column; align-items: center; justify-content: center; }
.pct { font-size: 46px; font-weight: 800; line-height: 1; }
.pct small { font-size: 20px; color: var(--text-secondary); }
.state { font-size: 12px; font-weight: 700; letter-spacing: 0.08em; margin-top: 4px; text-align: center;
         line-height: 1.25;
         color: {{ 'var(--success)' if charging else 'var(--text-tertiary)' }}; }
.range { font-size: 18px; font-weight: 600; color: var(--text-secondary); }
</style>
<div class="ev">
  <div class="ring"><div class="hole">
    <span class="icon" style="font-size: 20px; color: var(--success)">&#xF0B6C;</span>
    <div class="pct">{{ pct | round | int }}<small>%</small></div>
    <div class="state">{{ 'CHARGING<br>' ~ states('sensor.car_charge_power') ~ ' kW' if charging else 'PLUGGED IN' }}</div>
  </div></div>
  <div class="range">{{ states('sensor.car_range') }} km range</div>
</div>
```

#### Power dial (SVG)

An SVG half-circle drawn with `stroke-dasharray`. SVG paint attributes can't read `var(--x)`, so the template picks a concrete colour from thresholds.

<img src="../samples/html/power_dial.png" alt="Power dial (SVG)" width="200">

```html
{% set kw = states('sensor.home_power_now') | float(0) %}
{% set limit = 6.0 %}
{% set frac = [kw / limit, 1] | min %}
{# SVG paint attributes can't read var(--x): pick a concrete colour here. #}
{% set color = '#30d158' if frac < 0.5 else ('#ff9f0a' if frac < 0.8 else '#ff453a') %}
{% set arc = 3.1416 * 90 %}
<style>
.dial { height: 100%; display: flex; flex-direction: column; align-items: center;
        justify-content: center; }
.dial svg { width: 210px; }
.read { margin-top: -62px; text-align: center; }
.read .v { font-size: 52px; font-weight: 800; line-height: 1; }
.read .v small { font-size: 20px; color: var(--text-secondary); }
.read .l { font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: var(--text-tertiary); }
.ends { width: 196px; display: flex; justify-content: space-between; margin-top: 8px;
        font-size: 12px; font-weight: 600; color: var(--text-tertiary); }
</style>
<div class="dial">
  <svg viewBox="0 0 200 110">
    <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="rgba(255,255,255,0.12)"
          stroke-width="16" stroke-linecap="round"/>
    <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="{{ color }}"
          stroke-width="16" stroke-linecap="round"
          stroke-dasharray="{{ arc * frac }} {{ arc }}"/>
  </svg>
  <div class="read">
    <div class="v">{{ kw }}<small> kW</small></div>
    <div class="l">{{ name | upper }}</div>
  </div>
  <div class="ends"><span>0</span><span>{{ limit | int }} kW</span></div>
</div>
```

#### Departure board

A Jinja loop over a list attribute (`state_attr(..., 'departures')`), with delayed trains in red and long names truncated in the template.

<img src="../samples/html/departures.png" alt="Departure board" width="200">

```html
<style>
.board { height: 100%; display: flex; flex-direction: column; padding: 12px 10px;
         box-sizing: border-box; gap: 2px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;
        font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: var(--text-tertiary); }
.row { display: flex; align-items: center; gap: 8px; padding: 9px 0;
       border-top: 1px solid var(--hairline); }
.line { min-width: 34px; text-align: center; border-radius: 8px; padding: 3px 0;
        font-size: 14px; font-weight: 800; color: #000; background: var(--warning); }
.dest { flex: 1; font-size: 16px; font-weight: 600; white-space: nowrap; }
.min { white-space: nowrap; }
.min { font-size: 20px; font-weight: 800; text-align: right; }
.min small { font-size: 12px; color: var(--text-secondary); }
.late { color: var(--error); }
</style>
<div class="board">
  <div class="head"><span><span class="icon">&#xF052C;</span> {{ name | upper }}</span>
    <span>{{ now.strftime('%H:%M') }}</span></div>
  {% for d in state_attr('sensor.next_trains', 'departures')[:4] %}
  <div class="row">
    <span class="line">{{ d.line }}</span>
    <span class="dest">{{ d.destination | truncate(12, true, '…', 0) }}</span>
    <span class="min {{ 'late' if d.delay }}">{{ d.minutes }}<small> min</small></span>
  </div>
  {% endfor %}
</div>
```

#### Room temperatures

Bar widths computed in Jinja and clamped with `min`/`max`, coloured by threshold.

<img src="../samples/html/room_bars.png" alt="Room temperatures" width="200">

```html
{% set rooms = [(states('sensor.living_temp'), 'Living'), (states('sensor.bedroom_temp'), 'Bedroom'),
                (states('sensor.office_temp'), 'Office'), (states('sensor.kids_temp'), 'Kids'),
                (states('sensor.bathroom_temp'), 'Bath')] %}
<style>
.rooms { height: 100%; display: flex; flex-direction: column; justify-content: center;
         gap: 9px; padding: 0 14px; box-sizing: border-box; }
.title { font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: var(--text-tertiary); }
.r { display: flex; align-items: center; gap: 8px; }
.r .n { width: 62px; font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.r .track { flex: 1; height: 14px; border-radius: 7px; background: var(--track); }
.r .fill { height: 100%; border-radius: 7px; }
.r .t { width: 44px; text-align: right; font-size: 18px; font-weight: 800; }
</style>
<div class="rooms">
  <div class="title">ROOMS · °C</div>
  {% for value, label in rooms %}
  {% set t = value | float(0) %}
  {% set color = 'var(--info)' if t < 19 else ('var(--success)' if t < 23 else 'var(--warning)') %}
  <div class="r">
    <span class="n">{{ label }}</span>
    <div class="track"><div class="fill" style="width: {{ [[(t - 15) * 10, 4] | max, 100] | min }}%; background: {{ color }}"></div></div>
    <span class="t" style="color: {{ color }}">{{ t }}</span>
  </div>
  {% endfor %}
</div>
```

#### Who's home

Initials avatars ringed by presence, a CSS grid, and a count computed with `selectattr`.

<img src="../samples/html/presence.png" alt="Who's home" width="200">

```html
{% set people = [(states('person.alice'), 'Alice'), (states('person.bob'), 'Bob'),
                 (states('person.chloe'), 'Chloé'), (states('person.dan'), 'Dan')] %}
{% set home = people | selectattr(0, 'equalto', 'home') | list | length %}
<style>
.who { height: 100%; display: flex; flex-direction: column; justify-content: center;
       gap: 14px; padding: 0 10px; box-sizing: border-box; }
.count { text-align: center; font-size: 14px; font-weight: 700; letter-spacing: 0.08em;
         color: var(--text-tertiary); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 6px; }
.p { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.av { width: 58px; height: 58px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center; font-size: 26px; font-weight: 800; }
.in .av { background: rgba(48,209,88,0.18); border: 3px solid var(--success); }
.out .av { background: var(--chip-bg); border: 3px solid var(--hairline); color: var(--text-tertiary); }
.p .s { font-size: 12px; font-weight: 700; letter-spacing: 0.06em; }
.in .s { color: var(--success); } .out .s { color: var(--text-tertiary); }
</style>
<div class="who">
  <div class="count">{{ home }} OF {{ people | length }} HOME</div>
  <div class="grid">
  {% for st, label in people %}
    <div class="p {{ 'in' if st == 'home' else 'out' }}">
      <div class="av">{{ label[0] }}</div>
      <div class="s">{{ 'HOME' if st == 'home' else ('AWAY' if st == 'not_home' else st | upper) }}</div>
    </div>
  {% endfor %}
  </div>
</div>
```

#### Air quality

A level picked from a threshold table, a pill badge, and a marker positioned on a gradient scale.

<img src="../samples/html/air_quality.png" alt="Air quality" width="200">

```html
{% set co2 = states('sensor.office_co2') | float(0) %}
{% set levels = [(800, 'Good', 'var(--success)'), (1200, 'Moderate', 'var(--warning)'),
                 (99999, 'Ventilate', 'var(--error)')] %}
{% set level = levels | selectattr(0, 'gt', co2) | first %}
<style>
.aq { height: 100%; display: flex; flex-direction: column; justify-content: center;
      gap: 12px; padding: 0 18px; box-sizing: border-box; }
.top { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700;
       letter-spacing: 0.08em; color: var(--text-tertiary); }
.v { font-size: 72px; font-weight: 800; line-height: 0.9; letter-spacing: -0.02em; }
.v small { font-size: 18px; color: var(--text-secondary); letter-spacing: 0; }
.badge { align-self: flex-start; border-radius: 999px; padding: 5px 12px;
         font-size: 16px; font-weight: 800; color: #000; background: {{ level[2] }}; }
.scale { position: relative; height: 10px; border-radius: 5px;
         background: linear-gradient(90deg, var(--success) 0%, var(--success) 30%,
                     var(--warning) 50%, var(--error) 80%); }
.mark { position: absolute; top: -5px; width: 6px; height: 20px; border-radius: 3px;
        background: var(--text-primary); left: {{ [[(co2 - 400) / 16, 0] | max, 97] | min }}%; }
.ticks { display: flex; justify-content: space-between; font-size: 11px;
         font-weight: 600; color: var(--text-tertiary); }
</style>
<div class="aq">
  <div class="top"><span class="icon" style="font-size: 20px">&#xF07E4;</span>{{ name | upper }}</div>
  <div class="v">{{ co2 | int }}<small> ppm</small></div>
  <div class="badge">{{ level[1] }}</div>
  <div><div class="scale"><div class="mark"></div></div>
       <div class="ticks"><span>400</span><span>1200</span><span>2000</span></div></div>
</div>
```

### Written with utility classes

Templates without a `<style>` block (the synthwave clock keeps one for its own `@keyframes`), rendered with **Tailwind utility classes** on; the animated ones also need **Animate** on and a 2s **Animation Loop**. The control center, battery and alarm take their colours from the theme.

#### Control center

Six tiles from one Jinja macro: a tile that is on gets its role's tint (`bg-warning/15 ring-1 ring-warning/50`) and an off one the neutral `bg-chip`, both as classes built in the template.

<img src="../samples/html/tw_control_center.png" alt="Control center" width="200">

```html
{% macro tile(label, glyph, on, role, detail) %}
<div class="flex flex-col justify-between rounded-2xl p-2.5 {{ 'bg-%s/15 ring-1 ring-%s/50' % (role, role) if on else 'bg-chip' }}">
  {{ icon(glyph, role if on else 'muted', 24) }}
  <div class="leading-none">
    <div class="text-[13px] font-extrabold {{ 'text-fg' if on else 'text-fg-2' }}">{{ label }}</div>
    <div class="mt-1 text-[11px] font-bold {{ 'text-' ~ role if on else 'text-fg-3' }}">{{ detail }}</div>
  </div>
</div>
{% endmacro %}
{% set kitchen = is_state('light.kitchen', 'on') %}
{% set living = is_state('light.living_room', 'on') %}
{% set garage = is_state('cover.garage_door', 'open') %}
{% set locked = is_state('lock.front_door', 'locked') %}
{% set playing = is_state('media_player.living_room', 'playing') %}
{% set alarm = states('alarm_control_panel.home') %}
{% set active = [kitchen, living, garage, playing] | select | list | length %}
<div class="h-full flex flex-col gap-2 p-2.5">
  <div class="flex items-baseline justify-between px-1 pt-0.5 leading-none">
    <span class="text-[13px] font-extrabold tracking-[0.14em] text-fg-2">HOME</span>
    <span class="text-[12px] font-bold text-fg-3">{{ active }} active</span>
  </div>
  <div class="grid flex-1 grid-cols-3 grid-rows-2 gap-2">
    {{ tile('Kitchen', 'mdi:ceiling-light', kitchen, 'warning', '%d%%' % ((state_attr('light.kitchen', 'brightness') or 0) / 2.55) if kitchen else 'Off') }}
    {{ tile('Living', 'mdi:floor-lamp', living, 'warning', 'On' if living else 'Off') }}
    {{ tile('Music', 'mdi:speaker', playing, 'info', 'Playing' if playing else 'Idle') }}
    {{ tile('Garage', 'mdi:garage-open' if garage else 'mdi:garage', garage, 'error', 'Open' if garage else 'Closed') }}
    {{ tile('Door', 'mdi:lock' if locked else 'mdi:lock-open-variant', true, 'success' if locked else 'error', 'Locked' if locked else 'Unlocked') }}
    {{ tile('Alarm', 'mdi:shield-home', alarm.startswith('armed'), 'primary', alarm.replace('armed_', '') | capitalize if alarm.startswith('armed') else 'Off') }}
  </div>
</div>
```

#### Home battery

A glass capsule filled to the charge with a gradient that turns amber, then red, as it drains (`from-{{ hue }}-600`), a glow in the same colour, and the time to full or empty from the battery's power.

<img src="../samples/html/tw_battery.png" alt="Home battery" width="200">

```html
{% set pct = states('sensor.home_battery') | float(0) %}
{% set kw = states('sensor.home_battery_power') | float(0) %}
{% set capacity_kwh = 13.5 %}
{% set hours = (capacity_kwh * (100 - pct) / 100 / kw) if kw > 0 else (capacity_kwh * pct / 100 / -kw) if kw < 0 else 0 %}
{% set hue = 'emerald' if pct > 50 else 'amber' if pct > 20 else 'red' %}
<div class="h-full flex items-center gap-5 px-6">
  <div class="relative h-[188px] w-[76px] flex-none">
    <div class="absolute -top-2 left-1/2 h-2 w-7 -translate-x-1/2 rounded-t-md bg-fg/20"></div>
    <div class="absolute inset-0 rounded-[26px] bg-chip ring-2 ring-fg/15">
      <div class="absolute inset-1.5 overflow-hidden rounded-[20px]">
        <div class="absolute inset-x-0 bottom-0 h-[{{ pct | round | int }}%] rounded-[20px] bg-linear-to-t from-{{ hue }}-600 via-{{ hue }}-400 to-{{ hue }}-200 shadow-[0_0_24px] shadow-{{ hue }}-400/60"></div>
        <div class="absolute inset-0 bg-[repeating-linear-gradient(to_top,transparent_0_22px,rgb(0_0_0/0.35)_22px_24px)]"></div>
      </div>
    </div>
  </div>
  <div class="flex flex-col gap-2.5 leading-none whitespace-nowrap">
    <div class="text-[13px] font-extrabold tracking-[0.14em] text-fg-3">BATTERY</div>
    <div class="text-[54px] font-extrabold tracking-tight">{{ pct | round | int }}<span class="text-[24px] text-fg-2">%</span></div>
    <div class="flex items-center gap-1 text-[16px] font-extrabold {{ 'text-success' if kw > 0 else 'text-warning' if kw < 0 else 'text-fg-2' }}">
      {{ icon('mdi:battery-charging' if kw > 0 else 'mdi:battery-arrow-down' if kw < 0 else 'mdi:battery', 'success' if kw > 0 else 'warning' if kw < 0 else 'muted', 18) }}{{ '%+.1f' | format(kw) }} kW
    </div>
    {% if hours %}
    <div class="text-[13px] font-bold text-fg-2">{{ 'Full' if kw > 0 else 'Empty' }} in {{ hours | int }}h {{ '%02d' | format((hours * 60) % 60) }}m</div>
    {% endif %}
  </div>
</div>
```

#### Synthwave clock

Chrome digits from a gradient clipped to the text (`bg-clip-text text-transparent`) with a neon `drop-shadow`, a striped sun cut with a `mask-image`, a grid floor from a repeating conic gradient, horizon lines rolling towards you, and twinkling `animate-pulse` stars placed with classes built in Jinja (`left-[{{ x }}px]`).

<img src="../samples/html/tw_synthwave.gif" alt="Synthwave clock" width="200">

```html
<style>
@keyframes floor { from { top: 0%; opacity: 0; } 30% { opacity: 1; } to { top: 100%; opacity: 1; } }
</style>
<div class="relative h-full bg-linear-to-b from-indigo-950 via-purple-900 to-fuchsia-700">
  {% for x, y, d in [(18, 22, 0), (52, 64, 1), (96, 12, 0), (148, 40, 1), (196, 18, 0), (222, 70, 1), (30, 104, 1), (210, 112, 0)] %}
  <div class="absolute left-[{{ x }}px] top-[{{ y }}px] size-[2px] rounded-full bg-white/80 animate-pulse [animation-delay:-{{ d }}s]"></div>
  {% endfor %}
  <div class="absolute inset-x-0 top-3 text-center leading-none">
    <div class="text-[60px] font-extrabold tracking-tight bg-linear-to-b from-white from-40% to-pink-300 bg-clip-text text-transparent drop-shadow-[0_0_8px] drop-shadow-pink-500">{{ now.strftime('%H:%M') }}</div>
    <div class="mt-1.5 text-[12px] font-extrabold tracking-[0.35em] text-pink-200/80">{{ now.strftime('%a %d %b').upper() }}</div>
  </div>
  <div class="absolute left-1/2 top-[92px] size-[112px] -translate-x-1/2 rounded-full shadow-[0_0_56px_6px] shadow-pink-500/60"></div>
  <div class="absolute left-1/2 top-[92px] size-[112px] -translate-x-1/2 rounded-full bg-linear-to-b from-yellow-200 via-orange-400 to-pink-600 [mask-image:linear-gradient(to_bottom,#000_33%,transparent_33%_35%,#000_35%_42%,transparent_42%_45%,#000_45%_50%,transparent_50%_54%,#000_54%)]"></div>
  <div class="absolute inset-x-0 top-[160px] bottom-0 overflow-hidden bg-indigo-950 bg-[repeating-conic-gradient(from_90deg_at_50%_0%,transparent_0deg_9deg,rgb(244_114_182/0.75)_9deg_10deg)]">
    <div class="absolute inset-x-0 top-0 h-[2px] bg-pink-300 shadow-[0_0_14px_2px] shadow-pink-500"></div>
    {% for delay in [0, 0.5, 1, 1.5] %}
    <div class="absolute inset-x-0 h-px bg-pink-400 animate-[floor_2s_cubic-bezier(0.55,0,1,0.45)_infinite] [animation-delay:-{{ delay }}s]"></div>
    {% endfor %}
  </div>
</div>
```

#### Alarm

The alarm's state as a shield with two `animate-ping` rings half a cycle apart, and a chip per sensor group. Triggered turns it red; disarmed, muted.

<img src="../samples/html/tw_alarm.gif" alt="Alarm" width="200">

```html
{% set alarm = states('alarm_control_panel.home') %}
{% set role = 'error' if alarm == 'triggered' else 'success' if alarm.startswith('armed') else 'muted' %}
{% set sensors = [('Doors', is_state('binary_sensor.doors', 'on')), ('Windows', is_state('binary_sensor.windows', 'on')), ('Motion', is_state('binary_sensor.motion', 'on'))] %}
<div class="h-full flex flex-col items-center justify-between px-3 pt-5 pb-3">
  <div class="relative grid size-[96px] place-items-center">
    <div class="absolute inset-5 rounded-full ring-2 ring-{{ role }}/70 animate-ping"></div>
    <div class="absolute inset-5 rounded-full ring-2 ring-{{ role }}/70 animate-ping [animation-delay:-0.5s]"></div>
    <div class="relative grid size-[96px] place-items-center rounded-full bg-{{ role }}/15 ring-1 ring-{{ role }}/40 shadow-[0_0_36px] shadow-{{ role }}/40">
      {{ icon('mdi:shield-alert' if alarm == 'triggered' else 'mdi:shield-home', role, 50) }}
    </div>
  </div>
  <div class="text-center leading-none">
    <div class="text-[26px] font-extrabold tracking-[0.04em] text-{{ role }}">{{ alarm.replace('armed_', 'armed ').replace('_', ' ') | upper }}</div>
    <div class="mt-1.5 text-[13px] font-bold text-fg-3">{{ sensors | rejectattr(1) | list | length }} of {{ sensors | length }} sensors clear</div>
  </div>
  <div class="flex w-full gap-1.5">
    {% for name, tripped in sensors %}
    <div class="flex flex-1 items-center justify-center gap-1 rounded-full py-1.5 text-[11px] font-extrabold {{ 'bg-error/20 text-error' if tripped else 'bg-chip text-fg-2' }}">
      {{ icon('mdi:alert-circle' if tripped else 'mdi:check-circle', 'error' if tripped else 'success', 13) }}{{ name }}
    </div>
    {% endfor %}
  </div>
</div>
```

## Fluid templates

Each cell is its own CSS viewport, so one template adapts to every cell size: `vmin`/`vw` scale the type with the cell, and media queries shed detail when space runs out. A built-in fluid kit is injected into every document:

| Class | Purpose |
|-------|---------|
| `.cell` | Flex-column scaffold filling the cell (`space-evenly`); add `.row` for horizontal |
| `.t-hero` | Primary value, scales with cell size, capped by width |
| `.t-value` | Secondary emphasized value |
| `.t-unit` | Unit suffix, secondary color |
| `.t-label` | Caps caption, tertiary color |
| `.hide-short` | Hidden when the cell is under 100px tall |
| `.hide-narrow` | Hidden when the cell is under 100px wide |
| `.hide-small` | Hidden when either dimension is under 130px |

The same template at fullscreen, 2×2, and 3×3. The hero scales, and captions and detail bands drop out automatically:

<img src="../samples/html_widget_fluid_1x1.png" alt="Fluid template fullscreen" width="200"> <img src="../samples/html_widget_grid.png" alt="Fluid template 2x2" width="200"> <img src="../samples/html_widget_fluid_3x3.png" alt="Fluid template 3x3" width="200">

```html
<div class="cell">
  <div class="t-label hide-short">{{ name | upper }}</div>
  <div class="t-hero">{{ state }}&deg;</div>
  <div class="t-unit hide-small">feels 20&deg;</div>
</div>
```

These samples are generated by `scripts/generate_html_samples.py` (run via `scripts/update_samples.py`).

## Animated widgets (opt-in)

Turn on the device's **Animations** switch entity and any HTML widget with its **Animate** option enabled renders its CSS animations (`@keyframes`) to a looping animated GIF, which the display plays natively. Views without animated widgets keep the smaller, faster JPEG path, and static cells in an animated view are rendered once and shared across frames. The **Animation Loop** option sets the loop length (0.8–4s; the view uses the longest loop among its widgets, at 10fps up to 2s and 7fps beyond). Every example below loops in 2 seconds.

### What animates

- **Interpolates:** `transform` (`translate`, `rotate`, `scale`, with `transform-origin`), `opacity`, `color`, `background-color`, `box-shadow`, `filter: blur()`, `background-position`, sizes and offsets (`width`, `left`, …), `border-radius`, `border-width`, `font-size` and `letter-spacing`.
- **Doesn't:** anything inside an `<svg>`. SMIL `<animate>`, CSS animations on SVG shapes and `stroke-dashoffset` all render static. Animate the HTML element wrapping the SVG instead (rotate it, move it, fade it); the [wind turbine](#wind-turbine) and the [thunderstorm](#thunderstorm)'s lightning work that way.
- **Staggering:** negative `animation-delay` starts an element partway through its cycle, so copies of one animation can run out of phase (rain, ripples, equalizer bars).

### Seamless loops

The GIF repeats the loop forever, so the last frame has to flow into the first:

- Make every duration equal to the loop, or divide it evenly (a 0.5s raindrop falls four times in a 2s loop).
- Prefer full turns (`rotate(0deg)` → `rotate(360deg)`) and ping-pong keyframes whose `0%` and `100%` are identical (`0%, 100% { … } 50% { … }`).
- Avoid sliding a gradient by a percentage `background-position`: it seams when it wraps. Cross-fade two layers with `opacity`, or move an element instead.

Animations are off by default: a GIF costs upload size and device decode time. The upload budget is 400KB; past it, the integration shows the first frame as a still image. The generator checks every example below against that budget.

The view editor plays a view with an animated widget on its own: the still frame shows first, with the screen's progress bar, then the GIF an unrotated display is sent, under an *Animated* badge. It plays whether or not a display's Animations switch is on (the editor names any display showing the view with it off). After a change to what the view shows (renaming it doesn't count), the still updates at once and the animation renders again once you've stopped editing for a second; a version rendered in the last couple of minutes (say, after you put an option back) plays instantly. A playing GIF is rendered again when the preview's live data moves on (once a minute), so a clock in it stays current — as a display would, on its refresh interval. Over the upload budget, the editor says so and shows the first frame, as the display would; a frame that failed to render says so and offers Retry.

### Radar sweep

A conic-gradient beam turns once per loop; each person at home is a blip whose ping is delayed to fire exactly as the beam passes it (`animation-delay` = the blip's angle as a share of the turn). Positions come from `rotate() translateY() rotate()`, so no trigonometry in Jinja.

<img src="../samples/html/anim_radar.gif" alt="Radar sweep" width="200">

```html
{% set people = [(states('person.alice'), 'A', 40, 52), (states('person.bob'), 'B', 150, 78),
                 (states('person.chloe'), 'C', 230, 34), (states('person.dan'), 'D', 310, 70)] %}
{% set home = people | selectattr(0, 'equalto', 'home') | list %}
<style>
/* One full turn per 2 s loop: rotation is seamless. */
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes ping { 0% { transform: scale(0.6); opacity: 1; } 70%, 100% { transform: scale(2.6); opacity: 0; } }
.scope { position: absolute; top: 4px; left: 4px; right: 4px; bottom: 4px; border-radius: 50%;
         background: radial-gradient(circle, #06240f 0%, #031208 70%, #010603 100%);
         box-shadow: inset 0 0 0 2px #1d6b33, inset 0 0 40px rgba(48,209,88,0.25); }
.c { position: absolute; left: 50%; top: 50%; }
.ring { border-radius: 50%; border: 1px solid rgba(48,209,88,0.35); }
.axis { background: rgba(48,209,88,0.25); }
.beam { top: 0; left: 0; right: 0; bottom: 0; border-radius: 50%;
        background: conic-gradient(from 0deg, rgba(48,209,88,0) 0deg, rgba(48,209,88,0) 290deg,
                    rgba(48,209,88,0.55) 358deg, #b9ffcb 359deg, rgba(48,209,88,0) 360deg);
        animation: sweep 2s linear infinite; }
.blip { width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: #6dff9a;
        box-shadow: 0 0 10px #30d158; }
.wave { width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%;
        border: 2px solid #6dff9a; animation: ping 2s ease-out infinite; }
.tag { width: 20px; margin: 4px 0 0 -10px; text-align: center; font-size: 10px; font-weight: 800; color: #6dff9a; }
.hud { width: 160px; margin-left: -80px; text-align: center; line-height: 1; }
.hud b { font-size: 34px; font-weight: 800; color: #eafff0; }
.hud span { display: block; font-size: 10px; font-weight: 800; letter-spacing: 0.2em; color: #30d158; margin-top: 3px; }
</style>
<div class="scope">
  {% for r in [44, 74, 104] %}
  <div class="c ring" style="width: {{ r * 2 }}px; height: {{ r * 2 }}px; margin: -{{ r }}px 0 0 -{{ r }}px"></div>
  {% endfor %}
  <div class="c axis" style="width: 1px; height: 216px; margin: -108px 0 0 0"></div>
  <div class="c axis" style="width: 216px; height: 1px; margin: 0 0 0 -108px"></div>
  <div class="c beam" style="left: 0; top: 0"></div>
  {% for st, tag, angle, dist in people if st == 'home' %}
  {# Ping when the beam passes: delay = angle's share of the 2 s turn. #}
  <div class="c" style="transform: rotate({{ angle }}deg) translateY(-{{ dist }}px) rotate(-{{ angle }}deg)">
    <div class="c wave" style="animation-delay: -{{ 2 - angle / 180 }}s"></div>
    <div class="c blip"></div><div class="c tag">{{ tag }}</div>
  </div>
  {% endfor %}
  <div class="c hud" style="top: 160px"><b>{{ home | length }}</b><span>AT HOME</span></div>
</div>
```

### Now playing

A record built from `repeating-radial-gradient` grooves spins only while `media_player.living_room` is playing; an equalizer of `scaleY` bars with staggered negative delays bounces beside the title.

<img src="../samples/html/anim_vinyl.gif" alt="Now playing" width="200">

```html
{% set playing = is_state('media_player.living_room', 'playing') %}
<style>
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes eq { 0%, 100% { transform: scaleY(0.25); } 50% { transform: scaleY(1); } }
.deck { position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 30% 20%, #2a1b3d 0%, #0b0710 70%); }
.record { position: absolute; top: 14px; left: 14px; width: 150px; height: 150px; border-radius: 50%;
          background: repeating-radial-gradient(circle, #111 0px, #111 2px, #222 3px, #111 4px);
          box-shadow: 0 8px 24px rgba(0,0,0,0.8), 0 0 0 2px #2b2b2b;
          {{ 'animation: spin 2s linear infinite;' if playing }} }
.label { position: absolute; top: 47px; left: 47px; width: 56px; height: 56px; border-radius: 50%;
         background: conic-gradient(#ff375f 0deg 90deg, #ffd60a 90deg 180deg, #ff375f 180deg 270deg, #ffd60a 270deg 360deg);
         display: flex; align-items: center; justify-content: center; }
.label i { width: 8px; height: 8px; border-radius: 50%; background: #0b0710; }
.sheen { position: absolute; top: 14px; left: 14px; width: 150px; height: 150px; border-radius: 50%;
         background: conic-gradient(from 20deg, rgba(255,255,255,0) 0deg, rgba(255,255,255,0.10) 30deg,
                     rgba(255,255,255,0) 70deg, rgba(255,255,255,0) 200deg, rgba(255,255,255,0.08) 230deg,
                     rgba(255,255,255,0) 260deg); }
.arm { position: absolute; top: 18px; left: 192px; width: 6px; height: 112px; border-radius: 3px;
       background: linear-gradient(#e5e5ea, #8e8e93); transform-origin: 50% 0%; transform: rotate(28deg); }
.pivot { position: absolute; top: 10px; left: 183px; width: 24px; height: 24px; border-radius: 50%;
         background: radial-gradient(circle at 40% 35%, #f2f2f7, #636366); }
.meta { position: absolute; left: 16px; right: 16px; bottom: 14px; display: flex; align-items: flex-end;
        justify-content: space-between; }
.title { font-size: 18px; font-weight: 800; color: #fff; line-height: 1.1; white-space: nowrap; }
.artist { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.6); }
.bars { display: flex; align-items: flex-end; gap: 3px; height: 30px; }
.bars i { width: 5px; height: 30px; border-radius: 2px; background: linear-gradient(#ffd60a, #ff375f);
          transform-origin: 50% 100%; animation: eq 1s ease-in-out infinite; }
</style>
<div class="deck"></div>
<div class="record"><div class="label"><i></i></div></div>
<div class="sheen"></div>
<div class="pivot"></div><div class="arm"></div>
<div class="meta">
  <div>
    <div class="title">{{ state_attr('media_player.living_room', 'media_title') | truncate(16, true, '…', 0) }}</div>
    <div class="artist">{{ state_attr('media_player.living_room', 'media_artist') }}</div>
  </div>
  <div class="bars">
    {% for d in [0, -0.35, -0.7, -0.15, -0.5] %}<i style="animation-delay: {{ d }}s"></i>{% endfor %}
  </div>
</div>
```

### Thunderstorm

Rain is 34 drops on staggered delays inside a tilted container, falling four times per loop. Two cloud banks sway in opposite directions, and a lightning bolt (SVG) flashes with the whole sky.

<img src="../samples/html/anim_rain.gif" alt="Thunderstorm" width="200">

```html
{% set t = state_attr('weather.london', 'temperature') | float(0) %}
<style>
/* Drops fall 300px in 0.5 s: four falls per 2 s loop, so the loop is seamless. */
@keyframes fall { from { transform: translateY(-60px); } to { transform: translateY(240px); } }
@keyframes drift { 0%, 100% { transform: translateX(-12px); } 50% { transform: translateX(12px); } }
@keyframes drift2 { 0%, 100% { transform: translateX(10px); } 50% { transform: translateX(-10px); } }
@keyframes flash { 0%, 62%, 70%, 76%, 100% { opacity: 0; } 64% { opacity: 0.6; } 73% { opacity: 0.45; } }
.sky { position: absolute; top: 0; left: 0; right: 0; bottom: 0;
       background: linear-gradient(180deg, #0f1522 0%, #1f2b3d 55%, #33475f 100%); }
.flash { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #dbe6ff;
         animation: flash 2s linear infinite; }
.bolt { position: absolute; top: 74px; left: 132px; width: 54px; animation: flash 2s linear infinite; }
.rain { position: absolute; top: -20px; left: -30px; width: 300px; height: 280px; transform: rotate(12deg); }
.drop { position: absolute; top: 0; width: 3px; border-radius: 1px;
        background: linear-gradient(rgba(170,210,255,0), rgba(190,220,255,0.9));
        animation: fall 0.5s linear infinite; }
.cloud { position: absolute; }
.puff { position: absolute; border-radius: 50%; }
.read { position: absolute; left: 16px; bottom: 14px; color: #fff; line-height: 1; }
.read b { font-size: 64px; font-weight: 800; letter-spacing: -0.03em; }
.read span { display: block; font-size: 14px; font-weight: 700; opacity: 0.8; margin-top: 4px; }
</style>
<div class="sky"></div>
<div class="flash"></div>
<div class="rain">
{% for i in range(34) %}
  <div class="drop" style="left: {{ (i * 53) % 290 }}px; height: {{ 16 + (i % 4) * 6 }}px;
       animation-delay: -{{ (i * 0.137) % 0.5 }}s; opacity: {{ 0.35 + (i % 3) * 0.25 }}"></div>
{% endfor %}
</div>
<div class="cloud" style="top: 12px; left: 110px; width: 130px; height: 60px; animation: drift2 2s ease-in-out infinite">
  {% for l, tp, w in [(0, 24, 120), (20, 4, 54), (56, -6, 62)] %}
  <div class="puff" style="left: {{ l }}px; top: {{ tp }}px; width: {{ w }}px; height: {{ w if w < 100 else 36 }}px;
       background: linear-gradient(#59677b, #3a4657)"></div>
  {% endfor %}
</div>
<div class="cloud" style="top: 34px; left: 20px; width: 150px; height: 66px; animation: drift 2s ease-in-out infinite">
  {% for l, tp, w in [(0, 28, 150), (22, 6, 62), (66, -8, 74)] %}
  <div class="puff" style="left: {{ l }}px; top: {{ tp }}px; width: {{ w }}px; height: {{ w if w < 100 else 40 }}px;
       background: linear-gradient(#aab6c6, #6b7a8f)"></div>
  {% endfor %}
</div>
{# The bolt is plain SVG: it flashes because its wrapper's opacity animates. #}
<div class="bolt"><svg viewBox="0 0 40 80" style="width: 54px">
  <path d="M24 0 L6 44 L18 44 L10 80 L36 30 L22 30 L32 0 Z" fill="#fff6c2"/></svg></div>
<div class="read"><b>{{ t | round | int }}&deg;</b>
  <span>{{ name }} · Thunderstorm {{ state_attr('weather.london', 'precipitation_probability') }}%</span></div>
```

### Doorbell

Three ripples, a third of a loop apart, expand and fade from the button while the bell rocks on a `transform-origin` near its top. Both are switched off in Jinja when the doorbell is idle.

<img src="../samples/html/anim_doorbell.gif" alt="Doorbell" width="200">

```html
{% set ringing = is_state('binary_sensor.doorbell', 'on') %}
<style>
@keyframes ripple { 0% { transform: scale(0.45); opacity: 0.9; } 100% { transform: scale(1.6); opacity: 0; } }
@keyframes ring { 0%, 50%, 100% { transform: rotate(0deg); } 10%, 30% { transform: rotate(-16deg); }
                  20%, 40% { transform: rotate(16deg); } }
.bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #140b02; }
.c { position: absolute; left: 50%; top: 42%; }
.wave { width: 150px; height: 150px; margin: -75px 0 0 -75px; border-radius: 50%;
        border: 3px solid #ffb340; animation: ripple 2s ease-out infinite; }
.btn { width: 96px; height: 96px; margin: -48px 0 0 -48px; border-radius: 50%;
       background: radial-gradient(circle at 40% 30%, #ffd27a, #ff9f0a 60%, #c46a00 100%);
       box-shadow: 0 0 30px rgba(255,159,10,0.7), inset 0 -6px 12px rgba(0,0,0,0.3);
       display: flex; align-items: center; justify-content: center; }
.bell { font-size: 52px; color: #2a1600; transform-origin: 50% 10%; {{ 'animation: ring 1s ease-in-out infinite;' if ringing }} }
.txt { position: absolute; left: 0; right: 0; bottom: 18px; text-align: center; line-height: 1; }
.txt b { font-size: 22px; font-weight: 800; color: #fff; }
.txt span { display: block; font-size: 13px; font-weight: 700; color: #ffb340; margin-top: 5px; letter-spacing: 0.08em; }
</style>
<div class="bg"></div>
{% if ringing %}
  {% for d in [0, -0.67, -1.33] %}<div class="c wave" style="animation-delay: {{ d }}s"></div>{% endfor %}
{% endif %}
<div class="c btn"><span class="icon bell">&#xF009A;</span></div>
<div class="txt"><b>{{ 'Someone at the door' if ringing else 'Front door' }}</b>
  <span>{{ name | upper }} · {{ now.strftime('%H:%M') }}</span></div>
```

### Washing machine

Laundry tumbles in a rotating drum behind a glass reflection, and bubbles rise on staggered delays. The progress bar and phase come from three sensors.

<img src="../samples/html/anim_washer.gif" alt="Washing machine" width="200">

```html
{% set left = states('sensor.washer_remaining') | int(0) %}
{% set pct = states('sensor.washer_progress') | float(0) %}
<style>
@keyframes tumble { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes rise { 0% { transform: translateY(0px) scale(0.6); opacity: 0; } 20% { opacity: 0.9; }
                  100% { transform: translateY(-70px) scale(1.1); opacity: 0; } }
.body { position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(180deg, #f2f2f7 0%, #d1d1d6 100%); }
.c { position: absolute; left: 50%; top: 104px; }
.rim { width: 164px; height: 164px; margin: -82px 0 0 -82px; border-radius: 50%;
       background: conic-gradient(#8e8e93, #f2f2f7, #8e8e93, #e5e5ea, #8e8e93);
       box-shadow: 0 6px 16px rgba(0,0,0,0.3); }
.glass { width: 140px; height: 140px; margin: -70px 0 0 -70px; border-radius: 50%; overflow: hidden;
         background: radial-gradient(circle at 50% 70%, #0a84ff 0%, #064a8f 55%, #02203f 100%);
         box-shadow: inset 0 8px 20px rgba(0,0,0,0.55); }
.drum { position: absolute; top: 0; left: 0; width: 140px; height: 140px; animation: tumble 2s linear infinite; }
.sock { position: absolute; border-radius: 40%; }
.bub { position: absolute; width: 10px; height: 10px; border-radius: 50%;
       border: 1.5px solid rgba(255,255,255,0.8); animation: rise 2s ease-in infinite; }
.shine { width: 140px; height: 140px; margin: -70px 0 0 -70px; border-radius: 50%;
         background: linear-gradient(135deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0) 40%); }
.panel { position: absolute; top: 10px; left: 14px; right: 14px; display: flex; justify-content: space-between;
         align-items: center; font-size: 11px; font-weight: 800; letter-spacing: 0.14em; color: #3a3a3c; }
.led { color: #30d158; }
.foot { position: absolute; left: 16px; right: 16px; bottom: 12px; display: flex; align-items: center; gap: 10px; }
.foot b { font-size: 22px; font-weight: 800; color: #1c1c1e; white-space: nowrap; }
.track { flex: 1; height: 8px; border-radius: 4px; background: rgba(0,0,0,0.12); }
.fill { height: 8px; border-radius: 4px; background: #0a84ff; width: {{ pct }}%; }
</style>
<div class="body"></div>
<div class="panel"><span>{{ name | upper }}</span><span class="led">&#9679; {{ states('sensor.washer_phase') | upper }}</span></div>
<div class="c rim"></div>
<div class="c glass">
  <div class="drum">
    <div class="sock" style="left: 26px; top: 30px; width: 40px; height: 26px; background: #ff375f"></div>
    <div class="sock" style="left: 78px; top: 44px; width: 36px; height: 30px; background: #ffd60a"></div>
    <div class="sock" style="left: 40px; top: 84px; width: 46px; height: 24px; background: #30d158"></div>
    <div class="sock" style="left: 92px; top: 88px; width: 26px; height: 26px; background: #bf5af2"></div>
  </div>
  {% for i in range(6) %}
  <div class="bub" style="left: {{ 22 + i * 18 }}px; top: 110px; animation-delay: -{{ (i * 0.7) % 2 }}s"></div>
  {% endfor %}
</div>
<div class="c shine"></div>
<div class="foot"><b>{{ left }} min</b><div class="track"><div class="fill"></div></div></div>
```

### Wind turbine

The scenery and both rotors are SVG. Shapes inside an SVG can't animate, but the element wrapping one can, so each rotor is an SVG in a spinning `<div>`.

<img src="../samples/html/anim_turbine.gif" alt="Wind turbine" width="200">

```html
{% set kw = states('sensor.wind_turbine_power') | float(0) %}
<style>
/* SVG can't animate from inside, but the element wrapping it can:
   each rotor is an SVG in a div that spins around its centre. */
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.sky { position: absolute; top: 0; left: 0; right: 0; bottom: 0;
       background: linear-gradient(180deg, #1e4f8f 0%, #5fa4d9 60%, #a9d4f2 100%); }
.rotor { position: absolute; animation: spin 2s linear infinite; }
.read { position: absolute; top: 14px; left: 16px; color: #fff; line-height: 1; }
.read b { font-size: 48px; font-weight: 800; letter-spacing: -0.03em; }
.read b small { font-size: 18px; opacity: 0.8; letter-spacing: 0; }
.read span { display: block; font-size: 11px; font-weight: 800; letter-spacing: 0.16em; opacity: 0.85; margin-top: 4px; }
</style>
<div class="sky"></div>
{# Far turbine, then hills, then the near turbine: plain SVG, no animation. #}
<svg style="position: absolute; top: 0; left: 0; width: 240px" viewBox="0 0 240 240">
  <path d="M58 120 L61 120 L63 196 L56 196 Z" fill="#dfe8f2"/>
  <path d="M0 190 C 60 160, 120 200, 240 170 L240 240 L0 240 Z" fill="#3f7d4a"/>
  <path d="M0 214 C 80 190, 160 230, 240 205 L240 240 L0 240 Z" fill="#2e6338"/>
  <path d="M160 108 L167 108 L171 226 L156 226 Z" fill="#f4f7fb"/>
</svg>
<div class="rotor" style="left: 30px; top: 92px; width: 58px; height: 58px">
  <svg viewBox="0 0 100 100" style="width: 58px">
    {% for a in [0, 120, 240] %}
    <path d="M50 50 C 46 30, 47 10, 50 2 C 53 10, 54 30, 50 50 Z" fill="#eef3f8" transform="rotate({{ a }} 50 50)"/>
    {% endfor %}
    <circle cx="50" cy="50" r="5" fill="#c9d4df"/>
  </svg>
</div>
<div class="rotor" style="left: 105px; top: 50px; width: 116px; height: 116px; animation-delay: -0.4s">
  <svg viewBox="0 0 100 100" style="width: 116px">
    {% for a in [0, 120, 240] %}
    <path d="M50 50 C 45 30, 46 10, 50 1 C 54 10, 55 30, 50 50 Z" fill="#ffffff" transform="rotate({{ a }} 50 50)"/>
    {% endfor %}
    <circle cx="50" cy="50" r="6" fill="#d6dee7"/>
  </svg>
</div>
<div class="read"><b>{{ kw }}<small> kW</small></b><span>{{ name | upper }}</span></div>
```

### Lava lamp

Three soft radial-gradient blobs wander on ping-pong paths and scale as they cross, behind a large reading.

<img src="../samples/html/anim_lava.gif" alt="Lava lamp" width="200">

```html
<style>
/* Soft radial blobs wander on ping-pong paths (0% = 100%), so the loop never jumps. */
@keyframes a { 0%, 100% { transform: translate(0px, 0px) scale(1); } 50% { transform: translate(60px, 40px) scale(1.25); } }
@keyframes b { 0%, 100% { transform: translate(0px, 0px) scale(1.2); } 50% { transform: translate(-70px, -30px) scale(0.9); } }
@keyframes c { 0%, 100% { transform: translate(0px, 0px); } 50% { transform: translate(30px, -60px); } }
.bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #0b0420; }
.blob { position: absolute; border-radius: 50%; }
.read { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column;
        align-items: center; justify-content: center; color: #fff; line-height: 1; }
.read span { font-size: 14px; font-weight: 800; letter-spacing: 0.2em; opacity: 0.85; }
.read b { font-size: 88px; font-weight: 800; letter-spacing: -0.04em; margin: 6px 0; }
.read em { font-style: normal; font-size: 15px; font-weight: 700; opacity: 0.85; }
</style>
<div class="bg"></div>
<div class="blob" style="left: -40px; top: -30px; width: 200px; height: 200px; animation: a 2s ease-in-out infinite;
     background: radial-gradient(circle, rgba(255,55,95,0.9) 0%, rgba(255,55,95,0) 70%)"></div>
<div class="blob" style="left: 90px; top: 80px; width: 200px; height: 200px; animation: b 2s ease-in-out infinite;
     background: radial-gradient(circle, rgba(10,132,255,0.9) 0%, rgba(10,132,255,0) 70%)"></div>
<div class="blob" style="left: 20px; top: 110px; width: 160px; height: 160px; animation: c 2s ease-in-out infinite;
     background: radial-gradient(circle, rgba(191,90,242,0.85) 0%, rgba(191,90,242,0) 70%)"></div>
<div class="read"><span>{{ name | upper }}</span><b>{{ state }}&deg;</b><em>{{ states('sensor.living_humidity') }}% humidity</em></div>
```

## Limitations

No JavaScript, no network fetches (use `picture()` for an entity's picture, `data:` URIs for others), and nothing animates inside an `<svg>` (animate its wrapper). `filter` does `blur()` and `drop-shadow()` only: colour filters such as `grayscale()` are ignored, and only the first function of a list applies. `text-shadow` and `background-clip: text` work. `text-overflow: ellipsis` draws the "…" on a single `white-space: nowrap` line in an `overflow: hidden` box; for anything else, truncate long strings in the template (e.g. `{{ name | truncate(12, true, '…', 0) }}`).
