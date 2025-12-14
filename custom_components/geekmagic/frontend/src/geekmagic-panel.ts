/**
 * GeekMagic Panel - Main entry point
 *
 * Custom panel for configuring GeekMagic displays.
 */

import { LitElement, html, css, nothing, PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  HomeAssistant,
  PanelInfo,
  Route,
  GeekMagicConfig,
  ViewConfig,
  DeviceConfig,
  WidgetConfig,
} from "./types";

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
  @state() private _page: "views" | "devices" | "editor" = "views";
  @state() private _config: GeekMagicConfig | null = null;
  @state() private _views: ViewConfig[] = [];
  @state() private _devices: DeviceConfig[] = [];
  @state() private _editingView: ViewConfig | null = null;
  @state() private _previewImage: string | null = null;
  @state() private _previewLoading = false;
  @state() private _loading = true;
  @state() private _saving = false;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      --mdc-theme-primary: var(--primary-color);
    }

    .header {
      display: flex;
      align-items: center;
      padding: 8px 16px;
      border-bottom: 1px solid var(--divider-color);
      background: var(--app-header-background-color);
    }

    .header-title {
      flex: 1;
      font-size: 20px;
      font-weight: 500;
      margin-left: 16px;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }

    .tab {
      padding: 8px 16px;
      border: none;
      background: none;
      cursor: pointer;
      border-radius: 4px;
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .tab:hover {
      background: var(--secondary-background-color);
    }

    .tab.active {
      background: var(--primary-color);
      color: var(--text-primary-color);
    }

    .content {
      flex: 1;
      overflow: auto;
      padding: 16px;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }

    /* Views List */
    .views-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .view-card {
      background: var(--card-background-color);
      border-radius: 8px;
      padding: 16px;
      cursor: pointer;
      border: 1px solid var(--divider-color);
      transition: box-shadow 0.2s;
    }

    .view-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .view-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .view-card-title {
      font-size: 16px;
      font-weight: 500;
    }

    .view-card-meta {
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .add-card {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100px;
      border: 2px dashed var(--divider-color);
      border-radius: 8px;
      cursor: pointer;
      color: var(--secondary-text-color);
    }

    .add-card:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    /* Editor Layout */
    .editor-container {
      display: flex;
      gap: 24px;
      height: 100%;
    }

    .editor-form {
      flex: 7;
      overflow-y: auto;
    }

    .editor-preview {
      flex: 3;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }

    .preview-image {
      width: 240px;
      height: 240px;
      border-radius: 8px;
      background: #000;
      object-fit: contain;
    }

    .preview-placeholder {
      width: 240px;
      height: 240px;
      border-radius: 8px;
      background: #1a1a1a;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #666;
    }

    /* Form Elements */
    .form-section {
      margin-bottom: 24px;
    }

    .form-section-title {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 8px;
      color: var(--secondary-text-color);
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-field {
      flex: 1;
    }

    .form-field label {
      display: block;
      font-size: 12px;
      margin-bottom: 4px;
      color: var(--secondary-text-color);
    }

    .form-field input,
    .form-field select {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font-size: 14px;
    }

    .form-field input:focus,
    .form-field select:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    /* Slots Grid */
    .slots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;
    }

    .slot-card {
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 16px;
    }

    .slot-header {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 12px;
      color: var(--primary-text-color);
    }

    /* Buttons */
    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.2s;
    }

    .btn-primary {
      background: var(--primary-color);
      color: var(--text-primary-color);
    }

    .btn-primary:hover {
      opacity: 0.9;
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: var(--secondary-background-color);
      color: var(--primary-text-color);
    }

    .btn-secondary:hover {
      background: var(--divider-color);
    }

    .btn-danger {
      background: var(--error-color, #db4437);
      color: white;
    }

    .editor-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .back-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      color: var(--primary-text-color);
    }

    /* Devices List */
    .devices-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .device-card {
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 16px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .device-name {
      font-size: 16px;
      font-weight: 500;
    }

    .device-status {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .device-status.online {
      background: #4caf50;
      color: white;
    }

    .device-status.offline {
      background: #f44336;
      color: white;
    }

    .view-checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
    }

    .view-checkbox input {
      width: 18px;
      height: 18px;
    }
  `;

  protected firstUpdated(): void {
    this._loadData();
  }

  private async _loadData(): Promise<void> {
    this._loading = true;
    try {
      // Load config and views in parallel
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
    } catch (err) {
      console.error("Failed to load GeekMagic config:", err);
    } finally {
      this._loading = false;
    }
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
      alert("Failed to create view");
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
      // Update local state
      this._views = this._views.map((v) =>
        v.id === this._editingView!.id ? this._editingView! : v
      );
      this._page = "views";
      this._editingView = null;
    } catch (err) {
      console.error("Failed to save view:", err);
      alert("Failed to save view");
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
      alert("Failed to delete view");
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

    const widgets = [...this._editingView.widgets];
    const existingIndex = widgets.findIndex((w) => w.slot === slot);

    if (existingIndex >= 0) {
      widgets[existingIndex] = { ...widgets[existingIndex], ...updates };
    } else {
      widgets.push({ slot, type: "clock", ...updates });
    }

    this._editingView = { ...this._editingView, widgets };
    this._refreshPreview();
  }

  private async _toggleDeviceView(
    device: DeviceConfig,
    viewId: string,
    enabled: boolean
  ): Promise<void> {
    let newViews: string[];
    if (enabled) {
      newViews = [...device.assigned_views, viewId];
    } else {
      newViews = device.assigned_views.filter((v) => v !== viewId);
    }

    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: device.entry_id,
        view_ids: newViews,
      });
      // Update local state
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
          <span>Loading...</span>
        </div>
      `;
    }

    return html`
      <div class="header">
        <span class="header-title">GeekMagic</span>
        ${this._page !== "editor"
          ? html`
              <div class="tabs">
                <button
                  class="tab ${this._page === "views" ? "active" : ""}"
                  @click=${() => (this._page = "views")}
                >
                  Views
                </button>
                <button
                  class="tab ${this._page === "devices" ? "active" : ""}"
                  @click=${() => (this._page = "devices")}
                >
                  Devices
                </button>
              </div>
            `
          : nothing}
      </div>
      <div class="content">${this._renderPage()}</div>
    `;
  }

  private _renderPage() {
    switch (this._page) {
      case "views":
        return this._renderViewsList();
      case "devices":
        return this._renderDevicesList();
      case "editor":
        return this._renderEditor();
    }
  }

  private _renderViewsList() {
    return html`
      <div class="views-grid">
        ${this._views.map(
          (view) => html`
            <div class="view-card" @click=${() => this._editView(view)}>
              <div class="view-card-header">
                <span class="view-card-title">${view.name}</span>
                <button
                  class="btn btn-danger"
                  @click=${(e: Event) => {
                    e.stopPropagation();
                    this._deleteView(view);
                  }}
                >
                  Delete
                </button>
              </div>
              <div class="view-card-meta">
                Layout: ${view.layout} | Theme: ${view.theme} | Widgets:
                ${view.widgets.length}
              </div>
            </div>
          `
        )}
        <div class="add-card" @click=${this._createView}>
          <span>+ Add View</span>
        </div>
      </div>
    `;
  }

  private _renderDevicesList() {
    if (this._devices.length === 0) {
      return html`<p>No GeekMagic devices configured.</p>`;
    }

    return html`
      <div class="devices-list">
        ${this._devices.map(
          (device) => html`
            <div class="device-card">
              <div class="device-header">
                <span class="device-name">${device.name}</span>
                <span
                  class="device-status ${device.online ? "online" : "offline"}"
                >
                  ${device.online ? "Online" : "Offline"}
                </span>
              </div>
              <div class="form-section-title">Assigned Views</div>
              ${this._views.map(
                (view) => html`
                  <label class="view-checkbox">
                    <input
                      type="checkbox"
                      ?checked=${device.assigned_views.includes(view.id)}
                      @change=${(e: Event) =>
                        this._toggleDeviceView(
                          device,
                          view.id,
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    ${view.name}
                  </label>
                `
              )}
              ${this._views.length === 0
                ? html`<p>No views available. Create a view first.</p>`
                : nothing}
            </div>
          `
        )}
      </div>
    `;
  }

  private _renderEditor() {
    if (!this._editingView || !this._config) return nothing;

    const slotCount =
      this._config.layout_types[this._editingView.layout]?.slots || 4;

    return html`
      <div class="editor-header">
        <button class="back-btn" @click=${() => (this._page = "views")}>
          ← Back
        </button>
        <div class="form-field" style="flex: 1;">
          <input
            type="text"
            .value=${this._editingView.name}
            @input=${(e: Event) =>
              this._updateEditingView({
                name: (e.target as HTMLInputElement).value,
              })}
            placeholder="View name"
          />
        </div>
        <button
          class="btn btn-primary"
          ?disabled=${this._saving}
          @click=${this._saveView}
        >
          ${this._saving ? "Saving..." : "Save"}
        </button>
      </div>

      <div class="editor-container">
        <div class="editor-form">
          <div class="form-section">
            <div class="form-row">
              <div class="form-field">
                <label>Layout</label>
                <select
                  .value=${this._editingView.layout}
                  @change=${(e: Event) =>
                    this._updateEditingView({
                      layout: (e.target as HTMLSelectElement).value,
                    })}
                >
                  ${Object.entries(this._config.layout_types).map(
                    ([key, info]) =>
                      html`<option value=${key}>
                        ${info.name} (${info.slots} slots)
                      </option>`
                  )}
                </select>
              </div>
              <div class="form-field">
                <label>Theme</label>
                <select
                  .value=${this._editingView.theme}
                  @change=${(e: Event) =>
                    this._updateEditingView({
                      theme: (e.target as HTMLSelectElement).value,
                    })}
                >
                  ${Object.entries(this._config.themes).map(
                    ([key, name]) =>
                      html`<option value=${key}>${name}</option>`
                  )}
                </select>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section-title">Widgets</div>
            <div class="slots-grid">
              ${Array.from({ length: slotCount }, (_, i) =>
                this._renderSlotEditor(i)
              )}
            </div>
          </div>
        </div>

        <div class="editor-preview">
          <h3>Preview</h3>
          ${this._previewLoading
            ? html`<div class="preview-placeholder">Loading...</div>`
            : this._previewImage
              ? html`<img
                  class="preview-image"
                  src="data:image/png;base64,${this._previewImage}"
                  alt="Preview"
                />`
              : html`<div class="preview-placeholder">No preview</div>`}
          <button
            class="btn btn-secondary"
            style="margin-top: 16px;"
            @click=${() => this._refreshPreview()}
          >
            Refresh
          </button>
        </div>
      </div>
    `;
  }

  private _renderSlotEditor(slot: number) {
    if (!this._config) return nothing;

    const widget = this._editingView?.widgets.find((w) => w.slot === slot);
    const widgetType = widget?.type || "";
    const schema = this._config.widget_types[widgetType];

    return html`
      <div class="slot-card">
        <div class="slot-header">Slot ${slot + 1}</div>
        <div class="form-field">
          <label>Widget Type</label>
          <select
            .value=${widgetType}
            @change=${(e: Event) =>
              this._updateWidget(slot, {
                type: (e.target as HTMLSelectElement).value,
              })}
          >
            <option value="">-- Empty --</option>
            ${Object.entries(this._config.widget_types).map(
              ([key, info]) => html`<option value=${key}>${info.name}</option>`
            )}
          </select>
        </div>

        ${schema?.needs_entity
          ? html`
              <div class="form-field">
                <label>Entity</label>
                <input
                  type="text"
                  .value=${widget?.entity_id || ""}
                  @input=${(e: Event) =>
                    this._updateWidget(slot, {
                      entity_id: (e.target as HTMLInputElement).value,
                    })}
                  placeholder="sensor.example"
                />
              </div>
            `
          : nothing}

        <div class="form-field">
          <label>Label (optional)</label>
          <input
            type="text"
            .value=${widget?.label || ""}
            @input=${(e: Event) =>
              this._updateWidget(slot, {
                label: (e.target as HTMLInputElement).value,
              })}
            placeholder="Custom label"
          />
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "geekmagic-panel": GeekMagicPanel;
  }
}
