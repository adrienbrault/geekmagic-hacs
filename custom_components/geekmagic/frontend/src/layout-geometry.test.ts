import { describe, it, expect } from "vitest";
import { slotRectStyle } from "./layout-geometry";

describe("slotRectStyle", () => {
  it("places a quarter cell as percentages inset by half the gap", () => {
    expect(slotRectStyle({ x: 0.5, y: 0, w: 0.5, h: 0.5 }, 2)).toBe(
      "left: calc(50% + 1px); top: calc(0% + 1px); " +
        "width: calc(50% - 2px); height: calc(50% - 2px)"
    );
  });

  it("covers the whole square when there is no gap", () => {
    expect(slotRectStyle({ x: 0, y: 0, w: 1, h: 1 }, 0)).toBe(
      "left: calc(0% + 0px); top: calc(0% + 0px); " +
        "width: calc(100% - 0px); height: calc(100% - 0px)"
    );
  });

  it("rounds thirds to two decimals", () => {
    expect(slotRectStyle({ x: 0.6667, y: 0.3333, w: 0.3333, h: 0.6667 }, 2)).toBe(
      "left: calc(66.67% + 1px); top: calc(33.33% + 1px); " +
        "width: calc(33.33% - 2px); height: calc(66.67% - 2px)"
    );
  });
});
