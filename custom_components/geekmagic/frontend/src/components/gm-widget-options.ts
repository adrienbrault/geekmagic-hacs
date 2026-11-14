/**
 * The options form of one widget: every option its schema declares that
 * applies right now (``visible_when``), in schema order.
 *
 * Fires ``option-change`` with ``{key, value}``; ``value`` undefined clears
 * the option. Hidden options keep their stored value.
 */
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  ColorThreshold,
  HomeAssistant,
  ProgressItem,
  StatusEntity,
  WidgetConfig,
  WidgetOption,
  WidgetTypeSchema,
} from "../types";
import { parseColorInput, rgbToHex, type RGBTuple } from "../color-utils";
import { newProgressItem, newStatusEntity, newThreshold } from "../panel-defaults";
import { resolveSelectedValue } from "../select-compat";
import { visibleOptions } from "../option-visibility";
import { rowTitle } from "../format";
import { moveItem } from "../rotation";
import { mdi, shared } from "../styles";

declare global {
  namespace Intl {
    function supportedValuesOf(key: string): string[];
  }
}

const TIMEZONES: string[] = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return ["UTC", "Europe/London", "Europe/Paris", "America/New_York", "Asia/Tokyo"];
  }
})();

const isRgb = (value: unknown): value is RGBTuple =>
  Array.isArray(value) && value.length === 3 && value.every((n) => typeof n === "number");

@customElement("gm-widget-options")
export class GmWidgetOptions extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) schema!: WidgetTypeSchema;
  @property({ attribute: false }) widget!: WidgetConfig;
  @state() private _expanded = new Set<string>();

  private _emit(key: string, value: unknown): void {
    this.dispatchEvent(new CustomEvent("option-change", { detail: { key, value } }));
  }

  private _friendly = (entityId: string): string | undefined =>
    this.hass.states[entityId]?.attributes.friendly_name as string | undefined;

  render() {
    const options = visibleOptions(this.schema.options ?? [], this.widget.options);
    const toggles = options.filter((o) => o.type === "boolean");
    const fields = options.filter((o) => o.type !== "boolean");
    return html`
      ${fields.map((opt) => this._field(opt))}
      ${toggles.length
        ? html`<div class="toggles" role="group" aria-label="Show">
            ${toggles.map((opt) => this._toggle(opt))}
          </div>`
        : nothing}
    `;
  }

  private _value(opt: WidgetOption): unknown {
    return this.widget.options?.[opt.key] ?? opt.default;
  }

  private _toggle(opt: WidgetOption) {
    const id = `opt-${opt.key}`;
    return html`<label class="toggle" for=${id}>
      <span>${opt.label}</span>
      <ha-switch
        id=${id}
        .checked=${!!this._value(opt)}
        @change=${(e: Event) => this._emit(opt.key, (e.target as HTMLInputElement).checked)}
      ></ha-switch>
    </label>`;
  }

  private _select(label: string, value: string, choices: { value: string; label: string }[], onPick: (v: string) => void) {
    const keys = choices.map((c) => c.value);
    return html`<ha-select
      .label=${label}
      .value=${value}
      .options=${choices}
      @selected=${(e: CustomEvent) => {
        const picked = resolveSelectedValue(e.detail, keys);
        if (picked !== undefined && picked !== value) onPick(picked);
      }}
      @closed=${(e: Event) => e.stopPropagation()}
    >
      ${choices.map((c) => html`<mwc-list-item value=${c.value}>${c.label}</mwc-list-item>`)}
    </ha-select>`;
  }

  private _field(opt: WidgetOption) {
    const value = this._value(opt);
    switch (opt.type) {
      case "select": {
        const choices = (opt.options ?? []).map((o) => ({ value: o, label: o }));
        return html`<div class="field">
          ${this._select(opt.label, String(value ?? ""), choices, (v) => this._emit(opt.key, v))}
        </div>`;
      }
      case "number":
        return html`<div class="field">
          <ha-input
            type="number"
            .label=${opt.label}
            .value=${value !== undefined && value !== null ? String(value) : ""}
            .min=${opt.min !== undefined ? String(opt.min) : ""}
            .max=${opt.max !== undefined ? String(opt.max) : ""}
            @input=${(e: Event) => {
              const raw = (e.target as HTMLInputElement).value;
              this._emit(opt.key, raw === "" ? undefined : parseFloat(raw));
            }}
          ></ha-input>
        </div>`;
      case "text":
        return html`<div class="field">
          <ha-input
            .label=${opt.label}
            .value=${(value as string) ?? ""}
            .placeholder=${opt.placeholder ?? ""}
            @input=${(e: Event) => this._emit(opt.key, (e.target as HTMLInputElement).value)}
          ></ha-input>
        </div>`;
      case "textarea":
        return html`<div class="field">
          <label class="caption" for="ta-${opt.key}">${opt.label}</label>
          <textarea
            id="ta-${opt.key}"
            .value=${(value as string) ?? ""}
            placeholder=${opt.placeholder ?? ""}
            spellcheck="false"
            @input=${(e: Event) => this._emit(opt.key, (e.target as HTMLTextAreaElement).value)}
          ></textarea>
        </div>`;
      case "icon":
        return html`<div class="field">
          <ha-icon-picker
            .hass=${this.hass}
            .label=${opt.label}
            .value=${(value as string) ?? ""}
            @value-changed=${(e: CustomEvent) => this._emit(opt.key, e.detail.value || undefined)}
          ></ha-icon-picker>
        </div>`;
      case "entity":
        return html`<div class="field">
          <ha-selector
            .hass=${this.hass}
            .selector=${{ entity: {} }}
            .value=${(value as string) ?? ""}
            .label=${opt.label}
            @value-changed=${(e: CustomEvent) => this._emit(opt.key, e.detail.value || undefined)}
          ></ha-selector>
        </div>`;
      case "color":
        return html`<div class="field">
          ${this._color(opt.label, isRgb(value) ? value : undefined, (rgb) => this._emit(opt.key, rgb), true)}
        </div>`;
      case "timezone": {
        const choices = [
          { value: "", label: "Home Assistant default" },
          ...TIMEZONES.map((tz) => ({ value: tz, label: tz })),
        ];
        return html`<div class="field">
          ${this._select(opt.label, String(value ?? ""), choices, (v) => this._emit(opt.key, v))}
        </div>`;
      }
      case "thresholds":
        return this._thresholds(opt, (value as ColorThreshold[]) ?? []);
      case "progress_items":
        return this._progressItems(opt, (value as ProgressItem[]) ?? []);
      case "status_entities":
        return this._statusEntities(opt, (value as StatusEntity[]) ?? []);
      default:
        return nothing;
    }
  }

  /**
   * Swatch + hex. Unset is not a colour: the device uses the theme's
   * semantic colour, so it shows hatched as "Theme default" (issue #170).
   */
  private _color(label: string, rgb: RGBTuple | undefined, onChange: (rgb: RGBTuple | undefined) => void, clearable: boolean) {
    const hex = rgb ? rgbToHex(rgb) : "";
    const pick = (e: Event) => {
      const parsed = parseColorInput((e.target as HTMLInputElement).value);
      if (parsed) onChange(parsed);
    };
    return html`<div class="color">
      <label class="swatch ${hex ? "" : "unset"}" style=${hex ? `background:${hex}` : ""} title="Pick a colour">
        <input type="color" .value=${hex || "#ffffff"} @input=${pick} aria-label="${label} colour" />
      </label>
      <ha-input
        class="grow"
        .label=${label}
        .value=${hex}
        placeholder="Theme default"
        @change=${(e: Event) => {
          const raw = (e.target as HTMLInputElement).value.trim();
          if (!raw) return clearable ? onChange(undefined) : undefined;
          const parsed = parseColorInput(raw);
          if (parsed) onChange(parsed);
        }}
      ></ha-input>
      ${clearable && hex
        ? html`<ha-icon-button .path=${mdi.close} label="Use the theme's colour" @click=${() => onChange(undefined)}></ha-icon-button>`
        : nothing}
    </div>`;
  }

  private _thresholds(opt: WidgetOption, items: ColorThreshold[]) {
    const update = (next: ColorThreshold[]) => this._emit(opt.key, next);
    return html`<div class="array">
      <div class="array-title">${opt.label}</div>
      ${items.map(
        (item, idx) => html`<div class="threshold">
          <ha-input
            class="threshold-value"
            type="number"
            label="From"
            .value=${String(item.value)}
            @input=${(e: Event) => {
              const next = [...items];
              next[idx] = { ...item, value: parseFloat((e.target as HTMLInputElement).value) || 0 };
              update(next);
            }}
          ></ha-input>
          ${this._color("Colour", item.color as RGBTuple, (rgb) => {
            const next = [...items];
            next[idx] = { ...item, color: rgb ?? item.color };
            update(next);
          }, false)}
          <ha-icon-button .path=${mdi.delete} label="Remove" @click=${() => update(items.filter((_, i) => i !== idx))}></ha-icon-button>
        </div>`
      )}
      <ha-button appearance="plain" size="s" @click=${() => update([...items, newThreshold()])}>
        <ha-svg-icon slot="start" .path=${mdi.plus}></ha-svg-icon>Add Threshold
      </ha-button>
    </div>`;
  }

  private _rows<T extends { entity_id: string; label?: string }>(
    opt: WidgetOption,
    items: T[],
    kind: string,
    addLabel: string,
    blank: () => T,
    body: (item: T, set: (patch: Partial<T>) => void) => unknown
  ) {
    const update = (next: T[]) => this._emit(opt.key, next);
    const toggle = (key: string) => {
      const next = new Set(this._expanded);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      this._expanded = next;
    };
    return html`<div class="array">
      <div class="array-title">${opt.label}</div>
      ${items.map((item, idx) => {
        const key = `${kind}-${idx}`;
        const open = this._expanded.has(key);
        const set = (patch: Partial<T>) => {
          const next = [...items];
          next[idx] = { ...item, ...patch };
          update(next);
        };
        const title = rowTitle(item, this._friendly, "New entity");
        return html`<div class="array-item ${open ? "open" : ""}">
          <div class="array-item-header">
            <button class="reset grow row" aria-expanded=${open ? "true" : "false"} @click=${() => toggle(key)}>
              ${item.entity_id
                ? html`<ha-state-icon .hass=${this.hass} .stateObj=${this.hass.states[item.entity_id]}></ha-state-icon>`
                : html`<ha-icon icon="mdi:plus-circle-outline"></ha-icon>`}
              <span class="array-item-title ellipsis grow ${item.entity_id ? "" : "muted"}">${title}</span>
            </button>
            <ha-icon-button .path=${mdi.up} label="Move up" .disabled=${idx === 0} @click=${() => update(moveItem(items, idx, -1))}></ha-icon-button>
            <ha-icon-button .path=${mdi.down} label="Move down" .disabled=${idx === items.length - 1} @click=${() => update(moveItem(items, idx, 1))}></ha-icon-button>
            <ha-icon-button .path=${mdi.delete} label="Remove" @click=${() => update(items.filter((_, i) => i !== idx))}></ha-icon-button>
          </div>
          <div class="array-item-content ${open ? "" : "collapsed"}">${body(item, set)}</div>
        </div>`;
      })}
      <ha-button
        appearance="plain"
        size="s"
        @click=${() => {
          update([...items, blank()]);
          this._expanded = new Set([...this._expanded, `${kind}-${items.length}`]);
        }}
      >
        <ha-svg-icon slot="start" .path=${mdi.plus}></ha-svg-icon>${addLabel}
      </ha-button>
    </div>`;
  }

  private _entity(value: string, set: (id: string) => void) {
    return html`<ha-selector
      .hass=${this.hass}
      .selector=${{ entity: {} }}
      .value=${value}
      .label=${"Entity"}
      @value-changed=${(e: CustomEvent) => set(e.detail.value ?? "")}
    ></ha-selector>`;
  }

  private _statusEntities(opt: WidgetOption, items: StatusEntity[]) {
    return this._rows(opt, items, "status", "Add Status Entity", newStatusEntity, (item, set) => html`
      ${this._entity(item.entity_id, (entity_id) => set({ entity_id }))}
      <ha-input label="Label" .value=${item.label ?? ""} @input=${(e: Event) => set({ label: (e.target as HTMLInputElement).value })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${item.icon ?? ""} @value-changed=${(e: CustomEvent) => set({ icon: e.detail.value || undefined })}></ha-icon-picker>
    `);
  }

  private _progressItems(opt: WidgetOption, items: ProgressItem[]) {
    return this._rows(opt, items, "progress", "Add Progress Item", newProgressItem, (item, set) => html`
      ${this._entity(item.entity_id, (entity_id) => set({ entity_id }))}
      <ha-input label="Label" .value=${item.label ?? ""} @input=${(e: Event) => set({ label: (e.target as HTMLInputElement).value })}></ha-input>
      <ha-input type="number" label="Target" .value=${item.target !== undefined ? String(item.target) : "100"} @input=${(e: Event) => set({ target: parseFloat((e.target as HTMLInputElement).value) || 100 })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${item.icon ?? ""} @value-changed=${(e: CustomEvent) => set({ icon: e.detail.value || undefined })}></ha-icon-picker>
      ${this._color("Colour", isRgb(item.color) ? item.color : undefined, (color) => set({ color }), true)}
    `);
  }

  static styles = [
    shared,
    css`
      :host {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .field > * {
        display: block;
        width: 100%;
      }
      .caption {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      textarea {
        width: 100%;
        min-height: 140px;
        padding: 10px 12px;
        font-family: var(--ha-font-family-code, ui-monospace, monospace);
        font-size: 13px;
        line-height: 1.5;
        color: var(--primary-text-color);
        background: var(--secondary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        resize: vertical;
      }
      textarea:focus {
        outline: 2px solid var(--primary-color);
        outline-offset: -1px;
      }
      .toggles {
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        overflow: hidden;
      }
      .toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 48px;
        padding: 0 16px;
        cursor: pointer;
        font-size: 14px;
      }
      .toggle + .toggle {
        border-top: 1px solid var(--divider-color);
      }
      .color {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .swatch {
        position: relative;
        flex: none;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 1px solid var(--divider-color);
        cursor: pointer;
      }
      .swatch.unset {
        background: repeating-linear-gradient(
          45deg,
          var(--secondary-background-color) 0 5px,
          var(--divider-color) 5px 10px
        );
      }
      .swatch input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
        height: 100%;
      }
      .swatch:focus-within {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      .array {
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: stretch;
      }
      .array > ha-button {
        align-self: flex-start;
      }
      .array-title {
        font-size: 14px;
        font-weight: 500;
      }
      .threshold {
        display: grid;
        grid-template-columns: 96px 1fr auto;
        align-items: center;
        gap: 8px;
      }
      .array-item {
        border: 1px solid var(--divider-color);
        border-radius: 12px;
      }
      .array-item-header {
        display: flex;
        align-items: center;
        padding: 0 4px 0 12px;
        min-height: 48px;
        --mdc-icon-size: 20px;
      }
      .array-item-header > button {
        min-height: 48px;
        gap: 12px;
        color: var(--state-icon-color, var(--secondary-text-color));
      }
      .array-item-title {
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .array-item-title.muted {
        color: var(--secondary-text-color);
      }
      .array-item-content {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 4px 12px 12px;
      }
      .array-item-content.collapsed {
        display: none;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-widget-options": GmWidgetOptions;
  }
}
