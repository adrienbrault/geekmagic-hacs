---
name: release-highlights
description: Append a curated "Highlights" section — screenshots, animated GIFs and PR demo videos of the new features — to a published GitHub release whose body was generated with `--generate-notes`, leaving that generated changelog untouched; also corrects an existing Highlights section. Use as the last step of every release, and when the user asks to "enrich release X", "add screenshots/media to the release notes", "update/fix the release highlights", or wants a release body that shows the features rather than only listing PR titles.
---

# release-highlights

GitHub's generated notes are the changelog; they are not the story. This skill turns a release body from

```
## What's Changed
* fix: … by @someone in #123
* feat: … by @someone in #124

**Full Changelog**: …/compare/1.8.1...1.9.0
```

into the same block **plus** a curated section below it: what changed for the person holding the display, with the media that proves it. Good worked examples: 1.8.0 (a feature release with screenshots and GIFs), 1.9.0 (helpers with a three-card table, a repair dialog) and 1.9.6 (before/after from tags, an inline video). Read them with `gh release view 1.8.0 --json body --jq .body`.

The body is read in two places: GitHub's release page, and Home Assistant's update dialog (HACS shows the release notes there). Write so the text stands on its own: outside GitHub a video URL is only a link, and an image may not load.

## The one hard rule

**The generated block is untouchable.** Never remove, reorder, reword, re-emit or "tidy" `## What's Changed`, its bullets, the contributor line, or `**Full Changelog**`. New content goes **below** it, separated by a `---` line. Everything up to and including the `**Full Changelog**` line must stay an exact prefix of the body (GitHub normalizes CRLF to LF on save, so compare with line endings normalized).

What follows the separator is yours, including a Highlights section written earlier: correcting one is the same edit.

Anything else about the release — tag, assets, draft state, title, GitHub's own "Contributors" panel — is out of scope. This skill edits the *body*, nothing else.

## When to use

- Right after `gh release create … --generate-notes` (step 7 of the release process in `CLAUDE.md`)
- "Enrich release 1.9.0", "add the screenshots to the release notes", "update/fix the highlights for X"
- Not for cuts that have no generated notes yet, and not to rewrite a body the user wrote by hand

## Workflow

### 0. Snapshot the release

```bash
TAG=1.9.6
W=$(mktemp -d)                                      # /tmp may not be writable; keep every file here
gh release view "$TAG" --json tagName,body,isDraft,publishedAt
gh release view "$TAG" --json body --jq .body > "$W/orig.md"   # byte-exact original
PREV=$(git describe --tags --abbrev=0 "$TAG^")      # previous release tag
```

Check `PREV` against the `compare/PREV...TAG` URL in the generated block; they must agree.

If the body is empty or does not contain `## What's Changed`, stop and ask — the user may want generated notes first (`gh release edit "$TAG" --generate-notes` would *replace* the body).

### 1. Inventory what the release actually contains

```bash
# PRs named by the generated notes
grep -o '/pull/[0-9]*' "$W/orig.md" | sort -u
# media added or changed between the previous release and this one
git diff --name-status "$PREV" "$TAG" -- samples docs | grep -E '\.(png|gif|webp|mp4|webm)$'
# which commit changed a given sample, and so which PR
git log --oneline "$PREV".."$TAG" -- samples/12_security.png
```

For every PR, fetch the **body and its comments** — before/after screenshots and the only real videos usually live there:

```bash
gh api "repos/{owner}/{repo}/pulls/N" --jq .body
gh api "repos/{owner}/{repo}/issues/N/comments" --paginate --jq '.[].body'
```

A release with many PRs is normal (1.7.0 had 25); pick the handful a user would notice. Fix-only releases may legitimately have no media at all.

### 2. Choose media by this order of trust

1. **A file added in this release** (`A` in the diff) — pin it to the tag, e.g. a widget sample or a panel screenshot.
2. **A before/after pair from tags** — when a PR changed what a committed sample shows, `PREV` is the before and `TAG` is the after (1.9.6's lock status: LOCKED in green before, OPEN in red after).
3. **Media in the PR body** — keep the URL exactly as the PR has it (usually a raw URL at a commit SHA on the `pr-assets` branch or the author's branch). A PR's before/after pointing at a mid-PR commit can predate a later fix in the same release: prefer the same files at the tag.
4. **Media in a PR comment** — a bare `https://github.com/user-attachments/assets/<uuid>` on its own line renders as an inline video player on GitHub. This is the only way real video demos reach a release note.
5. **Nothing** — write prose only. Never borrow an older sample to illustrate a new feature.

Modified (`M`) files are a regeneration from an engine bump as often as a feature. `git log` on the file says which PR changed it; that PR's body says why.

### 3. Look at every image before captioning it

Download each image at the exact URL you will publish and open it (the Read tool shows images; put two or three side by side with Pillow when comparing). Caption only what is visible in that file, at that ref. 1.9.6 shipped a caption promising "the open-padlock icon" under a sample that still drew a closed padlock: the open one only arrived in 1.10.0. Nobody had opened the image.

### 4. Pin the URLs

| Source | URL |
|---|---|
| repo file | `https://raw.githubusercontent.com/<owner>/<repo>/<TAG>/<path>` — a tag or a full commit SHA, never `main` |
| doc link | `https://github.com/<owner>/<repo>/blob/<TAG>/<path>#anchor` — same rule |
| PR body/comment | leave the SHA URL as-is |
| video | `https://github.com/user-attachments/assets/<uuid>` on its own line |

Pinning keeps the note correct after `main` moves and after the samples are regenerated. The verifier rejects branch refs.

### 5. Write the section

```markdown
## Highlights

### <what a user notices, not the PR title>

One short paragraph: the change, and why it matters at 0.6–1 m from a 27 mm panel.
Bullets only where they carry distinct facts.

| 1.9.6 | 1.10.0 |
|:-:|:-:|
| <img src="…" alt="…"> | <img src="…" alt="…"> |

<p align="center">
  <img src="…" alt="…" width="720">
</p>
```

- 2–4 sections for a feature release; for a patch release a single `## Highlights` with 3–6 tight bullets is right.
- Device frames are 240×240: `width="200"` outside tables; inside a table, omit `width` and let the column size it.
- Panel screenshots: `width="700"`–`720`, centred in a `<p align="center">`.
- Animated repo media are GIFs and render inline; they cost bandwidth, so one or two per release.
- Do not restate the changelog bullet-for-bullet, and do not add marketing adjectives. The generated list says *what merged*; this section says *what it looks like*.

**Write for the person with the display, not for the code.**

- Name things the way the panel, Home Assistant or the docs name them: the **Rotate views** switch, the Status widget, `geekmagic.notify`, the HTML widget's `forecast()`. Code identifiers a user never types (`ON_STATES`, `keep_only_image`, `entities/list`, `format_number`) stay in the PR. Say what the user saw instead: "999,950 showed as 1000k".
- CI, refactors, tests, tooling and `CLAUDE.md` changes get no section. If one changes something users feel (a faster install, a smaller download), one line under "Also" is the most it gets.

**Every claim is checked, not remembered.**

- Each sentence must trace to a PR body, a PR comment, an issue, or the code at the tag. If unsure, leave it out.
- Count numbers with a command: `grep -o '/pull/[0-9]*' "$W/orig.md" | sort -u | wc -l` for "N pull requests", the diff for "N samples". Counting `* ` lines also counts the "New Contributors" lines: that is how 1.9.1 said "Sixteen pull requests" for fifteen.
- Describe a mechanism only as the PR describes it. Paraphrasing a root cause from memory is how a note ends up saying the opposite of the PR.

### 6. Assemble, apply, verify

```bash
# the current body up to its **Full Changelog** line, then the separator, then the highlights
python3 - "$W" <<'PY'
import sys
w = sys.argv[1]
body = open(f"{w}/orig.md", encoding="utf-8").read().replace("\r\n", "\n")
start = body.index("**Full Changelog**")
end = body.find("\n", start)
generated = body if end == -1 else body[:end]
high = open(f"{w}/hl.md", encoding="utf-8").read().strip()
open(f"{w}/notes.md", "w", encoding="utf-8").write(f"{generated}\n\n---\n\n{high}\n")
PY

gh release edit "$TAG" --notes-file "$W/notes.md"
python3 .claude/skills/release-highlights/scripts/verify_release_notes.py "$TAG" "$W/orig.md"
```

The same assembly works for a first enrichment and for a correction: it keeps the generated block and replaces whatever followed it. For a correction, start `hl.md` from the old section (everything after the `---`) and edit it.

The verifier is stdlib-only and shells out to `gh`. It fails unless:
- the saved body's generated block is still an exact prefix;
- `## What's Changed` and `**Full Changelog**` each still appear exactly once;
- `Highlights` comes after them;
- every image or video URL returns 200 with the expected content type;
- every repo URL is pinned to a tag or SHA, and every `blob` link resolves.

Fix and re-edit until it passes. Re-running `gh release edit` is safe. Pass `--allow-missing-highlights` when you only want to check the generated block.

### 7. Report

Give the release URL, the sections added or corrected, which PRs each visual came from, and anything left prose-only because no media existed. That last part matters: it tells the maintainer where a future screenshot would pay off.

## Edge cases

- **No media anywhere** (common for patch releases): a short bullet list of the fixes worth knowing, no images. Say so rather than fabricating a visual.
- **The generated list repeats a PR** (merge + branch): leave the duplicates; that block is not yours to edit.
- **Draft releases**: editing is fine; verify after publish too if the user publishes later.
- **A video only exists locally**: ask before uploading it as a release asset — links render inline, assets need the user's call.
