# GeekMagic Display for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

<p align="center">
  <img src="https://github.com/user-attachments/assets/09890b95-8a94-4df9-bf2f-6b9a6ac0d5e9" alt="GeekMagic Display running Home Assistant dashboard" width="400">
</p>

A Home Assistant custom integration for GeekMagic displays (SmallTV Pro, Ultra, and similar ESP8266/ESP32-based devices).

> **How it works:** Home Assistant renders your dashboards itself, with the [Blitz](https://github.com/DioxusLabs/blitz) HTML/CSS engine (no browser), and pushes the images to the device over HTTP. No flashing needed: the device keeps its firmware. Known stock firmware profiles are supported, as is the SD_PRO-style firmware some Ultra units ship with.

## Contents

- [Dashboard samples](#dashboard-samples)
- [Features](#features)
- [Installation](#installation)
- [Widgets](#widgets)
- [Layouts](#layouts)
- [Themes](#themes)
- [Configuration](#configuration)
- [Entities, services & automations](#entities-services--automations)
- [Device compatibility](#device-compatibility)
- [Development](#development)
- [Background & Credits](#background--credits)

More detail lives in [`docs/`](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/README.md): [every widget at every size](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md), the [HTML widget](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/html-widget.md), [layouts](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/layouts.md), [entities & the notify service](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/automation.md), [device compatibility](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/devices/README.md) and [development](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/development.md).

## Dashboard samples

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/01_system_monitor.png" alt="System Monitor" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/02_smart_home.png" alt="Smart Home" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/03_weather.png" alt="Weather" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/04_server_stats.png" alt="Server Stats" width="200">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/05_media_player.png" alt="Media Player" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/06_energy_monitor.png" alt="Energy Monitor" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/07_fitness.png" alt="Fitness Tracker" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/08_clock_dashboard.png" alt="Clock Dashboard" width="200">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/09_network_monitor.png" alt="Network Monitor" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/10_thermostat.png" alt="Thermostat" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/11_batteries.png" alt="Batteries" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/12_security.png" alt="Security" width="200">
</p>

## Features

- **17 widget types**: entity, date/time, gauge (bar/ring/arc), progress, multi progress, clock, weather, status, status list, climate, chart, candlestick, media player, camera, image, text, and a free-form HTML widget
- **19 layouts**: fullscreen, grids, splits, columns/rows, hero variants and sidebars
- **17 themes**: complete design systems (type, shapes, chrome, effects), not just palettes; the default is watchOS-inspired
- **Visual configuration**: a GeekMagic sidebar panel with a live preview
- **Global views**: create views once, assign them to any number of devices, and cycle through them automatically
- **HTML widget**: design your own cells with HTML/CSS and Jinja, optionally animated
- **Live labels**: every widget's label accepts a Home Assistant template
- **Notifications**: a `geekmagic.notify` action shows temporary alerts with text, icons, camera images, or any picture by URL/path
- **Automation-friendly**: brightness, sleep/wake, view selection and cycling are all entities
- **Configurable refresh**: every 1-300 seconds

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click "Custom repositories"
3. Add this repository URL (type: Integration)
4. Install "GeekMagic Display"
5. Restart Home Assistant

### Manual

1. Copy `custom_components/geekmagic` to your Home Assistant's `custom_components` folder
2. Restart Home Assistant

## Widgets

Every widget adapts to the cell it lands in. Here is each one fullscreen, in a 2×2 grid and in a 3×3 grid; click a name for every size and its options.

| Widget | Fullscreen | 2×2 grid | 3×3 grid |
|--------|:-:|:-:|:-:|
| **[Entity](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#entity)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/entity_icon_1x1.png" alt="Entity 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/entity_icon_2x2.png" alt="Entity 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/entity_icon_3x3.png" alt="Entity 3x3"> |
| **[Date / Time](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#date--time)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/datetime_1x1.png" alt="Date / Time 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/datetime_2x2.png" alt="Date / Time 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/datetime_3x3.png" alt="Date / Time 3x3"> |
| **[Gauge (Bar)](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#gauge)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_bar_1x1.png" alt="Gauge (Bar) 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_bar_2x2.png" alt="Gauge (Bar) 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_bar_3x3.png" alt="Gauge (Bar) 3x3"> |
| **[Gauge (Ring)](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#gauge)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_ring_1x1.png" alt="Gauge (Ring) 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_ring_2x2.png" alt="Gauge (Ring) 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_ring_3x3.png" alt="Gauge (Ring) 3x3"> |
| **[Gauge (Arc)](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#gauge)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_arc_1x1.png" alt="Gauge (Arc) 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_arc_2x2.png" alt="Gauge (Arc) 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/gauge_arc_3x3.png" alt="Gauge (Arc) 3x3"> |
| **[Progress](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#progress)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/progress_1x1.png" alt="Progress 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/progress_2x2.png" alt="Progress 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/progress_3x3.png" alt="Progress 3x3"> |
| **[Multi Progress](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#multi-progress)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/multi_progress_1x1.png" alt="Multi Progress 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/multi_progress_2x2.png" alt="Multi Progress 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/multi_progress_3x3.png" alt="Multi Progress 3x3"> |
| **[Clock](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#clock)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/clock_1x1.png" alt="Clock 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/clock_2x2.png" alt="Clock 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/clock_3x3.png" alt="Clock 3x3"> |
| **[Weather](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#weather)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/weather_1x1.png" alt="Weather 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/weather_2x2.png" alt="Weather 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/weather_3x3.png" alt="Weather 3x3"> |
| **[Status](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#status)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_1x1.png" alt="Status 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_2x2.png" alt="Status 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_3x3.png" alt="Status 3x3"> |
| **[Status List](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#status-list)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_list_1x1.png" alt="Status List 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_list_2x2.png" alt="Status List 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/status_list_3x3.png" alt="Status List 3x3"> |
| **[Climate](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#climate)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/climate_1x1.png" alt="Climate 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/climate_2x2.png" alt="Climate 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/climate_3x3.png" alt="Climate 3x3"> |
| **[Chart](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#chart)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/chart_1x1.png" alt="Chart 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/chart_2x2.png" alt="Chart 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/chart_3x3.png" alt="Chart 3x3"> |
| **[Candlestick](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#candlestick-chart)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/candlestick_1x1.png" alt="Candlestick 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/candlestick_2x2.png" alt="Candlestick 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/candlestick_3x3.png" alt="Candlestick 3x3"> |
| **[Media Player](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#media-player)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/media_1x1.png" alt="Media Player 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/media_2x2.png" alt="Media Player 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/media_3x3.png" alt="Media Player 3x3"> |
| **[Camera](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#camera)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/camera_1x1.png" alt="Camera 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/camera_2x2.png" alt="Camera 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/camera_3x3.png" alt="Camera 3x3"> |
| **[Image](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#image)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/image_1x1.png" alt="Image 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/image_2x2.png" alt="Image 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/image_3x3.png" alt="Image 3x3"> |
| **[Text](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#text)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/text_1x1.png" alt="Text 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/text_2x2.png" alt="Text 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/widgets/text_3x3.png" alt="Text 3x3"> |
| **[HTML](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/html-widget.md)** | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html_widget_fluid_1x1.png" alt="HTML 1x1"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html_widget_grid.png" alt="HTML 2x2"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html_widget_fluid_3x3.png" alt="HTML 3x3"> |

The HTML widget takes any HTML/CSS and Jinja you write, animated with CSS if you like. [20 example templates](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/html-widget.md#examples), each shown with its source:

<p align="center"><img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html/anim_radar.gif" alt="Radar sweep" width="200"> <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html/anim_vinyl.gif" alt="Now playing" width="200"> <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html/anim_turbine.gif" alt="Wind turbine" width="200"> <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/html/anim_washer.gif" alt="Washing machine" width="200"></p>

Every widget's label also accepts a Home Assistant template ([details](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#templates-in-labels)).

### State icons

Entity widgets pick icons and wording from the entity's state: binary sensors by `device_class` (door open/closed, motion detected/clear, lock locked/unlocked…, from Home Assistant's own icon definitions), and lights, switches and fans by on/off ([details](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/widgets.md#binary-sensor-states-and-icons)).

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/16_binary_sensors.png" alt="Binary sensor states" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/17_binary_sensors_more.png" alt="More binary sensor states" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/18_domain_icons.png" alt="Domain state icons" width="200">
</p>

## Layouts

19 layouts split the screen into slots. A few of them:

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_fullscreen.png" alt="Fullscreen" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_grid_2x2.png" alt="Grid 2x2" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_grid_3x3.png" alt="Grid 3x3" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_hero.png" alt="Hero" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_hero_corner_tl.png" alt="Hero corner" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_sidebar_left.png" alt="Sidebar left" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_split_h_1_2.png" alt="Split 1:2" width="200">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_three_row.png" alt="Three rows" width="200">
</p>

See [all layouts](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/layouts.md) with their slot counts.

## Themes

Choose from **17 built-in themes** that go beyond colours: each applies a complete design system with its own typography (rounded Nunito on most themes), spacing, shapes, tinted gauge tracks, and visual effects.

The default `watchOS` theme is inspired by Apple's watchOS Human Interface Guidelines: true-black background, Apple system colors, opacity-based text hierarchy, tinted Activity-ring style gauges, and no card chrome, so widgets float on the background for maximum information density. `StandBy` is the same system on translucent cards, like iOS StandBy widgets; `Night` is a red-on-black bedside mode that overrides every widget colour.

| watchOS | StandBy | Night | Classic |
|:-:|:-:|:-:|:-:|
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_watchos.png" alt="watchOS"><br>**Default**, Apple watchOS HIG-inspired | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_standby.png" alt="StandBy"><br>Translucent cards, like iOS StandBy | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_night.png" alt="Night"><br>Red-on-black bedside mode | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_classic.png" alt="Classic"><br>Subtle card chrome, system colors |
| **Minimal** | **Neon** | **Retro** | **Soft** |
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_minimal.png" alt="Minimal"><br>Sharp, monochrome | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_neon.png" alt="Neon"><br>Cyberpunk with glow | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_retro.png" alt="Retro"><br>Terminal scanlines | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_soft.png" alt="Soft"><br>Cozy, very rounded |
| **Ocean** | **Sunset** | **Forest** | **Light** |
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_ocean.png" alt="Ocean"><br>Deep blue, nautical | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_sunset.png" alt="Sunset"><br>Warm coral/orange | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_forest.png" alt="Forest"><br>Natural earth tones | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_light.png" alt="Light"><br>Clean white background |
| **Candy** | **Blueprint** | **Ink** | **Aurora** |
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_candy.png" alt="Candy"><br>Playful pastels | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_blueprint.png" alt="Blueprint"><br>Engineering drawing on drafting-grid paper | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_ink.png" alt="Ink"><br>Warm newsprint with one pot of red ink | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_aurora.png" alt="Aurora"><br>Luminous mesh-gradient poster, frosted glass |
| **Brutal** | | | |
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/layouts/layout_theme_brutal.png" alt="Brutal"><br>Neo-brutalism: hard borders, harder shadows | | | |

### StandBy and Night

The dashboards above in the **StandBy** theme (widgets on translucent cards) and the **Night** theme (a single red ramp for the bedside, overriding every widget colour):

| StandBy | | | |
|:-:|:-:|:-:|:-:|
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/19_standby_smart_home.png" alt="StandBy: Smart Home"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/19_standby_energy.png" alt="StandBy: Energy"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/19_standby_clock.png" alt="StandBy: Clock"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/19_standby_thermostat.png" alt="StandBy: Thermostat"> |
| **Night** | | | |
| <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/20_night_clock.png" alt="Night: Clock"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/20_night_weather.png" alt="Night: Weather"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/20_night_thermostat.png" alt="Night: Thermostat"> | <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/samples/20_night_batteries.png" alt="Night: Batteries"> |

## Configuration

### Adding a device

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "GeekMagic"
4. Enter your device's IP address

### Changing a device's address

If DHCP moves your device to a new IP, use **Reconfigure** on the integration entry (the three-dot menu next to the device) and enter the new address. The entry keeps its views, options and entity IDs, so automations referencing the device keep working.

### Using the GeekMagic panel

After installation, a **GeekMagic** item appears in your sidebar.

#### Views tab

Create and manage display views:

- **Create views** with the "+ Add View" button
- **Edit views** by clicking on them
- **Delete views** via the menu on each card

#### View editor

The editor provides a live preview and widget configuration:

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/docs/panel-editor.png" alt="GeekMagic View Editor" width="700">
</p>

- **Preview**: see the real rendering as you configure
- **Layout**: pick one of the 19 layouts
- **Theme**: pick one of the 17 themes
- **Widgets**: each slot shows a position grid; click cells to swap widget positions
- **Entity picker**: Home Assistant's native entity selector with filtering

#### Devices tab

Assign views to your GeekMagic devices:

- Check which views each device should display
- Assigned views form the device's rotation. Cycling is off by default: turn on the device's **View Cycling** switch (starts at 30 s) or set **View Cycle Interval** (1-300 s) to rotate automatically, or switch views by hand with the **Display** select and the next/previous buttons
- Picking one of the device's built-in modes (Clock, Weather...) while View Cycling is on shows it for one cycle interval, then the rotation resumes with the next view. Turn View Cycling off to stay on a built-in mode
- Drag to reorder the rotation sequence

#### Device info page

Each device exposes entities for brightness, refresh interval, the displayed view, and status (see [Entities, services & automations](#entities-services--automations)):

<p align="center">
  <img src="https://raw.githubusercontent.com/adrienbrault/geekmagic-hacs/main/docs/device-info.png" alt="GeekMagic Device Info" width="700">
</p>

## Entities, services & automations

Each device gets entities to control it from automations: a **Display** select (which view or built-in screen is shown), **Brightness**, an **Active** switch to sleep/wake the screen, **View Cycling** with its interval, **Animations**, refresh interval, image quality, rotation, and buttons to refresh or step through views. A `geekmagic.notify` action shows temporary alerts, with a camera snapshot or any picture by URL/path:

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  message: "Someone at the door"
  image: camera.front_door
  duration: 30
```

See [Entities, services & automations](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/automation.md) for the full entity list, how the integration limits flash writes, every notify option, and a presence-based sleep/wake automation.

## Device compatibility

| Device / firmware | Support |
| --- | --- |
| SmallTV Ultra, stock firmware | Full |
| SmallTV-PRO, stock firmware | Full, with a managed picture album (select the Picture app on the device once after setup) |
| Ultra with SD_PRO community-style firmware | Through the Photo slideshow |
| Smart Weather Clock, legacy web-form firmware | Through Photo mode, slot 1 |

Other GeekMagic devices may work if they expose one of those APIs. See [Device compatibility](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/devices/README.md) for how each profile is detected, per-device reports, open-source firmware, and how to capture a report for a device that doesn't work yet.

## Development

```bash
uv sync                    # install dependencies
uv run pytest              # run tests
scripts/dev-ha             # throwaway Home Assistant with a fake device and demo views (Docker)
```

See [Development](https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/development.md) for the local Home Assistant, regenerating samples and screenshots, and testing against a real device.

## Background & Credits

I have a **GeekMagic Ultra** with ESP8266, which has [limited possibilities for flashing with ESPHome](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029). Instead of fighting the hardware, this integration takes a different approach: render everything server-side and push images to the device.

Special thanks to:
- The [Home Assistant Community thread](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029) for documenting GeekMagic device capabilities
- **[Aydar (@aydarik)](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029/214)** for sharing the [bash script](https://gist.github.com/aydarik/e81edaf63041a85fb0325a1c8c2e4bac) that demonstrated how to push images to these devices - the core inspiration for this integration

## License

MIT
