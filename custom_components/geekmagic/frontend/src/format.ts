/** Display strings and small derived values for the panel. */
import type { GeekMagicConfig, ViewConfig } from "./types";
import { visibleCount } from "./view-ops";

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function slotCount(config: GeekMagicConfig | null, layout: string): number {
  return config?.layout_types[layout]?.slots ?? 4;
}

/** "Grid 2×2 · watchOS · 4 widgets" */
export function viewMeta(config: GeekMagicConfig | null, view: ViewConfig): string {
  const layout = config?.layout_types[view.layout]?.name ?? view.layout;
  const theme = config?.themes[view.theme] ?? view.theme;
  const count = visibleCount(view, slotCount(config, view.layout));
  return `${layout} · ${theme} · ${plural(count, "widget")}`;
}

/** Title of an array-editor row: what the user named it, or what it is. */
export function rowTitle(
  item: { label?: string; entity_id?: string },
  friendlyName: (entityId: string) => string | undefined,
  fallback: string
): string {
  if (item.label) return item.label;
  if (item.entity_id) return friendlyName(item.entity_id) ?? item.entity_id;
  return fallback;
}

/** Choices for the rotation interval, in seconds; keeps an odd current value. */
export function intervalChoices(current: number): { value: number; label: string }[] {
  const base = [5, 10, 15, 30, 60, 120, 300];
  const values = base.includes(current) || current <= 0 ? base : [...base, current].sort((a, b) => a - b);
  return values.map((value) => ({ value, label: formatSeconds(value) }));
}

export function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds} s`;
  if (seconds % 60 === 0) return `${seconds / 60} min`;
  return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

/**
 * URL of an image entity's current picture. The proxy URL stays the same
 * from frame to frame while the entity state (its last update) changes, so
 * the state busts the browser cache.
 */
export function imageEntityUrl(picture: string | undefined, state: string | undefined): string | null {
  if (!picture) return null;
  const sep = picture.includes("?") ? "&" : "?";
  return state ? `${picture}${sep}v=${encodeURIComponent(state)}` : picture;
}

/** A name not used by any view: "New view", "New view 2", ... */
export function suggestName(views: ViewConfig[], base = "New view"): string {
  const taken = new Set(views.map((v) => v.name));
  if (!taken.has(base)) return base;
  let n = 2;
  while (taken.has(`${base} ${n}`)) n += 1;
  return `${base} ${n}`;
}
