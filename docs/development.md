# Development

**Contents:** [Setup](#setup) · [Local Home Assistant](#local-home-assistant-docker) · [Samples and screenshots](#samples-and-screenshots) · [Testing against a real device](#testing-against-a-real-device)

Contributor conventions (design system, Blitz engine gotchas, commit style, release process) live in [CLAUDE.md](../CLAUDE.md).

## Setup

Use [`uv`](https://docs.astral.sh/uv/) for everything Python:

```bash
uv sync                              # Install dependencies
uv run pytest                        # Run tests
uv run ruff check .                  # Lint
uv run pre-commit run --all-files    # Run all checks
```

The panel's frontend lives in `custom_components/geekmagic/frontend/`. After changing `src/`, run `npm run build` there and commit the rebuilt `dist/` too, since HACS installs straight from the repo.

## Local Home Assistant (Docker)

One command starts a throwaway Home Assistant running this checkout's integration, ready to test: onboarding is done, you are logged in automatically, a fake GeekMagic device is added, and ten demo views are assigned to it (clock, entity, gauges, weather, media, charts, candlestick, climate, status, progress; plus the same board in five themes).

```bash
scripts/dev-ha              # start; prints the URLs below
scripts/dev-ha restart      # pick up Python changes (~10s)
scripts/dev-ha watch        # ...or restart automatically on every change
scripts/dev-ha logs         # follow HA logs
scripts/dev-ha screenshot   # regenerate the README's UI screenshots
scripts/dev-ha reset        # wipe everything; next start is fresh
```

- `http://localhost:8123`: Home Assistant (no login prompt)
- `http://localhost:8123/geekmagic`: the GeekMagic panel
- `http://localhost:8124`: the fake device's screen, live, with a log of every request the integration made (unimplemented endpoints show in red)

Requires Docker. Ports bind to `127.0.0.1` only; if 8123/8124 are taken, the next free ports are used and remembered per worktree. `GEEKMAGIC_HOST=<ip> scripts/dev-ha` also adds your real device (it is then driven by every Home Assistant that has it configured, so it will flip between their dashboards), and `HA_VERSION=beta scripts/dev-ha` tests against the HA beta. The demo data comes from HA's `demo` integration plus two sensors that random-walk every 10s, so charts have history. For scripts, the login is `dev`/`dev` and a long-lived API token is in `dev/.state/token`.

## Samples and screenshots

The device images in the README and these docs (`samples/`) are rendered by the real pipeline from mock data:

```bash
uv run python scripts/update_samples.py
```

It runs `scripts/generate_samples.py` and `scripts/generate_html_samples.py`, then deletes any file under `samples/` that no generator produced, so add a generator rather than placing images by hand. CI regenerates samples on pull requests and pushes a `chore: regenerate samples` commit when they change.

The README's UI screenshots, the View Editor (`docs/panel-editor.png`) and the Device info page (`docs/device-info.png`), come from the dev Home Assistant instead, on demand:

```bash
scripts/dev-ha                # if it isn't running yet
scripts/dev-ha screenshot     # both; headless Playwright, Chromium downloads once
scripts/dev-ha screenshot editor --view "05 Home status" --dark -o /tmp/editor.png
scripts/dev-ha screenshot device -o /tmp/device.png
```

It isn't part of CI or `update_samples.py`: the demo sensors and the clock move, so every capture differs.

## Testing against a real device

You can smoke-test the device client from a repo checkout before installing into Home Assistant:

```bash
uv run python scripts/device_cli.py probe <DEVICE-IP>
uv run python scripts/device_cli.py render-test <DEVICE-IP> --dashboard clock
uv run python scripts/device_cli.py upload-file <DEVICE-IP> path/to/image.jpg
uv run python scripts/device_cli.py brightness <DEVICE-IP> get
uv run python scripts/device_cli.py brightness <DEVICE-IP> set 80
```

`probe` only reads from the device. `render-test`, `upload-file`, and `brightness set` change the display. The render/upload smoke tests back up readable device settings first, hold the test image on screen for 15 seconds, then restore the original settings. Use `--hold-seconds N` to change the viewing window. `--takeover-album` can make Pro Picture mode deterministic by backing up the existing album, clearing it for the test, and restoring it afterward. If a Pro test image uploads but is not visible, manually select the Picture app on the device, or add `--try-enter-picture` to let the CLI press the Pro menu buttons during a live smoke test. Home Assistant does not press those buttons automatically. If your workstation has multiple routes to the device subnet, add `--bind-address LOCAL-IP` to the CLI command to force the source interface used for both aiohttp and raw firmware fallback requests.

For firmware that the integration doesn't support yet, see [Device compatibility](devices/README.md#device-doesnt-work-help-us-add-support).
