import { describe, expect, it } from "vitest";
import { addViews, cycled, moveItem, moveTo, neighbour, removeView } from "./rotation";

describe("rotation", () => {
  it("moves an item earlier or later", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b", "c"], 2, -1)).toEqual(["a", "c", "b"]);
  });

  it("ignores moves past either end, returning the same list", () => {
    const list = ["a", "b"];
    expect(moveItem(list, 0, -1)).toBe(list);
    expect(moveItem(list, 1, 1)).toBe(list);
    expect(moveItem(list, 5, 1)).toBe(list);
  });

  it("drags to a position", () => {
    expect(moveTo(["a", "b", "c", "d"], 0, 2)).toEqual(["b", "c", "a", "d"]);
    expect(moveTo(["a", "b", "c", "d"], 3, 0)).toEqual(["d", "a", "b", "c"]);
  });

  it("adds without duplicates, keeping order", () => {
    expect(addViews(["a"], ["b", "a", "c"])).toEqual(["a", "b", "c"]);
  });

  it("removes", () => {
    expect(removeView(["a", "b", "c"], "b")).toEqual(["a", "c"]);
  });

  it("finds neighbours, wrapping", () => {
    expect(neighbour(["a", "b", "c"], "c", 1)).toBe("a");
    expect(neighbour(["a", "b", "c"], "a", -1)).toBe("c");
    expect(neighbour(["a", "b"], null, 1)).toBe("a");
    expect(neighbour([], "a", 1)).toBeNull();
  });

  it("steps over skipped views, as View Cycling does", () => {
    expect(cycled(["a", "b", "c"], ["b"])).toEqual(["a", "c"]);
    expect(neighbour(["a", "b", "c"], "a", 1, ["b"])).toBe("c");
    expect(neighbour(["a", "b", "c"], "a", -1, ["c"])).toBe("b");
    // From a skipped view on screen, to the nearest cycled one
    expect(neighbour(["a", "b", "c"], "b", 1, ["b"])).toBe("c");
    expect(neighbour(["a", "b", "c"], "b", -1, ["b"])).toBe("a");
    // Nothing else cycles: stay
    expect(neighbour(["a", "b", "c"], "a", 1, ["b", "c"])).toBe("a");
    // Nothing on screen: the first (or last) cycled view
    expect(neighbour(["a", "b", "c"], null, 1, ["a"])).toBe("b");
    expect(neighbour(["a", "b", "c"], null, -1, ["c"])).toBe("b");
  });
});
