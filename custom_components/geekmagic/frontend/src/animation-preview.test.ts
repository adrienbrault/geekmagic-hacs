import { describe, expect, it } from "vitest";
import {
  AnimationCache,
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

