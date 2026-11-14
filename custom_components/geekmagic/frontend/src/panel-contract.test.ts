/**
 * Contract with the backend: tests/fixtures/panel_option_shapes.json holds
 * one stored value per option type, in the shape this panel saves, and
 * tests/test_panel_contract.py renders every widget with those values.
 * This side keeps the fixture honest: it must match the panel's types, and
 * the blank rows the panel inserts on "Add" must be in it.
 */
import { describe, expect, it } from "vitest";
import shapes from "../../../../tests/fixtures/panel_option_shapes.json";
import type { RGBTuple } from "./color-utils";
import { newProgressItem, newStatusEntity, newThreshold } from "./panel-defaults";
import type { ColorThreshold, ProgressItem, StatusEntity, WidgetOption } from "./types";

type ScalarOptionType = "boolean" | "select" | "number" | "text" | "textarea";

/** What the panel stores for each structured option type. */
interface PanelOptionValues {
  color: RGBTuple;
  thresholds: ColorThreshold[];
  progress_items: ProgressItem[];
  status_entities: StatusEntity[];
  icon: string;
  timezone: string;
  entity: string;
}

// A new structured option type must get an entry above (and in the fixture).
type Structured = Exclude<WidgetOption["type"], ScalarOptionType>;
type SameKeys<A, B> = [A] extends [B] ? ([B] extends [A] ? true : false) : false;
const everyTypeCovered: SameKeys<Structured, keyof PanelOptionValues> = true;

// JSON imports type tuples as number[]; relax tuples, keep everything else.
type FromJson<T> = T extends readonly [number, number, number]
  ? number[]
  : T extends (infer U)[]
    ? FromJson<U>[]
    : T extends object
      ? { [K in keyof T]: FromJson<T[K]> }
      : T;

// Compile-time: `npm run typecheck` fails if the fixture drifts from the types.
const fixture: FromJson<PanelOptionValues> = shapes;

describe("panel option contract fixture", () => {
  it("covers every structured option type", () => {
    expect(everyTypeCovered).toBe(true);
  });

  it("stores colours as RGB triples", () => {
    const colours = [
      fixture.color,
      ...fixture.thresholds.map((t) => t.color),
      ...fixture.progress_items.flatMap((i) => (i.color ? [i.color] : [])),
    ];
    for (const rgb of colours) {
      expect(rgb).toHaveLength(3);
      for (const channel of rgb) {
        expect(Number.isInteger(channel) && channel >= 0 && channel <= 255).toBe(true);
      }
    }
  });

  it("includes the blank rows the panel saves before they are filled in", () => {
    expect(fixture.thresholds).toContainEqual(newThreshold());
    expect(fixture.progress_items).toContainEqual(newProgressItem());
    expect(fixture.status_entities).toContainEqual(newStatusEntity());
  });
});
