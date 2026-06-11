---
name: sample-review
description: Visually review the rendered 240x240 sample images (samples/) efficiently by building labeled contact sheets sized for LLM vision, instead of Reading 170+ PNGs one by one. Use when the user asks to "review the samples/generated images", "check how the widgets look", critique the design, or after a rendering change that should be verified visually across widgets/layouts/themes.
---

# sample-review

Review every generated sample image in ~10 Reads by tiling them onto labeled
contact sheets, then zooming into suspects. A 240x240 PNG read alone wastes
almost the entire vision budget; a well-packed sheet shows 9-28 renders at
native resolution in one Read.

## Key constraint: vision resolution

Image input is downscaled to ~1568px on the longest side. Size every sheet to
stay at or under that, so tiles keep native pixels:

| Purpose | cols x rows | scale | tile px | per sheet |
|---|---|---|---|---|
| Overview of 240px screens | 3 x 4 | 1.5 | 360 | 9-12 |
| Widget size matrix (7 sizes/type) | 6-7 cols | 1.0 | 240 | 28 (4 types) |
| Zoom / detail pass | 2 x 2 | 3.0 | 720 | 4 |

Never exceed ~1456px sheet width — past 1568 the whole sheet gets downscaled
and you lose more than you gain.

## Workflow

1. Regenerate: `uv run python scripts/generate_samples.py`
   - A local regen produces anti-aliasing-only pixel diffs in every PNG
     (freetype/Pillow drift). **Never commit them** — review, then
     `git checkout -- samples/`. The canonical samples are committed by the
     "Regenerate samples" GitHub workflow on a pinned Linux environment.
2. Build overview sheets (one Read each):

   ```bash
   uv run .claude/skills/sample-review/contact_sheet.py /tmp/review/dash_a.png \
       --cols 3 --scale 1.5 samples/0*.png
   ```

   Suggested grouping: dashboards (2 sheets), `samples/layouts/layout_*` minus
   themes (1), `layout_theme_*` (1), `samples/widgets/` grouped 4 widget types
   per sheet with sizes ordered `1x1 2x1 1x2 2x2 3x2 2x3 3x3` (4 sheets).
3. Read each sheet and note suspects (truncation, empty space, misalignment,
   washed-out colors, inconsistent font sizes within one grid).
4. Zoom pass: rebuild only the suspect files as 2x2 sheets at `--scale 3`
   (720px tiles) — this is the pass where small captions, baselines, and
   ellipses become legible. Don't skip it; overview sheets hide 10px text.
5. Judge against CLAUDE.md "Design System" rules: space usage
   (space-evenly, no dead bottom half), hierarchy (hero vs supporting),
   theme sentinels, and font-size consistency across same-grid cells.

## Pitfalls

- `samples/widgets/widget_*.png` (tiny 120x80-ish thumbnails) are stale
  orphans no longer produced by `generate_samples.py` — do not treat them as
  evidence of current rendering bugs.
- Remember physical scale when judging: the full screen is ~1.5in/4cm, so a
  3x3 cell is ~13mm and a 10px glyph is ~1mm. If you must squint at a 720px
  zoom tile, a user cannot read it on-device.
- Use NEAREST upscaling (the script default) — it keeps pixel edges honest
  instead of blurring rendering artifacts away.
