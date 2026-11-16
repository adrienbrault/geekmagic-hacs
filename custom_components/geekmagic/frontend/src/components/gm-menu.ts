/**
 * An overflow (⋮) menu: an icon button and a popover list of actions.
 *
 * Own element rather than ha-dropdown, whose API moved across HA releases.
 * Items are ``{label, action, danger?, disabled?}``; picking one fires
 * ``action`` with the item's key in ``detail``.
 */
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { type MenuPlacement, placeMenu } from "../menu-placement";
import { mdi } from "../styles";

export interface MenuItem {
  key: string;
  label: string;
  icon?: string;
  danger?: boolean;
  disabled?: boolean;
}

@customElement("gm-menu")
export class GmMenu extends LitElement {
  @property({ attribute: false }) items: MenuItem[] = [];
  @property() label = "More actions";
  @state() private _open = false;
  /**
   * Fixed position, so scroll containers can't clip the popover; placed
   * below or above the button, whichever keeps it on screen (placeMenu).
   */
  @state() private _at: MenuPlacement = { top: 0, right: 0, maxHeight: 0 };

  private _outside = (event: Event) => {
    if (!event.composedPath().includes(this)) this._open = false;
  };

  private _keys = (event: KeyboardEvent) => {
    if (event.key === "Escape") this._open = false;
  };

  connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener("click", this._outside, true);
    document.addEventListener("keydown", this._keys);
    window.addEventListener("resize", this._close);
    // Scroll events stop at shadow roots; wheel and touch moves don't.
    document.addEventListener("wheel", this._scrollAway, { passive: true, capture: true });
    document.addEventListener("touchmove", this._scrollAway, { passive: true, capture: true });
  }

  disconnectedCallback(): void {
    document.removeEventListener("click", this._outside, true);
    document.removeEventListener("keydown", this._keys);
    window.removeEventListener("resize", this._close);
    document.removeEventListener("wheel", this._scrollAway, true);
    document.removeEventListener("touchmove", this._scrollAway, true);
    super.disconnectedCallback();
  }

  protected updated(changed: Map<string, unknown>): void {
    if (changed.has("_open") && this._open) {
      // The menu's height is only known once it rendered: place it before
      // the browser paints it
      const menu = this.renderRoot.querySelector<HTMLElement>(".menu");
      if (menu) {
        const viewport = { width: window.innerWidth, height: window.innerHeight };
        this._at = placeMenu(this.getBoundingClientRect(), menu.scrollHeight, viewport);
      }
      this.renderRoot.querySelector<HTMLElement>("[role=menuitem]:not([disabled])")?.focus();
    }
  }

  private _toggle(event: Event): void {
    event.stopPropagation();
    this._open = !this._open;
  }

  private _menuStyle(): string {
    const { top, bottom, right, maxHeight } = this._at;
    const edge = bottom === undefined ? `top:${top}px` : `bottom:${bottom}px`;
    return `${edge};right:${right}px;max-height:${maxHeight}px`;
  }

  private _close = () => {
    this._open = false;
  };

  /** Scrolling the page (not the menu itself) would leave it floating. */
  private _scrollAway = (event: Event) => {
    if (this._open && !event.composedPath().some((el) => el instanceof HTMLElement && el.classList.contains("menu"))) {
      this._open = false;
    }
  };

  private _pick(event: Event, item: MenuItem): void {
    event.stopPropagation();
    if (item.disabled) return;
    this._open = false;
    this.dispatchEvent(new CustomEvent("action", { detail: item.key }));
  }

  render() {
    return html`
      <ha-icon-button
        .path=${mdi.dots}
        .label=${this.label}
        aria-haspopup="menu"
        aria-expanded=${this._open ? "true" : "false"}
        @click=${this._toggle}
      ></ha-icon-button>
      ${this._open
        ? html`<div
            class="menu"
            role="menu"
            style=${this._menuStyle()}
            @click=${(e: Event) => e.stopPropagation()}
          >
            ${this.items.map(
              (item) => html`<button
                role="menuitem"
                class=${item.danger ? "danger" : ""}
                ?disabled=${item.disabled}
                @click=${(e: Event) => this._pick(e, item)}
              >
                ${item.icon ? html`<ha-icon .icon=${item.icon}></ha-icon>` : nothing}
                <span>${item.label}</span>
              </button>`
            )}
          </div>`
        : nothing}
    `;
  }

  static styles = css`
    :host {
      position: relative;
      display: inline-block;
    }
    .menu {
      position: fixed;
      z-index: 10;
      overflow: auto;
      min-width: 200px;
      padding: 4px 0;
      border-radius: 12px;
      background: var(--card-background-color);
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.22);
      border: 1px solid var(--divider-color);
    }
    button {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      padding: 10px 16px;
      font: inherit;
      font-size: 14px;
      text-align: left;
      color: var(--primary-text-color);
      background: none;
      border: 0;
      cursor: pointer;
      --mdc-icon-size: 20px;
    }
    button:hover:not([disabled]),
    button:focus-visible {
      background: var(--secondary-background-color);
      outline: none;
    }
    button[disabled] {
      color: var(--disabled-text-color);
      cursor: default;
    }
    button.danger {
      color: var(--error-color);
    }
    ha-icon {
      color: var(--secondary-text-color);
    }
    button.danger ha-icon {
      color: inherit;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-menu": GmMenu;
  }
}
