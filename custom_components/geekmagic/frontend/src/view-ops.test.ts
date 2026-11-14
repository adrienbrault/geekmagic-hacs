import { describe, expect, it } from "vitest";
import type { ViewConfig } from "./types";
import {
  clearSlot,
  cloneView,
  overflowWidgets,
  removeOverflow,
  setOption,
  setWidget,
  setWidgetType,
  swapSlots,
  visibleCount,
  widgetAt,
} from "./view-ops";

const view = (): ViewConfig => ({
  id: "v",
  name: "View",
  layout: "grid_2x2",
  theme: "watchos",
  widgets: [
    { slot: 0, type: "clock", options: { show_date: true } },
    { slot: 1, type: "entity", entity_id: "sensor.temp", label: "Room" },
  ],
});

/** Fails if ``fn`` mutates its input anywhere in the tree. */
function pure<T>(fn: (v: ViewConfig) => T): T {
  const input = view();
  const before = JSON.stringify(input);
  const result = fn(input);
  expect(JSON.stringify(input)).toBe(before);
  return result;
}

describe("view-ops", () => {
  it("cloneView is deep", () => {
    const original = view();
    const copy = cloneView(original);
    copy.widgets[0].options!.show_date = false;
    expect(original.widgets[0].options!.show_date).toBe(true);
  });

  it("swapSlots exchanges and leaves the source untouched", () => {
    const swapped = pure((v) => swapSlots(v, 0, 1));
    expect(widgetAt(swapped, 0)?.type).toBe("entity");
    expect(widgetAt(swapped, 1)?.type).toBe("clock");
  });

  it("swapSlots into an empty slot moves the widget", () => {
    const moved = pure((v) => swapSlots(v, 1, 3));
    expect(widgetAt(moved, 1)).toBeUndefined();
    expect(widgetAt(moved, 3)?.entity_id).toBe("sensor.temp");
  });

  it("a swap then discard (keep the original) loses nothing", () => {
    const stored = view();
    const draft = swapSlots(cloneView(stored), 0, 1);
    expect(widgetAt(draft, 0)?.type).toBe("entity");
    expect(widgetAt(stored, 0)?.type).toBe("clock");
  });

  it("setWidget merges, or creates an empty slot's widget", () => {
    const edited = pure((v) => setWidget(v, 1, { label: "Living room" }));
    expect(widgetAt(edited, 1)).toMatchObject({ type: "entity", label: "Living room" });
    const created = pure((v) => setWidget(v, 2, { type: "gauge" }));
    expect(widgetAt(created, 2)).toEqual({ slot: 2, type: "gauge" });
  });

  it("setWidgetType keeps entity and label, resets options", () => {
    const changed = pure((v) => setWidgetType(v, 1, "gauge", { style: "ring" }));
    expect(widgetAt(changed, 1)).toEqual({
      slot: 1,
      type: "gauge",
      entity_id: "sensor.temp",
      label: "Room",
      options: { style: "ring" },
    });
  });

  it("setOption sets and removes", () => {
    const set = pure((v) => setOption(v, 0, "show_seconds", true));
    expect(widgetAt(set, 0)?.options).toEqual({ show_date: true, show_seconds: true });
    const removed = setOption(set, 0, "show_date", undefined);
    expect(widgetAt(removed, 0)?.options).toEqual({ show_seconds: true });
  });

  it("clearSlot empties one slot", () => {
    const cleared = pure((v) => clearSlot(v, 0));
    expect(cleared.widgets.map((w) => w.slot)).toEqual([1]);
  });

  it("counts and trims widgets beyond the layout", () => {
    const v = setWidget(view(), 3, { type: "text" });
    expect(visibleCount(v, 4)).toBe(3);
    expect(visibleCount(v, 1)).toBe(1);
    expect(overflowWidgets(v, 2).map((w) => w.slot)).toEqual([3]);
    expect(removeOverflow(v, 2).widgets.map((w) => w.slot)).toEqual([0, 1]);
  });

  it("an untyped placeholder is not a visible widget", () => {
    const v = setWidget(view(), 2, { label: "x" });
    expect(visibleCount(v, 4)).toBe(2);
    expect(overflowWidgets(setWidget(view(), 5, { label: "x" }), 4)).toEqual([]);
  });
});
