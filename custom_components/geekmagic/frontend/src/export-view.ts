/**
 * Copying a view out of the panel: as JSON, or for an AI with the entity
 * data it reads (``geekmagic/views/export``). Pure apart from the
 * clipboard, which is passed in.
 */
import type { ViewConfig } from "./types";

/** Where people learn to design views with an AI (the Claude plugin). */
export const AI_DESIGN_DOCS =
  "https://github.com/adrienbrault/geekmagic-hacs/blob/main/docs/ai-design.md";

/** What ``geekmagic/views/export`` with data returns: a states file and its view. */
export interface ViewExport {
  version: number;
  integration_version: string;
  now: string;
  timezone?: string;
  view: Record<string, unknown>;
  entities: Record<string, Record<string, unknown>>;
  templates: Record<string, Record<string, string>>;
}

/** A view as a file: what the import and the offline renderer read (no id, no timestamps). */
export function portableView(view: ViewConfig): Record<string, unknown> {
  const { name, layout, theme, widgets } = view;
  return { name, layout, theme, widgets };
}

export function viewJson(view: ViewConfig): string {
  return `${JSON.stringify(portableView(view), null, 2)}\n`;
}

export function exportJson(data: ViewExport): string {
  return `${JSON.stringify(data, null, 1)}\n`;
}

/** The entity ids whose data an export sends, sorted. */
export function exportedEntities(data: ViewExport): string[] {
  return Object.keys(data.entities).sort();
}

/** Whether any rendered template goes along (they can read other entities). */
export function hasTemplates(data: ViewExport): boolean {
  return Object.values(data.templates).some((rendered) => Object.keys(rendered).length > 0);
}

/**
 * Write ``text`` to the clipboard; false when the browser won't. Home
 * Assistant served over plain http (not localhost) isn't a secure context
 * and has no ``navigator.clipboard``; the caller then shows the text to
 * copy by hand.
 */
export async function copyText(
  text: string,
  clipboard: Pick<Clipboard, "writeText"> | undefined = globalThis.navigator?.clipboard
): Promise<boolean> {
  if (!clipboard?.writeText) return false;
  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
