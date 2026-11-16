/**
 * Importing a view designed elsewhere (the offline renderer, an AI): the
 * pure half of the import dialog.
 *
 * The text is parsed here; checking, remapping entity ids and validating
 * is the backend's (``geekmagic/views/check``, built on ``view_io``), so
 * the panel and the offline renderer can't disagree about a view.
 */
import type { ViewConfig, WidgetConfig } from "./types";
import { suggestName } from "./format";

/** One entity id a view reads, and whether this Home Assistant has it. */
export interface CheckedEntity {
  id: string;
  exists: boolean;
  domain: string;
}

/** ``geekmagic/views/check``'s result. */
export interface ViewCheck {
  /** The view with the entity map applied. */
  view: Record<string, unknown>;
  errors: string[];
  warnings: string[];
  entities: CheckedEntity[];
}

export type ParsedImport =
  | { view: Record<string, unknown>; error?: undefined }
  | { view?: undefined; error: string };

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** The content of the first ``` fenced block, or the whole text (trimmed). */
export function stripFences(text: string): string {
  const fenced = /```[^\n`]*\n([\s\S]*?)```/.exec(text);
  return (fenced ? fenced[1] : text).trim();
}

/**
 * A pasted view: a bare view object (what the panel stores, and what the
 * offline renderer's ``--save-view`` writes), in or out of a code fence.
 * An object carrying the view under ``view`` (a panel export) is unwrapped.
 */
export function parseImport(text: string): ParsedImport {
  const json = stripFences(text);
  if (!json) return { error: "Paste a view's JSON." };
  let value: unknown;
  try {
    value = JSON.parse(json);
  } catch (err) {
    return { error: `This isn't valid JSON: ${err instanceof Error ? err.message : String(err)}` };
  }
  if (isObject(value) && !("layout" in value) && isObject(value.view)) value = value.view;
  if (!isObject(value)) return { error: "A view is a JSON object with a layout and widgets." };
  return { view: value };
}

/** The entities this Home Assistant doesn't have: one mapping row each. */
export function missingEntities(entities: CheckedEntity[]): CheckedEntity[] {
  return entities.filter((entity) => !entity.exists);
}

/** The picks that change something (an empty pick leaves the id as is). */
export function entityMap(picks: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(picks).filter(([from, to]) => to && to !== from)
  );
}

/** The name to save under: the view's own, else a fresh one, never taken. */
export function importName(view: Record<string, unknown>, views: ViewConfig[]): string {
  const own = typeof view.name === "string" ? view.name.trim() : "";
  return suggestName(views, own || "Imported view");
}

/**
 * What views/create or views/update gets: layout, theme and widgets only
 * (never the source's id or timestamps). The theme is always sent:
 * views/create would default a missing one to classic, while the preview
 * (and every device) shows a view without a theme in watchOS.
 */
export function importPayload(view: Record<string, unknown>): {
  layout: string;
  theme: string;
  widgets: WidgetConfig[];
} {
  return {
    layout: String(view.layout ?? ""),
    theme: typeof view.theme === "string" && view.theme ? view.theme : "watchos",
    widgets: Array.isArray(view.widgets) ? (view.widgets as WidgetConfig[]) : [],
  };
}
