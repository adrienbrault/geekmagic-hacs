# Entities, services & automations

Each GeekMagic device gets a set of entities for control and monitoring, plus a `geekmagic.notify` service for temporary alerts. Both work in automations, scripts and dashboards like any other Home Assistant entity or action.

**Contents:** [Entities](#entities) · [Flash memory writes](#flash-memory-writes) · [Presence-based sleep/wake](#presence-based-sleepwake) · [`geekmagic.notify`](#geekmagicnotify)

## Entities

Entity IDs follow the device's name: a device named "Desk Display" gets `number.desk_display_brightness`, and so on. Below, `<device>` stands for that prefix.

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| `select.<device>_display` | Select | What the screen shows: one of the views assigned to the device, or one of the firmware's built-in screens (clock, weather…). With View Cycling on, a built-in screen shows for one cycle interval, then the rotation resumes |
| `number.<device>_brightness` | Number | Display brightness (0-100%) |
| `switch.<device>_active` | Switch | Wake/sleep the display (see [below](#presence-based-sleepwake)) |
| `switch.<device>_view_cycling` | Switch | Automatically rotate through the assigned views (off by default; turning it on starts at 30 s) |
| `number.<device>_view_cycle_interval` | Number | Seconds between views when cycling (0 = manual only) |
| `switch.<device>_animations` | Switch | Render [animated HTML widgets](html-widget.md#animated-widgets-opt-in) as GIFs (off by default) |
| `number.<device>_refresh_interval` | Number | Seconds between renders (1-300) |
| `number.<device>_image_quality` | Number | JPEG quality of uploaded frames (1-95) |
| `select.<device>_display_rotation` | Select | Rotate the rendered image (0°, 90°, 180°, 270°) |

### Buttons

| Entity | Type | Description |
|--------|------|-------------|
| `button.<device>_refresh_display` | Button | Render and upload immediately |
| `button.<device>_next_screen` | Button | Switch to the next view in the rotation |
| `button.<device>_previous_screen` | Button | Switch to the previous view in the rotation |
| `button.<device>_reboot` | Button | Reboot the device, e.g. from an automation when it stops updating. The dashboard is pushed again once it is back. Stock Ultra/Pro use `/set?reboot=1`; SD_PRO and the legacy Weather Clock use `/restart`. Not created for unrecognised firmware |

### Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.<device>_status` | Sensor | Connection status, with the host, refresh interval and number of assigned views as attributes |
| `sensor.<device>_storage_used` | Sensor | Device storage usage percentage |
| `sensor.<device>_storage_free` | Sensor | Free storage in kB |
| `image.<device>_display_preview` | Image | The frame most recently sent to the display |

## Flash memory writes

Every upload is a write to the device's flash memory. A frame identical to the one already on the screen is not uploaded again: a static dashboard is re-sent only every 5 minutes (in case the device rebooted or was switched to another mode), plus right after a manual refresh, a settings change, a notification, or the device coming back online. Content that changes on every refresh (a clock with seconds, a live camera) is still uploaded every time, so a longer refresh interval and the Active switch below remain the main levers.

## Presence-based sleep/wake

The **Active** switch pauses the display when no one is in the room. When turned off, the screen dims to zero and all rendering stops (saving CPU cycles and flash memory writes). When turned on, brightness is restored and the display refreshes immediately.

Wire it to any presence sensor, motion sensor, media player or person tracker with an automation:

```yaml
automation:
  - alias: "GeekMagic: sleep when room is empty"
    triggers:
      - trigger: state
        entity_id: binary_sensor.office_presence
        to: "off"
        for: "00:05:00"   # optional: wait 5 min before sleeping
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.desk_display_active

  - alias: "GeekMagic: wake when room is occupied"
    triggers:
      - trigger: state
        entity_id: binary_sensor.office_presence
        to: "on"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.desk_display_active
```

## `geekmagic.notify`

Shows a temporary notification on the display, interrupting the normal view rotation.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `device_id` | Yes | - | GeekMagic device(s) to show the notification on |
| `message` | No | - | Notification text. If omitted, the image/icon displays fullscreen |
| `icon` | No | - | MDI icon to display (e.g., `mdi:bell`, `mdi:alert`) |
| `image` | No | - | Entity for image source (`camera.*`, `image.*`, or `media_player.*`) |
| `image_url` | No | - | Picture by URL or local path (see the [Image widget](widgets.md#image) for allowed paths). Takes precedence over `image` |
| `duration` | No | 10 | How long to show the notification (1-300 seconds) |
| `theme` | No | `watchos` | Visual theme for the notification (any [theme](../README.md#themes) name) |

### Examples

**Simple text notification:**

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  message: "Motion detected!"
  icon: mdi:motion-sensor
```

**Doorbell with camera snapshot:**

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  message: "Someone at the door"
  image: camera.front_door
  duration: 30
```

**Fullscreen camera (no message):**

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  image: camera.front_door
  duration: 15
```

**Now playing notification:**

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  message: "Now Playing"
  image: media_player.spotify
  theme: neon
```

**Alarm picture from a file (no message):**

```yaml
action: geekmagic.notify
data:
  device_id: "abc123"
  image_url: /local/alarm-bell.png
  duration: 20
```
