#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
#     "beautifulsoup4>=4.12",
#     "playwright>=1.49",
# ]
# ///
"""Reverse-engineer a GeekMagic-style device by crawling its web UI.

No firmware assumptions: every endpoint, page, parameter, and payload in the
output was discovered by following links and string literals served *by the
device itself*. If it's not in the output, the device didn't tell us about it.

Output: a Markdown report + a JSON sidecar in the chosen output directory.

Usage:
    uv run scripts/reverse_engineer_device.py 10.76.1.217
    uv run scripts/reverse_engineer_device.py http://10.76.3.239 --out docs/devices
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from urllib.parse import parse_qsl, urljoin, urlparse, urlunsplit

import httpx
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 6.0
MAX_FETCHES = 200
# Body preview shown inline in the rendered report. Sized to fit the largest
# real-world responses we've observed (a ~20 KB JS file on SD_PRO firmware).
# Bumping this is cheap because there's only ever one preview per endpoint;
# the trade-off is a slightly bigger report.raw.md.
MAX_BODY_PREVIEW = 32768

# Path tokens that imply state change. Endpoints whose path matches any of
# these are catalogued but NEVER probed (we never want to flip a relay, reboot
# a device, or save a wifi password during reconnaissance).
#
# KNOWN LIMITATION: only the *path* of a URL is matched, not query params.
# An endpoint like `/api?cmd=restart` would be recorded under path `/api`,
# which doesn't match any token, and `probe_safe` would happily GET it. We
# accept this trade-off because matching query *values* against an English
# verb list produces too many false positives.
STATE_CHANGE_TOKENS = re.compile(
    # Verbs only — nouns like `brt`/`theme`/`config` would cause false positives
    # against legitimate read-only endpoints (`/brt.json`, `/theme/list`, etc.).
    # `interval` is included because some firmwares (SD_PRO) use it as the
    # last segment of a setter path: `/theme/interval?val=N`. The query-only
    # form `/theme/interval` (without `val=`) silently writes a default and
    # would not be caught if we matched only verbs.
    r"(?:^|/)(?:set|save|delete|del|remove|restart|reboot|update|upload|"
    r"connect|disconnect|clear|reset|factory|wipe|reload|format|toggle|"
    r"interval|doUpload|wifisave|update_ota)(?:$|/|\?)",
    re.IGNORECASE,
)

# JSON keys whose values are ALWAYS masked — credentials, tokens, etc.
# `pass` is anchored with word-boundary on both sides so it matches `wifi_pass`
# and `passphrase` but not `bypass` or `compass`.
SENSITIVE_KEY = re.compile(
    r"password|passphrase|(?:^|_)pass(?:$|_)|pwd|weatherkey|apikey|api_key|"
    r"secret|token|^p$|^key$",
    re.IGNORECASE,
)

# JSON keys whose values are masked unless --no-network-redact — wifi / network
# identity. Default-on because reports are typically attached to public bug
# reports or committed as docs. Includes single-letter `a` because the
# GeekMagic Pro firmware encodes the connected SSID under that key (`^p$` for
# password is in SENSITIVE_KEY for the same reason).
NETWORK_KEY = re.compile(
    r"^ssid$|wifi_ssid|wifi_name|^ss$|^bssid$|^mac$|mac_addr|hostname|^a$",
    re.IGNORECASE,
)

# IPv4 in plain text — replaced everywhere in the rendered report.
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# MAC address in plain text — colon-separated hex, six groups.
MAC_RE = re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")

# `<option value="X">` and `>X</option>` patterns — devices that return WiFi
# scan results as an HTML option list (e.g. SD_PRO `/scanwifi`) leak SSIDs
# this way. Sledgehammer: redact every option value/content in body previews.
# The optional `\\?` accepts JSON-escaped quotes (`value=\"X\"`) too — body
# previews end up inside JSON strings in the sidecar.
OPTION_VALUE_RE = re.compile(r"""(<option\b[^>]*\bvalue=)(\\?["'])(.*?)\2""", re.IGNORECASE)
OPTION_TEXT_RE = re.compile(r">([^<]{1,80})</option>", re.IGNORECASE)

# Captures any string literal in JS that looks like an absolute path.
JS_PATH_LIT = re.compile(r"""['"`](/[A-Za-z0-9_\-./?&=%~+:,@!$*();]*)['"`]""")

# Captures relative path-like literals ending with a known web extension.
# Catches dynamically-built nav (`{ href: "network.html" }`) that the absolute
# pattern misses. Resolved against the device root in `_normalize`.
JS_REL_FILE_LIT = re.compile(
    r"""['"`]((?!https?://)(?!//)[A-Za-z0-9_][\w./-]*\.(?:html?|js|css|json))['"`]"""
)

# Context-aware JS call patterns — give the path stronger evidence than a
# bare literal. The kind is recorded so the report can show *how* a path was
# discovered (e.g. `fetch('/x')` vs `'/x'` as a random string).
JS_CALL_PATTERNS: dict[str, re.Pattern[str]] = {
    "fetch": re.compile(r"""fetch\s*\(\s*['"`](/[^'"`]+)"""),
    "getData": re.compile(r"""getData\s*\(\s*['"`](/[^'"`]+)"""),
    "getResponse": re.compile(r"""getResponse\s*\(\s*['"`](/[^'"`]+)"""),
    "xhrOpen": re.compile(r"""\.open\s*\(\s*['"`][A-Z]+['"`]\s*,\s*['"`](/[^'"`]+)"""),
    "jquery": re.compile(r"""\$\.(?:get|post|ajax|getJSON)\s*\(\s*['"`](/[^'"`]+)"""),
    "assignAction": re.compile(r"""\.action\s*=\s*['"`](/[^'"`]+)"""),
    "windowLocation": re.compile(r"""(?:window\.)?location(?:\.href)?\s*=\s*['"`](/[^'"`]+)"""),
}


@dataclass
class Endpoint:
    path: str  # path only, no query
    methods: set[str] = field(default_factory=set)
    query_keys: set[str] = field(default_factory=set)
    examples: list[str] = field(default_factory=list)  # full path?query examples
    evidence: list[dict] = field(default_factory=list)
    form_fields: list[str] = field(default_factory=list)
    state_change: bool = False
    probe: dict | None = None


class _FailedResponse:
    """Stand-in for a connection failure so we can keep walking the tree."""

    def __init__(self, err: str) -> None:
        self.error = err
        self.status_code = 0
        self.headers: dict[str, str] = {}
        self.text = ""
        self.content = b""


class Crawler:
    def __init__(
        self,
        base: str,
        *,
        timeout: float,
        max_fetches: int,
        redact_network: bool = True,
    ) -> None:
        self.base = base.rstrip("/")
        self.host = urlparse(self.base).netloc
        self.client = httpx.Client(
            base_url=self.base,
            timeout=timeout,
            follow_redirects=False,
            headers={
                "Accept-Encoding": "gzip, deflate",
                "User-Agent": "geekmagic-reverse-engineer/0.1",
            },
        )
        self.max_fetches = max_fetches
        self.redact_network = redact_network
        self.fetched: dict[str, httpx.Response | _FailedResponse] = {}
        self.endpoints: dict[str, Endpoint] = {}

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- fetching ----

    def fetch(self, path: str) -> httpx.Response | _FailedResponse | None:
        if path in self.fetched:
            return self.fetched[path]
        if len(self.fetched) >= self.max_fetches:
            return None
        try:
            r = self.client.get(path)
        except (httpx.HTTPError, OSError) as e:
            failed = _FailedResponse(str(e))
            self.fetched[path] = failed
            return failed
        self.fetched[path] = r
        return r

    def _normalize(self, raw: str) -> str:
        """Return a path-only (and query if any) URL on the target host, or ''."""
        if not raw or raw.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
            return ""
        u = urlparse(urljoin(self.base + "/", raw))
        if u.scheme and u.scheme not in ("http", "https"):
            return ""
        if u.netloc and u.netloc != self.host:
            return ""
        path = u.path or "/"
        return urlunsplit(("", "", path, u.query, ""))

    # ---- crawl loop ----

    def crawl(self) -> None:
        # deque for O(1) popleft + parallel set for O(1) membership test.
        queue: deque[str] = deque(["/"])
        queued: set[str] = {"/"}
        while queue:
            current = queue.popleft()
            r = self.fetch(current)
            if r is None or isinstance(r, _FailedResponse) or r.status_code != 200:
                continue
            ct = r.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            text = r.text if any(t in ct for t in ("text", "json", "javascript")) else ""
            new_paths = self._extract(current, text, ct)
            for p in new_paths:
                if p and p not in self.fetched and p not in queued:
                    queue.append(p)
                    queued.add(p)

    # ---- extraction ----

    def _record(self, source: str, raw_path: str, kind: str, **extra: Any) -> str:
        """Record an endpoint reference and return its normalized path."""
        norm = self._normalize(raw_path)
        if not norm:
            return ""
        ep_path, _, query = norm.partition("?")
        ep = self.endpoints.setdefault(ep_path, Endpoint(path=ep_path))
        ep.methods.add(extra.get("method", "GET"))
        if query:
            for k, _v in parse_qsl(query, keep_blank_values=True):
                ep.query_keys.add(k)
            if norm not in ep.examples:
                ep.examples.append(norm)
        ep.evidence.append({"source": source, "kind": kind, **extra})
        if STATE_CHANGE_TOKENS.search(ep_path):
            ep.state_change = True
        return norm

    def _extract(self, source: str, text: str, ct: str) -> list[str]:
        new_paths: list[str] = []

        if "html" in ct:
            soup = BeautifulSoup(text, "html.parser")

            for tag in soup.find_all(href=True):
                href = tag.get("href")
                norm = self._record(source, href, "html_href", tag=tag.name)
                if norm and _is_followable(norm) and not _is_state_change_path(norm):
                    new_paths.append(norm)

            for tag in soup.find_all(src=True):
                src = tag.get("src")
                norm = self._record(source, src, "html_src", tag=tag.name)
                if norm and _is_followable(norm) and not _is_state_change_path(norm):
                    new_paths.append(norm)

            for form in soup.find_all("form"):
                action = form.get("action") or source
                method = (form.get("method") or "GET").upper()
                fields = [
                    i.get("name")
                    for i in form.find_all(["input", "select", "textarea"])
                    if i.get("name")
                ]
                norm = self._record(source, action, "form", method=method, fields=fields)
                if norm:
                    ep_path = norm.split("?", 1)[0]
                    ep = self.endpoints[ep_path]
                    for f in fields:
                        if f not in ep.form_fields:
                            ep.form_fields.append(f)
                    # A form is a state-change only if its method is not GET, or
                    # its action path already matches the state-change heuristic.
                    # A `<form method="GET" action="/status.json">` is a search
                    # form, not a mutation — leave it probable.
                    if method != "GET" or _is_state_change_path(ep_path):
                        ep.state_change = True

            body = soup.find("body")
            onload = body.get("onload", "") if body else ""
            for m in JS_PATH_LIT.finditer(onload):
                self._record(source, m.group(1), "html_onload")

            for tag in soup.find_all(onclick=True):
                for m in JS_PATH_LIT.finditer(tag.get("onclick", "")):
                    self._record(source, m.group(1), "html_onclick", element=tag.name)

            for script in soup.find_all("script"):
                if script.string:
                    new_paths.extend(self._extract_js(source, script.string))

        elif "javascript" in ct or source.endswith(".js"):
            new_paths.extend(self._extract_js(source, text))

        elif "json" in ct:
            self._extract_json_paths(source, text)

        return new_paths

    def _extract_js(self, source: str, text: str) -> list[str]:
        text = _strip_js_comments(text)

        new_paths: list[str] = []
        seen: set[str] = set()
        for kind, pat in JS_CALL_PATTERNS.items():
            for m in pat.finditer(text):
                p = m.group(1)
                self._record(source, p, f"js_{kind}")
                seen.add(p)

        # Catch-all literal — but only when not already attributed to a stronger
        # context. Helps surface things like inline string constants.
        for m in JS_PATH_LIT.finditer(text):
            p = m.group(1)
            if p in seen:
                continue
            self._record(source, p, "js_literal")
            seen.add(p)

        # Relative literals ending in .html/.js/.css/.json — common pattern for
        # dynamically-built nav. Enqueue them as crawl targets when followable.
        for m in JS_REL_FILE_LIT.finditer(text):
            p = m.group(1)
            if p in seen:
                continue
            norm = self._record(source, p, "js_rel_file")
            if norm and _is_followable(norm) and not _is_state_change_path(norm):
                new_paths.append(norm)

        return new_paths

    def _extract_json_paths(self, source: str, text: str) -> None:
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return
        url_like = re.compile(r"^/[\w./?&=%~+:,@!$*();-]+$")

        def walk(v: Any) -> None:
            if isinstance(v, str):
                if url_like.fullmatch(v):
                    self._record(source, v, "json_value")
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)

        walk(data)


def _is_followable(norm_path: str) -> bool:
    """Should we enqueue this as a new crawl target (HTML/JS/CSS)?"""
    leaf = norm_path.split("?", 1)[0].rsplit("/", 1)[-1].lower()
    if not leaf:
        return True  # directory-ish (`/`, `/foo/`)
    if "." not in leaf:
        return True  # no extension — likely a route
    return leaf.endswith((".html", ".htm", ".js", ".css"))


def _is_state_change_path(norm_path: str) -> bool:
    """True if the path matches a state-change verb. Used to skip from crawl."""
    return bool(STATE_CHANGE_TOKENS.search(norm_path.split("?", 1)[0]))


def _strip_js_comments(text: str) -> str:
    """Remove JS comments while preserving string literals.

    A naive `s/\\/\\/.*$//` truncates strings containing `//` (e.g.
    `"http://device/api"` → `"http:`). This walks the source with a tiny
    state machine that understands `"` `'` `` ` `` string boundaries.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        c2 = text[i : i + 2]
        # block comment
        if c2 == "/*":
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        # line comment
        if c2 == "//":
            end = text.find("\n", i + 2)
            i = n if end == -1 else end
            continue
        # string literal — copy verbatim through its closing quote
        if c in ("'", '"', "`"):
            quote = c
            out.append(c)
            i += 1
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i : i + 2])
                    i += 2
                    continue
                out.append(text[i])
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------- probing ----------


def _ensure_chromium() -> None:
    """Install chromium for Playwright on first use, idempotently."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        msg = str(e).lower()
        if "executable doesn't exist" not in msg and "please install" not in msg:
            raise
    else:
        return

    print(
        "[geekmagic-reverse-engineer] Installing Chromium for Playwright (one-time, ~150 MB)...",
        file=sys.stderr,
    )
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )


def browse_pages(crawler: Crawler, paths: list[str], timeout_ms: int = 8000) -> None:
    """Load each HTML page in a real browser and capture runtime requests.

    Same-host only. Any request whose path matches the state-change heuristic
    is BLOCKED before it fires (recorded as `runtime_blocked`), so loading a
    page that secretly calls `/restart` on load can't brick anything.
    """
    if not paths:
        return

    _ensure_chromium()
    from playwright.sync_api import Error as PWError
    from playwright.sync_api import sync_playwright

    base = crawler.base
    device_host = crawler.host

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(ignore_https_errors=True)
            try:
                for path in paths:
                    page = ctx.new_page()
                    source_label = f"runtime:{path}"

                    def on_route(route, request, _src=source_label):
                        url = request.url
                        # Strict host match — `startswith(base)` was a prefix
                        # match that mis-attributed neighbouring devices.
                        parsed = urlparse(url)
                        if parsed.netloc != device_host:
                            route.continue_()
                            return
                        rel = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
                        if _is_state_change_path(rel):
                            crawler._record(
                                _src,
                                rel,
                                "runtime_blocked",
                                method=request.method,
                            )
                            with contextlib.suppress(PWError):
                                route.abort()
                            return
                        crawler._record(
                            _src,
                            rel,
                            "runtime_request",
                            method=request.method,
                            resource_type=request.resource_type,
                        )
                        route.continue_()

                    page.route("**/*", on_route)
                    with contextlib.suppress(PWError):
                        page.goto(
                            base + path,
                            wait_until="networkidle",
                            timeout=timeout_ms,
                        )
                    page.close()
            finally:
                # Always close the context even if a page raises mid-loop.
                ctx.close()
        finally:
            browser.close()


def probe_safe(crawler: Crawler) -> None:
    """GET every discovered endpoint that isn't state-changing."""
    for ep in crawler.endpoints.values():
        if ep.state_change:
            continue
        # Skip non-GET only references.
        if ep.methods and ep.methods.issubset({"POST", "PUT", "DELETE", "PATCH"}):
            continue
        target = ep.examples[0] if ep.examples else ep.path
        r = crawler.fetched.get(target) or crawler.fetch(target)
        if r is None:
            ep.probe = {"error": "max-fetches reached"}
            continue
        if isinstance(r, _FailedResponse):
            ep.probe = {"error": r.error}
            continue
        ep.probe = _summarize_response(r, redact_network=crawler.redact_network)


def _summarize_response(r: httpx.Response, *, redact_network: bool = True) -> dict[str, Any]:
    ct = r.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    size = len(r.content)
    summary: dict[str, Any] = {
        "status": r.status_code,
        "content_type": ct,
        "size": size,
    }
    text = r.text if size else ""
    if r.status_code == 200 and ("json" in ct or (text and text.strip().startswith(("{", "[")))):
        try:
            data = json.loads(text)
        except ValueError:
            pass
        else:
            summary["body"] = redact(data, redact_network=redact_network)
            summary["schema"] = schema_of(data)
            return summary
    if text:
        summary["body_preview"] = text[:MAX_BODY_PREVIEW]
        if size > MAX_BODY_PREVIEW:
            summary["body_preview"] += f"\n... (truncated {size - MAX_BODY_PREVIEW} bytes)"
    return summary


def redact(value: Any, *, redact_network: bool = True) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and SENSITIVE_KEY.search(k):
                out[k] = "[REDACTED]"
            elif isinstance(k, str) and redact_network and NETWORK_KEY.search(k):
                out[k] = "[REDACTED-NETWORK]"
            else:
                out[k] = redact(v, redact_network=redact_network)
        return out
    if isinstance(value, list):
        return [redact(v, redact_network=redact_network) for v in value]
    return value


def scrub_network_text(text: str, device_host: str) -> str:
    """Mask network identity in already-rendered text.

    - Device's own IPv4 → `<DEVICE>`; every other IPv4 → `<IP>`
    - MAC addresses → `<MAC>`
    - `<option value="X">…</option>` patterns (devices that return WiFi scan
      results as an HTML option list) → both attribute and text masked
    """
    bare_host = device_host.split(":", 1)[0]
    if IPV4_RE.fullmatch(bare_host):
        text = text.replace(bare_host, "<DEVICE>")
    text = IPV4_RE.sub("<IP>", text)
    text = MAC_RE.sub("<MAC>", text)
    # Replacement re-uses the captured (possibly-escaped) opening quote on both
    # sides — keeps the surrounding JSON-encoding intact.
    text = OPTION_VALUE_RE.sub(r"\1\2[REDACTED-NETWORK]\2", text)
    return OPTION_TEXT_RE.sub(">[REDACTED-NETWORK]</option>", text)


def schema_of(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: schema_of(v) for k, v in value.items()}
    if isinstance(value, list):
        if not value:
            return ["<empty>"]
        return [schema_of(value[0])]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


# ---------- reporting ----------


def render_markdown(crawler: Crawler) -> str:
    out: list[str] = []
    label = "<DEVICE>" if crawler.redact_network else f"`{crawler.host}`"
    out.append(f"# Device {label}\n")
    redaction_note = (
        " Network identity (SSIDs, IP addresses, MAC/BSSID) is masked by default; "
        "rerun with `--no-network-redact` to keep them."
        if crawler.redact_network
        else ""
    )
    out.append(
        "_Generated by `geekmagic-reverse-engineer`. "
        "All facts below were discovered by crawling the device's own HTML/JS/CSS. "
        f"No firmware assumptions were applied.{redaction_note}_\n"
    )

    # Identification — any probed JSON that looks like it identifies the device.
    id_eps = [
        ep
        for ep in crawler.endpoints.values()
        if ep.probe
        and ep.probe.get("status") == 200
        and isinstance(ep.probe.get("body"), dict)
        and any(k in ep.probe["body"] for k in ("v", "m", "version", "model", "fw", "firmware"))
    ]
    if id_eps:
        out.append("## Identification\n")
        for ep in id_eps:
            out.append(f"`GET {ep.path}`\n")
            out.append(f"```json\n{json.dumps(ep.probe['body'], indent=2)}\n```\n")

    # HTML pages.
    pages = [
        (p, r)
        for p, r in crawler.fetched.items()
        if not isinstance(r, _FailedResponse)
        and r.status_code == 200
        and "html" in r.headers.get("content-type", "").lower()
    ]
    if pages:
        out.append("## HTML pages\n")
        out.append("| Path | Size | Title |")
        out.append("|------|------|-------|")
        for path, r in sorted(pages):
            title = _extract_title(r.text) or ""
            title = title.replace("|", "\\|")
            out.append(f"| `{path}` | {len(r.content)} B | {title} |")
        out.append("")

    # JSON read endpoints.
    json_eps = [
        ep
        for ep in crawler.endpoints.values()
        if ep.probe and ep.probe.get("status") == 200 and "body" in ep.probe and ep not in id_eps
    ]
    if json_eps:
        out.append("## JSON endpoints (read-only, safely probed)\n")
        for ep in sorted(json_eps, key=lambda e: e.path):
            out.append(f"### `GET {ep.path}`")
            probe = ep.probe or {}
            out.append(f"- Content-Type: `{probe.get('content_type')}` — {probe.get('size')} B")
            schema_json = json.dumps(probe.get("schema"), indent=2)
            sample_json = json.dumps(probe.get("body"), indent=2)
            out.append("- Schema:\n")
            out.append("  ```json")
            out.append(_indent(schema_json, 2))
            out.append("  ```")
            out.append("- Sample response:\n")
            out.append("  ```json")
            out.append(_indent(sample_json, 2))
            out.append("  ```")
            out.append("- Evidence: " + _evidence_str(ep))
            out.append("")

    # Non-JSON read endpoints. Exclude HTML pages (already in the table above)
    # by looking at the fetched response's content-type, NOT the probe's — they
    # can differ when the endpoint is referenced as both a page and an asset.
    def _is_html_response(ep: Endpoint) -> bool:
        target = ep.examples[0] if ep.examples else ep.path
        resp = crawler.fetched.get(target)
        if resp is None or isinstance(resp, _FailedResponse):
            return False
        return "html" in resp.headers.get("content-type", "").lower()

    other_eps = [
        ep
        for ep in crawler.endpoints.values()
        if ep.probe
        and ep.probe.get("status") == 200
        and "body" not in ep.probe
        and ep not in id_eps
        and not _is_html_response(ep)
    ]
    if other_eps:
        out.append("## Other read endpoints (text/binary, safely probed)\n")
        for ep in sorted(other_eps, key=lambda e: e.path):
            probe = ep.probe or {}
            out.append(f"### `GET {ep.path}`")
            out.append(f"- Content-Type: `{probe.get('content_type')}` — {probe.get('size')} B")
            preview = probe.get("body_preview")
            if preview:
                out.append("- Preview:\n")
                out.append("  ```")
                out.append(_indent(preview, 2))
                out.append("  ```")
            out.append("- Evidence: " + _evidence_str(ep))
            out.append("")

    # State-changing endpoints — catalogued only.
    state_eps = [ep for ep in crawler.endpoints.values() if ep.state_change]
    if state_eps:
        out.append("## State-changing endpoints (catalogued, NOT probed)\n")
        out.append(
            "These paths were detected but never executed because their path "
            "matched a state-change token (`set`, `save`, `delete`, `restart`, "
            "`upload`, etc.) or they were a form action. "
            "Use the JS evidence to learn their inputs and effects.\n"
        )
        for ep in sorted(state_eps, key=lambda e: e.path):
            methods = ", ".join(sorted(ep.methods)) or "GET"
            out.append(f"### `{methods} {ep.path}`")
            if ep.query_keys:
                out.append(
                    "- Query parameters observed: "
                    + ", ".join(f"`{k}`" for k in sorted(ep.query_keys))
                )
            if ep.form_fields:
                out.append("- Form fields: " + ", ".join(f"`{f}`" for f in ep.form_fields))
            if ep.examples:
                out.append("- Example URLs observed:")
                out.extend(f"  - `{ex}`" for ex in ep.examples[:8])
            out.append("- Evidence: " + _evidence_str(ep))
            out.append("")

    # Probed but failed (404 etc.).
    failed = [
        ep
        for ep in crawler.endpoints.values()
        if ep.probe
        and isinstance(ep.probe.get("status"), int)
        and ep.probe["status"] not in (200, 0)
    ]
    if failed:
        out.append("## Probed but not served (likely dead code or removed feature)\n")
        for ep in sorted(failed, key=lambda e: e.path):
            probe = ep.probe or {}
            out.append(
                f"- `{ep.path}` → HTTP {probe.get('status')} "
                f"(`{probe.get('content_type', '')}`) — "
                f"evidence: {_evidence_str(ep)}"
            )
        out.append("")

    # Connection failures.
    errors = [ep for ep in crawler.endpoints.values() if ep.probe and ep.probe.get("error")]
    if errors:
        out.append("## Connection failures while probing\n")
        for ep in sorted(errors, key=lambda e: e.path):
            probe = ep.probe or {}
            out.append(f"- `{ep.path}` — {probe.get('error')}")
        out.append("")

    out.append("---")
    out.append(
        f"_Discovered {len(crawler.endpoints)} endpoints across "
        f"{len(crawler.fetched)} fetched resources._"
    )
    return "\n".join(out) + "\n"


def _evidence_str(ep: Endpoint) -> str:
    parts: list[str] = [f"`{ev['kind']}` in `{ev['source']}`" for ev in ep.evidence[:6]]
    if len(ep.evidence) > 6:
        parts.append(f"(+{len(ep.evidence) - 6} more)")
    return "; ".join(parts) if parts else "—"


def _indent(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in text.splitlines())


def _extract_title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl a GeekMagic-style device and document its HTTP API."
    )
    parser.add_argument("host", help="Device URL or host (e.g. 10.76.1.217)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/devices"),
        help="Output directory (default: docs/devices)",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-fetches", type=int, default=MAX_FETCHES)
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Crawl only — skip the probing pass.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip the Playwright runtime-capture pass.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help=(
            "Subdirectory name under --out (default: current UTC timestamp "
            "in `YYYY-MM-DD_HH-MM-SS` form). Each run gets its own dir."
        ),
    )
    parser.add_argument(
        "--no-network-redact",
        action="store_true",
        help=(
            "Disable default-on redaction of network identity "
            "(SSIDs, IP addresses, MAC/BSSID). Credentials/tokens are always "
            "redacted regardless of this flag."
        ),
    )
    args = parser.parse_args()

    # `--name` must be a single path component (no slashes, no `..`, no
    # absolute paths). Without this, `--name ../../etc/passwd` would write
    # outside `--out` and could clobber unrelated files.
    if args.name is not None:
        name_path = Path(args.name)
        if (
            args.name != name_path.name
            or args.name in ("", ".", "..")
            or "/" in args.name
            or "\\" in args.name
        ):
            parser.error(
                "--name must be a single path component (no slashes, `..`, or absolute paths)"
            )

    base = args.host if args.host.startswith(("http://", "https://")) else f"http://{args.host}"

    redact_network = not args.no_network_redact
    run_started = datetime.now(UTC)

    def _stderr_scrub(msg: str) -> str:
        """Apply network redaction to stderr text when --no-network-redact
        is not set, so error messages don't leak the device IP."""
        if not redact_network:
            return msg
        host = urlparse(base).netloc.split(":", 1)[0]
        if host:
            msg = msg.replace(host, "<DEVICE>")
        return IPV4_RE.sub("<IP>", msg)

    with Crawler(
        base,
        timeout=args.timeout,
        max_fetches=args.max_fetches,
        redact_network=redact_network,
    ) as crawler:
        crawler.crawl()

        # Browser pass before probing — runtime requests may discover endpoints
        # we then want probe_safe() to fetch + summarize.
        if not args.no_browser:
            html_paths = sorted(
                p
                for p, r in crawler.fetched.items()
                if not isinstance(r, _FailedResponse)
                and r.status_code == 200
                and "html" in r.headers.get("content-type", "").lower()
            )
            try:
                browse_pages(crawler, html_paths)
            except Exception as e:
                print(
                    _stderr_scrub(
                        f"[geekmagic-reverse-engineer] Browser pass failed "
                        f"({e!r}); continuing with static results only."
                    ),
                    file=sys.stderr,
                )

        if not args.no_probe:
            probe_safe(crawler)

    # Bail before creating the run dir if we got nothing. Writing empty
    # report files for an unreachable device pollutes `docs/devices/` and
    # forces the user to `rm -rf` before retrying.
    any_success = any(
        not isinstance(r, _FailedResponse) and r.status_code == 200
        for r in crawler.fetched.values()
    )
    if not any_success:
        print(
            _stderr_scrub(
                f"[geekmagic-reverse-engineer] No successful fetches from "
                f"{crawler.host}; device may be unreachable. "
                f"Nothing written — try again."
            ),
            file=sys.stderr,
        )
        return 1

    run_name = args.name or run_started.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = args.out / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    md_path = run_dir / "report.raw.md"
    json_path = run_dir / "report.json"
    polished_path = run_dir / "report.md"
    run_meta_path = run_dir / "run.json"

    # Breakdown counts — also written into run.json so consumers don't have
    # to re-derive them from the bigger sidecar.
    n_state = sum(1 for ep in crawler.endpoints.values() if ep.state_change)
    n_probed = sum(
        1 for ep in crawler.endpoints.values() if ep.probe and ep.probe.get("status") == 200
    )
    n_failed = sum(
        1
        for ep in crawler.endpoints.values()
        if ep.probe
        and isinstance(ep.probe.get("status"), int)
        and ep.probe["status"] not in (200, 0)
    )
    n_blocked = sum(
        1
        for ep in crawler.endpoints.values()
        for ev in ep.evidence
        if ev.get("kind") == "runtime_blocked"
    )

    md_text = render_markdown(crawler)
    if redact_network:
        md_text = scrub_network_text(md_text, crawler.host)
    md_path.write_text(md_text)

    # Seed the polished report from the template so the agent has a starting
    # skeleton to fill in. Only copy if it doesn't exist — never clobber a
    # human-curated report on rerun.
    template_path = Path(__file__).parent / "TEMPLATE.md"
    if template_path.exists() and not polished_path.exists():
        polished_path.write_text(template_path.read_text())

    # Run metadata for archival / diffing across firmware updates.
    run_meta = {
        "started_at": run_started.isoformat(),
        "host": "<DEVICE>" if redact_network else base.rstrip("/"),
        "script": Path(__file__).name,
        "flags": {
            "timeout": args.timeout,
            "max_fetches": args.max_fetches,
            "no_probe": args.no_probe,
            "no_browser": args.no_browser,
            "no_network_redact": args.no_network_redact,
            "name": args.name,
        },
        "summary": {
            "endpoints_total": len(crawler.endpoints),
            "fetched_total": len(crawler.fetched),
            "probed_ok": n_probed,
            "probed_failed": n_failed,
            "state_changing": n_state,
            "runtime_blocked": n_blocked,
        },
    }
    run_meta_text = json.dumps(run_meta, indent=2)
    if redact_network:
        run_meta_text = scrub_network_text(run_meta_text, crawler.host)
    run_meta_path.write_text(run_meta_text)

    sidecar = {
        "host": "<DEVICE>" if redact_network else base.rstrip("/"),
        "fetched": {p: _resp_summary(r) for p, r in crawler.fetched.items()},
        "endpoints": {
            p: {
                "methods": sorted(ep.methods),
                "query_keys": sorted(ep.query_keys),
                "examples": ep.examples,
                "state_change": ep.state_change,
                "form_fields": ep.form_fields,
                "evidence": ep.evidence,
                "probe": ep.probe,
            }
            for p, ep in crawler.endpoints.items()
        },
    }
    sidecar_text = json.dumps(sidecar, indent=2, default=str)
    if redact_network:
        sidecar_text = scrub_network_text(sidecar_text, crawler.host)
    json_path.write_text(sidecar_text)

    print(f"Wrote {md_path}", file=sys.stderr)
    print(f"Wrote {json_path}", file=sys.stderr)
    print(
        f"Endpoints: {len(crawler.endpoints)} total — "
        f"{n_probed} probed OK, {n_failed} 4xx/5xx, "
        f"{n_state} state-changing (not probed), "
        f"{n_blocked} runtime-blocked",
        file=sys.stderr,
    )

    # Exit code: non-zero when the device looks unreachable. Lets CI / the
    # skill detect "couldn't talk to the device at all" vs. "discovered N
    # endpoints". Treat as unreachable if no resource came back 200.
    return 0


def _resp_summary(r: httpx.Response | _FailedResponse) -> dict[str, Any]:
    if isinstance(r, _FailedResponse):
        return {"error": r.error}
    return {
        "status": r.status_code,
        "content_type": r.headers.get("content-type", ""),
        "size": len(r.content),
    }


if __name__ == "__main__":
    sys.exit(main())
