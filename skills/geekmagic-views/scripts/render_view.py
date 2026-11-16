#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["blitz-py==0.6.0", "pillow", "jinja2"]
# ///
"""Render a GeekMagic view to a PNG, offline, with demo or exported entity data.

It runs the geekmagic-hacs integration's own rendering code (engine, fonts,
widgets, layouts, themes), not a copy, so the PNG is what the 240x240
display would show. Only the entity data is fake (the demo home) or a
snapshot (a states file exported from Home Assistant).

    uv run render_view.py --schema               # layouts, themes, widgets (JSON)
    uv run render_view.py --demo                 # the demo home's entities
    uv run render_view.py view.json -o view.png [--zoom 2]
    uv run render_view.py view.json --states mine.json      # your entities
    uv run render_view.py view.json --scenario night.json --theme watchos \\
        --theme standby -o sheet.png             # contact sheet: rows x themes
    uv run render_view.py view.json --check      # validate only
    uv run render_view.py view.json --map sensor.a=sensor.b --save-view out.json

(``python3 render_view.py`` works too: without uv it installs its
dependencies into a private virtualenv under the cache directory.)

view.json   {"name", "layout", "theme", "widgets": [{"type", "slot",
            "entity_id", "label", "color": [r, g, b], "options": {...}}]}

states.json {"version": 1, "now": "2026-11-16T08:30:00+01:00",   (optional)
             "timezone": "Europe/Paris",                   (optional)
             "entities": {"sensor.x": {"state": "21.5", "attributes": {...},
                 "history": [20.1, ...] | {"24": [...]},  (chart, history())
                 "candles": [[o, h, l, c], ...] | {"3600x20": [...]},
                 "forecast": [{"datetime": "+1", ...}],    (weather, forecast())
                 "picture": "cover.jpg"}},                 (camera, album art)
             "templates": {"<slot>": {"<label template>": "<rendered>"}},
             "images": {"<image widget source>": "file.png"}}

Entity data starts from the demo home (demo/home.json); each --states file
adds or replaces entities on top (--no-demo starts empty). Paths in a
states file are relative to it.

export.json The panel's "Copy for AI": a states file (with "timezone" and
            "integration_version") carrying the view under "view". Pass it
            as the view: its entity data goes on top of the demo home.

Exit status: 0 rendered; 1 the view has errors or a widget failed to
render; 2 the integration or its engine can't be loaded.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import urllib.request
import venv
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# The integration release this skill ships with (== manifest.json "version")
INTEGRATION_VERSION = "1.9.5"
# == manifest.json's pin, and the PEP 723 block above
BLITZ_VERSION = "0.6.0"
REQUIREMENTS = [f"blitz-py=={BLITZ_VERSION}", "pillow", "jinja2"]
REPO = "adrienbrault/geekmagic-hacs"
PACKAGE = "custom_components.geekmagic"

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
DEMO_STATES = SKILL_DIR / "demo" / "home.json"

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_UNAVAILABLE = 2

# Set in the child when the script re-runs itself in its private virtualenv
_IN_PRIVATE_ENV = "GEEKMAGIC_VIEWS_PRIVATE_ENV"


class UnavailableError(Exception):
    """The integration or its dependencies can't be loaded."""


# =============================================================================
# Finding the integration
# =============================================================================


def cache_dir() -> Path:
    """Where downloads and the private virtualenv live."""
    if override := os.environ.get("GEEKMAGIC_VIEWS_CACHE"):
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "geekmagic-views"


def find_checkout(start: Path) -> Path | None:
    """The directory holding ``custom_components/geekmagic``, walking up from ``start``.

    Found when the skill runs from the repository (a clone, or a Claude
    plugin installed from it).
    """
    for directory in (start, *start.parents):
        if (directory / "custom_components" / "geekmagic" / "view_io.py").is_file():
            return directory
    return None


def tarball_url(version: str) -> str:
    """The GitHub source tarball of a release tag."""
    return f"https://codeload.github.com/{REPO}/tar.gz/refs/tags/{version}"


def fetch_integration(
    version: str,
    cache: Path,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> Path:
    """The integration of release ``version``, downloaded once into ``cache``.

    Only ``custom_components/geekmagic`` is extracted (``filter="data"``:
    no links out of the directory, no special files), into a temporary
    directory renamed into place once complete. Returns the directory
    holding ``custom_components``.
    """
    target = cache / f"integration-{version}"
    if (target / "custom_components" / "geekmagic" / "view_io.py").is_file():
        return target
    url = tarball_url(version)
    try:
        with urlopen(url, timeout=60) as response:
            data = response.read()
    except OSError as err:
        raise UnavailableError(f"could not download {url}: {err}") from err

    cache.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=cache, prefix=".download-"))
    try:
        with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tar:
            members = []
            for member in tar.getmembers():
                parts = PurePosixPath(member.name).parts
                # <repo>-<tag>/custom_components/geekmagic/...
                if parts[1:3] == ("custom_components", "geekmagic"):
                    members.append(member.replace(name="/".join(parts[1:]), deep=False))
            if not members:
                raise UnavailableError(f"{url} has no custom_components/geekmagic")
            tar.extractall(staging, members=members, filter="data")
        package = staging / "custom_components" / "geekmagic"
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("version") != version:
            raise UnavailableError(
                f"{url} is version {manifest.get('version')!r}, expected {version!r}"
            )
        if not (package / "view_io.py").is_file():
            raise UnavailableError(
                f"geekmagic-hacs {version} predates the offline renderer: "
                "run this script from a clone of the repository instead"
            )
        try:
            staging.rename(target)
        except OSError:
            if not (target / "custom_components" / "geekmagic" / "view_io.py").is_file():
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def locate_integration() -> Path:
    """The integration's code: this checkout, else the matching release."""
    if override := os.environ.get("GEEKMAGIC_INTEGRATION_DIR"):
        return Path(override)
    if (root := find_checkout(HERE)) is not None:
        return root
    return fetch_integration(INTEGRATION_VERSION, cache_dir())


def import_view_io(root: Path) -> types.ModuleType:
    """Import the integration's ``view_io`` without its Home Assistant ``__init__``.

    The package modules are registered empty (as the engine self-test does)
    so ``custom_components/geekmagic/__init__.py``, which needs Home
    Assistant, never runs. Existing entries are left alone.
    """
    for name, path in (
        ("custom_components", root / "custom_components"),
        (PACKAGE, root / "custom_components" / "geekmagic"),
    ):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(path)]
            sys.modules[name] = module
    return importlib.import_module(f"{PACKAGE}.view_io")


# =============================================================================
# Dependencies
# =============================================================================


def missing_requirements() -> list[str]:
    """The requirements this interpreter lacks (blitz-py at its exact pin)."""
    from importlib import metadata  # noqa: PLC0415

    missing = []
    try:
        blitz = metadata.version("blitz-py")
    except metadata.PackageNotFoundError:
        blitz = None
    if blitz != BLITZ_VERSION:
        missing.append(f"blitz-py=={BLITZ_VERSION}")
    for module, requirement in (("PIL", "pillow"), ("jinja2", "jinja2")):
        if importlib.util.find_spec(module) is None:
            missing.append(requirement)
    return missing


def private_env_python() -> Path:
    """Python of the private virtualenv, created and filled on first use.

    Never the system Python's site-packages (PEP 668): a virtualenv under
    the cache directory, one per Python version and engine pin.
    """
    env_dir = cache_dir() / f"venv-py{sys.version_info[0]}{sys.version_info[1]}-{BLITZ_VERSION}"
    python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    ready = env_dir / ".installed"
    if not ready.is_file():
        print(
            f"Installing {', '.join(REQUIREMENTS)} into {env_dir} (first run only)...",
            file=sys.stderr,
            flush=True,
        )
        venv.create(env_dir, with_pip=True, clear=True)
        subprocess.run(  # noqa: S603 - our own virtualenv's pip
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--quiet",
                "--disable-pip-version-check",
                *REQUIREMENTS,
            ],
            check=True,
        )
        ready.write_text(" ".join(REQUIREMENTS), encoding="utf-8")
    return python


def ensure_requirements() -> None:
    """Re-run in the private virtualenv when this interpreter lacks a requirement."""
    missing = missing_requirements()
    if not missing:
        return
    if os.environ.get(_IN_PRIVATE_ENV):
        raise UnavailableError(f"missing {', '.join(missing)} even in the private virtualenv")
    try:
        python = private_env_python()
    except (OSError, subprocess.CalledProcessError) as err:
        raise UnavailableError(
            f"missing {', '.join(missing)} and could not install them ({err}); "
            "run with `uv run render_view.py`, or pip install them in a virtualenv"
        ) from err
    result = subprocess.run(  # noqa: S603 - this script, in its virtualenv
        [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
        env={**os.environ, _IN_PRIVATE_ENV: "1"},
        check=False,
    )
    sys.exit(result.returncode)


# =============================================================================
# Output
# =============================================================================


def demo_listing(states: Any) -> str:
    """One line per entity: id, state, unit, name, and its extra data."""
    lines = []
    for entity_id, data in states.entities.items():
        attrs = data.get("attributes") or {}
        unit = attrs.get("unit_of_measurement")
        line = f"{entity_id}  {data.get('state')}{f' {unit}' if unit else ''}"
        if name := attrs.get("friendly_name"):
            line += f"  ({name})"
        if extra := [key for key in ("history", "candles", "forecast", "picture") if key in data]:
            line += f"  [{', '.join(extra)}]"
        lines.append(line)
    return "\n".join(lines)


class _Collect(logging.Handler):
    """Keeps the integration's warnings and errors logged during a render."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _parse_map(pairs: list[str]) -> dict[str, str]:
    mapping = {}
    for pair in pairs:
        old, sep, new = pair.partition("=")
        if not sep or not old or not new:
            raise SystemExit(f"--map takes old_id=new_id, got {pair!r}")
        mapping[old.strip()] = new.strip()
    return mapping


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("view", nargs="?", help="view JSON file ('-' for stdin)")
    parser.add_argument("-o", "--output", default="view.png", help="PNG to write")
    parser.add_argument(
        "--states", type=Path, action="append", default=[], help="entity data (repeatable)"
    )
    parser.add_argument("--no-demo", action="store_true", help="don't start from the demo home")
    parser.add_argument(
        "--scenario",
        type=Path,
        action="append",
        default=[],
        help="also render with these overrides (repeatable): one contact-sheet row each",
    )
    parser.add_argument(
        "--theme",
        action="append",
        default=[],
        help="render in this theme (repeatable): one contact-sheet column each",
    )
    parser.add_argument("--zoom", type=int, default=1, help="upscale the PNG (nearest)")
    parser.add_argument("--schema", action="store_true", help="print layouts, themes, widgets")
    parser.add_argument("--demo", action="store_true", help="list the entity data")
    parser.add_argument("--check", action="store_true", help="validate the view, don't render")
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="replace an entity id everywhere in the view (repeatable)",
    )
    parser.add_argument("--save-view", type=Path, help="write the (remapped) view here")
    return parser


def run(args: argparse.Namespace, view_io: types.ModuleType) -> int:  # noqa: PLR0911
    """Everything after the integration is loaded."""
    if args.schema:
        print(json.dumps(view_io.schema(), separators=(",", ":"), default=str))
        return EXIT_OK
    base = [] if args.no_demo else [DEMO_STATES]
    try:
        states = view_io.load_states(*base, *args.states)
    except view_io.ViewFileError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_INVALID
    if args.demo:
        print(demo_listing(states))
        return EXIT_OK
    if not args.view:
        print("error: a view JSON file is required (see --help)", file=sys.stderr)
        return EXIT_INVALID

    try:
        text = sys.stdin.read() if args.view == "-" else Path(args.view).read_text("utf-8")
        view = json.loads(text)
    except (OSError, json.JSONDecodeError) as err:
        print(f"error: {args.view}: {err}", file=sys.stderr)
        return EXIT_INVALID
    if isinstance(view, dict) and "layout" not in view and isinstance(view.get("view"), dict):
        # A panel export: the view, and the entity data it reads on top
        try:
            base_dir = Path.cwd() if args.view == "-" else Path(args.view).parent
            states = states.merge(view_io.parse_states(view, base_dir))
        except view_io.ViewFileError as err:
            print(f"error: {args.view}: {err}", file=sys.stderr)
            return EXIT_INVALID
        view = view["view"]
    if args.map:
        view = view_io.remap_entities(view, _parse_map(args.map))
    if args.save_view:
        args.save_view.write_text(json.dumps(view, indent=1, ensure_ascii=False) + "\n", "utf-8")
        print(f"wrote {args.save_view}")

    check = view_io.validate_view(view)
    for theme in args.theme:
        if theme not in view_io.schema()["themes"]:
            check.errors.append(f"unknown theme {theme!r} given to --theme")
    for warning in check.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in check.errors:
        print(f"error: {error}", file=sys.stderr)
    if not check.ok:
        return EXIT_INVALID
    for problem in view_io.missing_data(view, states):
        print(f"warning: {problem}", file=sys.stderr)
    if args.check:
        print("ok")
        return EXIT_OK

    engine = importlib.import_module(f"{PACKAGE}.engine")
    if not engine.engine_available():
        print(
            f"error: the rendering engine (blitz-py=={BLITZ_VERSION}) is not available",
            file=sys.stderr,
        )
        return EXIT_UNAVAILABLE

    collect = _Collect()
    logger = logging.getLogger(PACKAGE)
    logger.addHandler(collect)
    logger.propagate = False
    try:
        scenarios = [("base", states)] + [
            (path.stem, states.merge(view_io.load_states(path))) for path in args.scenario
        ]
        themes = args.theme or [view.get("theme")]
        renders = []
        for name, data in scenarios:
            row = []
            for theme in themes:
                themed = {**view, "theme": theme} if theme else view
                row.append((f"{name} / {theme or 'default'}", view_io.render_view(themed, data)))
            renders.append(row)
    except view_io.ViewFileError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_INVALID
    finally:
        logger.removeHandler(collect)

    if len(renders) == 1 and len(renders[0]) == 1:
        png = view_io.zoom_png(renders[0][0][1], args.zoom)
        what = "view"
    else:
        png = view_io.contact_sheet(renders, args.zoom)
        what = "contact sheet"
    Path(args.output).write_bytes(png)
    print(f"wrote {args.output} ({what})")

    for record in collect.records:
        print(f"{record.levelname.lower()}: {record.getMessage()}", file=sys.stderr)
    if any(record.levelno >= logging.ERROR for record in collect.records):
        return EXIT_INVALID
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Parse, load the integration, run."""
    args = build_parser().parse_args(argv)
    if sys.version_info < (3, 12):  # noqa: UP036 - python3 may be older than the script
        print("error: Python 3.12 or newer is required", file=sys.stderr)
        return EXIT_UNAVAILABLE
    try:
        ensure_requirements()
        view_io = import_view_io(locate_integration())
    except UnavailableError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_UNAVAILABLE
    return run(args, view_io)


if __name__ == "__main__":
    sys.exit(main())
