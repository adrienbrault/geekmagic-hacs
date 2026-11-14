# Device compatibility

GeekMagic devices with the same case/name can ship with very different firmware. The integration detects the firmware/API profile first, then uses the matching upload and display flow.

| Device / firmware profile | Detection | Render support | Notes |
| --- | --- | --- | --- |
| SmallTV Ultra stock firmware | `/app.json` or `/v.json` with Ultra model | Full | Uses `/doUpload?dir=/image/`, `/set?theme=3`, and `/set?img=/image/{filename}`. |
| SmallTV-PRO stock firmware | `/v.json` with `GeekMagic SmallTV-PRO`, or `/.sys/app.json` | Full, with managed album | Uses `/doUpload?dir=/image/` and `/set?theme=4`. Picture mode is an album slideshow, so the integration can manage the album and keep only `dashboard.jpg`. See [below](#smalltv-pro-picture-mode). |
| Ultra / SD_PRO community-style firmware | `/theme/list` and `/photo/list` | Supported through Photo slideshow | This firmware is very different from stock Ultra firmware. It uses `/config`, `/api/set?key=...`, `/photo/upload`, `/photo/toggle`, and `/theme/list`; it does not support direct `/set?img=` image selection. |
| Smart Weather Clock legacy web-form firmware | Root page fingerprint (`id="giflist"` + `action='/connect'`), after every JSON path 404s | Supported through Photo mode, slot 1 | No JSON API at all. State is read field-by-field from `/home?num=<n>`, brightness set via `/updateLEDBrightness`, the display mode via `/themeselect?getstate=<n>`, and uploads go to `POST /upload` into the fixed photo slot `file1.jpg` with the other four slots disabled. No page navigation, album settings, or file listing. |

Other GeekMagic devices may work if they expose one of those API profiles. If a device has the same product name but a different web UI or endpoint set, run the probe command from [Development](../development.md#testing-against-a-real-device) and attach the output to an issue, or [capture a report](#device-doesnt-work-help-us-add-support).

## Device reports

Per-device captures of every page, endpoint and payload, generated from real hardware:

- [SmallTV-PRO V3.3.76EN](new-pro/report.md)
- [SmallTV-Ultra V9.0.40](old-ultra/report.md)
- [SmallTV Ultra, SD_PRO community firmware](new-ultra-sdpro/report.md)
- [Smart Weather Clock, legacy web-form firmware](smart-weather-clock-legacy/report.md)

## SmallTV-PRO picture mode

Pro Picture mode is an album slideshow. During Pro setup, Home Assistant asks for confirmation to manage that album. When enabled, the integration removes other pictures from the Pro album and keeps one managed `dashboard.jpg` image updated so the display cannot rotate away from the HA dashboard. After setup, manually select the Picture app on the device; the integration does not press the Pro menu buttons automatically because the firmware does not expose enough menu state to do that reliably.

The Picture app's **Auto display** setting (in the device's web UI) is yours: the integration only turns it on, with a 1-second interval, when the album has never been configured, and otherwise leaves it as you set it. On older Pro firmware (V3.3.x) the Picture app only repaints the updated dashboard while Auto display is on, so if the dashboard stops updating there, turn it back on.

## Alternative firmware

For users interested in open-source firmware:

- [geekmagic-tv-esp8266](https://github.com/bvweerd/geekmagic-tv-esp8266) by [@bvweerd](https://github.com/bvweerd): an ESP8266 firmware for GeekMagic devices that implements the same API
- [SmartClock-OSS](https://github.com/michaeldale/smartclock-oss) by [@michaeldale](https://github.com/michaeldale): open-source firmware for the SD Pro "Smart Weather Clock" clone (not the SmallTV, Pro or Ultra), with geekmagic-hacs dashboard support

## Device doesn't work? Help us add support

If the integration doesn't work with your device or firmware version, you can generate a per-device reference report yourself and either attach it to a bug report or open a PR adding it to this folder. The repo ships with a Claude Code skill ([`.claude/skills/geekmagic-reverse-engineer/`](../../.claude/skills/geekmagic-reverse-engineer/SKILL.md)) that crawls your device, watches it run in a headless browser, and produces a redacted Markdown report describing every page, endpoint, parameter, and payload, purely from what the device tells us about itself.

To run it from a clone of this repo, point Claude Code at your device and ask:

> "Use the geekmagic-reverse-engineer skill against `<DEVICE-IP>` and produce a PR-ready report."

The skill handles privacy by default (credentials, SSIDs, IP addresses, MAC addresses are auto-redacted; review the output and scrub anything else before sharing). The reports above are good examples of the format.
