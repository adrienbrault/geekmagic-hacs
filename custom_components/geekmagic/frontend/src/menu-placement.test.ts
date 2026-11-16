import { describe, expect, it } from "vitest";
import { placeMenu } from "./menu-placement";

const viewport = { width: 1000, height: 800 };

describe("placeMenu", () => {
  it("opens below the button when the menu fits there", () => {
    const placed = placeMenu({ top: 100, bottom: 140, right: 900 }, 200, viewport);
    expect(placed).toEqual({ top: 140, right: 100, maxHeight: 652 });
  });

  it("opens above a button near the bottom of the viewport", () => {
    const placed = placeMenu({ top: 700, bottom: 740, right: 900 }, 200, viewport);
    // Hangs from just above the button, so its last item stays on screen
    expect(placed).toEqual({ bottom: 100, right: 100, maxHeight: 692 });
  });

  it("caps the height on the roomier side when neither side fits", () => {
    const short = { width: 1000, height: 300 };
    expect(placeMenu({ top: 100, bottom: 140, right: 900 }, 400, short)).toEqual({
      top: 140,
      right: 100,
      maxHeight: 152,
    });
    expect(placeMenu({ top: 200, bottom: 240, right: 900 }, 400, short)).toEqual({
      bottom: 100,
      right: 100,
      maxHeight: 192,
    });
  });

  it("keeps a margin from the right edge", () => {
    expect(placeMenu({ top: 100, bottom: 140, right: 998 }, 100, viewport).right).toBe(8);
  });
});
