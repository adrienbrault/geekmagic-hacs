/**
 * Pure state transitions for the panel.
 *
 * Nothing here may mutate its input: the editor works on a draft of a
 * view, and discarding the draft (Back) must never leak into the saved
 * views.
 */

import type { ViewConfig, WidgetConfig, WidgetTypeSchema } from "./types";

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
 * Set the widget type of `slot`. A new type starts from a clean config:
 * options belong to the old type, and the entity survives only when the
 * new type takes one from that domain. `label`/`color` carry over. An
 * empty type removes the slot's widget. Re-selecting the current type is
 * a no-op (ha-select can re-fire `selected` on render).
 */
export function changeWidgetType(
  widgets: WidgetConfig[],
  slot: number,
  newType: string,
  schemas: Record<string, WidgetTypeSchema>,
  timezone: string
): WidgetConfig[] {
  const current = widgets.find((w) => w.slot === slot);
  if (newType === (current?.type ?? "")) return widgets;
  if (!newType) return widgets.filter((w) => w.slot !== slot);

  const schema = schemas[newType];
  const entityId = current?.entity_id;
  const keepEntity =
    !!entityId &&
    !!schema?.needs_entity &&
    (!schema.entity_domains ||
      schema.entity_domains.includes(entityId.split(".")[0]));

  const next: WidgetConfig = { slot, type: newType };
  if (current?.label !== undefined) next.label = current.label;
  if (current?.color !== undefined) next.color = current.color;
  if (keepEntity) next.entity_id = entityId;
  // New clocks default to the browser's timezone.
  if (newType === "clock") next.options = { timezone };

  return current
    ? widgets.map((w) => (w === current ? next : w))
    : [...widgets, next];
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
