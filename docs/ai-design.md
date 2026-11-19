# Design views with Claude

This repository is a Claude plugin. Its `geekmagic-views` skill lets Claude design views for your display, render them with the integration's own engine (the same fonts, widgets, layouts and themes as your device, so the picture Claude looks at is the frame the display would show), and hand you the view to import in the GeekMagic panel.

Claude designs against a demo home of about 45 entities (temperatures, energy, lights, locks, weather, media, a camera...) or against your own entities' data exported from the panel. It reads the same references as you would: [widgets](widgets.md), the [HTML widget](html-widget.md) and its gallery, and [layouts](layouts.md).

## Install

### Claude Code

In a Claude Code session:

```text
/plugin marketplace add adrienbrault/geekmagic-hacs
/plugin install geekmagic-hacs@geekmagic-hacs
```

Or from your shell: `claude plugin marketplace add adrienbrault/geekmagic-hacs`, then `claude plugin install geekmagic-hacs@geekmagic-hacs`.

The plugin's version is the integration's: a new release brings the skill's updates. Claude Code doesn't auto-update third-party marketplaces by default; to get them without asking, run `/plugin`, open the **Marketplaces** tab, select `geekmagic-hacs`, and choose **Enable auto-update**. Otherwise update it from the same place with **Update marketplace**.

The renderer runs with [uv](https://docs.astral.sh/uv/) when it is installed (`uv run` reads the script's dependencies), else with Python 3.12 or newer, which installs them (`blitz-py`, `pillow`, `jinja2`) into a private virtualenv under `~/.cache/geekmagic-views` the first time.

### claude.ai and the Claude desktop app

1. Go to [**Customize > Plugins**](https://claude.ai/customize/plugins).
2. Choose **Add > Add marketplace** and enter `adrienbrault/geekmagic-hacs`.
3. Add the **geekmagic-hacs** plugin.

Claude renders views by running code, so:

- Code execution must be turned on for your account (the setting that lets Claude run code and create files).
- Claude's sandbox must be able to download Python packages from PyPI the first time. On Team and Enterprise plans, an Owner decides whether code execution can reach the network, and which hosts.

To get updates, select **Check for updates** on the marketplace, or turn on **Sync automatically**.

The renderer needs the integration's code. It uses the copy installed with the plugin; when it can't find one, it downloads the matching integration release from GitHub. That download works from the first release that contains the renderer (any release after 1.9.5), and only if the sandbox can reach GitHub.

## Design a new view

Ask for what you want on the screen, for example:

- "Design a GeekMagic view for my bedside: time, tomorrow's weather, and whether the front door is locked."
- "A 2x2 energy view: solar, house power with today's curve, battery, and the electricity price."
- "An HTML widget that shows my next three buses as a departure board."

Claude picks a layout and widgets, renders the view, looks at the picture, fixes what reads badly, and checks it against edge cases (an entity going `unavailable`, long names, big numbers, night time) and other themes in one contact sheet. It shows you the renders as it goes, so you can steer: "bigger clock", "try the night theme", "swap the chart for a gauge".

It builds on the demo home's entities. Tell it your real entity ids (`sensor.office_co2`, `lock.entrance`...) and it swaps them in before handing the view over; anything it misses, the panel asks you to map when you import.

## Rework a view you already have

In the GeekMagic panel, open the view's menu:

- **Copy view JSON** copies the view alone. Paste it to Claude: it renders it with the demo home and works from there.
- **Copy for AI (includes entity data)** copies one JSON document: the view together with the current data of the entities it uses (states, attributes, chart history, candles, forecasts, what its label templates show), the time and your timezone. Before copying, the panel lists the entities it will send. Tokens, `entity_picture` and location attributes (latitude, longitude, GPS accuracy...) are stripped, and no pictures are included.

Paste the copy into the chat (or attach it as a file) and say what to change. Claude saves it and renders it as is first, so you both start from what your display shows, with your entity ids, values and clock. Where your view shows a camera snapshot or album art, Claude puts in a demo picture. The copy only holds the data your view reads today: if Claude adds an entity or changes a chart's period, it previews that part with demo data, and your display shows the real thing once you import.

If Home Assistant isn't served over https, the browser won't let the panel copy: it shows the text instead, selected, for you to copy.

The **Design views with AI** link next to **Import view** opens this page.

## Import the result

Claude ends with the view as JSON (a file, and in a code block). In Home Assistant:

1. Open the GeekMagic panel and choose **Import view**.
2. Paste the JSON. A whole **Copy for AI** document works too: the panel takes the view out of it and ignores the data.
3. If the view uses entity ids your Home Assistant doesn't have, pick a replacement for each.
4. Check the preview, then save it as a new view, or over an existing one (the one you copied, to replace it with Claude's rework).

Then add the view to a display's rotation, or edit it further in the view editor like any other view.
