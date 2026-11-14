#!/usr/bin/env python3
"""Regenerate every README sample and prune the ones nothing produces.

Run from the repo root:

    uv run python scripts/update_samples.py

Runs ``generate_samples.py`` and ``generate_html_samples.py``, then deletes
any file under ``samples/`` (and the panel's widget previews, cropped from
the widget samples) that neither generator wrote or confirmed, so stale
renders can't accumulate. CI runs this same command on pull requests
(.github/workflows/samples.yml).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import generate_html_samples, generate_samples  # noqa: E402
from scripts.sample_io import PRODUCED, prune  # noqa: E402


def main() -> None:
    generate_samples.main()
    generate_html_samples.main()
    # Prune only after every generator finished: a crash mid-run must not
    # read as "these files are orphans".
    removed = prune(ROOT / "samples", PRODUCED)
    removed += prune(generate_samples.PREVIEWS_DIR, PRODUCED)
    print(f"Samples up to date: {len(PRODUCED)} produced, {len(removed)} pruned")


if __name__ == "__main__":
    main()
