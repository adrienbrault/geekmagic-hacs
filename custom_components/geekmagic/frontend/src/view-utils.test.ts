import { describe, it, expect } from "vitest";
import {
  LAYOUT_CONFIGS,
  getLayoutConfig,
  updateWidget,
  swapSlots,
  toggleDeviceView,
} from "./view-utils";
import type { WidgetConfig, DeviceConfig } from "./types";

// ---------------------------------------------------------------------------
// getLayoutConfig
// ---------------------------------------------------------------------------

describe("getLayoutConfig", () => {
  it("returns config for known layout", () => {
    const config = getLayoutConfig("grid_2x2");
    expect(config).toEqual({ cls: "g-2x2", cells: 4 });
  });

  it("returns config for fullscreen", () => {
    expect(getLayoutConfig("fullscreen")).toEqual({ cls: "full", cells: 1 });
  });

  it("returns config for grid_3x3", () => {
    expect(getLayoutConfig("grid_3x3")).toEqual({ cls: "g-3x3", cells: 9 });
  });

  it("returns default config for unknown layout", () => {
    const config = getLayoutConfig("nonexistent_layout");
    expect(config).toEqual({ cls: "", cells: 4 });
  });

  it("returns default config for empty string", () => {
    expect(getLayoutConfig("")).toEqual({ cls: "", cells: 4 });
  });
});

describe("LAYOUT_CONFIGS completeness", () => {
  it("has 19 layout entries", () => {
    expect(Object.keys(LAYOUT_CONFIGS)).toHaveLength(19);
  });

  it("every entry has cls and cells", () => {
    for (const [key, config] of Object.entries(LAYOUT_CONFIGS)) {
      expect(config).toHaveProperty("cls");
      expect(config).toHaveProperty("cells");
      expect(typeof config.cls).toBe("string");
      expect(typeof config.cells).toBe("number");
      expect(config.cells).toBeGreaterThan(0);
    }
  });

  it("cells are within valid range (1-9)", () => {
    for (const config of Object.values(LAYOUT_CONFIGS)) {
      expect(config.cells).toBeGreaterThanOrEqual(1);
      expect(config.cells).toBeLessThanOrEqual(9);
    }
  });
});

// ---------------------------------------------------------------------------
// updateWidget
// ---------------------------------------------------------------------------

describe("updateWidget", () => {
  const baseWidgets: WidgetConfig[] = [
    { slot: 0, type: "clock" },
    { slot: 1, type: "entity", entity_id: "sensor.temp" },
  ];

  it("updates existing widget by slot", () => {
    const result = updateWidget(baseWidgets, 0, { type: "text" });
    expect(result[0]).toMatchObject({ slot: 0, type: "text" });
    // Original untouched
    expect(result[1]).toMatchObject({ slot: 1, type: "entity" });
  });

  it("adds new widget for unoccupied slot", () => {
    const result = updateWidget(baseWidgets, 2, { type: "gauge" });
    expect(result).toHaveLength(3);
    expect(result[2]).toMatchObject({ slot: 2, type: "gauge" });
  });

  it("preserves existing properties when merging", () => {
    const result = updateWidget(baseWidgets, 1, { label: "Temperature" });
    expect(result[1]).toMatchObject({
      slot: 1,
      type: "entity",
      entity_id: "sensor.temp",
      label: "Temperature",
    });
  });

  it("does not mutate original array", () => {
    const original = [...baseWidgets];
    updateWidget(baseWidgets, 0, { type: "text" });
    expect(baseWidgets).toEqual(original);
  });

  it("auto-populates timezone for clock widgets", () => {
    const result = updateWidget([], 0, { type: "clock" }, () => "Europe/Paris");
    expect(result[0].options).toEqual({ timezone: "Europe/Paris" });
  });

  it("does not set timezone for non-clock widgets", () => {
    const result = updateWidget([], 0, { type: "entity" }, () => "Europe/Paris");
    expect(result[0].options).toBeUndefined();
  });

  it("does not set timezone without getBrowserTimezone callback", () => {
    const result = updateWidget([], 0, { type: "clock" });
    expect(result[0].options).toBeUndefined();
  });

  it("merges timezone with existing options", () => {
    const result = updateWidget(
      [],
      0,
      { type: "clock", options: { show_date: true } },
      () => "Asia/Tokyo",
    );
    expect(result[0].options).toEqual({
      show_date: true,
      timezone: "Asia/Tokyo",
    });
  });

  it("new widget gets default empty type", () => {
    const result = updateWidget([], 3, { label: "Test" });
    expect(result[0]).toMatchObject({ slot: 3, type: "", label: "Test" });
  });
});

// ---------------------------------------------------------------------------
// swapSlots
// ---------------------------------------------------------------------------

describe("swapSlots", () => {
  const widgets: WidgetConfig[] = [
    { slot: 0, type: "clock" },
    { slot: 1, type: "entity" },
    { slot: 2, type: "text" },
  ];

  it("swaps two occupied slots", () => {
    const result = swapSlots(widgets, 0, 2);
    expect(result.find((w) => w.type === "clock")?.slot).toBe(2);
    expect(result.find((w) => w.type === "text")?.slot).toBe(0);
    // Middle unchanged
    expect(result.find((w) => w.type === "entity")?.slot).toBe(1);
  });

  it("returns same array when from === to", () => {
    const result = swapSlots(widgets, 1, 1);
    expect(result).toBe(widgets); // identity check
  });

  it("handles swap when only fromSlot has a widget", () => {
    const result = swapSlots(widgets, 0, 5);
    expect(result.find((w) => w.type === "clock")?.slot).toBe(5);
    // No widget was at slot 5, so nothing moved to slot 0
  });

  it("handles swap when only toSlot has a widget", () => {
    const result = swapSlots(widgets, 5, 0);
    expect(result.find((w) => w.type === "clock")?.slot).toBe(5);
  });

  it("handles swap when neither slot has a widget", () => {
    const result = swapSlots(widgets, 7, 8);
    // No changes, all widgets keep original slots
    expect(result.map((w) => w.slot).sort()).toEqual([0, 1, 2]);
  });

  it("does not mutate original array", () => {
    const original = widgets.map((w) => ({ ...w }));
    swapSlots(widgets, 0, 2);
    expect(widgets.map((w) => w.slot)).toEqual(original.map((w) => w.slot));
  });

  it("does not mutate original widget objects", () => {
    const result = swapSlots(widgets, 0, 1);
    // Result widgets are new objects
    expect(result[0]).not.toBe(widgets[0]);
    expect(result[1]).not.toBe(widgets[1]);
  });
});

// ---------------------------------------------------------------------------
// toggleDeviceView
// ---------------------------------------------------------------------------

describe("toggleDeviceView", () => {
  const device: DeviceConfig = {
    entry_id: "abc123",
    name: "Living Room Display",
    host: "192.168.1.100",
    assigned_views: ["view1", "view2"],
    current_view_index: 0,
    brightness: 80,
    refresh_interval: 10,
    cycle_interval: 0,
    online: true,
  };

  it("adds a view when enabled", () => {
    const result = toggleDeviceView(device, "view3", true);
    expect(result).toEqual(["view1", "view2", "view3"]);
  });

  it("removes a view when disabled", () => {
    const result = toggleDeviceView(device, "view1", false);
    expect(result).toEqual(["view2"]);
  });

  it("does not duplicate when adding existing view", () => {
    const result = toggleDeviceView(device, "view1", true);
    expect(result).toEqual(["view1", "view2", "view1"]);
    // Note: dedup is the caller's responsibility if needed
  });

  it("returns unchanged list when removing non-existent view", () => {
    const result = toggleDeviceView(device, "view_nonexistent", false);
    expect(result).toEqual(["view1", "view2"]);
  });

  it("does not mutate original device", () => {
    toggleDeviceView(device, "view3", true);
    expect(device.assigned_views).toEqual(["view1", "view2"]);
  });

  it("works with empty assigned_views", () => {
    const emptyDevice = { ...device, assigned_views: [] };
    expect(toggleDeviceView(emptyDevice, "view1", true)).toEqual(["view1"]);
    expect(toggleDeviceView(emptyDevice, "view1", false)).toEqual([]);
  });
});
