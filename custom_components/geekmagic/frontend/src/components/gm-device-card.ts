/**
 * One display: its live screen, what it shows, its controls, and its
 * rotation (the ordered views it cycles through) as a filmstrip.
 *
 * Controls go through the device's own entities (resolved by the backend),
 * so automations and this card always agree. Rotation edits send the whole
 * ordered list; the card shows them at once and rolls back on failure.
 * Fires ``devices-changed`` after any change and ``edit-view`` (view id).
 *
 * A display whose config entry isn't loaded (Home Assistant can't reach it,
 * it's disabled, its setup failed) has no live screen or controls: the card
 * says why instead, and its rotation stays editable (saved to the entry,
 * applied once it loads) but can't show a view now.
 */
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { DeviceConfig, HomeAssistant, ViewConfig } from "../types";
import type { GeekMagicApi } from "../api";
import { errorMessage } from "../preview-queue";
import { addViews, moveItem, moveTo, neighbour, removeView } from "../rotation";
import { formatSeconds, imageEntityUrl, intervalChoices, plural } from "../format";
import { resolveSelectedValue } from "../select-compat";
import { deviceStatus, type DeviceStatus } from "../device-status";
import { mdi, shared } from "../styles";
import "./gm-dialog";
import "./gm-menu";
import "./gm-screen";

@customElement("gm-device-card")
export class GmDeviceCard extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) api!: GeekMagicApi;
  @property({ attribute: false }) device!: DeviceConfig;
  @property({ attribute: false }) views: ViewConfig[] = [];
  @property({ attribute: false }) thumbs = new Map<string, string>();
  @property({ type: Boolean }) narrow = false;

  /** Rotation as shown (optimistic), until the backend confirms it. */
  @state() private _rotation: string[] = [];
  @state() private _addOpen = false;
  @state() private _adding = new Set<string>();
  @state() private _brightness: number | null = null;

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("device")) this._rotation = [...this.device.assigned_views];
  }

  // ---- entity helpers --------------------------------------------------------

  private _state(key: keyof NonNullable<DeviceConfig["entities"]>) {
    const id = this.device.entities?.[key];
    return id ? this.hass.states[id] : undefined;
  }

  private _notify(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true })
    );
  }

  private _changed(): void {
    this.dispatchEvent(new CustomEvent("devices-changed", { bubbles: true, composed: true }));
  }

  private async _service(domain: string, service: string, data: Record<string, unknown>, what: string) {
    try {
      await this.api.callService(domain, service, data);
    } catch (err) {
      this._notify(`Couldn't ${what}: ${errorMessage(err)}`);
    }
    this._changed();
  }

  // ---- actions -------------------------------------------------------------------

  private async _show(viewId: string | null): Promise<void> {
    if (!viewId) return;
    try {
      await this.api.showView(this.device.entry_id, viewId);
    } catch (err) {
      this._notify(`Couldn't show that view: ${errorMessage(err)}`);
    }
    this._changed();
  }

  private async _setRotation(next: string[], what: string): Promise<void> {
    const before = this._rotation;
    this._rotation = next;
    try {
      await this.api.assignViews(this.device.entry_id, next);
    } catch (err) {
      this._rotation = before;
      this._notify(`Couldn't ${what}: ${errorMessage(err)}`);
    }
    this._changed();
  }

  private _thumbAction(viewId: string, index: number, action: string): void {
    switch (action) {
      case "show":
        void this._show(viewId);
        break;
      case "edit":
        this.dispatchEvent(new CustomEvent("edit-view", { detail: viewId, bubbles: true, composed: true }));
        break;
      case "earlier":
        void this._setRotation(moveItem(this._rotation, index, -1), "reorder the rotation");
        break;
      case "later":
        void this._setRotation(moveItem(this._rotation, index, 1), "reorder the rotation");
        break;
      case "remove":
        void this._setRotation(removeView(this._rotation, viewId), "remove the view");
        break;
    }
  }

  // ---- render --------------------------------------------------------------------

  render() {
    const device = this.device;
    const status = deviceStatus(device);
    const preview = this._state("preview");
    const active = this._state("active");
    const paused = active?.state === "off";
    const builtin = device.display_mode === "builtin";
    const src =
      preview && preview.state !== "unavailable"
        ? imageEntityUrl(preview.attributes.entity_picture as string | undefined, preview.state)
        : null;
    const resolved = src && this.hass.hassUrl ? this.hass.hassUrl(src) : src;
    const current = this.views.find((v) => v.id === device.current_view_id);

    return html`
      <ha-card outlined>
        <div class="top ${this.narrow ? "narrow" : ""}">
          <gm-screen
            .src=${resolved}
            .size=${this.narrow ? 200 : 184}
            alt="${device.name}'s screen"
            ?dim=${!device.online || paused}
          >
            <div slot="empty" class="screen-empty">
              ${device.online
                ? html`<ha-spinner size="s"></ha-spinner><span>Waiting for the first frame</span>`
                : html`<ha-icon icon=${status.kind === "disabled" ? "mdi:monitor-off" : "mdi:lan-disconnect"}></ha-icon
                    ><span>${status.label}</span>`}
            </div>
            ${paused
              ? html`<div class="screen-badge"><ha-icon icon="mdi:pause"></ha-icon></div>`
              : nothing}
          </gm-screen>
          <div class="info">
            <div class="name-row">
              <h2 class="ellipsis">${device.name}</h2>
              <span class="status ${status.kind}">
                <span class="led"></span>${status.label}
              </span>
            </div>
            <a class="host" href="http://${device.host}" target="_blank" rel="noopener noreferrer">${device.host}</a>

            ${!status.live
              ? this._renderNotLoaded(status)
              : !device.online
              ? html`<ha-alert alert-type="warning">Can't reach the display at ${device.host}.</ha-alert>`
              : paused
                ? html`<div class="now">
                    <span class="now-label">Paused</span>
                    <ha-button size="s" appearance="filled" @click=${() =>
                      this._service("switch", "turn_on", { entity_id: active!.entity_id }, "resume")}>Resume</ha-button>
                  </div>`
                : builtin
                  ? html`<div class="now">
                      <ha-icon icon="mdi:television-classic"></ha-icon>
                      <span class="now-label">Built-in: <strong>${device.builtin_mode ?? "firmware screen"}</strong></span>
                      ${this._rotation.length
                        ? html`<ha-button size="s" appearance="filled" @click=${() => this._show(this._rotation[0])}>Show my views</ha-button>`
                        : nothing}
                    </div>`
                  : html`<div class="now">
                      <span class="now-label">Now showing</span>
                      <strong class="ellipsis now-view">${current?.name ?? (this._rotation.length ? "—" : "Welcome screen")}</strong>
                      ${this._rotation.length > 1
                        ? html`<span class="stepper">
                            <ha-icon-button .path=${mdi.prev} label="Previous view" @click=${() =>
                              this._show(neighbour(this._rotation, device.current_view_id ?? null, -1))}></ha-icon-button>
                            <ha-icon-button .path=${mdi.next} label="Next view" @click=${() =>
                              this._show(neighbour(this._rotation, device.current_view_id ?? null, 1))}></ha-icon-button>
                          </span>`
                        : nothing}
                    </div>`}
            ${status.live ? this._renderControls(!device.online) : nothing}
          </div>
        </div>
        ${this._renderRotation(status.live)}
      </ha-card>
      ${this._addOpen ? this._renderAddDialog() : nothing}
    `;
  }

  private _renderNotLoaded(status: DeviceStatus) {
    const reason = this.device.reason;
    return html`<ha-alert class="not-loaded" alert-type=${status.alert ?? "warning"} title=${status.title ?? ""}>
      ${reason ? html`<div class="reason">${reason}</div>` : nothing}
      ${status.hint ? html`<div>${status.hint}</div>` : nothing}
    </ha-alert>`;
  }

  private _renderControls(disabled: boolean) {
    const brightness = this._state("brightness");
    const cycling = this._state("view_cycling");
    const interval = this._state("cycle_interval");
    const value = this._brightness ?? Number(brightness?.state ?? NaN);
    const seconds = Number(interval?.state ?? NaN);
    const choices = intervalChoices(Number.isFinite(seconds) ? seconds : 30);
    return html`<div class="controls">
      ${brightness && Number.isFinite(value)
        ? html`<div class="control">
            <ha-icon icon="mdi:brightness-6" title="Brightness"></ha-icon>
            <ha-slider
              class="grow"
              min="0"
              max="100"
              step="1"
              .value=${value}
              ?disabled=${disabled}
              aria-label="Brightness"
              @input=${(e: Event) => (this._brightness = Number((e.target as HTMLInputElement).value))}
              @change=${async (e: Event) => {
                const next = Number((e.target as HTMLInputElement).value);
                await this._service("number", "set_value", { entity_id: brightness.entity_id, value: next }, "set the brightness");
                this._brightness = null;
              }}
            ></ha-slider>
            <span class="value">${Math.round(value)}%</span>
          </div>`
        : nothing}
      ${cycling && this._rotation.length > 1
        ? html`<div class="control">
            <ha-icon icon="mdi:rotate-right" title="Rotate views"></ha-icon>
            <label class="grow switch-label" for="cycle-${this.device.entry_id}">Rotate views</label>
            ${cycling.state === "on" && interval && Number.isFinite(seconds)
              ? html`<ha-select
                  class="interval"
                  label="Every"
                  .value=${String(seconds)}
                  .options=${choices.map((c) => ({ value: String(c.value), label: c.label }))}
                  ?disabled=${disabled}
                  @selected=${(e: CustomEvent) => {
                    const picked = resolveSelectedValue(e.detail, choices.map((c) => String(c.value)));
                    if (picked && Number(picked) !== seconds) {
                      void this._service("number", "set_value", { entity_id: interval.entity_id, value: Number(picked) }, "change the interval");
                    }
                  }}
                  @closed=${(e: Event) => e.stopPropagation()}
                >
                  ${choices.map((c) => html`<mwc-list-item value=${String(c.value)}>${c.label}</mwc-list-item>`)}
                </ha-select>`
              : nothing}
            <ha-switch
              id="cycle-${this.device.entry_id}"
              .checked=${cycling.state === "on"}
              ?disabled=${disabled}
              @change=${(e: Event) =>
                this._service("switch", (e.target as HTMLInputElement).checked ? "turn_on" : "turn_off", { entity_id: cycling.entity_id }, "change rotation")}
            ></ha-switch>
          </div>`
        : nothing}
    </div>`;
  }

  /** ``live``: the display runs, so a view can be shown now. */
  private _renderRotation(live: boolean) {
    const byId = new Map(this.views.map((v) => [v.id, v]));
    const rotation = this._rotation.filter((id) => byId.has(id));
    const cycling = this._state("view_cycling")?.state === "on";
    const unassigned = this.views.filter((v) => !this._rotation.includes(v.id));
    const onScreen = this.device.display_mode === "builtin" ? null : this.device.current_view_id;
    return html`<div class="rotation">
      <div class="rotation-head">
        <span class="caption">Rotation</span>
        <span class="muted">${plural(rotation.length, "view")}</span>
        ${!live
          ? html`<span class="muted hint">Changes apply once the display is back.</span>`
          : rotation.length > 1 && !cycling
          ? html`<span class="muted hint">Rotation is off: tap a view to show it.</span>`
          : rotation.length > 1
            ? html`<span class="muted hint">Every ${formatSeconds(Number(this._state("cycle_interval")?.state ?? 0))}</span>`
            : nothing}
      </div>
      <div class="strip-row">
        <ha-sortable
          draggable-selector=".thumb"
          .disabled=${this.narrow}
          @item-moved=${(e: CustomEvent<{ oldIndex: number; newIndex: number }>) => {
            e.stopPropagation();
            // Indices are positions in the strip, which skips ids of views
            // that no longer exist: reorder that list.
            void this._setRotation(moveTo(rotation, e.detail.oldIndex, e.detail.newIndex), "reorder the rotation");
          }}
        >
          <div class="strip" role="list">
            ${rotation.map((id, index) => {
              const view = byId.get(id)!;
              const current = id === onScreen;
              return html`<div class="thumb ${current ? "current" : ""}" role="listitem" data-view-id=${id}>
                <button
                  class="reset thumb-button focus-ring"
                  aria-current=${current ? "true" : "false"}
                  aria-label=${live ? `Show ${view.name} now` : view.name}
                  title=${current ? `${view.name} (on screen)` : live ? `Show ${view.name} now` : view.name}
                  aria-disabled=${live ? "false" : "true"}
                  @click=${() => live && this._show(id)}
                >
                  ${this.thumbs.get(id)
                    ? html`<img src=${this.thumbs.get(id)!} alt="" draggable="false" />`
                    : html`<span class="skeleton"></span>`}
                  <span class="thumb-name ellipsis">${view.name}</span>
                </button>
                <gm-menu
                  class="thumb-menu"
                  label="${view.name} actions"
                  .items=${[
                    { key: "show", label: "Show now", icon: "mdi:monitor-eye", disabled: current || !live },
                    { key: "edit", label: "Edit view", icon: "mdi:pencil" },
                    { key: "earlier", label: "Move earlier", icon: "mdi:arrow-left", disabled: index === 0 },
                    { key: "later", label: "Move later", icon: "mdi:arrow-right", disabled: index === rotation.length - 1 },
                    { key: "remove", label: "Remove from rotation", icon: "mdi:playlist-remove", danger: true },
                  ]}
                  @action=${(e: CustomEvent<string>) => this._thumbAction(id, this._rotation.indexOf(id), e.detail)}
                ></gm-menu>
              </div>`;
            })}
          </div>
        </ha-sortable>
        ${unassigned.length || !rotation.length
          ? html`<button
              class="reset add-thumb focus-ring ${rotation.length ? "" : "wide"}"
              @click=${() => {
                this._adding = new Set();
                this._addOpen = true;
              }}
              ?disabled=${!unassigned.length}
            >
              <ha-svg-icon .path=${mdi.plus}></ha-svg-icon>
              <span>${rotation.length ? "Add" : "Add views to show on this display"}</span>
              ${rotation.length ? nothing : html`<span class="muted">Until then it shows the welcome screen.</span>`}
            </button>`
          : nothing}
      </div>
    </div>`;
  }

  private _renderAddDialog() {
    const candidates = this.views.filter((v) => !this._rotation.includes(v.id));
    const toggle = (id: string) => {
      const next = new Set(this._adding);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      this._adding = next;
    };
    return html`<gm-dialog open heading="Add to ${this.device.name}" @cancel=${() => (this._addOpen = false)}>
      <div class="pick-grid">
        ${candidates.map(
          (view) => html`<label class="pick ${this._adding.has(view.id) ? "on" : ""}">
            <input type="checkbox" .checked=${this._adding.has(view.id)} @change=${() => toggle(view.id)} />
            ${this.thumbs.get(view.id)
              ? html`<img src=${this.thumbs.get(view.id)!} alt="" />`
              : html`<span class="skeleton"></span>`}
            <span class="ellipsis">${view.name}</span>
          </label>`
        )}
      </div>
      <ha-button slot="actions" appearance="plain" @click=${() => (this._addOpen = false)}>Cancel</ha-button>
      <ha-button
        slot="actions"
        variant="brand"
        appearance="accent"
        ?disabled=${!this._adding.size}
        @click=${() => {
          this._addOpen = false;
          const ids = candidates.filter((v) => this._adding.has(v.id)).map((v) => v.id);
          void this._setRotation(addViews(this._rotation, ids), "add the views");
        }}
        >Add ${this._adding.size ? plural(this._adding.size, "view") : ""}</ha-button
      >
    </gm-dialog>`;
  }

  static styles = [
    shared,
    css`
      :host {
        display: block;
        min-width: 0;
      }
      ha-card {
        overflow: hidden;
      }
      .top {
        display: flex;
        gap: 24px;
        padding: 20px;
        align-items: flex-start;
      }
      .top.narrow {
        flex-direction: column;
        align-items: center;
        padding: 16px;
        gap: 16px;
      }
      .info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
      }
      .name-row {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      h2 {
        font-size: 22px;
        font-weight: 400;
        line-height: 28px;
        min-width: 0;
      }
      .status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .led {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--disabled-text-color);
      }
      .online .led {
        background: var(--success-color, #43a047);
        box-shadow: 0 0 0 3px rgba(67, 160, 71, 0.18);
      }
      .retrying .led,
      .starting .led {
        background: var(--warning-color, #ffa600);
      }
      .failed .led {
        background: var(--error-color, #db4437);
      }
      .not-loaded .reason {
        margin-bottom: 4px;
        font-size: 12px;
        line-height: 16px;
        overflow-wrap: anywhere;
        color: var(--secondary-text-color);
      }
      .host {
        margin-top: -8px;
        font-size: 13px;
        color: var(--secondary-text-color);
        text-decoration: none;
        width: fit-content;
      }
      .host:hover {
        text-decoration: underline;
      }
      .now {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 48px;
        padding: 4px 4px 4px 14px;
        border-radius: 12px;
        background: var(--secondary-background-color);
        font-size: 14px;
      }
      .now-label {
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .now-view {
        flex: 1;
        min-width: 0;
        font-weight: 500;
      }
      .now > ha-button {
        margin-left: auto;
      }
      .stepper {
        display: flex;
        margin-left: auto;
      }
      .controls {
        display: flex;
        flex-direction: column;
      }
      .control {
        display: flex;
        align-items: center;
        gap: 12px;
        min-height: 52px;
        padding-left: 14px;
        color: var(--secondary-text-color);
      }
      .control + .control {
        border-top: 1px solid var(--divider-color);
      }
      .control ha-icon {
        flex: none;
      }
      .value {
        width: 44px;
        text-align: right;
        font-variant-numeric: tabular-nums;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .switch-label {
        color: var(--primary-text-color);
        font-size: 14px;
        cursor: pointer;
      }
      .interval {
        width: 120px;
      }
      .screen-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      .screen-badge {
        position: absolute;
        right: 8px;
        bottom: 8px;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.7);
        color: #fff;
      }
      .rotation {
        border-top: 1px solid var(--divider-color);
        padding: 14px 20px 18px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .rotation-head {
        display: flex;
        align-items: baseline;
        column-gap: 12px;
        row-gap: 2px;
        flex-wrap: wrap;
        font-size: 13px;
      }
      .caption {
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .strip-row {
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding: 4px 2px 6px;
        scrollbar-width: thin;
      }
      ha-sortable {
        display: contents;
      }
      .strip {
        display: flex;
        gap: 12px;
      }
      .thumb {
        position: relative;
        flex: none;
        width: 92px;
      }
      .thumb-button {
        display: flex;
        flex-direction: column;
        gap: 6px;
        width: 100%;
        border-radius: 10px;
      }
      .thumb img,
      .thumb .skeleton {
        display: block;
        width: 92px;
        height: 92px;
        border-radius: 10px;
        background-color: #000;
        box-shadow: 0 0 0 1px var(--divider-color);
        transition: box-shadow 0.15s, transform 0.15s;
      }
      .thumb-button:hover:not([aria-disabled="true"]) img {
        transform: translateY(-2px);
      }
      /* Not "disabled": a disabled button swallows the pointer events the
         sortable needs, and the rotation stays reorderable. */
      .thumb-button[aria-disabled="true"] {
        cursor: default;
      }
      .thumb.current img {
        box-shadow:
          0 0 0 2px var(--card-background-color),
          0 0 0 4px var(--primary-color);
      }
      .thumb-name {
        display: block;
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
        text-align: center;
      }
      .thumb.current .thumb-name {
        color: var(--primary-color);
        font-weight: 500;
      }
      .thumb-menu {
        position: absolute;
        top: 4px;
        right: 4px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.6);
        --mdc-icon-button-size: 32px;
        --mdc-icon-size: 18px;
        color: #fff;
        opacity: 0;
        transition: opacity 0.12s;
      }
      .thumb:hover .thumb-menu,
      .thumb:focus-within .thumb-menu,
      .narrow ~ .rotation .thumb-menu {
        opacity: 1;
      }
      @media (hover: none) {
        .thumb-menu {
          opacity: 1;
        }
      }
      .add-thumb {
        flex: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        width: 92px;
        height: 92px;
        border-radius: 10px;
        border: 2px dashed var(--divider-color);
        color: var(--secondary-text-color);
        font-size: 13px;
        --mdc-icon-size: 24px;
      }
      .add-thumb:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
      }
      .add-thumb.wide {
        width: 100%;
        height: auto;
        padding: 20px;
        text-align: center;
      }
      .add-thumb[disabled] {
        opacity: 0.5;
        cursor: default;
      }
      .pick-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
        gap: 12px;
        max-height: 50vh;
        overflow: auto;
        padding: 4px;
      }
      .pick {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 12px;
        color: var(--primary-text-color);
        cursor: pointer;
      }
      .pick img,
      .pick .skeleton {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 10px;
        background-color: #000;
        box-shadow: 0 0 0 1px var(--divider-color);
      }
      .pick.on img,
      .pick.on .skeleton {
        box-shadow: 0 0 0 3px var(--primary-color);
      }
      .pick input {
        position: absolute;
        top: 6px;
        left: 6px;
        width: 18px;
        height: 18px;
        accent-color: var(--primary-color);
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-device-card": GmDeviceCard;
  }
}
