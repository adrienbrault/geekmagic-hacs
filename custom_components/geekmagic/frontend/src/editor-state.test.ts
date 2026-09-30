import { describe, it, expect } from "vitest";
import {
  changeWidgetType,
  cloneView,
  swapWidgetSlots,
  toggleAssignedView,
} from "./editor-state";
import type { ViewConfig, WidgetConfig, WidgetTypeSchema } from "./types";

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

describe("changeWidgetType", () => {
  const schemas: Record<string, WidgetTypeSchema> = {
    entity: { name: "Entity", needs_entity: true, options: [] },
    gauge: {
      name: "Gauge",
      needs_entity: true,
      entity_domains: ["sensor"],
      options: [],
    },
    weather: {
      name: "Weather",
      needs_entity: true,
      entity_domains: ["weather"],
      options: [],
    },
    clock: { name: "Clock", needs_entity: false, options: [] },
  };
  const entity: WidgetConfig = {
    type: "entity",
    slot: 1,
    entity_id: "sensor.temp",
    label: "Temp",
    options: { show_name: true },
  };
  const change = (widgets: WidgetConfig[], type: string) =>
    changeWidgetType(widgets, 1, type, schemas, "Europe/Paris");

  it("drops the entity and options when the new type cannot use them", () => {
    expect(change([entity], "weather")).toEqual([
      { type: "weather", slot: 1, label: "Temp" },
    ]);
  });

  it("keeps an entity whose domain the new type accepts", () => {
    expect(change([entity], "gauge")).toEqual([
      { type: "gauge", slot: 1, label: "Temp", entity_id: "sensor.temp" },
    ]);
  });

  it("seeds a new clock with the given timezone", () => {
    expect(change([entity], "clock")).toEqual([
      { type: "clock", slot: 1, label: "Temp", options: { timezone: "Europe/Paris" } },
    ]);
  });

  it("removes the widget for the empty type", () => {
    const other: WidgetConfig = { type: "clock", slot: 0 };
    expect(change([other, entity], "")).toEqual([other]);
  });

  it("adds a widget to an empty slot", () => {
    expect(change([], "gauge")).toEqual([{ type: "gauge", slot: 1 }]);
  });

  it("returns the input untouched when the type is unchanged", () => {
    const widgets = [entity];
    expect(change(widgets, "entity")).toBe(widgets);
    const empty: WidgetConfig[] = [];
    expect(change(empty, "")).toBe(empty);
  });
});

describe("toggleAssignedView", () => {
  it("adds and removes without mutating the input", () => {
    const assigned = ["a", "b"];
    expect(toggleAssignedView(assigned, "c", true)).toEqual(["a", "b", "c"]);
    expect(toggleAssignedView(assigned, "a", false)).toEqual(["b"]);
    expect(assigned).toEqual(["a", "b"]);
  });

  it("composes successive toggles on the latest list", () => {
    let assigned: string[] = [];
    assigned = toggleAssignedView(assigned, "a", true);
    assigned = toggleAssignedView(assigned, "b", true);
    expect(assigned).toEqual(["a", "b"]);
  });

  it("never duplicates an id", () => {
    expect(toggleAssignedView(["a"], "a", true)).toEqual(["a"]);
    expect(toggleAssignedView(["a"], "x", false)).toEqual(["a"]);
  });
});
