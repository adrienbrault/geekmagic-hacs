import { describe, expect, it } from "vitest";
import type { DeviceConfig } from "./types";
import { anyWaiting, deviceStatus } from "./device-status";

const loaded: DeviceConfig = {
  entry_id: "a",
  name: "Desk",
  host: "10.0.0.5",
  assigned_views: ["v1"],
  current_view_index: 0,
  brightness: 50,
  refresh_interval: 10,
  cycle_interval: 0,
  online: true,
  state: "loaded",
  reason: null,
  disabled: false,
  display_mode: "custom",
  current_view_id: "v1",
  builtin_mode: null,
  entities: { brightness: "number.desk_brightness" },
};

// As devices/list returns an entry Home Assistant couldn't set up.
const retrying: DeviceConfig = {
  ...loaded,
  entry_id: "b",
  host: "10.76.1.217",
  current_view_index: null,
  brightness: null,
  online: false,
  state: "setup_retry",
  reason: "Could not connect to GeekMagic device at 10.76.1.217: timed out",
  display_mode: null,
  current_view_id: null,
  entities: {},
};

describe("deviceStatus", () => {
  it("keeps a loaded display live, online or not", () => {
    expect(deviceStatus(loaded)).toEqual({ kind: "online", live: true, label: "Online" });
    expect(deviceStatus({ ...loaded, online: false })).toEqual({
      kind: "offline",
      live: true,
      label: "Offline",
    });
  });

  it("treats a backend without the state field as loaded", () => {
    const { state: _state, ...old } = loaded;
    expect(deviceStatus(old).live).toBe(true);
  });

  it("explains a display Home Assistant is retrying", () => {
    const status = deviceStatus(retrying);
    expect(status.live).toBe(false);
    expect(status.kind).toBe("retrying");
    expect(status.label).toBe("Not connected");
    expect(status.title).toContain("10.76.1.217");
    expect(status.hint).toMatch(/retrying on its own/);
    expect(status.hint).toMatch(/powered on/);
    expect(status.alert).toBe("warning");
  });

  it("says a disabled display is disabled, not unreachable", () => {
    const status = deviceStatus({ ...retrying, state: "not_loaded", reason: null, disabled: true });
    expect(status.kind).toBe("disabled");
    expect(status.live).toBe(false);
    expect(status.hint).toMatch(/Enable it/);
  });

  it("sends a failed setup to the logs", () => {
    for (const state of ["setup_error", "migration_error", "failed_unload", "not_loaded"] as const) {
      const status = deviceStatus({ ...retrying, state, reason: null });
      expect(status.kind, state).toBe("failed");
      expect(status.live, state).toBe(false);
    }
  });

  it("shows a display being set up as connecting", () => {
    expect(deviceStatus({ ...retrying, state: "setup_in_progress" }).kind).toBe("starting");
  });
});

describe("anyWaiting", () => {
  it("is true while any display isn't loaded", () => {
    expect(anyWaiting([])).toBe(false);
    expect(anyWaiting([loaded, { ...loaded, online: false }])).toBe(false);
    expect(anyWaiting([loaded, retrying])).toBe(true);
    expect(anyWaiting([loaded, { ...retrying, state: "setup_in_progress" }])).toBe(true);
  });

  it("doesn't poll for a display that only the user can bring back", () => {
    expect(anyWaiting([{ ...retrying, state: "not_loaded", reason: null, disabled: true }])).toBe(false);
    expect(anyWaiting([{ ...retrying, state: "setup_error", reason: null }])).toBe(false);
  });
});
