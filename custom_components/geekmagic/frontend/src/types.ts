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

export interface DeviceConfig {
  entry_id: string;
  name: string;
  host: string;
  assigned_views: string[];
  current_view_index: number;
  brightness: number;
  refresh_interval: number;
  cycle_interval: number;
  online: boolean;
}

export interface WidgetTypeSchema {
  name: string;
  needs_entity: boolean;
  entity_domains?: string[];
  options: WidgetOption[];
}

export interface WidgetOption {
  key: string;
  type: "boolean" | "select" | "number" | "text";
  label: string;
  default?: unknown;
  options?: string[];
  min?: number;
  max?: number;
}

export interface LayoutTypeInfo {
  slots: number;
  name: string;
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
}

export interface EntitiesListResponse {
  entities: EntityInfo[];
  total: number;
  has_more: boolean;
}
