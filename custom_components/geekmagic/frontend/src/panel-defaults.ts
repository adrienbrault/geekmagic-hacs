/**
 * Blank rows the panel inserts when the user clicks "Add" in an array
 * editor. They are saved as-is until filled in, so the backend must render
 * them; tests/fixtures/panel_option_shapes.json carries each one (checked
 * by panel-contract.test.ts) and tests/test_panel_contract.py renders it.
 */
import type { ColorThreshold, ProgressItem, StatusEntity } from "./types";

export const newThreshold = (): ColorThreshold => ({ value: 0, color: [255, 255, 0] });

export const newProgressItem = (): ProgressItem => ({ entity_id: "", target: 100 });

export const newStatusEntity = (): StatusEntity => ({ entity_id: "" });
