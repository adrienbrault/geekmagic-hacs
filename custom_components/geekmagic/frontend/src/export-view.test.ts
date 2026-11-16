import { describe, expect, it, vi } from "vitest";
import {
  copyText,
  exportedEntities,
  exportJson,
  hasTemplates,
  portableView,
  viewJson,
  type ViewExport,
} from "./export-view";
import { parseImport } from "./import-view";
import type { ViewConfig } from "./types";

const STORED: ViewConfig = {
  id: "abc",
  name: "Desk",
  layout: "grid_2x2",
  theme: "standby",
  widgets: [{ type: "clock", slot: 0 }],
  created_at: "2026-11-16T08:00:00",
  updated_at: "2026-11-16T09:00:00",
};

const EXPORT: ViewExport = {
  version: 1,
  integration_version: "1.9.0",
  now: "2026-11-16T08:30:00+01:00",
  timezone: "Europe/Paris",
  view: portableView(STORED, 4),
  entities: { "sensor.b": { state: "2" }, "sensor.a": { state: "1" } },
  templates: { "0": {} },
};

describe("copying a view", () => {
  it("leaves out the widgets the layout hides (an import would refuse them)", () => {
    const shrunk = { ...STORED, layout: "fullscreen", widgets: [...STORED.widgets, { type: "clock", slot: 1 }] };
    expect(portableView(shrunk, 1).widgets).toEqual(STORED.widgets);
  });

  it("leaves out what only this panel means", () => {
    expect(portableView(STORED, 4)).toEqual({
      name: "Desk",
      layout: "grid_2x2",
      theme: "standby",
      widgets: [{ type: "clock", slot: 0 }],
    });
  });

  it("imports back as the same view, alone or in an export", () => {
    expect(parseImport(viewJson(STORED, 4)).view).toEqual(portableView(STORED, 4));
    expect(parseImport(exportJson(EXPORT)).view).toEqual(portableView(STORED, 4));
  });
});

describe("an export", () => {
  it("lists the entities it sends", () => {
    expect(exportedEntities(EXPORT)).toEqual(["sensor.a", "sensor.b"]);
  });

  it("says whether rendered templates go along", () => {
    expect(hasTemplates(EXPORT)).toBe(false);
    expect(hasTemplates({ ...EXPORT, templates: { "1": { "{{ 1 }}": "1" } } })).toBe(true);
  });
});

describe("copyText", () => {
  it("writes to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    expect(await copyText("x", { writeText })).toBe(true);
    expect(writeText).toHaveBeenCalledWith("x");
  });

  it("reports a browser that won't (no secure context, or refused)", async () => {
    expect(await copyText("x", undefined)).toBe(false);
    expect(await copyText("x", { writeText: vi.fn().mockRejectedValue(new Error("no")) })).toBe(
      false
    );
  });
});
