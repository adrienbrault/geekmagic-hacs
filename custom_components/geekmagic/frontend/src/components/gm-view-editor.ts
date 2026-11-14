/**
 * The view editor: the device's screen on the left, an inspector on the
 * right. Click (or arrow-key to) a cell on the screen to edit its widget;
 * drag one cell onto another to swap them.
 *
 * Owns the draft, the saved snapshot (unsaved-changes detection), the
 * selected slot and the previews. Saving stays here and reports with a
 * toast; ``leave`` asks the shell to go back to the list.
 */
import { LitElement, css, html, nothing, svg, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  GeekMagicConfig,
  HomeAssistant,
  PreviewResponse,
  ViewConfig,
  WidgetConfig,
  WidgetTypeSchema,
} from "../types";
import { GeekMagicApi, limited, pngUrl, type ViewDraft } from "../api";
import { PreviewQueue, errorMessage, type PreviewState } from "../preview-queue";
import {
  clearSlot,
  cloneView,
  overflowWidgets,
  removeOverflow,
  setOption,
  setWidget,
  setWidgetType,
  swapSlots,
  widgetAt,
} from "../view-ops";
import { plural, slotCount } from "../format";
import { CATEGORY_COLORS, CATEGORY_TITLES, mdi, shared } from "../styles";
import "./gm-dialog";
import "./gm-menu";
import "./gm-screen";
import "./gm-widget-options";

type Rect = [number, number, number, number];
type Tab = "widget" | "view";

const CATEGORY_ORDER = ["values", "home", "time", "history", "pictures", "custom"];

@customElement("gm-view-editor")
export class GmViewEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) config!: GeekMagicConfig;
  @property({ attribute: false }) api!: GeekMagicApi;
  @property({ attribute: false }) view!: ViewConfig;

  @state() private _draft!: ViewConfig;
  @state() private _saved = "";
  @state() private _slot = 0;
  @state() private _tab: Tab = "widget";
  @state() private _changingType = false;
  @state() private _saving = false;
  @state() private _discardOpen = false;
  @state() private _preview: PreviewState<PreviewResponse> = {
    result: null,
    loading: false,
    error: null,
  };
  @state() private _themeTiles = new Map<string, string>();
  @state() private _width = 1200;
  @state() private _dragFrom: number | null = null;

  private _queue = new PreviewQueue<ViewDraft, PreviewResponse>(
    (draft) => this.api.render(draft),
    (s) => (this._preview = s)
  );
  private _resize = new ResizeObserver((entries) => {
    this._width = entries[0]?.contentRect.width ?? this._width;
  });
  private _themeTimer: ReturnType<typeof setTimeout> | undefined;
  private _themeGeneration = 0;

  /** True when the draft differs from what was last loaded or saved. */
  get dirty(): boolean {
    return JSON.stringify(this._draft) !== this._saved;
  }

  /** Back arrow: ask first if there are unsaved edits. */
  requestLeave(): void {
    if (this.dirty) this._discardOpen = true;
    else this._leave();
  }

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("view") && this.view && this.view.id !== this._draft?.id) {
      this._draft = cloneView(this.view);
      this._saved = JSON.stringify(this._draft);
      this._slot = 0;
      this._queue.now(this._draft);
    }
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.updateComplete.then(() => {
      const content = this.renderRoot.querySelector(".content");
      if (content) this._resize.observe(content);
    });
  }

  disconnectedCallback(): void {
    this._queue.dispose();
    this._resize.disconnect();
    clearTimeout(this._themeTimer);
    this._themeGeneration += 1;
    super.disconnectedCallback();
  }

  // ---- edits ---------------------------------------------------------------

  private get _slotCount(): number {
    return slotCount(this.config, this._draft.layout);
  }

  private _edit(next: ViewConfig, { render = true } = {}): void {
    this._draft = next;
    if (render) this._queue.request(next);
    if (this._tab === "view") this._scheduleThemeTiles();
  }

  private _select(slot: number): void {
    this._slot = Math.max(0, Math.min(slot, this._slotCount - 1));
    this._changingType = false;
    this._tab = "widget";
  }

  private _pickType(type: string): void {
    const initial: Record<string, unknown> =
      type === "clock" ? { timezone: Intl.DateTimeFormat().resolvedOptions().timeZone } : {};
    this._edit(setWidgetType(this._draft, this._slot, type, initial));
    this._changingType = false;
  }

  private _setLayout(layout: string): void {
    const next = { ...this._draft, layout };
    this._edit(next);
    this._slot = Math.min(this._slot, slotCount(this.config, layout) - 1);
  }

  // ---- save / leave ----------------------------------------------------------

  private _notify(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true })
    );
  }

  private async _save(): Promise<void> {
    if (this._saving) return;
    const saved = this._draft;
    this._saving = true;
    try {
      await this.api.updateView(saved);
      this._saved = JSON.stringify(saved);
      this._notify(`Saved "${saved.name}"`);
      this.dispatchEvent(new CustomEvent("saved", { detail: cloneView(saved) }));
    } catch (err) {
      this._notify(`Couldn't save "${saved.name}": ${errorMessage(err)}`);
    } finally {
      this._saving = false;
    }
  }

  private _leave(): void {
    this._discardOpen = false;
    this.dispatchEvent(new CustomEvent("leave"));
  }

  // ---- theme tiles ------------------------------------------------------------

  private _scheduleThemeTiles(): void {
    clearTimeout(this._themeTimer);
    this._themeTimer = setTimeout(() => void this._renderThemeTiles(), 600);
  }

  /** Render the draft in every theme (lazily, two at a time). */
  private async _renderThemeTiles(): Promise<void> {
    const generation = ++this._themeGeneration;
    const draft = this._draft;
    const key = (theme: string) => `${theme}|${draft.layout}|${JSON.stringify(draft.widgets)}`;
    const themes = Object.keys(this.config.themes).filter((t) => !this._themeTiles.has(key(t)));
    await limited(themes, 2, async (theme) => {
      if (generation !== this._themeGeneration) return;
      try {
        const result = await this.api.render({ ...draft, theme });
        if (generation !== this._themeGeneration) return;
        this._themeTiles = new Map(this._themeTiles).set(key(theme), pngUrl(result.image));
      } catch {
        // A tile without a picture still names its theme.
      }
    });
  }

  private _themeTile(theme: string): string | undefined {
    const d = this._draft;
    return this._themeTiles.get(`${theme}|${d.layout}|${JSON.stringify(d.widgets)}`);
  }

  // ---- render -----------------------------------------------------------------

  render() {
    if (!this._draft) return nothing;
    const narrow = this._width < 900;
    return html`
      <div class="toolbar editor-header">
        <ha-icon-button .path=${mdi.back} label="Back" @click=${() => this.requestLeave()}></ha-icon-button>
        <input
          class="title-input"
          aria-label="View name"
          .value=${this._draft.name}
          @input=${(e: Event) =>
            this._edit({ ...this._draft, name: (e.target as HTMLInputElement).value }, { render: false })}
        />
        ${this.dirty
          ? html`<span class="unsaved" title="Unsaved changes"
              ><span class="dot"></span><span class="unsaved-text">Unsaved changes</span></span
            >`
          : nothing}
        <ha-button
          variant="brand"
          appearance="accent"
          ?disabled=${!this.dirty || this._saving}
          .loading=${this._saving}
          @click=${this._save}
          >${this._saving ? "Saving…" : "Save"}</ha-button
        >
      </div>
      <div class="content ${narrow ? "narrow" : "wide"}">
        <div class="layout">
          <div class="stage">${this._renderStage(narrow)}</div>
          <div class="inspector">${this._renderInspector()}</div>
        </div>
      </div>
      ${this._discardOpen
        ? html`<gm-dialog open heading="Discard unsaved changes?" @cancel=${() => (this._discardOpen = false)}>
            Your edits to "${this._draft.name}" haven't been saved.
            <ha-button slot="actions" appearance="plain" @click=${() => (this._discardOpen = false)}>Keep editing</ha-button>
            <ha-button slot="actions" variant="danger" appearance="accent" @click=${() => this._leave()}>Discard</ha-button>
          </gm-dialog>`
        : nothing}
    `;
  }

  private _screenSize(narrow: boolean): number {
    if (narrow) return Math.min(240, Math.max(160, this._width - 120));
    return this._width >= 1100 ? 480 : 360;
  }

  private _rects(): Rect[] {
    const count = this._slotCount;
    const fromPreview = this._preview.result?.slots;
    if (fromPreview && fromPreview.length === count) {
      return fromPreview.map(([x1, y1, x2, y2]) => [x1 / 240, y1 / 240, (x2 - x1) / 240, (y2 - y1) / 240]);
    }
    return (this.config.layout_types[this._draft.layout]?.rects ?? []).slice(0, count);
  }

  private _slotName(slot: number): string {
    const widget = widgetAt(this._draft, slot);
    const schema = widget?.type ? this.config.widget_types[widget.type] : undefined;
    const what = schema ? [schema.name, widget?.label].filter(Boolean).join(", ") : "Empty";
    return `Slot ${slot + 1}: ${what}`;
  }

  private _overlayKeys(event: KeyboardEvent): void {
    const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (delta === undefined) return;
    event.preventDefault();
    const next = (this._slot + delta + this._slotCount) % this._slotCount;
    this._select(next);
    this.updateComplete.then(() =>
      this.renderRoot.querySelectorAll<HTMLElement>(".slot-hit")[next]?.focus()
    );
  }

  private _renderStage(narrow: boolean) {
    const size = this._screenSize(narrow);
    const hidden = overflowWidgets(this._draft, this._slotCount);
    const image = this._preview.result ? pngUrl(this._preview.result.image) : null;
    const empty = this._draft.widgets.every((w) => !w.type);
    return html`
      <div class="stage-inner">
        <gm-screen
          .src=${image}
          .size=${size}
          img-class="preview-image"
          alt="Preview of ${this._draft.name}"
          ?busy=${this._preview.loading}
        >
          <div class="overlay" role="listbox" aria-label="Slots" @keydown=${this._overlayKeys}>
            ${this._rects().map(([x, y, w, h], slot) => {
              const widget = widgetAt(this._draft, slot);
              const selected = slot === this._slot;
              return html`<button
                class="slot-hit ${selected ? "selected" : ""} ${widget?.type ? "" : "empty"} ${this._dragFrom !== null && this._dragFrom !== slot ? "drop" : ""}"
                style="left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${h * 100}%"
                role="option"
                aria-selected=${selected ? "true" : "false"}
                aria-label=${this._slotName(slot)}
                tabindex=${selected ? 0 : -1}
                draggable=${widget?.type ? "true" : "false"}
                @click=${() => this._select(slot)}
                @dragstart=${(e: DragEvent) => {
                  this._dragFrom = slot;
                  e.dataTransfer?.setData("text/plain", String(slot));
                }}
                @dragend=${() => (this._dragFrom = null)}
                @dragover=${(e: DragEvent) => e.preventDefault()}
                @drop=${(e: DragEvent) => {
                  e.preventDefault();
                  if (this._dragFrom !== null && this._dragFrom !== slot) {
                    this._edit(swapSlots(this._draft, this._dragFrom, slot));
                    this._slot = slot;
                  }
                  this._dragFrom = null;
                }}
              >
                ${widget?.type ? nothing : html`<ha-svg-icon .path=${mdi.plus}></ha-svg-icon>`}
              </button>`;
            })}
          </div>
          <div slot="empty" class="screen-empty">
            ${this._preview.error ? nothing : html`<ha-spinner size="s"></ha-spinner>`}
          </div>
        </gm-screen>
        <div class="stage-caption">
          ${empty
            ? html`<p><strong>Pick a cell to add a widget.</strong></p>
                <p class="muted">An empty view shows a clock on the display.</p>`
            : html`<p class="muted">
                ${narrow ? "Tap" : "Click"} a cell to edit it${narrow ? "" : ", drag one onto another to swap"}.
              </p>`}
        </div>
        ${this._preview.error
          ? html`<ha-alert alert-type="error" title="Preview failed">
              ${this._preview.error}
              <ha-button slot="action" appearance="plain" size="s" @click=${() => this._queue.now(this._draft)}>Retry</ha-button>
            </ha-alert>`
          : nothing}
        ${hidden.length
          ? html`<ha-alert alert-type="warning">
              ${plural(hidden.length, "widget")} ${hidden.length === 1 ? "doesn't" : "don't"} fit
              this layout and ${hidden.length === 1 ? "is" : "are"} hidden.
              <ha-button
                slot="action"
                appearance="plain"
                size="s"
                @click=${() => this._edit(removeOverflow(this._draft, this._slotCount))}
                >Remove hidden widgets</ha-button
              >
            </ha-alert>`
          : nothing}
      </div>
    `;
  }

  private _renderInspector() {
    const tab = (id: Tab, label: string) => html`<button
      role="tab"
      class="reset tab ${this._tab === id ? "active" : ""}"
      aria-selected=${this._tab === id ? "true" : "false"}
      @click=${() => {
        this._tab = id;
        if (id === "view") this._scheduleThemeTiles();
      }}
    >
      ${label}
    </button>`;
    return html`
      <ha-card outlined>
        <div class="tabs" role="tablist">
          ${tab("widget", `Slot ${this._slot + 1}`)} ${tab("view", "Layout & theme")}
        </div>
        <div class="panel" role="tabpanel">
          ${this._tab === "widget" ? this._renderWidgetTab() : this._renderViewTab()}
        </div>
      </ha-card>
    `;
  }

  private _renderWidgetTab() {
    const widget = widgetAt(this._draft, this._slot);
    const schema = widget?.type ? this.config.widget_types[widget.type] : undefined;
    if (!widget?.type || !schema || this._changingType) {
      return this._renderPicker(widget?.type);
    }
    return this._renderWidget(widget, schema);
  }

  private _badge(schema: WidgetTypeSchema | undefined, size = 40) {
    const color = CATEGORY_COLORS[schema?.category ?? "custom"] ?? CATEGORY_COLORS.custom;
    return html`<span class="icon-badge" style="--size:${size}px;--badge-color:${color}"
      ><ha-icon .icon=${schema?.icon ?? "mdi:widgets"}></ha-icon
    ></span>`;
  }

  private _renderPicker(current?: string) {
    const entries = Object.entries(this.config.widget_types);
    const groups = CATEGORY_ORDER.map((category) => ({
      category,
      items: entries.filter(([, s]) => (s.category ?? "custom") === category),
    })).filter((g) => g.items.length);
    const other = entries.filter(([, s]) => s.category && !CATEGORY_ORDER.includes(s.category));
    if (other.length) groups.push({ category: "custom", items: other });
    return html`
      <div class="picker-head">
        <div>
          <h3>${current ? "Change widget" : `Add a widget to slot ${this._slot + 1}`}</h3>
          <p class="muted">${current ? "The entity and label carry over." : "Pick what this cell shows."}</p>
        </div>
        ${current
          ? html`<ha-button appearance="plain" @click=${() => (this._changingType = false)}>Cancel</ha-button>`
          : nothing}
      </div>
      ${groups.map(
        (group) => html`<div class="group">
          <div class="group-title">${CATEGORY_TITLES[group.category] ?? "Other"}</div>
          <div class="tiles">
            ${group.items.map(
              ([type, schema]) => html`<button
                class="reset tile focus-ring ${type === current ? "current" : ""}"
                aria-label=${schema.name}
                @click=${() => this._pickType(type)}
              >
                ${this._badge(schema, 36)}
                <span class="tile-text">
                  <span class="tile-name">${schema.name}</span>
                  <span class="tile-desc">${schema.description ?? ""}</span>
                </span>
              </button>`
            )}
          </div>
        </div>`
      )}
    `;
  }

  private _renderMiniMap() {
    const rects = this._rects();
    if (rects.length < 2) return nothing;
    return html`<div class="position">
      <span class="caption">Position</span>
      <div class="minimap" role="group" aria-label="Move to slot">
        ${rects.map(
          ([x, y, w, h], slot) => html`<button
            class="reset mini ${slot === this._slot ? "here" : ""}"
            style="left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${h * 100}%"
            aria-label=${slot === this._slot ? `Slot ${slot + 1} (here)` : `Move to slot ${slot + 1}`}
            title=${slot === this._slot ? "Here" : `Move to slot ${slot + 1} (swaps)`}
            @click=${() => {
              if (slot === this._slot) return;
              this._edit(swapSlots(this._draft, this._slot, slot));
              this._slot = slot;
            }}
          ></button>`
        )}
      </div>
    </div>`;
  }

  private _renderWidget(widget: WidgetConfig, schema: WidgetTypeSchema) {
    const slot = this._slot;
    return html`
      <div class="widget-head">
        ${this._badge(schema)}
        <div class="grow">
          <h3>${schema.name}</h3>
          <p class="muted ellipsis">${schema.description ?? ""}</p>
        </div>
        <ha-button appearance="plain" size="s" @click=${() => (this._changingType = true)}>Change</ha-button>
        <gm-menu
          .items=${[{ key: "clear", label: "Clear slot", icon: "mdi:close-circle-outline", danger: true }]}
          @action=${() => this._edit(clearSlot(this._draft, slot))}
        ></gm-menu>
      </div>
      ${this._renderMiniMap()}
      ${schema.needs_entity
        ? html`<ha-selector
            class="entity-field"
            .hass=${this.hass}
            .selector=${{ entity: schema.entity_domains ? { domain: schema.entity_domains } : {} }}
            .value=${widget.entity_id ?? ""}
            .label=${"Entity"}
            .required=${true}
            @value-changed=${(e: CustomEvent) =>
              this._edit(setWidget(this._draft, slot, { entity_id: e.detail.value || undefined }))}
          ></ha-selector>`
        : nothing}
      ${schema.uses_label === false
        ? nothing
        : html`<ha-input
            class="label-input"
            label="Label"
            hint="Optional. Supports templates."
            .value=${widget.label ?? ""}
            @input=${(e: Event) =>
              this._edit(setWidget(this._draft, slot, { label: (e.target as HTMLInputElement).value }))}
          ></ha-input>`}
      ${schema.options?.length
        ? html`<gm-widget-options
            .hass=${this.hass}
            .schema=${schema}
            .widget=${widget}
            @option-change=${(e: CustomEvent<{ key: string; value: unknown }>) =>
              this._edit(setOption(this._draft, slot, e.detail.key, e.detail.value))}
          ></gm-widget-options>`
        : nothing}
    `;
  }

  private _renderViewTab() {
    const layouts = Object.entries(this.config.layout_types);
    return html`
      <div class="group">
        <div class="group-title">Layout</div>
        <div class="layout-tiles" role="radiogroup" aria-label="Layout">
          ${layouts.map(
            ([key, info]) => html`<button
              class="reset layout-tile focus-ring ${this._draft.layout === key ? "current" : ""}"
              role="radio"
              aria-checked=${this._draft.layout === key ? "true" : "false"}
              aria-label=${info.name}
              title="${info.name} · ${plural(info.slots, "slot")}"
              @click=${() => this._setLayout(key)}
            >
              <svg viewBox="0 0 1 1" aria-hidden="true">
                ${info.rects.map(
                  ([x, y, w, h]) =>
                    svg`<rect x=${x + 0.01} y=${y + 0.01} width=${Math.max(w - 0.02, 0.01)} height=${Math.max(h - 0.02, 0.01)} rx="0.04"></rect>`
                )}
              </svg>
              <span class="tile-name">${info.name}</span>
              <span class="tile-desc">${plural(info.slots, "slot")}</span>
            </button>`
          )}
        </div>
      </div>
      <div class="group">
        <div class="group-title">Theme</div>
        <div class="theme-tiles" role="radiogroup" aria-label="Theme">
          ${Object.entries(this.config.themes).map(([key, name]) => {
            const src = this._themeTile(key);
            return html`<button
              class="reset theme-tile focus-ring ${this._draft.theme === key ? "current" : ""}"
              role="radio"
              aria-checked=${this._draft.theme === key ? "true" : "false"}
              aria-label=${name}
              @click=${() => this._edit({ ...this._draft, theme: key })}
            >
              ${src ? html`<img src=${src} alt="" />` : html`<span class="skeleton"></span>`}
              <span class="tile-name">${name}</span>
            </button>`;
          })}
        </div>
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: var(--header-height, 56px);
        padding: 0 12px 0 4px;
        flex: none;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      .title-input {
        flex: 1;
        min-width: 0;
        font: inherit;
        font-size: 20px;
        line-height: 28px;
        color: inherit;
        background: transparent;
        border: 0;
        border-bottom: 2px solid transparent;
        padding: 4px 4px 2px;
        border-radius: 4px 4px 0 0;
      }
      .title-input:hover {
        border-bottom-color: var(--divider-color);
      }
      .title-input:focus {
        outline: none;
        border-bottom-color: var(--primary-color);
        background: var(--secondary-background-color);
      }
      .unsaved {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--warning-color, #ffa600);
      }
      .content {
        flex: 1;
        overflow: auto;
        container-type: inline-size;
      }
      .layout {
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 32px;
        align-items: start;
      }
      .narrow .layout {
        grid-template-columns: minmax(0, 1fr);
        padding: 0 12px 24px;
        gap: 12px;
      }
      .narrow .unsaved-text {
        display: none;
      }
      .stage {
        position: sticky;
        top: 24px;
      }
      .narrow .stage {
        top: 0;
        z-index: 2;
        margin: 0 -12px;
        padding: 12px 12px 8px;
        background: var(--primary-background-color);
        border-bottom: 1px solid var(--divider-color);
      }
      .stage-inner {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .wide .stage-inner {
        align-items: flex-start;
      }
      .stage-inner ha-alert {
        width: 100%;
        max-width: 528px;
      }
      .stage-caption {
        text-align: center;
        font-size: 14px;
        line-height: 20px;
      }
      .wide .stage-caption {
        text-align: left;
      }
      .narrow .stage-caption {
        display: none;
      }
      .overlay {
        position: absolute;
        inset: 0;
      }
      .slot-hit {
        position: absolute;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        margin: 0;
        border: 0;
        border-radius: 6px;
        background: transparent;
        cursor: pointer;
        color: rgba(255, 255, 255, 0.85);
        --mdc-icon-size: 28px;
        transition: box-shadow 0.12s, background 0.12s;
      }
      .slot-hit:hover {
        box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.55);
      }
      .slot-hit.empty {
        box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.28);
        background-image: linear-gradient(rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.06));
        outline: 1px dashed rgba(255, 255, 255, 0.45);
        outline-offset: -5px;
      }
      .slot-hit.selected {
        box-shadow:
          inset 0 0 0 3px var(--primary-color),
          0 0 0 1px rgba(0, 0, 0, 0.4);
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
      }
      .slot-hit.drop {
        box-shadow: inset 0 0 0 2px var(--accent-color, var(--primary-color));
      }
      .slot-hit:focus-visible {
        outline: 2px solid #fff;
        outline-offset: -6px;
      }
      .screen-empty {
        display: flex;
        align-items: center;
        justify-content: center;
      }
      ha-card {
        overflow: hidden;
      }
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--divider-color);
        padding: 0 8px;
      }
      .tab {
        position: relative;
        padding: 14px 16px;
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      .tab.active {
        color: var(--primary-color);
      }
      .tab.active::after {
        content: "";
        position: absolute;
        left: 12px;
        right: 12px;
        bottom: 0;
        height: 3px;
        border-radius: 3px 3px 0 0;
        background: var(--primary-color);
      }
      .panel {
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding: 20px;
      }
      .narrow .panel {
        padding: 16px;
      }
      h3 {
        font-size: 16px;
        font-weight: 500;
        line-height: 24px;
      }
      .muted {
        font-size: 13px;
      }
      .picker-head,
      .widget-head {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .picker-head > div {
        flex: 1;
      }
      .group {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .group-title,
      .caption {
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 8px;
      }
      .tile {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        background: var(--card-background-color);
        transition: background 0.12s, border-color 0.12s;
      }
      .tile:hover {
        background: var(--secondary-background-color);
      }
      .tile.current,
      .layout-tile.current,
      .theme-tile.current {
        border-color: var(--primary-color);
        box-shadow: inset 0 0 0 1px var(--primary-color);
        background: var(--gm-tint);
      }
      .tile-text {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }
      .tile-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .tile-desc {
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
      }
      .position {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .minimap {
        position: relative;
        width: 64px;
        height: 64px;
        border-radius: 8px;
        background: var(--gm-bezel);
      }
      .mini {
        position: absolute;
        padding: 0;
        border: 2px solid var(--gm-bezel);
        border-radius: 5px;
        background: rgba(255, 255, 255, 0.22);
        cursor: pointer;
      }
      .mini:hover {
        background: rgba(255, 255, 255, 0.45);
      }
      .mini.here {
        background: var(--primary-color);
        cursor: default;
      }
      .entity-field,
      .label-input {
        display: block;
      }
      .layout-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
        gap: 8px;
      }
      .layout-tile,
      .theme-tile {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        padding: 10px 6px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        text-align: center;
      }
      .layout-tile:hover,
      .theme-tile:hover {
        background: var(--secondary-background-color);
      }
      .layout-tile svg {
        width: 44px;
        height: 44px;
        border-radius: 6px;
        background: var(--gm-bezel);
        padding: 2px;
      }
      .layout-tile rect {
        fill: rgba(255, 255, 255, 0.55);
      }
      .layout-tile.current rect {
        fill: var(--primary-color);
      }
      .layout-tile .tile-name {
        font-size: 12px;
        line-height: 16px;
      }
      .layout-tile .tile-desc {
        font-size: 11px;
      }
      .theme-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
        gap: 8px;
      }
      .theme-tile img,
      .theme-tile .skeleton {
        display: block;
        width: 100%;
        aspect-ratio: 1;
        border-radius: 6px;
        background-color: #000;
      }
      .theme-tile .tile-name {
        font-size: 12px;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-view-editor": GmViewEditor;
  }
}
