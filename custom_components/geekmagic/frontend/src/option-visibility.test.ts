import { describe, expect, it } from "vitest";
import type { WidgetOption } from "./types";
import { isOptionVisible, visibleOptions } from "./option-visibility";

const style: WidgetOption = {
  key: "style",
  type: "select",
  label: "Style",
  options: ["bar", "ring", "arc"],
  default: "bar",
};
const showName: WidgetOption = { key: "show_name", type: "boolean", label: "Name", default: true };
const orientation: WidgetOption = {
  key: "orientation",
  type: "select",
  label: "Bar Orientation",
  visible_when: { style: ["bar"] },
};
const both: WidgetOption = {
  key: "both",
  type: "text",
  label: "Both",
  visible_when: { style: ["bar", "arc"], show_name: [true] },
};
const all = [style, showName, orientation, both];

describe("option visibility", () => {
  it("unconditioned options are always shown", () => {
    expect(isOptionVisible(style, all, {})).toBe(true);
  });

  it("falls back to the default when unset", () => {
    expect(isOptionVisible(orientation, all, undefined)).toBe(true);
    expect(isOptionVisible(orientation, all, { style: "ring" })).toBe(false);
  });

  it("any of the allowed values, and all of the keys", () => {
    expect(isOptionVisible(both, all, { style: "arc" })).toBe(true);
    expect(isOptionVisible(both, all, { style: "arc", show_name: false })).toBe(false);
    expect(isOptionVisible(both, all, { style: "ring", show_name: true })).toBe(false);
  });

  it("an unknown key never hides", () => {
    const typo: WidgetOption = { ...orientation, visible_when: { stlye: ["bar"] } };
    expect(isOptionVisible(typo, [...all, typo], { style: "ring" })).toBe(true);
  });

  it("filters a schema's options", () => {
    expect(visibleOptions(all, { style: "ring" }).map((o) => o.key)).toEqual([
      "style",
      "show_name",
    ]);
  });
});
