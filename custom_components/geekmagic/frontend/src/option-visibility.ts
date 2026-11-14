/**
 * Which options of a widget apply, given its other options.
 *
 * Schemas declare ``visible_when: {key: [allowed, ...]}``: every key must
 * match (AND), and each key matches any of its values (OR), compared
 * against the stored value or, when unset, that option's default. A hidden
 * option keeps its stored value; the editor never deletes it.
 */
import type { WidgetOption } from "./types";

export function isOptionVisible(
  option: WidgetOption,
  all: WidgetOption[],
  values: Record<string, unknown> | undefined
): boolean {
  const when = option.visible_when;
  if (!when) return true;
  return Object.entries(when).every(([key, allowed]) => {
    const source = all.find((o) => o.key === key);
    if (!source) return true; // unknown key: never hide on a typo
    const value = values?.[key] ?? source.default;
    return allowed.some((candidate) => candidate === value);
  });
}

export function visibleOptions(
  all: WidgetOption[],
  values: Record<string, unknown> | undefined
): WidgetOption[] {
  return all.filter((option) => isOptionVisible(option, all, values));
}
