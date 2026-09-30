import { describe, it, expect } from "vitest";
import { cloneView, swapWidgetSlots } from "./editor-state";
import type { ViewConfig, WidgetConfig } from "./types";

const view = (): ViewConfig => ({
  id: "v1",
  name: "Kitchen",
  layout: "grid_2x2",
  theme: "watchos",
  widgets: [
    { type: "clock", slot: 0, options: { timezone: "UTC" } },
    { type: "entity", slot: 1, entity_id: "sensor.temp" },
  ],
});

describe("cloneView", () => {
  it("shares no widget objects with the source", () => {
    const source = view();
    const draft = cloneView(source);
    expect(draft).toEqual(source);
    draft.widgets[0].slot = 3;
    draft.widgets[0].options!.timezone = "Europe/Paris";
    expect(source.widgets[0]).toEqual({
      type: "clock",
      slot: 0,
      options: { timezone: "UTC" },
    });
  });
});

describe("swapWidgetSlots", () => {
  it("swaps two occupied slots without mutating the input", () => {
    const widgets = view().widgets;
    const snapshot = structuredClone(widgets);
    const swapped = swapWidgetSlots(widgets, 0, 1);
    expect(swapped.map((w) => [w.type, w.slot])).toEqual([
      ["clock", 1],
      ["entity", 0],
    ]);
    expect(widgets).toEqual(snapshot);
    expect(swapped[0]).not.toBe(widgets[0]);
  });

  it("moves a widget into an empty slot", () => {
    const widgets: WidgetConfig[] = [{ type: "clock", slot: 0 }];
    expect(swapWidgetSlots(widgets, 0, 3)).toEqual([{ type: "clock", slot: 3 }]);
    expect(widgets[0].slot).toBe(0);
  });

  it("moves an empty slot's partner back into it", () => {
    const widgets: WidgetConfig[] = [{ type: "clock", slot: 2 }];
    expect(swapWidgetSlots(widgets, 0, 2)).toEqual([{ type: "clock", slot: 0 }]);
  });

  it("is a no-op for the same slot", () => {
    const widgets = view().widgets;
    expect(swapWidgetSlots(widgets, 1, 1)).toBe(widgets);
  });
});
