/**
 * What a display card says about its connection, from devices/list.
 *
 * A display whose config entry isn't loaded (Home Assistant can't reach
 * it and is retrying, it's disabled, or its setup failed) is still
 * configured and keeps its rotation; it just has no live screen or
 * controls until it loads.
 */
import type { DeviceConfig } from "./types";

export type DeviceStatusKind = "online" | "offline" | "retrying" | "starting" | "disabled" | "failed";

export interface DeviceStatus {
  kind: DeviceStatusKind;
  /** Home Assistant runs the display: live screen, controls, "show now". */
  live: boolean;
  /** Short label next to the name. */
  label: string;
  /** For a display that isn't live: what happened and what to do. */
  title?: string;
  hint?: string;
  /** ha-alert type for that message. */
  alert?: "warning" | "info" | "error";
}

const SETTINGS = "Settings → Devices & services";

export function deviceStatus(device: DeviceConfig): DeviceStatus {
  // A backend without the field only lists loaded entries.
  const state = device.state ?? "loaded";
  if (state === "loaded") {
    return device.online
      ? { kind: "online", live: true, label: "Online" }
      : { kind: "offline", live: true, label: "Offline" };
  }
  if (device.disabled) {
    return {
      kind: "disabled",
      live: false,
      label: "Disabled",
      title: "This display is disabled",
      hint: `Enable it in ${SETTINGS} to show your views on it again.`,
      alert: "info",
    };
  }
  if (state === "setup_retry") {
    return {
      kind: "retrying",
      live: false,
      label: "Not connected",
      title: `Can't reach the display at ${device.host}`,
      hint:
        "Home Assistant keeps retrying on its own. Check that the display is powered on " +
        "and reachable on your network.",
      alert: "warning",
    };
  }
  if (state === "setup_in_progress" || state === "unload_in_progress") {
    return {
      kind: "starting",
      live: false,
      label: "Connecting",
      title: "Connecting to the display…",
      alert: "info",
    };
  }
  return {
    kind: "failed",
    live: false,
    label: "Not loaded",
    title: "Home Assistant couldn't set up this display",
    hint: `Check the Home Assistant logs, then reload it from ${SETTINGS}.`,
    alert: "error",
  };
}

/**
 * Whether any display may load on its own (Home Assistant is retrying or
 * setting it up), so the panel should re-check. A disabled display or a
 * failed setup only changes when the user acts, so it isn't polled.
 */
export function anyWaiting(devices: DeviceConfig[]): boolean {
  return devices.some((device) => {
    const kind = deviceStatus(device).kind;
    return kind === "retrying" || kind === "starting";
  });
}
