import { describe, expect, it } from "vitest";
import type { GeekMagicConfig, ViewConfig } from "./types";
import {
  formatSeconds,
  imageEntityUrl,
  intervalChoices,
  plural,
  rowTitle,
  suggestName,
  viewMeta,
} from "./format";

const config = {
  widget_types: {},
  layout_types: {
    grid_2x2: { slots: 4, name: "Grid 2×2", rects: [] },
    fullscreen: { slots: 1, name: "Fullscreen", rects: [] },
  },
  themes: { watchos: "watchOS" },
} as GeekMagicConfig;

const view = (layout: string, slots: number[]): ViewConfig => ({
  id: "v",
  name: "V",
  layout,
  theme: "watchos",
  widgets: slots.map((slot) => ({ slot, type: "clock" })),
});

describe("format", () => {
  it("pluralises", () => {
    expect(plural(1, "widget")).toBe("1 widget");
    expect(plural(0, "widget")).toBe("0 widgets");
  });

  it("describes a view, counting only widgets the layout shows", () => {
    expect(viewMeta(config, view("grid_2x2", [0]))).toBe("Grid 2×2 · watchOS · 1 widget");
    expect(viewMeta(config, view("fullscreen", [0, 1, 2]))).toBe(
      "Fullscreen · watchOS · 1 widget"
    );
  });

  it("titles array rows by label, then entity name", () => {
    const names = (id: string) => (id === "light.bed" ? "Bed Light" : undefined);
    expect(rowTitle({ label: "Bed", entity_id: "light.bed" }, names, "New")).toBe("Bed");
    expect(rowTitle({ entity_id: "light.bed" }, names, "New")).toBe("Bed Light");
    expect(rowTitle({ entity_id: "light.gone" }, names, "New")).toBe("light.gone");
    expect(rowTitle({ entity_id: "" }, names, "New entity")).toBe("New entity");
  });

  it("offers intervals, keeping an odd current value", () => {
    expect(intervalChoices(30).map((c) => c.value)).toEqual([5, 10, 15, 30, 60, 120, 300]);
    expect(intervalChoices(45).map((c) => c.value)).toContain(45);
    expect(formatSeconds(90)).toBe("1 min 30 s");
    expect(formatSeconds(120)).toBe("2 min");
  });

  it("busts the image cache with the entity state", () => {
    expect(imageEntityUrl("/api/image_proxy/x?token=t", "2026-01-01T00:00:00")).toBe(
      "/api/image_proxy/x?token=t&v=2026-01-01T00%3A00%3A00"
    );
    expect(imageEntityUrl(undefined, "s")).toBeNull();
  });

  it("suggests an unused name", () => {
    expect(suggestName([])).toBe("New view");
    expect(suggestName([{ ...view("grid_2x2", []), name: "New view" }])).toBe("New view 2");
  });
});
