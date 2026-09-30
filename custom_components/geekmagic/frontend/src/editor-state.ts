/**
 * Pure state transitions for the panel.
 *
 * Nothing here may mutate its input: the editor works on a draft of a
 * view, and discarding the draft (Back) must never leak into the saved
 * views.
 */

import type { ViewConfig, WidgetConfig } from "./types";

/** A fully independent draft of `view` for the editor. */
export function cloneView(view: ViewConfig): ViewConfig {
  return structuredClone(view);
}

/**
 * Move the widget in `fromSlot` to `toSlot` (and the one there, if any,
 * back to `fromSlot`). Returns new widget objects; `widgets` is untouched.
 */
export function swapWidgetSlots(
  widgets: WidgetConfig[],
  fromSlot: number,
  toSlot: number
): WidgetConfig[] {
  if (fromSlot === toSlot) return widgets;
  return widgets.map((w) => {
    if (w.slot === fromSlot) return { ...w, slot: toSlot };
    if (w.slot === toSlot) return { ...w, slot: fromSlot };
    return w;
  });
}

/**
 * A device's assigned view ids with `viewId` ticked or unticked.
 * Idempotent (no duplicates, no-op removals) and order-preserving.
 */
export function toggleAssignedView(
  assigned: string[],
  viewId: string,
  enabled: boolean
): string[] {
  const without = assigned.filter((id) => id !== viewId);
  return enabled ? [...without, viewId] : without;
}
