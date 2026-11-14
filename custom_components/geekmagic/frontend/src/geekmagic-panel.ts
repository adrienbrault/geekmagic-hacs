/**
 * GeekMagic panel: the displays (live screen, controls, rotation) and the
 * views gallery; the view editor opens over it.
 *
 * Owns the loaded config, views, devices and view thumbnails. Children get
 * them as properties and report changes by events.
 */
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  DeviceConfig,
  GeekMagicConfig,
  HassEntity,
  HomeAssistant,
  PanelInfo,
  Route,
  ViewConfig,
} from "./types";
import { GeekMagicApi, limited, pngUrl } from "./api";
import { errorMessage } from "./preview-queue";
import { plural, suggestName, viewMeta } from "./format";
import { mdi, shared } from "./styles";
import { everyMinute } from "./minute-timer";
import { anyWaiting } from "./device-status";
import "./components/gm-device-card";
import "./components/gm-dialog";
import "./components/gm-menu";
import "./components/gm-view-editor";
import type { GmViewEditor } from "./components/gm-view-editor";

const viewKey = (view: ViewConfig) => JSON.stringify([view.layout, view.theme, view.widgets]);

/**
 * How often to re-check devices/list while a display isn't loaded. A
 * loaded display's changes arrive through its entities; one that isn't has
 * none to watch, so this is how its card notices it came back.
 */
const WAITING_RECHECK_MS = 30_000;

@customElement("geekmagic-panel")
export class GeekMagicPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) route!: Route;
  @property({ attribute: false }) panel!: PanelInfo;

  @state() private _config: GeekMagicConfig | null = null;
  @state() private _views: ViewConfig[] = [];
  @state() private _devices: DeviceConfig[] = [];
  @state() private _loadError: string | null = null;
  @state() private _editing: ViewConfig | null = null;
  @state() private _thumbs = new Map<string, string>();
  @state() private _failedThumbs = new Set<string>();
  @state() private _createOpen = false;
  @state() private _newName = "";
  @state() private _creating = false;
  @state() private _createError: string | null = null;
  @state() private _deleting: ViewConfig | null = null;
  @state() private _width = 1200;

  private _api = new GeekMagicApi(() => this.hass);
  private _thumbKeys = new Map<string, string>();
  private _watched = new Map<string, HassEntity | undefined>();
  private _devicesTimer: ReturnType<typeof setTimeout> | undefined;
  private _stopMinute: (() => void) | undefined;
  private _recheck: ReturnType<typeof setInterval> | undefined;
  private _thumbsRefreshing = false;
  private _resize = new ResizeObserver((entries) => {
    this._width = entries[0]?.contentRect.width ?? this._width;
  });

  // ---- lifecycle -----------------------------------------------------------------

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("beforeunload", this._warnBeforeUnload);
    document.addEventListener("visibilitychange", this._onVisible);
    this._resize.observe(this);
    // Thumbnails show live data (clocks first of all): keep them current.
    this._stopMinute = everyMinute(() => this._refreshThumbs());
  }

  disconnectedCallback(): void {
    window.removeEventListener("beforeunload", this._warnBeforeUnload);
    document.removeEventListener("visibilitychange", this._onVisible);
    this._resize.disconnect();
    clearTimeout(this._devicesTimer);
    this._stopMinute?.();
    clearInterval(this._recheck);
    this._recheck = undefined;
    super.disconnectedCallback();
  }

  protected firstUpdated(): void {
    void this._load();
  }

  protected willUpdate(changed: PropertyValues): void {
    // "Now showing" lives in devices/list; refetch when a device's live
    // picture or display select changes (cycling updates the picture).
    if (changed.has("hass") && this.hass) {
      let moved = false;
      for (const device of this._devices) {
        for (const id of [device.entities?.preview, device.entities?.display]) {
          if (!id) continue;
          const now = this.hass.states[id];
          if (this._watched.has(id) && this._watched.get(id) !== now) moved = true;
          this._watched.set(id, now);
        }
      }
      if (moved) this._refreshDevices();
    }
  }

  protected updated(changed: PropertyValues): void {
    if (changed.has("_devices")) this._syncRecheck();
  }

  /** Re-check devices/list periodically, only while a display isn't loaded. */
  private _syncRecheck(): void {
    const waiting = this.isConnected && anyWaiting(this._devices);
    if (waiting && !this._recheck) {
      this._recheck = setInterval(() => {
        if (document.visibilityState === "visible") this._refreshDevices();
      }, WAITING_RECHECK_MS);
    } else if (!waiting && this._recheck) {
      clearInterval(this._recheck);
      this._recheck = undefined;
    }
  }

  private _warnBeforeUnload = (event: BeforeUnloadEvent): void => {
    if (this._editor?.dirty) event.preventDefault();
  };

  private _onVisible = (): void => {
    if (document.visibilityState === "visible") {
      this._refreshDevices();
      this._refreshThumbs();
    }
  };

  private get _editor(): GmViewEditor | null {
    return this.renderRoot?.querySelector("gm-view-editor") ?? null;
  }

  // ---- data ------------------------------------------------------------------------

  private _notify(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true })
    );
  }

  private async _load(): Promise<void> {
    try {
      const [config, views, devices] = await Promise.all([
        this._api.config(),
        this._api.views(),
        this._api.devices(),
      ]);
      this._config = config;
      this._views = views;
      this._devices = devices;
      this._loadError = null;
      void this._renderThumbs();
    } catch (err) {
      this._loadError = errorMessage(err);
    }
  }

  private _refreshDevices(): void {
    clearTimeout(this._devicesTimer);
    this._devicesTimer = setTimeout(async () => {
      try {
        this._devices = await this._api.devices();
      } catch {
        // Keep what we have; the next change retries.
      }
    }, 300);
  }

  /** Render thumbnails for views that are new or changed (3 at a time). */
  private async _renderThumbs(): Promise<void> {
    const stale = this._views.filter((v) => this._thumbKeys.get(v.id) !== viewKey(v));
    for (const view of stale) this._thumbKeys.set(view.id, viewKey(view));
    await limited(stale, 3, async (view) => {
      try {
        const result = await this._api.render(view);
        this._thumbs = new Map(this._thumbs).set(view.id, pngUrl(result.image));
        if (this._failedThumbs.has(view.id)) {
          const failed = new Set(this._failedThumbs);
          failed.delete(view.id);
          this._failedThumbs = failed;
        }
      } catch {
        this._failedThumbs = new Set(this._failedThumbs).add(view.id);
      }
    });
  }

  /**
   * Re-render every thumbnail in place (each keeps its image until the new
   * one arrives). Only while the list is on screen and the tab visible.
   */
  private _refreshThumbs(): void {
    if (document.visibilityState !== "visible" || this._editing || this._thumbsRefreshing) return;
    this._thumbsRefreshing = true;
    void limited([...this._views], 3, async (view) => {
      const key = viewKey(view);
      try {
        const result = await this._api.render(view);
        // An edit since this render started brings its own thumbnail.
        if (this._thumbKeys.get(view.id) === key) {
          this._thumbs = new Map(this._thumbs).set(view.id, pngUrl(result.image));
        }
      } catch {
        // Keep the current thumbnail; the next minute retries.
      }
    }).finally(() => (this._thumbsRefreshing = false));
  }

  // ---- view actions -------------------------------------------------------------------

  private _openCreate(): void {
    this._newName = suggestName(this._views);
    this._createError = null;
    this._createOpen = true;
    this.updateComplete.then(() =>
      this.renderRoot.querySelector<HTMLElement>(".create-view-name")?.focus()
    );
  }

  private async _create(): Promise<void> {
    const name = this._newName.trim();
    if (!name || this._creating) return;
    this._creating = true;
    this._createError = null;
    try {
      const view = await this._api.createView(name);
      this._views = [...this._views, view];
      this._createOpen = false;
      this._editing = view;
    } catch (err) {
      this._createError = `Couldn't create the view: ${errorMessage(err)}`;
    } finally {
      this._creating = false;
    }
  }

  private async _duplicate(view: ViewConfig): Promise<void> {
    try {
      const copy = await this._api.duplicateView(view.id);
      this._views = [...this._views, copy];
      void this._renderThumbs();
    } catch (err) {
      this._notify(`Couldn't duplicate "${view.name}": ${errorMessage(err)}`);
    }
  }

  private async _delete(view: ViewConfig): Promise<void> {
    this._deleting = null;
    try {
      await this._api.deleteView(view.id);
      this._views = this._views.filter((v) => v.id !== view.id);
      this._notify(`Deleted "${view.name}"`);
      this._refreshDevices();
    } catch (err) {
      this._notify(`Couldn't delete "${view.name}": ${errorMessage(err)}`);
    }
  }

  private _onSaved(view: ViewConfig): void {
    this._views = this._views.map((v) => (v.id === view.id ? view : v));
    void this._renderThumbs();
  }

  private _devicesShowing(viewId: string): DeviceConfig[] {
    return this._devices.filter((d) => d.assigned_views.includes(viewId));
  }

  // ---- render ------------------------------------------------------------------------------

  render() {
    if (this._editing && this._config) {
      return html`<gm-view-editor
        .hass=${this.hass}
        .config=${this._config}
        .api=${this._api}
        .view=${this._editing}
        .previews=${{
          url: String(this.panel?.config?.previews_url ?? "/geekmagic_previews"),
          version: String(this.panel?.config?.previews_hash ?? "dev"),
        }}
        @saved=${(e: CustomEvent<ViewConfig>) => this._onSaved(e.detail)}
        @leave=${() => (this._editing = null)}
      ></gm-view-editor>`;
    }
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">GeekMagic</div>
      </div>
      <div class="content">${this._renderMain()}</div>
      ${this._config
        ? html`<ha-button class="fab" variant="brand" appearance="accent" size="l" @click=${this._openCreate}>
            <ha-svg-icon slot="start" .path=${mdi.plus}></ha-svg-icon>Add view
          </ha-button>`
        : nothing}
      ${this._renderCreateDialog()} ${this._renderDeleteDialog()}
    `;
  }

  private _renderMain() {
    if (this._loadError) {
      return html`<div class="page">
        <ha-alert alert-type="error" title="Couldn't load GeekMagic">
          ${this._loadError}
          <ha-button slot="action" appearance="plain" @click=${() => this._load()}>Retry</ha-button>
        </ha-alert>
      </div>`;
    }
    if (!this._config) {
      return html`<div class="loading"><ha-spinner></ha-spinner></div>`;
    }
    const narrow = this._width < 700;
    return html`<div class="page ${narrow ? "narrow" : ""}">
      <section>
        <h2 class="section-title">
          ${this._devices.length === 1 ? "Display" : "Displays"}
          ${this._devices.length > 1 ? html`<span class="count">${this._devices.length}</span>` : nothing}
        </h2>
        ${this._devices.length
          ? html`<div class="devices">
              ${this._devices.map(
                (device) => html`<gm-device-card
                  .hass=${this.hass}
                  .api=${this._api}
                  .device=${device}
                  .views=${this._views}
                  .thumbs=${this._thumbs}
                  .narrow=${narrow}
                  @devices-changed=${() => this._refreshDevices()}
                  @edit-view=${(e: CustomEvent<string>) => {
                    const view = this._views.find((v) => v.id === e.detail);
                    if (view) this._editing = view;
                  }}
                ></gm-device-card>`
              )}
            </div>`
          : html`<ha-alert alert-type="info" title="No displays yet">
              Add your GeekMagic display in
              <a href="/config/integrations/integration/geekmagic">Settings → Devices &amp; services</a>,
              then pick the views it shows here.
            </ha-alert>`}
      </section>
      <section>
        <h2 class="section-title">Views <span class="count">${this._views.length}</span></h2>
        ${this._views.length
          ? html`<div class="views">${this._views.map((view) => this._renderViewCard(view))}</div>`
          : html`<div class="empty">
              <ha-icon icon="mdi:view-dashboard-edit-outline"></ha-icon>
              <h3>Create your first view</h3>
              <p class="muted">A view is one screen: a layout, a theme, and the widgets in it.</p>
              <ha-button variant="brand" appearance="accent" @click=${this._openCreate}>Create a view</ha-button>
            </div>`}
      </section>
    </div>`;
  }

  private _renderViewCard(view: ViewConfig) {
    const thumb = this._thumbs.get(view.id);
    const on = this._devicesShowing(view.id);
    return html`<ha-card outlined class="view-card" @click=${() => (this._editing = view)}>
      <button class="reset preview focus-ring" aria-label="Edit ${view.name}">
        ${thumb
          ? html`<img src=${thumb} alt="" />`
          : this._failedThumbs.has(view.id)
            ? html`<span class="thumb-failed"><ha-icon icon="mdi:image-broken-variant"></ha-icon></span>`
            : html`<span class="skeleton"></span>`}
      </button>
      <div class="view-info">
        <div class="grow">
          <h3 class="ellipsis">${view.name}</h3>
          <div class="meta ellipsis">${viewMeta(this._config, view)}</div>
          <div class="meta ellipsis on ${on.length ? "assigned" : ""}">
            ${on.length
              ? html`<ha-icon icon="mdi:monitor"></ha-icon>${on.length === 1 ? on[0].name : plural(on.length, "display")}`
              : "Not on any display"}
          </div>
        </div>
        <gm-menu
          label="${view.name} actions"
          @click=${(e: Event) => e.stopPropagation()}
          .items=${[
            { key: "edit", label: "Edit", icon: "mdi:pencil" },
            { key: "duplicate", label: "Duplicate", icon: "mdi:content-copy" },
            { key: "delete", label: "Delete", icon: "mdi:delete", danger: true },
          ]}
          @action=${(e: CustomEvent<string>) => {
            if (e.detail === "edit") this._editing = view;
            if (e.detail === "duplicate") void this._duplicate(view);
            if (e.detail === "delete") this._deleting = view;
          }}
        ></gm-menu>
      </div>
    </ha-card>`;
  }

  private _renderCreateDialog() {
    if (!this._createOpen) return nothing;
    const close = () => {
      if (!this._creating) this._createOpen = false;
    };
    return html`<gm-dialog open heading="New view" @cancel=${close}>
      <ha-input
        class="create-view-name"
        label="Name"
        .value=${this._newName}
        @input=${(e: Event) => (this._newName = (e.target as HTMLInputElement).value)}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === "Enter") void this._create();
        }}
      ></ha-input>
      ${this._createError ? html`<ha-alert alert-type="error">${this._createError}</ha-alert>` : nothing}
      <ha-button slot="actions" appearance="plain" ?disabled=${this._creating} @click=${close}>Cancel</ha-button>
      <ha-button
        slot="actions"
        variant="brand"
        appearance="accent"
        ?disabled=${!this._newName.trim() || this._creating}
        .loading=${this._creating}
        @click=${() => this._create()}
        >Create</ha-button
      >
    </gm-dialog>`;
  }

  private _renderDeleteDialog() {
    const view = this._deleting;
    if (!view) return nothing;
    const on = this._devicesShowing(view.id);
    return html`<gm-dialog open heading='Delete "${view.name}"?' @cancel=${() => (this._deleting = null)}>
      ${on.length
        ? html`It will be removed from the rotation of ${on.map((d) => d.name).join(", ")}. This can't be undone.`
        : "This can't be undone."}
      <ha-button slot="actions" appearance="plain" @click=${() => (this._deleting = null)}>Cancel</ha-button>
      <ha-button slot="actions" variant="danger" appearance="accent" @click=${() => this._delete(view)}>Delete</ha-button>
    </gm-dialog>`;
  }

  static styles = [
    shared,
    css`
      :host {
        display: flex;
        flex-direction: column;
        /* HA gives custom panels no height: fill the viewport so the toolbar
           stays put and .content is the one scroller. */
        height: 100vh;
        height: 100dvh;
        background: var(--primary-background-color);
        color: var(--primary-text-color);
      }
      gm-view-editor {
        flex: 1;
        min-height: 0;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 4px;
        height: var(--header-height, 56px);
        padding: 0 12px 0 4px;
        flex: none;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      .title {
        font-size: 20px;
        line-height: 28px;
        margin-left: 12px;
      }
      .content {
        flex: 1;
        overflow: auto;
      }
      .page {
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px 24px 104px;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 32px;
      }
      .page.narrow {
        padding: 16px 16px 104px;
        gap: 24px;
      }
      .page.narrow .views {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .loading {
        display: flex;
        justify-content: center;
        padding: 96px 0;
      }
      .devices {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 16px;
      }
      section {
        min-width: 0;
      }
      .views {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 16px;
      }
      .view-card {
        cursor: pointer;
        overflow: hidden;
        transition: box-shadow 0.15s;
      }
      .view-card:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
      }
      .preview {
        display: block;
        width: 100%;
        aspect-ratio: 1;
        background: #000;
      }
      .preview img,
      .preview .skeleton,
      .thumb-failed {
        display: block;
        width: 100%;
        height: 100%;
      }
      .thumb-failed {
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.5);
        --mdc-icon-size: 40px;
      }
      .view-info {
        display: flex;
        align-items: flex-start;
        gap: 4px;
        padding: 12px 4px 12px 16px;
        border-top: 1px solid var(--divider-color);
      }
      .view-info h3 {
        font-size: 16px;
        font-weight: 500;
        line-height: 24px;
      }
      .meta {
        font-size: 13px;
        line-height: 18px;
        color: var(--secondary-text-color);
      }
      .on {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 2px;
        --mdc-icon-size: 14px;
      }
      .on.assigned {
        color: var(--primary-color);
      }
      .empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 48px 24px;
        text-align: center;
        border: 2px dashed var(--divider-color);
        border-radius: var(--gm-radius);
        --mdc-icon-size: 48px;
        color: var(--secondary-text-color);
      }
      .empty h3 {
        color: var(--primary-text-color);
        font-size: 18px;
        font-weight: 500;
      }
      .empty ha-button {
        margin-top: 8px;
      }
      .fab {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 3;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        border-radius: 999px;
        --ha-button-border-radius: 999px;
      }
      ha-alert a {
        color: var(--primary-color);
      }
      gm-dialog ha-input {
        display: block;
      }
      gm-dialog ha-alert {
        display: block;
        margin-top: 12px;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "geekmagic-panel": GeekMagicPanel;
  }
}
