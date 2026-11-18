---
name: release-highlights
description: Append a curated "Highlights" section — screenshots, animated GIFs and PR demo videos of the new features — to a published GitHub release whose body was generated with `--generate-notes`, leaving that generated changelog untouched. Use when the user asks to "enrich release X", "add screenshots/media to the release notes", "update release highlights", or wants a release body that shows the features rather than only listing PR titles.
---

# release-highlights

GitHub's generated notes are the changelog; they are not the story. This skill turns a release body from

```
## What's Changed
* fix: … by @someone in #123
* feat: … by @someone in #124

**Full Changelog**: …/compare/1.8.1...1.9.0
```

into the same block **plus** a curated section below it: what changed for the person holding the display, with the media that proves it. The releases 1.7.0 through 1.9.6 of this repo were enriched this way — read any of their bodies as a worked example (`gh release view 1.9.6 --json body`).

## The one hard rule

**The generated block is untouchable.** Never remove, reorder, reword, re-emit or "tidy" `## What's Changed`, its bullets, the contributor line, or `**Full Changelog**`. New content goes **below** it, separated by a `---` line. The original body must remain an exact prefix of the new body (GitHub normalizes CRLF to LF on save, so compare with line endings normalized).

Anything else about the release — tag, assets, draft state, title, GitHub's own "Contributors" panel — is out of scope. This skill edits the *body*, nothing else.

## When to use

- "Enrich release 1.9.0", "add the screenshots to the release notes", "update the highlights for X"
- The release exists and its body came from `gh release create --generate-notes`
- Not for cuts that have no generated notes yet, and not to rewrite a body the user wrote by hand

## Workflow

### 0. Snapshot the release

```bash
TAG=1.9.6
gh release view "$TAG" --json tagName,body,isDraft,publishedAt
gh release view "$TAG" --json body --jq .body > /tmp/rel_orig.md   # byte-exact original
PREV=$(git tag --sort=-v:refname | grep -B1 -x "$TAG" | head -1)   # previous release tag
```

If the body is empty or does not contain `## What's Changed`, stop and ask — the user may want generated notes first (`gh release edit "$TAG" --generate-notes` would *replace* the body).

### 1. Inventory what the release actually contains

```bash
# PRs named by the generated notes
gh release view "$TAG" --json body --jq .body | grep -o '/pull/[0-9]*' | sort -u
# media added between the previous release and this one
git diff --name-status "$PREV" "$TAG" -- samples docs | grep -E '\.(png|gif|webp|mp4|webm)$'
```

For every PR, fetch the **body and its comments** — before/after screenshots and the only real videos usually live in a comment:

```bash
gh api "repos/{owner}/{repo}/pulls/N"
gh api "repos/{owner}/{repo}/issues/N/comments" --paginate
```

A release with many PRs is normal (1.7.0 had 26); pick the handful a user would notice. Fix-only releases may legitimately have no media at all.

### 2. Choose media by this order of trust

1. **A file added in this release** (`A` in the diff) — pin it to the tag, e.g. a widget sample or a panel screenshot.
2. **A before/after pair from tags** — when the fix changed a committed sample, `PREV` is the before and `TAG` is the after (that is how the lock's locked/unlocked padlock was shown in 1.9.6).
3. **Media in the PR body** — keep the URL exactly as the PR has it (usually a raw URL at a commit SHA of the author's branch).
4. **Media in a PR comment** — a bare `https://github.com/user-attachments/assets/<uuid>` on its own line renders as an inline video player (confirm with `POST /markdown` before publishing). This is the only way real video demos reach a release note.
5. **Nothing** — write prose only. Never borrow an older sample to illustrate a new feature, and never caption an image with something the PR does not claim.

Modified (`M`) files are usually a regeneration from an engine bump; they are not "new features". Check `git diff --stat` and the PR body before using one.

### 3. Pin the URLs

| Source | URL |
|---|---|
| repo file | `https://raw.githubusercontent.com/<owner>/<repo>/<TAG>/<path>` — the tag, never `main` |
| PR body/comment | leave the SHA/branch URL as-is; verify it still resolves |
| video | `https://github.com/user-attachments/assets/<uuid>` on its own line |

Pinning to the tag keeps the note correct after `main` moves and after the samples are regenerated.

### 4. Write the section

```markdown
## Highlights

### <what a user notices, not the PR title>

One short paragraph: the change, and why it matters at 0.6–1 m from a 27 mm panel.
Bullets only where they carry distinct facts.

| Before | After |
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
- Every claim must come from the PR title/body or the code at the tag. If unsure, leave it out.

### 5. Assemble, apply, verify

```bash
# original bytes, then the separator, then the highlights — never the other way round
python3 - <<'PY'
orig = open("/tmp/rel_orig.md", "rb").read()
high = open("/tmp/hl.md", "rb").read().strip()
open("/tmp/rel_notes.md", "wb").write(orig + b"\n\n---\n\n" + high + b"\n")
PY

gh release edit "$TAG" --notes-file /tmp/rel_notes.md
python3 .claude/skills/release-highlights/scripts/verify_release_notes.py "$TAG" /tmp/rel_orig.md
```

The verifier is stdlib-only and shells out to `gh`; it fails unless the original body is still an exact prefix, `## What's Changed` / `**Full Changelog**` still appear exactly once, `Highlights` comes after them, and every image/video URL returns 200 with the expected content type. Fix and re-edit until it passes; re-running `gh release edit` is safe (the prefix check reads the *previous* body you saved, so keep that file). Pass `--allow-missing-highlights` when you only want to check the generated block.

### 6. Report

Give the release URL, the sections added, which PRs each visual came from, and anything left prose-only because no media existed. That last part matters: it tells the maintainer where a future screenshot would pay off.

## Edge cases

- **No media anywhere** (common for patch releases): a short bullet list of the fixes worth knowing, no images. Say so rather than fabricating a visual.
- **The generated list repeats a PR** (merge + branch): leave the duplicates; that block is not yours to edit.
- **Draft releases**: editing is fine; verify after publish too if the user publishes later.
- **A video only exists locally**: ask before uploading it as a release asset — links render inline, assets need the user's call.
