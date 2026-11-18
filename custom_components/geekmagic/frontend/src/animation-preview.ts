/**
 * What the view editor says about playing an animated view.
 *
 * The preview plays an animation whenever asked; a display only does when
 * its Animations switch is on. Otherwise it shows the animation's first
 * frame, so the editor names the displays that would.
 */
import type { DeviceConfig, HomeAssistant, PreviewResponse, ViewConfig } from "./types";

/** Names of the displays showing ``viewId`` with their Animations switch off. */
export function animationsOffOn(
  devices: DeviceConfig[],
  viewId: string,
  states: HomeAssistant["states"]
): string[] {
  return devices
    .filter((device) => device.assigned_views.includes(viewId))
    .filter((device) => {
      const switchId = device.entities?.animations;
      return switchId !== undefined && states[switchId]?.state === "off";
    })
    .map((device) => device.name);
}

/** What the screen's animation toggle shows and says, given the animation's state. */
export interface PlayControl {
  /** False while rendering: the toggle only reports it (one request at a time). */
  enabled: boolean;
  icon: "play" | "stop" | "spinner";
  label: string;
  /** For screen readers: the state the screen shows without a hover. */
  status: string;
}

export function playControl(on: boolean, loading: boolean, animated: boolean): PlayControl {
  if (!on) return { enabled: true, icon: "play", label: "Play the animation", status: "" };
  if (loading) {
    return {
      enabled: false,
      icon: "spinner",
      label: "Rendering the animation",
      status: "Rendering the animation…",
    };
  }
  return {
    enabled: true,
    icon: "stop",
    label: "Stop the animation",
    status: animated ? "Playing the animation." : "",
  };
}

/** The render input of a draft: equal keys render the same frame. */
export const renderKey = (view: Pick<ViewConfig, "layout" | "theme" | "widgets">): string =>
  JSON.stringify([view.layout, view.theme, view.widgets]);

/**
 * Worth keeping: a GIF, or an over-budget answer (its still and warning are
 * as definitive). A frame that failed to render may work next time.
 */
export const cacheable = (result: PreviewResponse): boolean =>
  result.animated || result.too_large;

/**
 * The last few rendered animations, by render key, so toggling one back on
 * (or undoing an edit) shows it without another render. Entries expire:
 * live content in a GIF (a clock, a reading) goes stale.
 */
export class AnimationCache<T> {
  private entries = new Map<string, { value: T; at: number }>();

  constructor(
    private readonly max = 4,
    private readonly ttlMs = 120_000,
    private readonly now: () => number = Date.now
  ) {}

  get(key: string): T | undefined {
    const entry = this.entries.get(key);
    if (!entry) return undefined;
    if (this.now() - entry.at > this.ttlMs) {
      this.entries.delete(key);
      return undefined;
    }
    return entry.value;
  }

  set(key: string, value: T): void {
    this.entries.delete(key); // re-inserted as the newest
    this.entries.set(key, { value, at: this.now() });
    while (this.entries.size > this.max) {
      const oldest = this.entries.keys().next().value as string;
      this.entries.delete(oldest);
    }
  }

  clear(): void {
    this.entries.clear();
  }
}
