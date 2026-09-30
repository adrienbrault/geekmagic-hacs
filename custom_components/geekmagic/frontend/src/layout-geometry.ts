/**
 * Layout geometry for the panel's layout picker and slot position grid.
 *
 * The backend sends every layout's slot rectangles normalized to the unit
 * square (computed from the real Layout classes), so the panel draws each
 * slot as an absolutely positioned box instead of guessing grid shapes.
 */

import type { SlotRect } from "./types";

function percent(fraction: number): string {
  return `${+(fraction * 100).toFixed(2)}%`;
}

/**
 * Inline style placing a slot inside a `position: relative` square.
 *
 * Each box is inset by half of `gapPx` on every side, so neighbouring
 * slots end up `gapPx` apart.
 */
export function slotRectStyle(rect: SlotRect, gapPx: number): string {
  const half = gapPx / 2;
  return [
    `left: calc(${percent(rect.x)} + ${half}px)`,
    `top: calc(${percent(rect.y)} + ${half}px)`,
    `width: calc(${percent(rect.w)} - ${gapPx}px)`,
    `height: calc(${percent(rect.h)} - ${gapPx}px)`,
  ].join("; ");
}
