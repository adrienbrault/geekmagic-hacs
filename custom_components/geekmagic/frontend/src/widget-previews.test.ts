import { describe, expect, it } from "vitest";
import { previewSize, previewUrl } from "./widget-previews";

describe("widget previews", () => {
  it("picks the size class closest to the slot", () => {
    expect(previewSize(224, 224)).toBe("1x1"); // fullscreen
    expect(previewSize(108, 108)).toBe("2x2");
    expect(previewSize(72, 72)).toBe("3x3");
    expect(previewSize(224, 108)).toBe("2x1"); // wide band
    expect(previewSize(108, 224)).toBe("1x2"); // tall column
    expect(previewSize(69, 108)).toBe("2x3");
    expect(previewSize(108, 69)).toBe("3x2");
  });

  it("matches cells of other layouts by shape and scale", () => {
    expect(previewSize(232, 150)).toBe("1x1"); // a hero above a footer
    expect(previewSize(70, 50)).toBe("3x3"); // a footer cell
    // 150px wide keeps every band, like a fullscreen cell, not a 108px column.
    expect(previewSize(150, 230)).toBe("1x1");
    expect(previewSize(110, 230)).toBe("1x2");
  });

  it("builds the URL from the type's sample, or none without one", () => {
    expect(previewUrl("/p", "abc", "entity", 108, 108)).toBe("/p/entity_icon_2x2.png?v=abc");
    expect(previewUrl("/p", "abc", "html", 108, 108)).toBeNull();
    expect(previewUrl("/p", "abc", "entity", 0, 108)).toBeNull();
  });
});
