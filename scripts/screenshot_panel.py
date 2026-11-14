# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "playwright>=1.49",
# ]
# ///
"""Screenshot the GeekMagic panel's view editor from the dev Home Assistant.

Regenerates the README's View Editor screenshot on demand:

    scripts/dev-ha                       # start the dev HA (seeds the demo views)
    scripts/dev-ha screenshot            # writes docs/panel-editor.png

or directly, e.g. another view or a dark UI:

    uv run scripts/screenshot_panel.py --view "05 Home status" --dark -o /tmp/editor.png

The dev HA auto-logs the browser in (trusted_networks), so no credentials
are needed. The editor has no URL of its own, so the script opens the
panel, clicks the view's card and waits for the rendered preview.

Not wired into CI or update_samples.py on purpose: the demo sensors
random-walk and the clock moves, so every run differs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTS_FILE = REPO_ROOT / "dev" / ".state" / "ports.env"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "panel-editor.png"
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


def screenshot(url: str, view: str, output: Path, *, dark: bool, width: int, height: int) -> None:
    """Open the view editor for ``view`` and save a viewport screenshot."""
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
        # Let entity pickers and icons settle (they load lazily).
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_500)
        # Opening the editor can leave a scroll container mid-page; start
        # the shot at the top of every one (they live in shadow roots).
        page.evaluate(_SCROLL_ALL_TO_TOP)
        page.wait_for_timeout(300)

        output.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output))
        browser.close()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default=None, help="HA base URL (default: this worktree's dev HA)")
    parser.add_argument(
        "--view", default=DEFAULT_VIEW, help=f"view name (default: {DEFAULT_VIEW!r})"
    )
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dark", action="store_true", help="dark HA UI")
    parser.add_argument("--width", type=int, default=1280, help="viewport width in CSS px")
    parser.add_argument("--height", type=int, default=1000, help="viewport height in CSS px")
    args = parser.parse_args()

    _ensure_chromium()
    url = (args.url or _default_url()).rstrip("/")
    screenshot(url, args.view, args.output, dark=args.dark, width=args.width, height=args.height)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
