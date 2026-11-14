/**
 * TypeScript type definitions for GeekMagic panel.
 */

// Home Assistant types (subset of what we need)
export interface HomeAssistant {
  connection: Connection;
  states: Record<string, HassEntity>;
  user?: HassUser;
  language: string;
  locale: HassLocale;
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ): Promise<unknown>;
  hassUrl(path?: string): string;
}

export interface Connection {
  sendMessagePromise<T>(message: MessageBase): Promise<T>;
}

export interface MessageBase {
  type: string;
  [key: string]: unknown;
}

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed: string;
  last_updated: string;
}

export interface HassUser {
  id: string;
  name: string;
  is_admin: boolean;
}

export interface HassLocale {
  language: string;
  number_format: string;
}

// Panel info passed by HA
export interface PanelInfo {
  config: Record<string, unknown>;
  url_path: string;
  title: string;
  icon: string;
}

// Route info
export interface Route {
  path: string;
  prefix: string;
}

// GeekMagic specific types
export interface ViewConfig {
  id: string;
  name: string;
  layout: string;
  theme: string;
  widgets: WidgetConfig[];
  created_at?: string;
  updated_at?: string;
}

export interface WidgetConfig {
  type: string;
  slot: number;
  entity_id?: string;
  label?: string;
  color?: [number, number, number];
  options?: Record<string, unknown>;
}

/** Home Assistant's ConfigEntryState values. */
export type ConfigEntryState =
  | "loaded"
  | "setup_error"
  | "migration_error"
  | "setup_retry"
  | "not_loaded"
  | "failed_unload"
  | "setup_in_progress"
  | "unload_in_progress";

/**
 * One configured display. Every config entry is listed, loaded or not; for
 * one that isn't loaded, the fields only a running display knows are null
 * (and ``entities`` empty).
 */
export interface DeviceConfig {
  entry_id: string;
  name: string;
  host: string;
  assigned_views: string[];
  current_view_index: number | null;
  brightness: number | null;
  refresh_interval: number;
  cycle_interval: number;
  online: boolean;
  /** The config entry's state; anything but "loaded" has no live device. */
  state?: ConfigEntryState;
  /** Why the entry isn't loaded (e.g. "Could not connect to …"), if known. */
  reason?: string | null;
  /** Disabled by the user in Settings → Devices & services. */
  disabled?: boolean;
  /** "custom" (our views) or "builtin" (a firmware screen). */
  display_mode?: string | null;
  /** The assigned view on screen; null in a built-in mode. */
  current_view_id?: string | null;
  builtin_mode?: string | null;
  /** Entity ids of the device's controls, resolved from the registry. */
  entities?: DeviceEntities;
}

export interface DeviceEntities {
  display?: string;
  brightness?: string;
  cycle_interval?: string;
  view_cycling?: string;
  active?: string;
  status?: string;
  preview?: string;
}

export type WidgetCategory = "values" | "home" | "time" | "history" | "pictures" | "custom";

export interface WidgetTypeSchema {
  name: string;
  icon?: string;
  category?: WidgetCategory;
  description?: string;
  /** False when the widget ignores the slot label. */
  uses_label?: boolean;
  needs_entity: boolean;
  entity_domains?: string[];
  options: WidgetOption[];
}

export interface WidgetOption {
  key: string;
  type:
    | "boolean"
    | "select"
    | "number"
    | "text"
    | "textarea"
    | "icon"
    | "color"
    | "entity"
    | "timezone"
    | "thresholds"
    | "progress_items"
    | "status_entities";
  label: string;
  default?: unknown;
  options?: string[];
  min?: number;
  max?: number;
  placeholder?: string;
  /** Shown only when every key's current value is one of its list. */
  visible_when?: Record<string, unknown[]>;
}

// Complex option types for array editors
export interface ProgressItem {
  entity_id: string;
  label?: string;
  target?: number;
  color?: [number, number, number];
  icon?: string;
  unit?: string;
}

export interface StatusEntity {
  entity_id: string;
  label?: string;
  icon?: string;
}

export interface ColorThreshold {
  value: number;
  color: [number, number, number];
}

export interface LayoutTypeInfo {
  slots: number;
  name: string;
  /** Slot rects as screen fractions [x, y, w, h]. */
  rects: [number, number, number, number][];
}

export interface GeekMagicConfig {
  widget_types: Record<string, WidgetTypeSchema>;
  layout_types: Record<string, LayoutTypeInfo>;
  themes: Record<string, string>;
}

export interface EntityInfo {
  entity_id: string;
  name: string;
  state: string;
  unit?: string;
  device_class?: string;
  area?: string;
  device?: string;
  domain: string;
  icon?: string;
}

// WebSocket response types
export interface ViewsListResponse {
  views: ViewConfig[];
}

export interface ViewResponse {
  view: ViewConfig;
  view_id?: string;
}

export interface DevicesListResponse {
  devices: DeviceConfig[];
}

export interface PreviewResponse {
  image: string;
  content_type: string;
  width: number;
  height: number;
  /** Pixel rects [x1, y1, x2, y2] of each slot as drawn. */
  slots?: [number, number, number, number][];
}

export interface EntitiesListResponse {
  entities: EntityInfo[];
  total: number;
  has_more: boolean;
}
