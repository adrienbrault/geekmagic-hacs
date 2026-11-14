/**
 * Edits to a view being edited, as pure functions.
 *
 * Every function returns a new view and never mutates its input: the editor
 * compares the draft against a snapshot to detect unsaved changes, and the
 * list keeps the stored views, so a shared object edited in place would
 * leak unsaved edits into both.
 */
import type { ViewConfig, WidgetConfig } from "./types";

/** A deep copy (views are plain JSON). */
export function cloneView(view: ViewConfig): ViewConfig {
  return JSON.parse(JSON.stringify(view)) as ViewConfig;
}

export function widgetAt(view: ViewConfig, slot: number): WidgetConfig | undefined {
  return view.widgets.find((w) => w.slot === slot);
}

/** Merge ``updates`` into the widget at ``slot`` (creating it if empty). */
export function setWidget(
  view: ViewConfig,
  slot: number,
  updates: Partial<WidgetConfig>
): ViewConfig {
  const existing = widgetAt(view, slot);
  const widgets = existing
    ? view.widgets.map((w) => (w.slot === slot ? { ...w, ...updates, slot } : w))
    : [...view.widgets, { type: "", ...updates, slot }];
  return { ...view, widgets };
}

/** Put a new widget type in ``slot``: entity and label carry over, options reset. */
export function setWidgetType(
  view: ViewConfig,
  slot: number,
  type: string,
  initialOptions: Record<string, unknown> = {}
): ViewConfig {
  const existing = widgetAt(view, slot);
  const next: WidgetConfig = { slot, type, options: { ...initialOptions } };
  if (existing?.entity_id) next.entity_id = existing.entity_id;
  if (existing?.label) next.label = existing.label;
  const widgets = existing
    ? view.widgets.map((w) => (w.slot === slot ? next : w))
    : [...view.widgets, next];
  return { ...view, widgets };
}

/** Set one option of the widget at ``slot``; ``undefined`` removes it. */
export function setOption(
  view: ViewConfig,
  slot: number,
  key: string,
  value: unknown
): ViewConfig {
  const existing = widgetAt(view, slot);
  const options = { ...(existing?.options ?? {}) };
  if (value === undefined) delete options[key];
  else options[key] = value;
  return setWidget(view, slot, { options });
}

/** Exchange the widgets of two slots (either may be empty). */
export function swapSlots(view: ViewConfig, a: number, b: number): ViewConfig {
  if (a === b) return view;
  const widgets = view.widgets.map((w) =>
    w.slot === a ? { ...w, slot: b } : w.slot === b ? { ...w, slot: a } : w
  );
  return { ...view, widgets };
}

export function clearSlot(view: ViewConfig, slot: number): ViewConfig {
  return { ...view, widgets: view.widgets.filter((w) => w.slot !== slot) };
}

/** Widgets stored in slots the layout doesn't have (kept, but not shown). */
export function overflowWidgets(view: ViewConfig, slotCount: number): WidgetConfig[] {
  return view.widgets.filter((w) => w.slot >= slotCount && w.type);
}

export function removeOverflow(view: ViewConfig, slotCount: number): ViewConfig {
  return { ...view, widgets: view.widgets.filter((w) => w.slot < slotCount) };
}

/** Widgets that will actually render: a type, in a slot the layout has. */
export function visibleCount(view: ViewConfig, slotCount: number): number {
  return view.widgets.filter((w) => w.type && w.slot < slotCount).length;
}
