import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  AnimationCache,
  Autoplay,
  type AutoplayState,
  animationStatus,
  animationsOffOn,
  cacheable,
  renderKey,
} from "./animation-preview";
import { imageUrl } from "./api";
import type { DeviceConfig, HassEntity, PreviewResponse } from "./types";

function device(name: string, views: string[], animations?: string): DeviceConfig {
  return {
    entry_id: name,
    name,
    host: "10.0.0.1",
    assigned_views: views,
    current_view_index: 0,
    brightness: 50,
    refresh_interval: 10,
    cycle_interval: 0,
    online: true,
    entities: animations ? { animations } : {},
  };
}

const states = (entries: Record<string, string>): Record<string, HassEntity> =>
  Object.fromEntries(
    Object.entries(entries).map(([entity_id, state]) => [
      entity_id,
      { entity_id, state, attributes: {} } as unknown as HassEntity,
    ])
  );

describe("animationsOffOn", () => {
  const devices = [
    device("Desk", ["v1"], "switch.desk_animations"),
    device("Shelf", ["v1", "v2"], "switch.shelf_animations"),
    device("Kitchen", ["v2"], "switch.kitchen_animations"),
  ];

  it("names the displays showing the view with Animations off", () => {
    const hass = states({
      "switch.desk_animations": "off",
      "switch.shelf_animations": "on",
      "switch.kitchen_animations": "off",
    });
    expect(animationsOffOn(devices, "v1", hass)).toEqual(["Desk"]);
    expect(animationsOffOn(devices, "v2", hass)).toEqual(["Kitchen"]);
  });

  it("stays quiet about what it can't know", () => {
    // No switch resolved (display not loaded), or its state isn't in yet
    const unloaded = [device("Desk", ["v1"])];
    expect(animationsOffOn(unloaded, "v1", states({}))).toEqual([]);
    expect(animationsOffOn(devices, "v1", states({ "switch.desk_animations": "unavailable" }))).toEqual([]);
  });

  it("ignores displays the view isn't assigned to", () => {
    expect(animationsOffOn(devices, "v3", states({ "switch.desk_animations": "off" }))).toEqual([]);
  });
});

describe("imageUrl", () => {
  it("keeps the preview's format", () => {
    expect(imageUrl({ image: "R0lG", content_type: "image/gif" })).toBe("data:image/gif;base64,R0lG");
    expect(imageUrl({ image: "iVBO", content_type: "image/png" })).toBe("data:image/png;base64,iVBO");
  });
});

describe("animationStatus", () => {
  it("says what the screen shows", () => {
    expect(animationStatus(true, false)).toBe("Rendering the animation…");
    expect(animationStatus(false, true)).toBe("Playing the animation.");
    expect(animationStatus(false, false)).toBe("");
  });
});

const response = (over: Partial<PreviewResponse>): PreviewResponse => ({
  image: "x",
  content_type: "image/png",
  width: 240,
  height: 240,
  animatable: true,
  animated: false,
  too_large: false,
  gif_bytes: null,
  max_bytes: 409600,
  ...over,
});

describe("cacheable", () => {
  it("keeps GIFs and over-budget answers, not failed frames", () => {
    expect(cacheable(response({ animated: true, content_type: "image/gif" }))).toBe(true);
    expect(cacheable(response({ too_large: true, gif_bytes: 500_000 }))).toBe(true);
    expect(cacheable(response({}))).toBe(false);
  });
});

describe("renderKey", () => {
  it("ignores what doesn't change the frame", () => {
    const view = { layout: "grid_2x2", theme: "watchos", widgets: [{ slot: 0, type: "clock" }] };
    expect(renderKey({ ...view, name: "Renamed" } as typeof view)).toBe(renderKey(view));
    expect(renderKey({ ...view, theme: "neon" })).not.toBe(renderKey(view));
  });
});

describe("AnimationCache", () => {
  it("hits on the same key and misses on another", () => {
    const cache = new AnimationCache<string>();
    cache.set("a", "gif-a");
    expect(cache.get("a")).toBe("gif-a");
    expect(cache.get("b")).toBeUndefined();
  });

  it("evicts the least recently stored beyond its size", () => {
    const cache = new AnimationCache<string>(2);
    cache.set("a", "1");
    cache.set("b", "2");
    cache.set("a", "1'"); // refreshed: now the newest
    cache.set("c", "3");
    expect(cache.get("b")).toBeUndefined();
    expect(cache.get("a")).toBe("1'");
    expect(cache.get("c")).toBe("3");
  });

  it("expires entries", () => {
    let now = 0;
    const cache = new AnimationCache<string>(4, 120_000, () => now);
    cache.set("a", "gif");
    now = 119_000;
    expect(cache.get("a")).toBe("gif");
    now = 121_000;
    expect(cache.get("a")).toBeUndefined();
  });

  it("clears", () => {
    const cache = new AnimationCache<string>();
    cache.set("a", "gif");
    cache.clear();
    expect(cache.get("a")).toBeUndefined();
  });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("Autoplay", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  type Draft = { id: string };
  function setup() {
    const pending = new Map<string, ReturnType<typeof deferred<string>>>();
    const fetch = vi.fn((draft: Draft) => {
      const d = deferred<string>();
      pending.set(draft.id, d);
      return d.promise;
    });
    const states: AutoplayState<string>[] = [];
    const cache = new AnimationCache<string>();
    const autoplay = new Autoplay<Draft, string>({
      fetch,
      onChange: (s) => states.push(s),
      key: (d) => d.id,
      cache,
      keep: (r) => r.startsWith("gif"),
      delay: 1000,
    });
    const last = () => states.at(-1);
    return { autoplay, fetch, pending, cache, last, states };
  }

  it("plays once the still says it can, after the draft settles", async () => {
    const { autoplay, fetch, pending, last } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(true);
    expect(fetch).not.toHaveBeenCalled(); // not settled yet
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(last()).toMatchObject({ loading: true, result: null });
    pending.get("a")!.resolve("gif-a");
    await vi.advanceTimersByTimeAsync(0);
    expect(last()).toEqual({ result: "gif-a", loading: false, error: null });
  });

  it("starts at once when the still arrives after the delay", async () => {
    const { autoplay, fetch } = setup();
    autoplay.edit({ id: "a" });
    await vi.advanceTimersByTimeAsync(1500);
    expect(fetch).not.toHaveBeenCalled(); // nothing known to animate yet
    autoplay.still(true);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("never renders a view with nothing to animate", async () => {
    const { autoplay, fetch } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(false);
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("debounces edits: shows the still, renders only the settled draft", async () => {
    const { autoplay, fetch, last } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(true);
    for (const id of ["b", "c", "d"]) {
      await vi.advanceTimersByTimeAsync(400);
      autoplay.edit({ id });
      expect(last()?.result).toBeNull();
      autoplay.still(true);
    }
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetch.mock.calls.map(([d]) => d.id)).toEqual(["d"]);
  });

  it("renders one at a time, drops a stale result and renders the latest once", async () => {
    const { autoplay, fetch, pending, cache, last } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(true);
    await vi.advanceTimersByTimeAsync(1000); // "a" in flight
    for (const id of ["b", "c"]) {
      autoplay.edit({ id });
      autoplay.still(true);
      await vi.advanceTimersByTimeAsync(1000); // settled while "a" runs
    }
    expect(fetch).toHaveBeenCalledTimes(1);
    pending.get("a")!.resolve("gif-a");
    await vi.advanceTimersByTimeAsync(0);
    expect(cache.get("a")).toBe("gif-a"); // kept for later
    expect(fetch.mock.calls.map(([d]) => d.id)).toEqual(["a", "c"]);
    expect(last()).toMatchObject({ result: null, loading: true });
    pending.get("c")!.resolve("gif-c");
    await vi.advanceTimersByTimeAsync(0);
    expect(last()).toEqual({ result: "gif-c", loading: false, error: null });
  });

  it("plays a draft rendered recently at once, with no request", async () => {
    const { autoplay, fetch, cache, last } = setup();
    cache.set("a", "gif-a");
    autoplay.edit({ id: "a" });
    expect(last()).toMatchObject({ result: "gif-a", loading: false });
    autoplay.still(true);
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("reports a failure, keeps nothing, and retries on request", async () => {
    const { autoplay, fetch, pending, cache, last } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(true);
    await vi.advanceTimersByTimeAsync(1000);
    pending.get("a")!.reject({ message: "boom" });
    await vi.advanceTimersByTimeAsync(0);
    expect(last()).toEqual({ result: null, loading: false, error: "boom" });
    expect(cache.get("a")).toBeUndefined();
    autoplay.refresh();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("renders again from fresh when live data moved on, not from the cache", async () => {
    const { autoplay, fetch, pending, cache, last } = setup();
    cache.set("a", "gif-a");
    autoplay.edit({ id: "a" });
    expect(last()).toMatchObject({ result: "gif-a" });
    autoplay.still(true); // the draft's still has arrived by the minute tick
    autoplay.refresh();
    expect(fetch).toHaveBeenCalledTimes(1); // the cached frame is stale now
    expect(last()).toMatchObject({ result: "gif-a", loading: true }); // the old frame stays
    pending.get("a")!.resolve("gif-a2");
    await vi.advanceTimersByTimeAsync(0);
    expect(last()).toEqual({ result: "gif-a2", loading: false, error: null });
    expect(cache.get("a")).toBe("gif-a2");
  });

  it("drops a render that lands after dispose", async () => {
    const { autoplay, pending, states } = setup();
    autoplay.edit({ id: "a" });
    autoplay.still(true);
    await vi.advanceTimersByTimeAsync(1000);
    const calls = states.length;
    autoplay.dispose();
    pending.get("a")!.resolve("gif-a");
    await vi.advanceTimersByTimeAsync(0);
    expect(states.length).toBe(calls);
  });
});
