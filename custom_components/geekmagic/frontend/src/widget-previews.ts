/**
 * Which preview the widget picker shows for a widget type in a given slot.
 *
 * Previews are one cell of each widget sample (samples/widgets), cropped by
 * scripts/update_samples.py at each grid size. The picker shows the size
 * whose cell is closest in shape and scale to the slot being filled, so a
 * 3×3 cell previews the compact rendering and a fullscreen slot the hero.
 */
import spec from "./widget-previews.json";

type Sizes = Record<string, [number, number]>;
const SIZES = spec.sizes as unknown as Sizes;
const SAMPLES = spec.samples as Record<string, string>;

/** The fluid kit's breakpoints: .hide-narrow, .hide-short, .hide-small. */
function bands(width: number, height: number): boolean[] {
  return [width < 100, height < 100, Math.min(width, height) < 130];
}

/**
 * The size class whose cell best matches a ``width``×``height`` px slot:
 * first one that sheds the same optional bands (what the widget shows),
 * then the closest in shape and scale.
 */
export function previewSize(width: number, height: number): string {
  const slotBands = bands(width, height);
  let best = "";
  let bestScore = Infinity;
  for (const [size, [w, h]] of Object.entries(SIZES)) {
    const mismatched = bands(w, h).filter((flag, i) => flag !== slotBands[i]).length;
    // Log ratios weigh "twice as wide" the same as "half as wide".
    const score = mismatched * 10 + Math.abs(Math.log(width / w)) + Math.abs(Math.log(height / h));
    if (score < bestScore) {
      best = size;
      bestScore = score;
    }
  }
  return best;
}

/** URL of the preview for ``type`` in a slot of that size, or null if none. */
export function previewUrl(
  base: string,
  version: string,
  type: string,
  width: number,
  height: number
): string | null {
  const sample = SAMPLES[type];
  if (!sample || !(width > 0) || !(height > 0)) return null;
  return `${base}/${sample}_${previewSize(width, height)}.png?v=${encodeURIComponent(version)}`;
}

/** The pixel size of a size class's cell (for the image's aspect ratio). */
export function previewCell(size: string): [number, number] | undefined {
  return SIZES[size];
}
