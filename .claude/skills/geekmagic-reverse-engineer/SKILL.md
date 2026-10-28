---
name: geekmagic-reverse-engineer
description: Discover and document what a GeekMagic-style display device exposes over HTTP by crawling it (no firmware assumptions). Use when (a) the user is debugging the HA extension against an unsupported device/firmware and needs to attach a capture to a bug report, (b) they want to contribute a per-device reference doc to this repo, or (c) a new device/firmware needs to be mapped before adding integration support. Triggers include "reverse engineer my device", "document this device", "the extension doesn't work with my device", "what does this firmware expose", or pointing you at a new device IP.
---

# geekmagic-reverse-engineer

Produces a reference doc of what a GeekMagic-style display device exposes over HTTP — pages, endpoints, parameters, payloads — **purely by crawling the device's own HTML/JS/CSS and watching it run in a headless browser**. No firmware assumptions. If it isn't in the doc, the device didn't tell us about it.

The output is the artifact a user attaches to a GitHub issue ("integration doesn't work with my firmware — here's what my device looks like") or that a contributor commits as `docs/devices/<host>.md` when adding support for a new model.

## When to use

- User reports an integration bug and we suspect a firmware version we haven't mapped
- User says "reverse engineer the device at <IP>" / "document this device"
- User wants to add support for a new device or firmware version
- Contributor wants to open a PR with their own device's spec under `docs/devices/`

## How to drive it

### 1. Run the discovery script

The script is bundled in this skill:

```bash
uv run .claude/skills/geekmagic-reverse-engineer/reverse_engineer_device.py <HOST>
```

`<HOST>` can be an IP, `host:port`, or a full `http://…` URL.

On first run, the script downloads Chromium for Playwright (~260 MB to `~/Library/Caches/ms-playwright/`). This is a one-time cost per machine.

**Output layout** (dir per run, so multiple captures of the same device over firmware updates stay side-by-side for diffing):

```
docs/devices/<run-name>/
├── report.raw.md   ← script output, verbatim — never edit by hand. Includes
│                     up to 32 KB of body preview per endpoint, which
│                     comfortably fits the source HTML/JS for slider
│                     min/max, label text, form fields, etc.
├── report.json     ← raw sidecar (mirrors report.raw.md, machine-readable)
├── report.md       ← polished, human-readable — pre-seeded from TEMPLATE.md
│                     for you to fill in (step 3)
└── run.json        ← run metadata + summary breakdown (probed_ok, failed,
                      state_changing, runtime_blocked)
```

`<run-name>` defaults to a UTC timestamp (`YYYY-MM-DD_HH-MM-SS`). Pass `--name` to override (must be a single path component — no slashes or `..`). After you produce the polished `report.md` in step 3, propose renaming the dir to something meaningful (e.g. `smalltv-ultra-V9.0.40`).

**Exit code:** 0 on success, 1 if the device was completely unreachable (no successful fetches). Useful for CI / scripted runs.

The script runs three passes in this order:

1. **Static crawl** — same-host BFS from `/`, following HTML/JS/CSS references. Extracts URL-shaped tokens from HTML attrs (`href`, `src`, `action`, `onclick`, `onload`), JS calls (`fetch(`, `getData(`, `XMLHttpRequest.open(`, `$.get/post/ajax(`, `.action = `, `location = `), absolute JS path literals, relative literals ending in `.html`/`.js`/`.css`/`.json`, and any URL-looking strings in JSON responses.

2. **Browser runtime capture** (Playwright headless Chromium) — loads each HTML page discovered in pass 1, captures **every** network request the page makes via `page.route()`, attributes them as `runtime_request` evidence. Same-host only. **State-change URLs are blocked before they fire** (recorded as `runtime_blocked`) — even if a page secretly calls `/restart` on load, the browser pass cannot trigger it.

3. **Safe probe** — GETs every discovered endpoint (static + runtime) that does not match a state-change pattern (`set`, `save`, `delete`, `restart`, `upload`, `connect`, `wifisave`, `update_ota`, `toggle`, `reboot`, …) and is not a form action.

**Default-on redactions** (apply to `report.raw.md`, `report.json`, and `run.json`):
- JSON values for credentials — keys matching `password|passphrase|(?:^|_)pass(?:$|_)|pwd|weatherkey|apikey|api_key|secret|token|^p$|^key$` → `[REDACTED]`. **Always on, cannot be disabled.**
- JSON values for network identity — keys matching `^ssid$|wifi_ssid|wifi_name|^ss$|^bssid$|^mac$|mac_addr|hostname|^a$` → `[REDACTED-NETWORK]`. Disabled with `--no-network-redact`.
- IPv4 addresses in body text — the device's own IP → `<DEVICE>`, every other IPv4 → `<IP>`. Also gated by `--no-network-redact`.
- MAC addresses in body text → `<MAC>`. Same gating.
- `<option value="X">…</option>` patterns (WiFi scan results returned as HTML option lists) → both attribute and text masked. Same gating.

Single-letter JSON keys to know about (GeekMagic-specific firmware encodings):
- `a` in `/.sys/config.json` is SSID, `p` is password (Pro firmware)
- `ss` in `/wifi.json` items is SSID (Ultra firmware)
- Both are covered by the regexes above.

The script will NEVER:
- Issue non-GET requests from the probe pass
- Follow redirects
- Probe an endpoint that matched the state-change heuristic (even if asked nicely by the page) — those go in the "catalogued, NOT probed" section instead
- Allow a runtime page to fire a state-change request (the browser intercepts and aborts before the request leaves the process)
- Click buttons or submit forms during the browser pass — only `goto(url, wait_until=networkidle)`
- Reach off-host

### 2. Audit for residual leaks across the whole dir

The script's default redactions catch credentials + network identity, but they're heuristic. Walk `report.raw.md`, `report.json`, and `run.json` looking for:
- **City / location strings** (weather config) — not masked by default
- **Generic-named API keys / IDs** the regex missed (`id`, `auth`, `clientId`, …)
- **Free-form text in `body_preview` blocks** — text/HTML responses get a preview that key-redaction doesn't touch; IPs/MACs/option-tags are scrubbed but anything else inside HTML body text is shown raw
- **Hidden form fields** in HTML body previews (login tokens, session IDs, …)
- **GitHub usernames / repo paths in OTA / firmware-update sections** if you don't want to advertise which fork the device runs

For each finding either:
- Edit the affected file directly (replace value with `[REDACTED]`), OR
- Add the JSON key to `SENSITIVE_KEY` / `NETWORK_KEY` in `reverse_engineer_device.py` and rerun (more durable)

Default to "scrub aggressively, ask later" — the dir is meant to be shared.

### 3. Fill in the polished `report.md`

`report.md` is pre-staged from [`TEMPLATE.md`](TEMPLATE.md) at script-run time, so it already exists in the run dir. **Edit it in place** — replace every `<!-- AGENT: ... -->` HTML comment with real content, removing the comment marker. Drop entire sections (heading + body) that don't apply to this device.

What the polished report should add on top of the raw one:
- **Executive summary** — model, firmware, identification endpoint. If the host is `<DEVICE>` (network-redact on), say so explicitly; don't try to invent an IP.
- **Compatibility section** — the highest-value output. Open `custom_components/geekmagic/device.py`, `const.py`, and `coordinator.py`. For each method `GeekMagicDevice` calls, check **both** that the endpoint exists on this device AND that the integration reads fields the device actually returns. Example: `get_state()` reads `data.get("brt")` and `data.get("img")` from `/app.json`, but old-Ultra firmware only returns `{"theme": N}` — the endpoint matches but the *fields* don't. Endpoint-by-endpoint comparison alone misses this; cross-check the field names in the `/app.json` sample inside `report.raw.md` against the integration source.
- **Endpoints grouped by purpose** (not alphabetically) — identification/system, display, network, content/data
- **Inferred semantics** for state-change endpoints — e.g. brightness range from `<input min max>` in the `body_preview` of the source HTML inside `report.raw.md`. If the page is larger than the 32 KB preview cap, ask the user to `curl http://<device>/page.html` and paste the relevant snippet — those captures aren't kept by the script.
- **Things to verify manually** — anything you couldn't determine with confidence

The raw report (`report.raw.md`) stays untouched as the appendix and source-of-truth artifact.

### 4. Verify state-changing endpoints with the user (optional)

If the user explicitly wants to confirm what a state-changing endpoint does (e.g. test that `/set?theme=N` actually switches the theme):
- Propose the exact curl command
- Wait for explicit user OK
- Run it once with a value the user agrees is safe (e.g., the current value)

Never auto-probe state-changing endpoints, even after the user gives "general" permission to reverse-engineer.

### 5. Rename, commit (or attach)

After polishing, propose renaming the run directory from the timestamp to something meaningful — typically `<model-slug>-<firmware-version>` (e.g. `smalltv-ultra-V9.0.40/`). Wait for user OK before renaming.

If contributing as a docs PR (per `CLAUDE.md`'s atomic-commit convention):

```bash
git add docs/devices/<run-name>/
git commit -m "docs: add reverse-engineering capture for <model> <version>"
```

If the user just wants to attach the report to a bug report, `report.md` is the single file to upload (it links back to `report.raw.md` / `report.json` in the same directory but doesn't require them to be useful).

## What's in each file

**`report.raw.md`** — script-generated, with these sections (omitted when empty):

| Section | Source |
|---|---|
| Identification | First probed JSON endpoint that returns a `v`/`m`/`version`/`model` field. Folded into the at-a-glance table of `report.md`. |
| HTML pages | Every `text/html` 200 fetched during crawl. **Quirk:** some firmwares serve JSON endpoints with `Content-Type: text/html` and they end up here too. |
| JSON endpoints (read-only, safely probed) | 200 responses parsed as JSON; full schema + sample (with redactions applied). |
| Other read endpoints | Non-JSON 200 (text/plain, etc.) with truncated preview. |
| State-changing endpoints (catalogued, NOT probed) | Path matched state-change regex, or was a non-GET form action, or a GET form pointing at a path that already matched. Includes `runtime_blocked` evidence if a page tried to fire it on load. |
| Probed but not served | Referenced in the UI but server returns 4xx/5xx. |
| Connection failures while probing | Timeouts, refused, etc. |

**`report.json`** — sidecar mirroring `report.raw.md` data. Diff-friendly across firmware updates.

**`run.json`** — small metadata file (timestamp, host, flags, summary counts). The summary breakdown (`probed_ok`, `probed_failed`, `state_changing`, `runtime_blocked`) is the same line the script prints to stderr.

**`report.md`** — the polished, human-written report (pre-seeded from `TEMPLATE.md`). The thing actually attached to bug reports / committed to docs.

## Tuning knobs

```
--out PATH             parent dir for runs (default: docs/devices)
--name NAME            subdir name within --out (default: UTC timestamp)
--timeout SECONDS      per-request HTTP timeout (default: 6.0)
--max-fetches N        hard cap on static fetches (default: 200)
--no-probe             skip the safe-probe pass entirely
--no-browser           skip the Playwright runtime-capture pass entirely
--no-network-redact    disable default SSID/IP/MAC masking
                       (credentials are always redacted regardless)
```

If a device has paths the heuristic misses (e.g. a UI that uses some custom `apply(...)` wrapper around fetch), extend `JS_CALL_PATTERNS` in the script and re-run. Don't bake firmware-specific seed lists — the whole point of this tool is to stay neutral.

## Known limitations

- **Doesn't enumerate query-parameter ranges.** If the UI has a slider that fires `/set?brt=<n>`, the script records the path and the param name but doesn't try values. Document the range yourself from the JS (e.g. `min="0" max="100"` on the slider).
- **Doesn't follow JS dynamically-built URLs.** If a path is constructed via string concatenation entirely from variables, the regex won't catch it. Look for `+` concatenation in the JS as a hint.
- **Doesn't decompile binary firmware.** This is web-API reverse engineering only. For protocol-level work (UART, OTA payload format), use a different tool.
- **No-probe-of-state-changers is hardcoded.** If you genuinely need to call one, do it manually with curl after confirming with the user — do not patch the script to bypass the safety.
