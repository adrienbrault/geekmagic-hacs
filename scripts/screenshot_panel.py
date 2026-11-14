# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "playwright>=1.49",
# ]
# ///
"""Screenshot the GeekMagic UI from the dev Home Assistant.

Regenerates the README's screenshots on demand:

    scripts/dev-ha                       # start the dev HA (seeds device + demo views)
    scripts/dev-ha screenshot            # writes docs/panel-main.png, panel-editor.png and
                                         # device-info.png

or one of them, with options, e.g. another view or a dark UI:

    uv run scripts/screenshot_panel.py editor --view "05 Home status" --dark -o /tmp/editor.png
    uv run scripts/screenshot_panel.py device -o /tmp/device.png

The dev HA auto-logs the browser in (trusted_networks), so no credentials
are needed. The editor has no URL of its own, so the script opens the
panel, clicks the view's card and waits for the rendered preview. The
device page is found through the frontend's own entity registry.

Not wired into CI or update_samples.py on purpose: the demo sensors
random-walk and the clock moves, so every run differs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTS_FILE = REPO_ROOT / "dev" / ".state" / "ports.env"
OUTPUTS = {
    "main": REPO_ROOT / "docs" / "panel-main.png",
    "editor": REPO_ROOT / "docs" / "panel-editor.png",
    "device": REPO_ROOT / "docs" / "device-info.png",
}
# Default viewport height per target: the device page's Configuration card
# sits below Controls/Sensors, so it needs a taller window.
HEIGHTS = {"main": 1000, "editor": 1000, "device": 1400}
DEFAULT_VIEW = "01 Overview (watchOS)"


_SCROLL_ALL_TO_TOP = """() => {
  const walk = (root) => {
    for (const el of root.querySelectorAll("*")) {
      if (el.scrollTop > 0) el.scrollTop = 0;
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  window.scrollTo(0, 0);
  walk(document);
}"""

# The first device the GeekMagic integration created, via the frontend's
# entity registry (hass.entities carries platform + device_id).
_GEEKMAGIC_DEVICE_ID = """() => {
  const hass = document.querySelector("home-assistant")?.hass;
  if (!hass || !hass.entities) return null;
  const ent = Object.values(hass.entities).find(
    (e) => e.platform === "geekmagic" && e.device_id
  );
  return ent ? ent.device_id : null;
}"""


def _default_url() -> str:
    """The dev HA of THIS worktree (scripts/dev-ha remembers its ports)."""
    port = "8123"
    if PORTS_FILE.exists():
        for line in PORTS_FILE.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "HA_PORT" and value.strip():
                port = value.strip()
    # 127.0.0.1, not localhost: see CLAUDE.md (aiodns + localhost).
    return f"http://127.0.0.1:{port}"


def _ensure_chromium() -> None:
    """Install Playwright's Chromium on first use (one-time, ~150 MB)."""
    from playwright.sync_api import Error, sync_playwright  # ty: ignore[import-not-found]

    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Error:
        print("Installing Chromium for Playwright (one-time)...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def _settle(page: Any) -> None:
    """Let lazy pickers/icons load, then reset every scroll container."""
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1_500)
    # Navigation can leave a scroll container mid-page; start the shot at
    # the top of every one (they live in shadow roots).
    page.evaluate(_SCROLL_ALL_TO_TOP)
    page.wait_for_timeout(300)


def _open_editor(page: Any, url: str, view: str) -> None:
    """Open the panel's view editor for ``view`` with its preview loaded."""
    page.goto(f"{url}/geekmagic", wait_until="domcontentloaded")
    # Playwright's CSS engine pierces HA's shadow roots.
    card = page.locator("ha-card.view-card").filter(has_text=view)
    try:
        card.first.wait_for(timeout=60_000)
    except Exception as err:
        names = page.locator("ha-card.view-card h3").all_inner_texts()
        msg = f"view {view!r} not found on {url}/geekmagic (views: {names})"
        raise SystemExit(msg) from err
    card.first.click()

    # Wait for the server-rendered preview to arrive and decode.
    preview = page.locator("img.preview-image")
    preview.wait_for(timeout=60_000)
    page.wait_for_function(
        "img => img.complete && img.naturalWidth > 0",
        arg=preview.element_handle(),
        timeout=30_000,
    )


def _open_main(page: Any, url: str) -> None:
    """Open the panel's main page with the display's live screen loaded."""
    page.goto(f"{url}/geekmagic", wait_until="domcontentloaded")
    try:
        page.locator("gm-device-card gm-screen img").first.wait_for(timeout=60_000)
    except Exception as err:
        msg = f"no GeekMagic display on {url}/geekmagic (run scripts/dev-ha first)"
        raise SystemExit(msg) from err
    # Every gallery thumbnail rendered (they load a few at a time).
    # Playwright's CSS engine pierces the panel's shadow roots.
    page.locator("ha-card.view-card").first.wait_for(timeout=60_000)
    for _ in range(120):
        if page.locator("ha-card.view-card .skeleton").count() == 0:
            break
        page.wait_for_timeout(500)


def _open_device(page: Any, url: str) -> None:
    """Open the GeekMagic device's page in Settings → Devices."""
    page.goto(f"{url}/config/devices/dashboard", wait_until="domcontentloaded")
    try:
        page.wait_for_function(_GEEKMAGIC_DEVICE_ID, timeout=60_000)
    except Exception as err:
        msg = f"no GeekMagic device on {url} (run scripts/dev-ha first)"
        raise SystemExit(msg) from err
    device_id = page.evaluate(_GEEKMAGIC_DEVICE_ID)
    page.goto(f"{url}/config/devices/device/{device_id}", wait_until="domcontentloaded")
    # The entity cards render once the device's entities resolve.
    page.locator("ha-device-entities-card").first.wait_for(timeout=60_000)


def screenshot(
    url: str, target: str, output: Path, *, view: str, dark: bool, width: int, height: int
) -> None:
    """Open ``target`` ("main", "editor" or "device") and save a viewport screenshot."""
    from playwright.sync_api import sync_playwright  # ty: ignore[import-not-found]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2,
            color_scheme="dark" if dark else "light",
        )
        # Collapse HA's sidebar to its icon rail, as on a real desktop.
        context.add_init_script("localStorage.setItem('dockedSidebar', JSON.stringify('auto'))")
        page = context.new_page()
        if target == "main":
            _open_main(page, url)
        elif target == "editor":
            _open_editor(page, url, view)
        else:
            _open_device(page, url)
        _settle(page)

        output.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output))
        browser.close()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "target",
        nargs="?",
        choices=["all", *OUTPUTS],
        default="all",
        help="what to capture (default: all, to their docs/ paths)",
    )
    parser.add_argument("--url", default=None, help="HA base URL (default: this worktree's dev HA)")
    parser.add_argument(
        "--view", default=DEFAULT_VIEW, help=f"editor: view name (default: {DEFAULT_VIEW!r})"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="output path (single target only)"
    )
    parser.add_argument("--dark", action="store_true", help="dark HA UI")
    parser.add_argument("--width", type=int, default=1280, help="viewport width in CSS px")
    parser.add_argument(
        "--height", type=int, default=None, help="viewport height in CSS px (default per target)"
    )
    args = parser.parse_args()

    targets = list(OUTPUTS) if args.target == "all" else [args.target]
    if args.output and len(targets) > 1:
        parser.error("-o/--output needs a single target (main, editor or device)")

    _ensure_chromium()
    url = (args.url or _default_url()).rstrip("/")
    for target in targets:
        output = args.output or OUTPUTS[target]
        screenshot(
            url,
            target,
            output,
            view=args.view,
            dark=args.dark,
            width=args.width,
            height=args.height or HEIGHTS[target],
        )
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
