import type { PreviewWarning } from "./types";
import { plural } from "./format";

export interface WarningText {
  title: string;
  body: string;
}

const MAX_ITEMS = 4;

function list(items: string[], quote: (item: string) => string): string {
  const shown = items.slice(0, MAX_ITEMS).map(quote).join(", ");
  const more = items.length - MAX_ITEMS;
  return more > 0 ? `${shown} and ${more} more` : shown;
}

/** What the editor tells the user about one preview warning. */
export function warningText(warning: PreviewWarning, slotName: string): WarningText {
  if (warning.kind === "overflow") {
    return {
      title: `${slotName}: text runs off the screen`,
      body:
        `${list(warning.items, (t) => `"${t}"`)} ${warning.items.length === 1 ? "is" : "are"} ` +
        "wider than the cell. Use fit() to size it, or a smaller font.",
    };
  }
  return {
    title: `${slotName}: ${plural(warning.items.length, "unknown class", "unknown classes")}`,
    body:
      `${list(warning.items, (c) => c)} ${warning.items.length === 1 ? "has" : "have"} ` +
      "no styles: a typo, or a utility the display can't paint.",
  };
}
