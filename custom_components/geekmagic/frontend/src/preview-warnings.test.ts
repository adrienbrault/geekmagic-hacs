import { describe, expect, it } from "vitest";
import { warningText } from "./preview-warnings";

describe("warningText", () => {
  it("names the overflowing text", () => {
    const text = warningText({ slot: 0, kind: "overflow", items: ["unavailable"] }, "Slot 1: HTML");
    expect(text.title).toBe("Slot 1: HTML: text runs off the screen");
    expect(text.body).toBe('"unavailable" is wider than the cell. Use fit() to size it, or a smaller font.');
  });

  it("lists unknown classes, capped", () => {
    const items = ["a", "b", "c", "d", "e", "f"];
    const text = warningText({ slot: 1, kind: "unknown_classes", items }, "Slot 2: HTML");
    expect(text.title).toBe("Slot 2: HTML: 6 unknown classes");
    expect(text.body).toBe("a, b, c, d and 2 more have no styles: a typo, or a utility the display can't paint.");
  });

  it("singular", () => {
    const text = warningText({ slot: 0, kind: "unknown_classes", items: ["blur-sm"] }, "Slot 1");
    expect(text.title).toBe("Slot 1: 1 unknown class");
    expect(text.body.startsWith("blur-sm has no styles")).toBe(true);
  });
});
