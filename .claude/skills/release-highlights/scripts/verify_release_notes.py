#!/usr/bin/env python3
"""Check that a release-notes edit left GitHub's generated block intact.

Usage:
    python3 .claude/skills/release-highlights/scripts/verify_release_notes.py TAG ORIGINAL_BODY.md

``ORIGINAL_BODY.md`` is the body saved *before* the edit (``gh release view
TAG --json body --jq .body``). Its generated block (everything up to and
including the ``**Full Changelog**`` line) is what must survive, so the
same check covers a first enrichment and a correction of an existing
Highlights section. The script fails unless:

* that generated block is still an exact prefix of the release body (line
  endings normalized, since GitHub rewrites CRLF to LF on save),
* ``## What's Changed`` and ``**Full Changelog**`` each appear exactly once,
* ``## Highlights`` comes after the generated changelog,
* every image / video URL in the body answers 200 with an ``image/*`` or
  ``video/*`` content type,
* every repo URL (raw file, ``blob``/``tree`` link) is pinned to a release
  tag or a full commit SHA, never a branch that moves (``main``), and every
  ``blob``/``tree`` link answers 200.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "release-highlights-verify"

_GH: str = shutil.which("gh") or sys.exit("the GitHub CLI (gh) is required, and must be on PATH")

# Media shapes the skill writes: HTML img/video tags, markdown images, and
# bare GitHub user-attachment URLs (which render as inline video players).
MEDIA_PATTERNS = (
    r'<img[^>]*\ssrc="([^"]+)"',
    r'<video[^>]*\ssrc="([^"]+)"',
    r"!\[[^\]]*\]\(([^)]+)\)",
    r"(https://github\.com/user-attachments/assets/[0-9a-fA-F-]+)",
)

GENERATED_MARKERS = ("## What's Changed", "**Full Changelog**")

# Repo URLs whose ref must not move: raw files and blob/tree links.
RAW_REF = r"https://raw\.githubusercontent\.com/[^/\s]+/[^/\s]+/([^/\s]+)/"
LINK_REF = r"https://github\.com/[^/\s]+/[^/\s]+/(?:blob|tree)/([^/\s]+)/[^\s)\"'>]*"
PINNED_REF = re.compile(r"\d+\.\d+\.\d+|[0-9a-f]{40}")


def gh(*args: str) -> str:
    """Run a gh command, exiting with its stderr on failure."""
    result = subprocess.run([_GH, *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def repo_name() -> str:
    """The current repository, as owner/name."""
    return gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()


def release(repo: str, tag: str) -> dict:
    """The release object for ``tag``."""
    return json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))


def media_urls(body: str) -> list[str]:
    """Every distinct media URL in the body, in document order."""
    seen: set[str] = set()
    urls: list[str] = []
    for pattern in MEDIA_PATTERNS:
        for url in re.findall(pattern, body, re.IGNORECASE):
            if url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def probe(url: str) -> tuple[int | None, str]:
    """GET one byte of ``url`` and report status and content type."""
    if not url.startswith(("http://", "https://")):
        return None, "not an http(s) URL"
    request = urllib.request.Request(  # noqa: S310 — scheme checked above
        url, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            response.read(1)
            return response.status, response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Content-Type", "") if err.headers else ""
    except Exception as err:  # report any failure verbatim
        return None, str(err)


def normalize(body: str) -> str:
    """Line-ending and trailing-whitespace tolerant body, for comparisons."""
    return body.replace("\r\n", "\n").strip()


def generated_block(body: str) -> str:
    """The body up to and including the ``**Full Changelog**`` line."""
    body = normalize(body)
    start = body.find("**Full Changelog**")
    if start == -1:
        return body
    end = body.find("\n", start)
    return body if end == -1 else body[:end]


def unpinned_refs(body: str) -> list[str]:
    """Repo URLs that point at a branch instead of a tag or a commit SHA."""
    return [
        match.group(0)
        for pattern in (RAW_REF, LINK_REF)
        for match in re.finditer(pattern, body)
        if not PINNED_REF.fullmatch(match.group(1))
    ]


def main() -> int:
    """Run the checks and return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="release tag, e.g. 1.9.6")
    parser.add_argument("original_body", type=Path, help="body saved before the edit")
    parser.add_argument(
        "--allow-missing-highlights",
        action="store_true",
        help="don't fail when the body has no `## Highlights` section",
    )
    args = parser.parse_args()

    repo = repo_name()
    rel = release(repo, args.tag)
    body = rel.get("body") or ""
    original = args.original_body.read_text(encoding="utf-8")

    failures: list[str] = []
    prefix_ok = bool(body) and normalize(body).startswith(generated_block(original))
    if not body:
        failures.append("the release body is empty")
    elif not prefix_ok:
        failures.append(
            "the generated block is not an exact prefix of the body — it was altered or moved"
        )

    for marker in GENERATED_MARKERS:
        count = body.count(marker)
        if count != 1:
            failures.append(f"`{marker}` appears {count} times (expected 1)")

    changed_at = body.find("## What's Changed")
    highlights_at = body.find("## Highlights")
    if highlights_at == -1:
        if not args.allow_missing_highlights:
            failures.append("no `## Highlights` section")
    elif highlights_at < changed_at:
        failures.append("`## Highlights` appears before the generated changelog")

    print(f"release : {args.tag} ({'draft' if rel.get('draft') else 'published'})")
    print(f"body    : {len(body)} chars, {len(media_urls(body))} media URL(s)")
    print(f"prefix  : {'ok' if prefix_ok else 'ALTERED'}")
    print(f"order   : changelog at {changed_at}, highlights at {highlights_at}")

    for index, url in enumerate(media_urls(body), start=1):
        status, content_type = probe(url)
        ok = status in (200, 206) and content_type.startswith(("image/", "video/"))
        print(f"  media {index}: {'ok ' if ok else 'BAD'} {status} {content_type or '?'} {url}")
        if not ok:
            failures.append(f"media {index} does not resolve to an image/video: {status} {url}")

    failures.extend(f"not pinned to a tag or commit SHA: {url}" for url in unpinned_refs(body))

    links = sorted({m.group(0) for m in re.finditer(LINK_REF, body)})
    for index, url in enumerate(links, start=1):
        status, _ = probe(url)
        print(f"  link {index}: {'ok ' if status in (200, 206) else 'BAD'} {status} {url}")
        if status not in (200, 206):
            failures.append(f"link {index} does not resolve: {status} {url}")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: generated block preserved, highlights below it, media and links live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
