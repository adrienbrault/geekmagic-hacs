/**
 * Import a view designed elsewhere: paste its JSON, map the entity ids
 * this Home Assistant doesn't have, preview it, save it.
 *
 * Parsing is ``import-view.ts``; remapping and validation are the
 * backend's (``geekmagic/views/check``), so an import is checked exactly as
 * the offline renderer checks a view. The preview is the device frame
 * (``geekmagic/preview/render``). Fires ``imported`` with the saved view
 * (``replaced`` when it overwrote one) and ``cancel``.
 */
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, PreviewResponse, ViewConfig } from "../types";
import { type GeekMagicApi, type ViewDraft, pngUrl } from "../api";
import { PreviewQueue, errorMessage, type PreviewState } from "../preview-queue";
import {
  type CheckedEntity,
  type ViewCheck,
  entityMap,
  importName,
  importPayload,
  missingEntities,
  parseImport,
} from "../import-view";
import { resolveSelectedValue } from "../select-compat";
import { plural } from "../format";
import { shared } from "../styles";
import "./gm-dialog";
import "./gm-screen";

export interface ImportedDetail {
  view: ViewConfig;
  replaced: boolean;
}

/** Saves a new view; any other target is the id of the view to replace. */
const NEW = "new";

@customElement("gm-import-dialog")
export class GmImportDialog extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) api!: GeekMagicApi;
  @property({ attribute: false }) views: ViewConfig[] = [];

  @state() private _text = "";
  @state() private _parseError: string | null = null;
  @state() private _source: Record<string, unknown> | null = null;
  @state() private _check: ViewCheck | null = null;
  @state() private _checkError: string | null = null;
  /** Rows: the ids the pasted view reads that this HA lacks (from the map-less check). */
  @state() private _missing: CheckedEntity[] = [];
  @state() private _picks: Record<string, string> = {};
  @state() private _name = "";
  @state() private _target = NEW;
  @state() private _saving = false;
  @state() private _saveError: string | null = null;
  @state() private _preview: PreviewState<PreviewResponse> = {
    result: null,
    loading: false,
    error: null,
  };

  private _parseTimer: ReturnType<typeof setTimeout> | undefined;
  private _checkSeq = 0;
  private _queue = this._newQueue();

  private _newQueue(): PreviewQueue<ViewDraft, PreviewResponse> {
    return new PreviewQueue<ViewDraft, PreviewResponse>(
      (view) => this.api.render(view),
      (next) => (this._preview = next)
    );
  }

  /** Drop the preview (and any render in flight): nothing valid to show. */
  private _clearPreview(): void {
    this._queue.dispose();
    this._queue = this._newQueue();
    this._preview = { result: null, loading: false, error: null };
  }

  disconnectedCallback(): void {
    clearTimeout(this._parseTimer);
    this._queue.dispose();
    this._checkSeq += 1;
    super.disconnectedCallback();
  }

  protected firstUpdated(): void {
    this.renderRoot.querySelector<HTMLTextAreaElement>("textarea")?.focus();
  }

  // ---- input ---------------------------------------------------------------------------

  private _onText(text: string): void {
    this._text = text;
    clearTimeout(this._parseTimer);
    this._parseTimer = setTimeout(() => void this._parse(), 300);
  }

  private async _parse(): Promise<void> {
    const parsed = parseImport(this._text);
    this._checkSeq += 1;
    this._picks = {};
    this._missing = [];
    this._check = null;
    this._checkError = null;
    this._saveError = null;
    if (parsed.error !== undefined) {
      this._source = null;
      this._parseError = this._text.trim() ? parsed.error : null;
      this._clearPreview();
      return;
    }
    this._parseError = null;
    this._source = parsed.view;
    this._name = importName(parsed.view, this.views);
    const check = await this._runCheck();
    if (check) this._missing = missingEntities(check.entities);
  }

  private _pick(entityId: string, value: string): void {
    this._picks = { ...this._picks, [entityId]: value };
    void this._runCheck();
  }

  /** Check the pasted view with the current picks; latest call wins. */
  private async _runCheck(): Promise<ViewCheck | null> {
    if (!this._source) return null;
    const mine = ++this._checkSeq;
    try {
      const check = await this.api.checkView(this._source, entityMap(this._picks));
      if (mine !== this._checkSeq) return null;
      this._check = check;
      this._checkError = null;
      // A view with errors renders as something else (build_layout falls back)
      if (check.errors.length) this._clearPreview();
      else this._queue.request(importPayload(check.view));
      return check;
    } catch (err) {
      if (mine !== this._checkSeq) return null;
      this._checkError = errorMessage(err);
      return null;
    }
  }

  // ---- save ----------------------------------------------------------------------------

  private get _canSave(): boolean {
    const check = this._check;
    if (!check || check.errors.length || this._saving) return false;
    return this._target !== NEW || Boolean(this._name.trim());
  }

  private async _save(): Promise<void> {
    const check = this._check;
    if (!check || !this._canSave) return;
    this._saving = true;
    this._saveError = null;
    const payload = importPayload(check.view);
    try {
      const replaced = this._target !== NEW;
      const view = replaced
        ? await this.api.replaceView(this._target, payload)
        : await this.api.importView(this._name.trim(), payload);
      this.dispatchEvent(new CustomEvent<ImportedDetail>("imported", { detail: { view, replaced } }));
    } catch (err) {
      this._saveError = `Couldn't save the view: ${errorMessage(err)}`;
    } finally {
      this._saving = false;
    }
  }

  private _cancel(): void {
    if (!this._saving) this.dispatchEvent(new CustomEvent("cancel"));
  }

  // ---- render --------------------------------------------------------------------------

  render() {
    const replacing = this.views.find((v) => v.id === this._target);
    return html`<gm-dialog open wide heading="Import a view" @cancel=${this._cancel}>
      <div class="import">
        <div class="source">
          <label class="field-label" for="json">View JSON</label>
          <textarea
            id="json"
            class="import-json"
            spellcheck="false"
            placeholder='{"layout": "grid_2x2", "theme": "watchos", "widgets": [...]}'
            .value=${this._text}
            @input=${(e: Event) => this._onText((e.target as HTMLTextAreaElement).value)}
          ></textarea>
          <p class="hint">
            Paste a view from an AI or from <code>render_view.py --save-view</code>. Code fences are fine.
          </p>
          ${this._parseError ? html`<ha-alert alert-type="error">${this._parseError}</ha-alert>` : nothing}
          ${this._checkError
            ? html`<ha-alert alert-type="error" title="Couldn't check the view">${this._checkError}</ha-alert>`
            : nothing}
          ${this._renderProblems()} ${this._renderMapping()}
        </div>
        <div class="side">
          <gm-screen
            .src=${this._preview.result ? pngUrl(this._preview.result.image) : null}
            .size=${240}
            img-class="import-preview"
            alt="Preview of the imported view"
            ?busy=${this._preview.loading}
          >
            <span slot="empty" class="empty"
              >${!this._source ? "Preview" : this._check?.errors.length ? "No preview: fix the errors" : "Rendering…"}</span
            >
          </gm-screen>
          ${this._preview.error
            ? html`<ha-alert alert-type="error" title="Preview failed">${this._preview.error}</ha-alert>`
            : nothing}
          ${this._renderTarget()}
        </div>
      </div>
      ${this._saveError ? html`<ha-alert alert-type="error">${this._saveError}</ha-alert>` : nothing}
      <ha-button slot="actions" appearance="plain" ?disabled=${this._saving} @click=${this._cancel}>Cancel</ha-button>
      <ha-button
        slot="actions"
        class="import-save"
        variant=${replacing ? "danger" : "brand"}
        appearance="accent"
        ?disabled=${!this._canSave}
        .loading=${this._saving}
        @click=${() => this._save()}
        >${replacing ? `Replace "${replacing.name}"` : "Save as new view"}</ha-button
      >
    </gm-dialog>`;
  }

  private _renderProblems() {
    const check = this._check;
    if (!check) return nothing;
    return html`
      ${check.errors.length
        ? html`<ha-alert alert-type="error" title="This view can't be imported">
            <ul>
              ${check.errors.map((e) => html`<li>${e}</li>`)}
            </ul>
          </ha-alert>`
        : nothing}
      ${check.warnings.length
        ? html`<ha-alert alert-type="warning" title=${plural(check.warnings.length, "warning")}>
            <ul>
              ${check.warnings.map((w) => html`<li>${w}</li>`)}
            </ul>
          </ha-alert>`
        : nothing}
    `;
  }

  private _renderMapping() {
    if (!this._missing.length) return nothing;
    return html`<section class="mapping">
      <h3>Entities to map</h3>
      <p class="hint">
        ${plural(this._missing.length, "entity isn't", "entities aren't")} in this Home Assistant. Pick yours;
        every use in the view follows, templates included.
      </p>
      ${this._missing.map(
        (entity) => html`<div class="map-row" data-entity-id=${entity.id}>
          <code class="from">${entity.id}</code>
          <ha-selector
            .hass=${this.hass}
            .selector=${{ entity: { domain: entity.domain } }}
            .value=${this._picks[entity.id] ?? ""}
            .label=${`Your ${entity.domain.replace(/_/g, " ")}`}
            .required=${false}
            @value-changed=${(e: CustomEvent) => this._pick(entity.id, e.detail.value ?? "")}
          ></ha-selector>
        </div>`
      )}
    </section>`;
  }

  private _renderTarget() {
    const choices = [
      { value: NEW, label: "A new view" },
      ...this.views.map((v) => ({ value: v.id, label: `Replace "${v.name}"` })),
    ];
    const keys = choices.map((c) => c.value);
    return html`<div class="target">
      <ha-select
        .label=${"Save as"}
        .value=${this._target}
        .options=${choices}
        @selected=${(e: CustomEvent) => {
          const picked = resolveSelectedValue(e.detail, keys);
          if (picked !== undefined) this._target = picked;
        }}
        @closed=${(e: Event) => e.stopPropagation()}
      >
        ${choices.map((c) => html`<mwc-list-item value=${c.value}>${c.label}</mwc-list-item>`)}
      </ha-select>
      ${this._target === NEW
        ? html`<ha-input
            class="import-name"
            label="Name"
            .value=${this._name}
            @input=${(e: Event) => (this._name = (e.target as HTMLInputElement).value)}
          ></ha-input>`
        : html`<p class="hint">Keeps its name and the displays showing it; its layout, theme and widgets are replaced.</p>`}
    </div>`;
  }

  static styles = [
    shared,
    css`
      .import {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 264px;
        gap: 24px;
        color: var(--primary-text-color);
      }
      @media (max-width: 720px) {
        .import {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .source,
      .side,
      .target,
      .mapping {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
      }
      .side {
        align-items: center;
      }
      .target {
        align-self: stretch;
      }
      .field-label {
        font-size: 14px;
        font-weight: 500;
      }
      textarea {
        width: 100%;
        min-height: 200px;
        resize: vertical;
        padding: 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        background: var(--secondary-background-color, transparent);
        color: var(--primary-text-color);
        font: 12px/1.45 var(--ha-font-family-code, ui-monospace, Menlo, monospace);
      }
      textarea:focus {
        outline: 2px solid var(--primary-color);
        outline-offset: -1px;
      }
      .hint {
        font-size: 13px;
        line-height: 18px;
        color: var(--secondary-text-color);
      }
      code {
        font-family: var(--ha-font-family-code, ui-monospace, Menlo, monospace);
        font-size: 12px;
      }
      h3 {
        font-size: 15px;
        font-weight: 500;
      }
      .map-row {
        display: grid;
        grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
        align-items: end;
        gap: 12px;
      }
      .map-row .from {
        padding-bottom: 20px;
        overflow-wrap: anywhere;
        color: var(--secondary-text-color);
      }
      ha-alert ul {
        margin: 4px 0 0;
        padding-left: 18px;
      }
      ha-alert,
      ha-select,
      ha-input {
        display: block;
        width: 100%;
      }
      .empty {
        color: rgba(255, 255, 255, 0.5);
        font-size: 13px;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-import-dialog": GmImportDialog;
  }
}
