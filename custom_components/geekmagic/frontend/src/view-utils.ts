/**
 * Pure utility functions extracted from the panel component for testability.
 *
 * These functions handle view/widget state transformations without
 * any Lit or DOM dependencies.
 */

import type { WidgetConfig, DeviceConfig } from "./types";

/** Layout configuration for the visual grid icon in the layout picker. */
export interface LayoutIconConfig {
  cls: string;
  cells: number;
}

/**
 * Hardcoded layout configurations for the frontend layout picker.
 *
 * IMPORTANT: This must stay in sync with LAYOUT_SLOT_COUNTS in const.py.
 * The contract test in tests/test_frontend_contract.py verifies this.
 */
export const LAYOUT_CONFIGS: Record<string, LayoutIconConfig> = {
  fullscreen: { cls: "full", cells: 1 },
  grid_2x2: { cls: "g-2x2", cells: 4 },
  grid_2x3: { cls: "g-2x3", cells: 6 },
  grid_3x2: { cls: "g-3x2", cells: 6 },
  grid_3x3: { cls: "g-3x3", cells: 9 },
  split_horizontal: { cls: "s-h", cells: 2 },
  split_vertical: { cls: "s-v", cells: 2 },
  split_h_1_2: { cls: "s-h-12", cells: 2 },
  split_h_2_1: { cls: "s-h-21", cells: 2 },
  three_column: { cls: "t-col", cells: 3 },
  three_row: { cls: "t-row", cells: 3 },
  hero: { cls: "hero", cells: 4 },
  hero_simple: { cls: "hero-simple", cells: 2 },
  sidebar_left: { cls: "sb-l", cells: 4 },
  sidebar_right: { cls: "sb-r", cells: 4 },
  hero_corner_tl: { cls: "hc-tl", cells: 6 },
  hero_corner_tr: { cls: "hc-tr", cells: 6 },
  hero_corner_bl: { cls: "hc-bl", cells: 6 },
  hero_corner_br: { cls: "hc-br", cells: 6 },
};

const DEFAULT_LAYOUT_CONFIG: LayoutIconConfig = { cls: "", cells: 4 };

/**
 * Get layout icon configuration for a given layout key.
 * Returns a default config if the key is unknown.
 */
export function getLayoutConfig(key: string): LayoutIconConfig {
  return LAYOUT_CONFIGS[key] || DEFAULT_LAYOUT_CONFIG;
}

/**
 * Update a widget in a widgets array, returning a new array.
 *
 * If a widget with the given slot exists, it's merged with the updates.
 * Otherwise a new widget entry is created for that slot.
 *
 * When switching to a "clock" widget type, the browser timezone is
 * auto-populated into options.timezone (if `getBrowserTimezone` is provided).
 */
export function updateWidget(
  widgets: WidgetConfig[],
  slot: number,
  updates: Partial<WidgetConfig>,
  getBrowserTimezone?: () => string,
): WidgetConfig[] {
  // Auto-populate timezone for clock widgets
  if (updates.type === "clock" && getBrowserTimezone) {
    updates = {
      ...updates,
      options: { ...updates.options, timezone: getBrowserTimezone() },
    };
  }

  const result = [...widgets];
  const existingIndex = result.findIndex((w) => w.slot === slot);

  if (existingIndex >= 0) {
    result[existingIndex] = { ...result[existingIndex], ...updates };
  } else {
    result.push({ slot, type: "", ...updates });
  }

  return result;
}

/**
 * Swap two widget slots, returning a new array.
 *
 * If fromSlot === toSlot, returns the original array unchanged.
 * Handles cases where one or both slots have no widget.
 */
export function swapSlots(
  widgets: WidgetConfig[],
  fromSlot: number,
  toSlot: number,
): WidgetConfig[] {
  if (fromSlot === toSlot) return widgets;

  const result = widgets.map((w) => ({ ...w }));
  const fromWidget = result.find((w) => w.slot === fromSlot);
  const toWidget = result.find((w) => w.slot === toSlot);

  if (fromWidget) fromWidget.slot = toSlot;
  if (toWidget) toWidget.slot = fromSlot;

  return result;
}

/**
 * Compute updated assigned_views list when toggling a view for a device.
 */
export function toggleDeviceView(
  device: DeviceConfig,
  viewId: string,
  enabled: boolean,
): string[] {
  if (enabled) {
    return [...device.assigned_views, viewId];
  }
  return device.assigned_views.filter((v) => v !== viewId);
}
