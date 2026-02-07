/**
 * GeekMagic Panel - Main entry point
 *
 * Custom panel for configuring GeekMagic displays.
 * Uses Home Assistant's Material Design components.
 */

import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  HomeAssistant,
  PanelInfo,
  Route,
  GeekMagicConfig,
  ViewConfig,
  DeviceConfig,
  WidgetConfig,
  WidgetOption,
  ProgressItem,
  StatusEntity,
  ColorThreshold,
} from "./types";
import { rgbToHex, parseColorInput, type RGBTuple } from "./color-utils";

// Type declaration for Intl.supportedValuesOf (ES2022+)
declare global {
  namespace Intl {
    function supportedValuesOf(key: string): string[];
  }
}

// Get all IANA timezones from the browser
const TIMEZONES: string[] = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    // Fallback for older browsers
    return [
      "UTC",
      "America/New_York",
      "America/Chicago",
      "America/Denver",
      "America/Los_Angeles",
      "Europe/London",
      "Europe/Paris",
      "Europe/Berlin",
      "Asia/Tokyo",
      "Asia/Shanghai",
      "Australia/Sydney",
    ];
  }
})();

// Debounce helper
function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

@customElement("geekmagic-panel")
export class GeekMagicPanel extends LitElement {
  // Props passed by Home Assistant
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) route!: Route;
  @property({ attribute: false }) panel!: PanelInfo;

  // Internal state
  @state() private _page: "main" | "editor" = "main";
  @state() private _config: GeekMagicConfig | null = null;
  @state() private _views: ViewConfig[] = [];
  @state() private _devices: DeviceConfig[] = [];
  @state() private _editingView: ViewConfig | null = null;
  @state() private _previewImage: string | null = null;
  @state() private _previewLoading = false;
  @state() private _loading = true;
  @state() private _saving = false;
  @state() private _expandedItems: Set<string> = new Set();
  @state() private _viewPreviews: Map<string, string> = new Map();

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      --mdc-theme-primary: var(--primary-color);
      --mdc-theme-on-primary: var(--text-primary-color);
    }

    /* Header */
    .header {
      display: flex;
      align-items: center;
      padding: 0 16px;
      height: 56px;
      border-bottom: 1px solid var(--divider-color);
      background: var(--app-header-background-color);
    }

    .header-title {
      font-size: 20px;
      font-weight: 400;
      margin-left: 8px;
    }

    .content {
      flex: 1;
      overflow: auto;
      padding: 16px;
      background: var(--primary-background-color);
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }

    /* Views Grid */
    .views-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }

    ha-card {
      --ha-card-border-radius: 12px;
    }

    .view-card {
      cursor: pointer;
    }

    .view-card:hover {
      --ha-card-background: var(--secondary-background-color);
    }

    .view-card-content {
      display: flex;
      align-items: center;
      padding: 16px;
      gap: 16px;
    }

    .view-card-preview {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      width: 80px;
      height: 80px;
      background: #000;
      border-radius: 8px;
    }

    .view-preview-image {
      width: 80px;
      height: 80px;
      border-radius: 8px;
      object-fit: contain;
    }

    .view-preview-placeholder {
      width: 80px;
      height: 80px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
    }

    .view-card-info {
      flex: 1;
      min-width: 0;
    }

    .view-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .view-card-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
    }

    .card-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
    }

    .card-content {
      padding: 0 16px 16px;
    }

    .card-meta {
      font-size: 14px;
      color: var(--secondary-text-color);
    }

    .add-card {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 120px;
      border: 2px dashed var(--divider-color);
      border-radius: 12px;
      cursor: pointer;
      color: var(--secondary-text-color);
      transition: all 0.2s;
    }

    .add-card:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    /* Sections */
    .section {
      margin-bottom: 32px;
    }

    .section-header {
      font-size: 18px;
      font-weight: 500;
      margin: 0 0 16px 0;
      color: var(--primary-text-color);
    }

    .empty-state-inline {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      color: var(--secondary-text-color);
      background: var(--card-background-color);
      border-radius: 12px;
    }

    /* Editor */
    .editor-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .editor-header ha-textfield {
      flex: 1;
    }

    .editor-form {
      width: 100%;
    }

    /* Preview section - above widgets */
    .preview-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 24px;
    }

    .preview-card {
      width: 100%;
      max-width: 300px;
    }

    .preview-card .card-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }

    .preview-image {
      width: 200px;
      height: 200px;
      border-radius: 8px;
      background: #000;
      object-fit: contain;
    }

    .preview-placeholder {
      width: 200px;
      height: 200px;
      border-radius: 8px;
      background: var(--secondary-background-color);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
    }

    /* Form Layout */
    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-row > * {
      flex: 1;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 24px 0 16px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .section-title:first-child {
      margin-top: 0;
    }

    /* Slots list - fluid responsive grid */
    .slots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      width: 100%;
    }

    /* Single column on mobile */
    @media (max-width: 600px) {
      .slots-grid {
        grid-template-columns: 1fr;
      }
    }

    .slot-card {
      --ha-card-border-radius: 8px;
    }

    .slot-card .card-content {
      padding: 16px;
    }

    .slot-header {
      display: flex;
      align-items: center;
      font-weight: 500;
      margin-bottom: 16px;
      color: var(--primary-text-color);
    }

    /* Tiny position grid */
    .position-grid {
      display: inline-grid;
      gap: 2px;
      margin-right: 12px;
      padding: 4px;
      background: var(--secondary-background-color);
      border-radius: 4px;
    }

    .position-grid.cols-2 {
      grid-template-columns: repeat(2, 16px);
    }

    .position-grid.cols-3 {
      grid-template-columns: repeat(3, 16px);
    }

    .position-cell {
      width: 16px;
      height: 16px;
      background: var(--divider-color);
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .position-cell:hover {
      background: var(--primary-color);
      opacity: 0.7;
    }

    .position-cell.active {
      background: var(--primary-color);
    }

    .position-cell.hero-main {
      grid-column: 1 / -1;
      width: auto;
      height: 24px;
    }

    /* Layout Picker */
    .layout-section {
      margin-bottom: 16px;
    }

    .layout-section-label {
      font-size: 12px;
      font-weight: 500;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
      display: block;
    }

    .layout-picker {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .layout-option {
      width: 48px;
      height: 48px;
      padding: 6px;
      border: 2px solid var(--divider-color);
      border-radius: 8px;
      background: var(--card-background-color);
      cursor: pointer;
      transition: all 0.15s;
    }

    .layout-option:hover {
      border-color: var(--primary-color);
    }

    .layout-option.selected {
      border-color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.1);
    }

    .layout-icon {
      width: 100%;
      height: 100%;
      display: grid;
      gap: 2px;
    }

    .layout-icon > div {
      background: var(--primary-text-color);
      opacity: 0.3;
      border-radius: 1px;
    }

    .layout-option.selected .layout-icon > div {
      opacity: 0.6;
    }

    /* Layout icon patterns */
    .layout-icon.full { grid-template: 1fr / 1fr; }
    .layout-icon.g-2x2 { grid-template: 1fr 1fr / 1fr 1fr; }
    .layout-icon.g-2x3 { grid-template: 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.g-3x2 { grid-template: 1fr 1fr 1fr / 1fr 1fr; }
    .layout-icon.g-3x3 { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.s-h { grid-template: 1fr / 1fr 1fr; }
    .layout-icon.s-v { grid-template: 1fr 1fr / 1fr; }
    .layout-icon.s-h-12 { grid-template: 1fr / 1fr 2fr; }
    .layout-icon.s-h-21 { grid-template: 1fr / 2fr 1fr; }
    .layout-icon.t-col { grid-template: 1fr / 1fr 1fr 1fr; }
    .layout-icon.t-row { grid-template: 1fr 1fr 1fr / 1fr; }
    .layout-icon.hero { grid-template: 2fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hero > div:first-child { grid-column: 1 / -1; }
    .layout-icon.hero-simple { grid-template: 2fr 1fr / 1fr; }

    /* Sidebar layouts */
    .layout-icon.sb-l { grid-template: 1fr 1fr 1fr / 2fr 1fr; }
    .layout-icon.sb-l > div:first-child { grid-row: 1 / -1; }

    .layout-icon.sb-r { grid-template: 1fr 1fr 1fr / 1fr 2fr; }
    .layout-icon.sb-r > div:nth-child(4) { grid-row: 1 / -1; }

    /* Corner hero layouts - use 3x3 grid with 2x2 hero spanning */
    .layout-icon.hc-tl { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-tl > div:first-child { grid-row: 1 / 3; grid-column: 1 / 3; }

    .layout-icon.hc-tr { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-tr > div:nth-child(2) { grid-row: 1 / 3; grid-column: 2 / 4; }

    .layout-icon.hc-bl { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-bl > div:nth-child(5) { grid-row: 2 / 4; grid-column: 1 / 3; }

    .layout-icon.hc-br { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-br > div:nth-child(5) { grid-row: 2 / 4; grid-column: 2 / 4; }

    .slot-field {
      margin-bottom: 16px;
    }

    .slot-field:last-child {
      margin-bottom: 0;
    }

    ha-select,
    ha-textfield {
      display: block;
      width: 100%;
    }

    ha-entity-picker {
      display: block;
      width: 100%;
    }

    /* Widget options */
    .widget-options {
      border-top: 1px solid var(--divider-color);
      padding-top: 16px;
      margin-top: 16px;
    }

    .option-field {
      margin-bottom: 12px;
    }

    .option-field:last-child {
      margin-bottom: 0;
    }

    .option-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
    }

    .option-row label {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    /* Array editors */
    .array-editor {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 12px;
      margin-top: 8px;
    }

    .array-editor-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .array-editor-header span {
      font-size: 14px;
      font-weight: 500;
    }

    .array-items {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .array-item {
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      overflow: hidden;
    }

    .array-item-header {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      background: var(--secondary-background-color);
      cursor: pointer;
    }

    .array-item-header:hover {
      background: var(--divider-color);
    }

    .array-item-title {
      flex: 1;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .array-item-actions {
      display: flex;
      gap: 4px;
    }

    .array-item-content {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .array-item-content.collapsed {
      display: none;
    }

    .add-item-button {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 8px;
      border: 1px dashed var(--divider-color);
      border-radius: 6px;
      cursor: pointer;
      color: var(--secondary-text-color);
      font-size: 14px;
      transition: all 0.2s;
    }

    .add-item-button:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    /* Color thresholds editor */
    .threshold-item-container {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
    }

    .threshold-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .threshold-value {
      width: 80px;
    }

    .threshold-color {
      width: 60px;
      height: 32px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }

    .threshold-hex-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: 88px; /* Align with color picker (80px value + 8px gap) */
    }

    .threshold-hex-input {
      flex: 1;
    }

    /* Color hex input fallback (Safari compatibility) */
    .color-hex-input {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }

    .color-hex-input ha-textfield {
      flex: 1;
    }

    .color-preview-swatch {
      width: 32px;
      height: 32px;
      border-radius: 4px;
      border: 1px solid var(--divider-color);
      flex-shrink: 0;
    }

    /* Devices */
    .devices-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-width: 800px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .device-name {
      font-size: 16px;
      font-weight: 500;
    }

    .device-status {
      font-size: 12px;
      padding: 4px 12px;
      border-radius: 12px;
      font-weight: 500;
    }

    .device-status.online {
      background: var(--success-color, #4caf50);
      color: white;
    }

    .device-status.offline {
      background: var(--error-color, #f44336);
      color: white;
    }

    .device-status a {
      color: inherit;
      text-decoration: none;
    }

    .views-checkboxes {
      margin-top: 16px;
    }

    .view-checkbox {
      display: flex;
      align-items: center;
      padding: 8px 0;
    }

    .view-checkbox ha-checkbox {
      margin-right: 8px;
    }

    /* Empty states */
    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--secondary-text-color);
    }

    .empty-state ha-icon {
      --mdc-icon-size: 48px;
      margin-bottom: 16px;
      opacity: 0.5;
    }
  `;

  protected firstUpdated(): void {
    this._loadData();
  }

  private async _loadData(): Promise<void> {
    this._loading = true;
    try {
      const [configResult, viewsResult, devicesResult] = await Promise.all([
        this.hass.connection.sendMessagePromise<GeekMagicConfig>({
          type: "geekmagic/config",
        }),
        this.hass.connection.sendMessagePromise<{ views: ViewConfig[] }>({
          type: "geekmagic/views/list",
        }),
        this.hass.connection.sendMessagePromise<{ devices: DeviceConfig[] }>({
          type: "geekmagic/devices/list",
        }),
      ]);
      this._config = configResult;
      this._views = viewsResult.views;
      this._devices = devicesResult.devices;

      // Load previews for all views
      this._loadViewPreviews();
    } catch (err) {
      console.error("Failed to load GeekMagic config:", err);
    } finally {
      this._loading = false;
    }
  }

  private async _loadViewPreviews(): Promise<void> {
    // Load previews in parallel for all views
    const previewPromises = this._views.map(async (view) => {
      try {
        const result = await this.hass.connection.sendMessagePromise<{
          image: string;
        }>({
          type: "geekmagic/preview/render",
          view_config: {
            layout: view.layout,
            theme: view.theme,
            widgets: view.widgets,
          },
        });
        return { id: view.id, image: result.image };
      } catch (err) {
        console.error(`Failed to load preview for view ${view.id}:`, err);
        return { id: view.id, image: null };
      }
    });

    const results = await Promise.all(previewPromises);
    const newPreviews = new Map<string, string>();
    for (const result of results) {
      if (result.image) {
        newPreviews.set(result.id, result.image);
      }
    }
    this._viewPreviews = newPreviews;
  }

  private async _createView(): Promise<void> {
    const name = prompt("Enter view name:", "New View");
    if (!name) return;

    try {
      const result = await this.hass.connection.sendMessagePromise<{
        view_id: string;
        view: ViewConfig;
      }>({
        type: "geekmagic/views/create",
        name,
        layout: "grid_2x2",
        theme: "classic",
        widgets: [],
      });
      this._views = [...this._views, result.view];
      this._editView(result.view);
    } catch (err) {
      console.error("Failed to create view:", err);
    }
  }

  private _editView(view: ViewConfig): void {
    this._editingView = { ...view, widgets: [...view.widgets] };
    this._page = "editor";
    this._refreshPreview();
  }

  private async _saveView(): Promise<void> {
    if (!this._editingView) return;

    this._saving = true;
    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/views/update",
        view_id: this._editingView.id,
        name: this._editingView.name,
        layout: this._editingView.layout,
        theme: this._editingView.theme,
        widgets: this._editingView.widgets,
      });
      this._views = this._views.map((v) =>
        v.id === this._editingView!.id ? this._editingView! : v
      );
      this._page = "main";
      this._editingView = null;
      // Refresh previews after save to show updated view
      this._loadViewPreviews();
    } catch (err) {
      console.error("Failed to save view:", err);
    } finally {
      this._saving = false;
    }
  }

  private async _deleteView(view: ViewConfig): Promise<void> {
    if (!confirm(`Delete view "${view.name}"?`)) return;

    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/views/delete",
        view_id: view.id,
      });
      this._views = this._views.filter((v) => v.id !== view.id);
    } catch (err) {
      console.error("Failed to delete view:", err);
    }
  }

  private _refreshPreview = debounce(async () => {
    if (!this._editingView) return;

    this._previewLoading = true;
    try {
      const result = await this.hass.connection.sendMessagePromise<{
        image: string;
      }>({
        type: "geekmagic/preview/render",
        view_config: {
          layout: this._editingView.layout,
          theme: this._editingView.theme,
          widgets: this._editingView.widgets,
        },
      });
      this._previewImage = result.image;
    } catch (err) {
      console.error("Failed to render preview:", err);
    } finally {
      this._previewLoading = false;
    }
  }, 500);

  private _updateEditingView(updates: Partial<ViewConfig>): void {
    if (!this._editingView) return;
    this._editingView = { ...this._editingView, ...updates };
    this._refreshPreview();
  }

  private _updateWidget(slot: number, updates: Partial<WidgetConfig>): void {
    if (!this._editingView) return;

    // Auto-populate timezone when switching to clock widget
    if (updates.type === "clock") {
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      updates = {
        ...updates,
        options: { ...updates.options, timezone: browserTz },
      };
    }

    const widgets = [...this._editingView.widgets];
    const existingIndex = widgets.findIndex((w) => w.slot === slot);

    if (existingIndex >= 0) {
      widgets[existingIndex] = { ...widgets[existingIndex], ...updates };
    } else {
      widgets.push({ slot, type: "", ...updates });
    }

    // Create new object to ensure Lit detects the change
    this._editingView = { ...this._editingView, widgets: [...widgets] };
    this.requestUpdate();
    this._refreshPreview();
  }

  private async _toggleDeviceView(
    device: DeviceConfig,
    viewId: string,
    enabled: boolean
  ): Promise<void> {
    const newViews = enabled
      ? [...device.assigned_views, viewId]
      : device.assigned_views.filter((v) => v !== viewId);

    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: device.entry_id,
        view_ids: newViews,
      });
      this._devices = this._devices.map((d) =>
        d.entry_id === device.entry_id ? { ...d, assigned_views: newViews } : d
      );
    } catch (err) {
      console.error("Failed to update device views:", err);
    }
  }

  render() {
    if (this._loading) {
      return html`
        <div class="loading">
          <ha-circular-progress indeterminate></ha-circular-progress>
        </div>
      `;
    }

    return html`
      <div class="header">
        <ha-menu-button
          .hass=${this.hass}
          .narrow=${this.narrow}
        ></ha-menu-button>
        <ha-icon icon="mdi:monitor-dashboard"></ha-icon>
        <span class="header-title">GeekMagic</span>
      </div>
      <div class="content">${this._renderPage()}</div>
    `;
  }

  private _renderPage() {
    switch (this._page) {
      case "main":
        return this._renderMain();
      case "editor":
        return this._renderEditor();
    }
  }

  private _renderMain() {
    return html`
      <!-- Devices Section -->
      <div class="section">
        <h2 class="section-header">Devices</h2>
        ${this._devices.length === 0
          ? html`
              <div class="empty-state-inline">
                <ha-icon icon="mdi:monitor-off"></ha-icon>
                <span>No devices configured. Add a device through Settings → Devices & Services.</span>
              </div>
            `
          : html`
              <div class="devices-list">
                ${this._devices.map(
                  (device) => html`
                    <ha-card>
                      <div class="card-content" style="padding-top: 16px;">
                        <div class="device-header">
                          <span class="device-name">${device.name}</span>
                          <span class="device-status ${device.online ? "online" : "offline"}">
                            <a href="http://${device.host}" target="_blank" rel="noopener noreferrer">${device.online ? "Online" : "Offline"}</a>
                          </span>
                        </div>
                        <div class="views-checkboxes">
                          ${this._views.length === 0
                            ? html`<p style="color: var(--secondary-text-color); margin: 8px 0 0;">
                                No views available. Create a view below.
                              </p>`
                            : this._views.map(
                                (view) => html`
                                  <label class="view-checkbox">
                                    <ha-checkbox
                                      .checked=${device.assigned_views.includes(view.id)}
                                      @change=${(e: Event) =>
                                        this._toggleDeviceView(
                                          device,
                                          view.id,
                                          (e.target as HTMLInputElement).checked
                                        )}
                                    ></ha-checkbox>
                                    ${view.name}
                                  </label>
                                `
                              )}
                        </div>
                      </div>
                    </ha-card>
                  `
                )}
              </div>
            `}
      </div>

      <!-- Views Section -->
      <div class="section">
        <h2 class="section-header">Views</h2>
        <div class="views-grid">
          ${this._views.map(
            (view) => html`
              <ha-card class="view-card" @click=${() => this._editView(view)}>
                <div class="view-card-content">
                  <div class="view-card-preview">
                    ${this._viewPreviews.has(view.id)
                      ? html`<img
                          class="view-preview-image"
                          src="data:image/png;base64,${this._viewPreviews.get(view.id)}"
                          alt="${view.name}"
                        />`
                      : html`<div class="view-preview-placeholder">
                          <ha-circular-progress indeterminate size="small"></ha-circular-progress>
                        </div>`}
                  </div>
                  <div class="view-card-info">
                    <div class="view-card-header">
                      <h3>${view.name}</h3>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          this._deleteView(view);
                        }}
                      ></ha-icon-button>
                    </div>
                    <div class="card-meta">
                      ${this._config?.layout_types[view.layout]?.name || view.layout}
                      &bull; ${this._config?.themes[view.theme] || view.theme}
                      &bull; ${view.widgets.length} widgets
                    </div>
                  </div>
                </div>
              </ha-card>
            `
          )}
          <div class="add-card" @click=${this._createView}>
            <ha-icon icon="mdi:plus"></ha-icon>
            <span style="margin-left: 8px">Add View</span>
          </div>
        </div>
      </div>
    `;
  }

  private _renderEditor() {
    if (!this._editingView || !this._config) return nothing;

    const slotCount =
      this._config.layout_types[this._editingView.layout]?.slots || 4;

    return html`
      <div class="editor-header">
        <ha-icon-button
          .path=${"M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"}
          @click=${() => (this._page = "main")}
        ></ha-icon-button>
        <ha-textfield
          .value=${this._editingView.name}
          @input=${(e: Event) =>
            this._updateEditingView({
              name: (e.target as HTMLInputElement).value,
            })}
          placeholder="View name"
        ></ha-textfield>
        <ha-button raised ?disabled=${this._saving} @click=${this._saveView}>
          ${this._saving ? "Saving..." : "Save"}
        </ha-button>
      </div>

      <div class="editor-form">
        <!-- Preview at top -->
        <div class="preview-section">
          <ha-card class="preview-card">
            <div class="card-header">
              <h3>Preview</h3>
              <ha-icon-button
                .path=${"M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"}
                @click=${() => this._refreshPreview()}
              ></ha-icon-button>
            </div>
            <div class="card-content">
              ${this._previewLoading
                ? html`<div class="preview-placeholder">
                    <ha-circular-progress indeterminate></ha-circular-progress>
                  </div>`
                : this._previewImage
                  ? html`<img
                      class="preview-image"
                      src="data:image/png;base64,${this._previewImage}"
                      alt="Preview"
                    />`
                  : html`<div class="preview-placeholder">No preview</div>`}
            </div>
          </ha-card>
        </div>

        <!-- Layout picker -->
        <div class="layout-section">
          <span class="layout-section-label">Layout</span>
          <div class="layout-picker">
            ${Object.entries(this._config.layout_types).map(
              ([key, info]) => html`
                <button
                  class="layout-option ${this._editingView?.layout === key
                    ? "selected"
                    : ""}"
                  @click=${() => this._updateEditingView({ layout: key })}
                  title="${info.name} (${info.slots} slots)"
                >
                  ${this._renderLayoutIcon(key)}
                </button>
              `
            )}
          </div>
        </div>

        <!-- Theme selector -->
        <div class="form-row">
          <ha-select
            label="Theme"
            .value=${this._editingView.theme}
            @selected=${(e: CustomEvent) => {
              const index = e.detail.index as number;
              const keys = Object.keys(this._config!.themes);
              const value = keys[index];
              if (value) this._updateEditingView({ theme: value });
            }}
            @closed=${(e: Event) => e.stopPropagation()}
          >
            ${Object.entries(this._config.themes).map(
              ([key, name]) => html`
                <mwc-list-item value=${key}>${name}</mwc-list-item>
              `
            )}
          </ha-select>
        </div>

        <!-- Widget slots -->
        <div class="section-title">Widgets</div>
        <div class="slots-grid">
          ${Array.from({ length: slotCount }, (_, i) =>
            this._renderSlotEditor(i, slotCount)
          )}
        </div>
      </div>
    `;
  }

  private _renderSlotEditor(slot: number, slotCount: number) {
    if (!this._config || !this._editingView) return nothing;

    const widget = this._editingView.widgets.find((w) => w.slot === slot);
    const widgetType = widget?.type || "";
    const schema = this._config.widget_types[widgetType];
    const layout = this._editingView.layout;

    return html`
      <ha-card class="slot-card">
        <div class="card-content">
          <div class="slot-header">
            ${this._renderPositionGrid(slot, slotCount, layout)}
            <span style="flex: 1;">Slot ${slot + 1}</span>
          </div>

          <div class="slot-field">
            <ha-select
              label="Widget Type"
              .value=${widgetType}
              @selected=${(e: CustomEvent) => {
                const index = e.detail.index as number;
                const keys = ["", ...Object.keys(this._config!.widget_types)];
                const value = keys[index] || "";
                this._updateWidget(slot, { type: value });
              }}
              @closed=${(e: Event) => e.stopPropagation()}
            >
              <mwc-list-item value="">-- Empty --</mwc-list-item>
              ${Object.entries(this._config.widget_types).map(
                ([key, info]) => html`
                  <mwc-list-item value=${key}>${info.name}</mwc-list-item>
                `
              )}
            </ha-select>
          </div>

          ${schema?.needs_entity
            ? html`
                <div class="slot-field">
                  <ha-selector
                    .hass=${this.hass}
                    .selector=${{
                      entity: schema.entity_domains
                        ? { domain: schema.entity_domains }
                        : {},
                    }}
                    .value=${widget?.entity_id || ""}
                    .label=${"Entity"}
                    @value-changed=${(e: CustomEvent) =>
                      this._updateWidget(slot, {
                        entity_id: e.detail.value,
                      })}
                  ></ha-selector>
                </div>
              `
            : nothing}

          <div class="slot-field">
            <ha-textfield
              label="Label (optional)"
              .value=${widget?.label || ""}
              @input=${(e: Event) =>
                this._updateWidget(slot, {
                  label: (e.target as HTMLInputElement).value,
                })}
            ></ha-textfield>
          </div>

          ${schema?.options?.length
            ? html`
                <div class="widget-options">
                  ${schema.options.map((opt) =>
                    this._renderOptionField(slot, widget, opt)
                  )}
                </div>
              `
            : nothing}
        </div>
      </ha-card>
    `;
  }

  private _renderOptionField(
    slot: number,
    widget: WidgetConfig | undefined,
    opt: WidgetOption
  ) {
    const value = widget?.options?.[opt.key] ?? opt.default;

    switch (opt.type) {
      case "boolean":
        return html`
          <div class="option-row">
            <label>${opt.label}</label>
            <ha-switch
              .checked=${!!value}
              @change=${(e: Event) =>
                this._updateWidgetOption(
                  slot,
                  opt.key,
                  (e.target as HTMLInputElement).checked
                )}
            ></ha-switch>
          </div>
        `;

      case "select":
        return html`
          <div class="option-field">
            <ha-select
              .label=${opt.label}
              .value=${value || opt.default || ""}
              @selected=${(e: CustomEvent) => {
                const index = e.detail.index as number;
                const selected = opt.options?.[index];
                if (selected !== undefined) {
                  this._updateWidgetOption(slot, opt.key, selected);
                }
              }}
              @closed=${(e: Event) => e.stopPropagation()}
            >
              ${opt.options?.map(
                (o) => html`<mwc-list-item value=${o}>${o}</mwc-list-item>`
              )}
            </ha-select>
          </div>
        `;

      case "number":
        return html`
          <div class="option-field">
            <ha-textfield
              type="number"
              .label=${opt.label}
              .value=${value !== undefined ? String(value) : ""}
              .min=${opt.min !== undefined ? String(opt.min) : ""}
              .max=${opt.max !== undefined ? String(opt.max) : ""}
              @input=${(e: Event) => {
                const val = (e.target as HTMLInputElement).value;
                this._updateWidgetOption(
                  slot,
                  opt.key,
                  val ? parseFloat(val) : undefined
                );
              }}
            ></ha-textfield>
          </div>
        `;

      case "text":
        return html`
          <div class="option-field">
            <ha-textfield
              .label=${opt.label}
              .value=${value || ""}
              .placeholder=${opt.placeholder || ""}
              @input=${(e: Event) =>
                this._updateWidgetOption(
                  slot,
                  opt.key,
                  (e.target as HTMLInputElement).value
                )}
            ></ha-textfield>
          </div>
        `;

      case "icon":
        return html`
          <div class="option-field">
            <ha-icon-picker
              .hass=${this.hass}
              .label=${opt.label}
              .value=${value || ""}
              @value-changed=${(e: CustomEvent) =>
                this._updateWidgetOption(slot, opt.key, e.detail.value)}
            ></ha-icon-picker>
          </div>
        `;

      case "color":
        return html`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ color_rgb: {} }}
              .value=${value}
              .label=${opt.label}
              @value-changed=${(e: CustomEvent) =>
                this._updateWidgetOption(slot, opt.key, e.detail.value)}
            ></ha-selector>
            <div class="color-hex-input">
              <div
                class="color-preview-swatch"
                style="background-color: ${rgbToHex(value as RGBTuple)}"
              ></div>
              <ha-textfield
                .value=${rgbToHex(value as RGBTuple)}
                .label=${"Hex (fallback)"}
                placeholder="#FF5500 or 255,85,0"
                @change=${(e: Event) => {
                  const parsed = parseColorInput(
                    (e.target as HTMLInputElement).value
                  );
                  if (parsed) {
                    this._updateWidgetOption(slot, opt.key, parsed);
                  }
                }}
              ></ha-textfield>
            </div>
          </div>
        `;

      case "entity":
        return html`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ entity: {} }}
              .value=${value || ""}
              .label=${opt.label}
              @value-changed=${(e: CustomEvent) =>
                this._updateWidgetOption(slot, opt.key, e.detail.value)}
            ></ha-selector>
          </div>
        `;

      case "thresholds":
        return this._renderThresholdsEditor(slot, opt.key, value as ColorThreshold[] | undefined);

      case "progress_items":
        return this._renderProgressItemsEditor(slot, opt.key, value as ProgressItem[] | undefined);

      case "status_entities":
        return this._renderStatusEntitiesEditor(slot, opt.key, value as StatusEntity[] | undefined);

      case "timezone":
        return html`
          <div class="option-field">
            <ha-combo-box
              .hass=${this.hass}
              .label=${opt.label}
              .value=${value || ""}
              .items=${TIMEZONES.map((tz) => ({ value: tz, label: tz }))}
              item-value-path="value"
              item-label-path="label"
              allow-custom-value
              @value-changed=${(e: CustomEvent) =>
                this._updateWidgetOption(slot, opt.key, e.detail.value)}
            ></ha-combo-box>
          </div>
        `;

      default:
        return nothing;
    }
  }

  private _updateWidgetOption(slot: number, key: string, value: unknown): void {
    if (!this._editingView) return;

    const widgets = [...this._editingView.widgets];
    const idx = widgets.findIndex((w) => w.slot === slot);

    if (idx >= 0) {
      const widget = widgets[idx];
      widgets[idx] = {
        ...widget,
        options: { ...(widget.options || {}), [key]: value },
      };
    } else {
      // Create new widget with this option
      widgets.push({
        slot,
        type: "",
        options: { [key]: value },
      });
    }

    this._editingView = { ...this._editingView, widgets: [...widgets] };
    this.requestUpdate();
    this._refreshPreview();
  }

  private _renderThresholdsEditor(
    slot: number,
    key: string,
    thresholds: ColorThreshold[] | undefined
  ) {
    const items = thresholds || [];

    return html`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Color Thresholds</span>
          </div>
          <div class="array-items">
            ${items.map(
              (item, idx) => html`
                <div class="threshold-item-container">
                  <div class="threshold-item">
                    <ha-textfield
                      class="threshold-value"
                      type="number"
                      label="Value"
                      .value=${String(item.value)}
                      @input=${(e: Event) => {
                        const newItems = [...items];
                        newItems[idx] = {
                          ...item,
                          value: parseFloat((e.target as HTMLInputElement).value) || 0,
                        };
                        this._updateWidgetOption(slot, key, newItems);
                      }}
                    ></ha-textfield>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${item.color}
                      @value-changed=${(e: CustomEvent) => {
                        const newItems = [...items];
                        newItems[idx] = { ...item, color: e.detail.value };
                        this._updateWidgetOption(slot, key, newItems);
                      }}
                    ></ha-selector>
                    <ha-icon-button
                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                      @click=${() => {
                        const newItems = items.filter((_, i) => i !== idx);
                        this._updateWidgetOption(slot, key, newItems);
                      }}
                    ></ha-icon-button>
                  </div>
                  <div class="threshold-hex-row">
                    <div
                      class="color-preview-swatch"
                      style="background-color: ${rgbToHex(item.color as RGBTuple)}"
                    ></div>
                    <ha-textfield
                      class="threshold-hex-input"
                      .value=${rgbToHex(item.color as RGBTuple)}
                      label="Hex (fallback)"
                      placeholder="#FF5500"
                      @change=${(e: Event) => {
                        const parsed = parseColorInput(
                          (e.target as HTMLInputElement).value
                        );
                        if (parsed) {
                          const newItems = [...items];
                          newItems[idx] = { ...item, color: parsed };
                          this._updateWidgetOption(slot, key, newItems);
                        }
                      }}
                    ></ha-textfield>
                  </div>
                </div>
              `
            )}
            <div
              class="add-item-button"
              @click=${() => {
                const newItems = [...items, { value: 0, color: [255, 255, 0] as [number, number, number] }];
                this._updateWidgetOption(slot, key, newItems);
              }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Threshold
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private _renderProgressItemsEditor(
    slot: number,
    key: string,
    items: ProgressItem[] | undefined
  ) {
    const progressItems = items || [];

    return html`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Progress Items (${progressItems.length})</span>
          </div>
          <div class="array-items">
            ${progressItems.map((item, idx) => {
              const itemKey = `${slot}-progress-${idx}`;
              const isExpanded = this._expandedItems.has(itemKey);

              return html`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(itemKey)}
                  >
                    <span class="array-item-title">
                      ${item.label || item.entity_id || `Item ${idx + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${idx > 0
                          ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z"
                          : ""}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          if (idx > 0) this._moveArrayItem(slot, key, progressItems, idx, -1);
                        }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${idx < progressItems.length - 1
                          ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"
                          : ""}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          if (idx < progressItems.length - 1)
                            this._moveArrayItem(slot, key, progressItems, idx, 1);
                        }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          const newItems = progressItems.filter((_, i) => i !== idx);
                          this._updateWidgetOption(slot, key, newItems);
                        }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${isExpanded ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${item.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(e: CustomEvent) =>
                        this._updateArrayItem(slot, key, progressItems, idx, {
                          entity_id: e.detail.value,
                        })}
                    ></ha-selector>
                    <ha-textfield
                      label="Label"
                      .value=${item.label || ""}
                      @input=${(e: Event) =>
                        this._updateArrayItem(slot, key, progressItems, idx, {
                          label: (e.target as HTMLInputElement).value,
                        })}
                    ></ha-textfield>
                    <ha-textfield
                      type="number"
                      label="Target"
                      .value=${item.target !== undefined ? String(item.target) : "100"}
                      @input=${(e: Event) =>
                        this._updateArrayItem(slot, key, progressItems, idx, {
                          target: parseFloat((e.target as HTMLInputElement).value) || 100,
                        })}
                    ></ha-textfield>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${item.icon || ""}
                      @value-changed=${(e: CustomEvent) =>
                        this._updateArrayItem(slot, key, progressItems, idx, {
                          icon: e.detail.value,
                        })}
                    ></ha-icon-picker>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${item.color}
                      .label=${"Color"}
                      @value-changed=${(e: CustomEvent) =>
                        this._updateArrayItem(slot, key, progressItems, idx, {
                          color: e.detail.value,
                        })}
                    ></ha-selector>
                  </div>
                </div>
              `;
            })}
            <div
              class="add-item-button"
              @click=${() => {
                const newItems = [...progressItems, { entity_id: "", target: 100 }];
                this._updateWidgetOption(slot, key, newItems);
                // Auto-expand the new item
                this._expandedItems.add(`${slot}-progress-${newItems.length - 1}`);
                this.requestUpdate();
              }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Progress Item
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private _renderStatusEntitiesEditor(
    slot: number,
    key: string,
    items: StatusEntity[] | undefined
  ) {
    const statusEntities = items || [];

    return html`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Status Entities (${statusEntities.length})</span>
          </div>
          <div class="array-items">
            ${statusEntities.map((item, idx) => {
              const itemKey = `${slot}-status-${idx}`;
              const isExpanded = this._expandedItems.has(itemKey);

              return html`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(itemKey)}
                  >
                    <span class="array-item-title">
                      ${item.label || item.entity_id || `Entity ${idx + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${idx > 0
                          ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z"
                          : ""}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          if (idx > 0) this._moveArrayItem(slot, key, statusEntities, idx, -1);
                        }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${idx < statusEntities.length - 1
                          ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"
                          : ""}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          if (idx < statusEntities.length - 1)
                            this._moveArrayItem(slot, key, statusEntities, idx, 1);
                        }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(e: Event) => {
                          e.stopPropagation();
                          const newItems = statusEntities.filter((_, i) => i !== idx);
                          this._updateWidgetOption(slot, key, newItems);
                        }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${isExpanded ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${item.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(e: CustomEvent) =>
                        this._updateArrayItem(slot, key, statusEntities, idx, {
                          entity_id: e.detail.value,
                        })}
                    ></ha-selector>
                    <ha-textfield
                      label="Label"
                      .value=${item.label || ""}
                      @input=${(e: Event) =>
                        this._updateArrayItem(slot, key, statusEntities, idx, {
                          label: (e.target as HTMLInputElement).value,
                        })}
                    ></ha-textfield>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${item.icon || ""}
                      @value-changed=${(e: CustomEvent) =>
                        this._updateArrayItem(slot, key, statusEntities, idx, {
                          icon: e.detail.value,
                        })}
                    ></ha-icon-picker>
                  </div>
                </div>
              `;
            })}
            <div
              class="add-item-button"
              @click=${() => {
                const newItems = [...statusEntities, { entity_id: "" }];
                this._updateWidgetOption(slot, key, newItems);
                // Auto-expand the new item
                this._expandedItems.add(`${slot}-status-${newItems.length - 1}`);
                this.requestUpdate();
              }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Status Entity
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private _toggleItemExpanded(key: string): void {
    if (this._expandedItems.has(key)) {
      this._expandedItems.delete(key);
    } else {
      this._expandedItems.add(key);
    }
    this._expandedItems = new Set(this._expandedItems);
  }

  private _updateArrayItem<T extends object>(
    slot: number,
    key: string,
    items: T[],
    idx: number,
    updates: Partial<T>
  ): void {
    const newItems = [...items];
    newItems[idx] = { ...newItems[idx], ...updates };
    this._updateWidgetOption(slot, key, newItems);
  }

  private _moveArrayItem<T>(
    slot: number,
    key: string,
    items: T[],
    idx: number,
    direction: -1 | 1
  ): void {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= items.length) return;

    const newItems = [...items];
    [newItems[idx], newItems[newIdx]] = [newItems[newIdx], newItems[idx]];
    this._updateWidgetOption(slot, key, newItems);
  }

  private _renderPositionGrid(
    currentSlot: number,
    slotCount: number,
    layout: string
  ) {
    // Determine grid dimensions based on layout
    let cols = 2;
    let rows = 2;
    let isHero = false;

    switch (layout) {
      case "fullscreen":
        cols = 1;
        rows = 1;
        break;
      case "grid_2x2":
        cols = 2;
        rows = 2;
        break;
      case "grid_2x3":
        cols = 3;
        rows = 2;
        break;
      case "grid_3x2":
        cols = 2;
        rows = 3;
        break;
      case "hero":
        cols = 3;
        rows = 2;
        isHero = true;
        break;
      case "split":
        cols = 2;
        rows = 1;
        break;
      case "three_column":
        cols = 3;
        rows = 1;
        break;
      default:
        cols = 2;
        rows = Math.ceil(slotCount / 2);
    }

    // Generate grid cells
    const cells = [];

    if (isHero) {
      // Hero layout: slot 0 is the big hero, slots 1-3 are footer
      cells.push(html`
        <div
          class="position-cell hero-main ${currentSlot === 0 ? "active" : ""}"
          @click=${() => this._swapSlots(currentSlot, 0)}
          title="Hero (main)"
        ></div>
      `);
      for (let i = 1; i <= 3; i++) {
        cells.push(html`
          <div
            class="position-cell ${currentSlot === i ? "active" : ""}"
            @click=${() => this._swapSlots(currentSlot, i)}
            title="Footer ${i}"
          ></div>
        `);
      }
    } else {
      for (let i = 0; i < slotCount; i++) {
        cells.push(html`
          <div
            class="position-cell ${currentSlot === i ? "active" : ""}"
            @click=${() => this._swapSlots(currentSlot, i)}
            title="Slot ${i + 1}"
          ></div>
        `);
      }
    }

    return html`
      <div class="position-grid cols-${cols}">${cells}</div>
    `;
  }

  private _renderLayoutIcon(key: string) {
    // Map layout key to CSS class and cell count
    const layoutConfig: Record<string, { cls: string; cells: number }> = {
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

    const config = layoutConfig[key] || { cls: "", cells: 4 };
    const cells = Array.from({ length: config.cells }, () => html`<div></div>`);

    return html`<div class="layout-icon ${config.cls}">${cells}</div>`;
  }

  private _swapSlots(fromSlot: number, toSlot: number): void {
    if (fromSlot === toSlot || !this._editingView) return;

    const widgets = [...this._editingView.widgets];
    const fromWidget = widgets.find((w) => w.slot === fromSlot);
    const toWidget = widgets.find((w) => w.slot === toSlot);

    // Swap slot assignments
    if (fromWidget) fromWidget.slot = toSlot;
    if (toWidget) toWidget.slot = fromSlot;

    this._editingView = { ...this._editingView, widgets: [...widgets] };
    this.requestUpdate();
    this._refreshPreview();
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "geekmagic-panel": GeekMagicPanel;
  }
}
