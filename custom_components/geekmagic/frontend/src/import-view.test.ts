import { describe, expect, it } from "vitest";
import {
  entityMap,
  importName,
  importPayload,
  missingEntities,
  parseImport,
  stripFences,
} from "./import-view";
import type { ViewConfig } from "./types";

const VIEW = { name: "Desk", layout: "grid_2x2", theme: "standby", widgets: [{ type: "clock", slot: 0 }] };

describe("stripFences", () => {
  it("takes the first fenced block, whatever its language tag", () => {
    expect(stripFences('Here it is:\n```json\n{"a": 1}\n```\nEnjoy!')).toBe('{"a": 1}');
    expect(stripFences('```\n{"a": 2}\n```')).toBe('{"a": 2}');
  });

  it("leaves unfenced text as is, trimmed", () => {
    expect(stripFences('  {"a": 1}\n')).toBe('{"a": 1}');
  });
});

describe("parseImport", () => {
  it("reads a bare view, fenced or not", () => {
    expect(parseImport(JSON.stringify(VIEW)).view).toEqual(VIEW);
    expect(parseImport("```json\n" + JSON.stringify(VIEW, null, 1) + "\n```").view).toEqual(VIEW);
  });

  it("unwraps a view carried under `view` (a panel export)", () => {
    const exported = { version: 1, view: VIEW, entities: {} };
    expect(parseImport(JSON.stringify(exported)).view).toEqual(VIEW);
  });

  it("explains what's wrong", () => {
    expect(parseImport("   ").error).toMatch(/Paste/);
    expect(parseImport("{nope").error).toMatch(/valid JSON/);
    expect(parseImport("[1, 2]").error).toMatch(/JSON object/);
    expect(parseImport('"grid_2x2"').error).toMatch(/JSON object/);
  });
});

describe("mapping", () => {
  const entities = [
    { id: "sensor.here", exists: true, domain: "sensor" },
    { id: "weather.demo", exists: false, domain: "weather" },
  ];

  it("offers a row per entity this Home Assistant lacks", () => {
    expect(missingEntities(entities).map((e) => e.id)).toEqual(["weather.demo"]);
  });

  it("keeps only the picks that change an id", () => {
    expect(
      entityMap({ "weather.demo": "weather.home", "sensor.a": "", "sensor.b": "sensor.b" })
    ).toEqual({ "weather.demo": "weather.home" });
  });
});

describe("saving", () => {
  const views = [{ id: "1", name: "Desk", layout: "grid_2x2", theme: "watchos", widgets: [] }] as ViewConfig[];

  it("names the copy after the view, never a taken name", () => {
    expect(importName(VIEW, views)).toBe("Desk 2");
    expect(importName({ ...VIEW, name: "Kitchen" }, views)).toBe("Kitchen");
    expect(importName({ layout: "fullscreen" }, views)).toBe("Imported view");
  });

  it("sends layout, theme and widgets only, with the theme the preview shows", () => {
    const stored = { ...VIEW, id: "abc", created_at: "x", updated_at: "y" };
    expect(importPayload(stored)).toEqual({
      layout: "grid_2x2",
      theme: "standby",
      widgets: VIEW.widgets,
    });
    expect(importPayload({ layout: "fullscreen" })).toEqual({
      layout: "fullscreen",
      theme: "watchos",
      widgets: [],
    });
  });
});
