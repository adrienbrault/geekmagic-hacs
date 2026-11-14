/**
 * A modal dialog on the native <dialog> (focus trap, Esc, top layer).
 *
 * The heading is rendered in this element's own shadow root so the
 * accessible name resolves (aria-labelledby can't cross shadow roots).
 * Closing by Esc or backdrop fires ``cancel``; the owner decides.
 */
import { LitElement, css, html } from "lit";
import { customElement, property, query } from "lit/decorators.js";

@customElement("gm-dialog")
export class GmDialog extends LitElement {
  @property() heading = "";
  @property({ type: Boolean, reflect: true }) open = false;
  @query("dialog") private _dialog!: HTMLDialogElement;

  protected updated(changed: Map<string, unknown>): void {
    if (!changed.has("open")) return;
    if (this.open && !this._dialog.open) this._dialog.showModal();
    if (!this.open && this._dialog.open) this._dialog.close();
  }

  private _cancel(event: Event): void {
    event.preventDefault();
    this.dispatchEvent(new CustomEvent("cancel"));
  }

  private _backdrop(event: MouseEvent): void {
    if (event.target === this._dialog) this._cancel(event);
  }

  render() {
    return html`
      <dialog
        aria-labelledby="heading"
        @cancel=${this._cancel}
        @click=${this._backdrop}
      >
        <div class="surface">
          <h2 id="heading">${this.heading}</h2>
          <div class="body"><slot></slot></div>
          <div class="actions"><slot name="actions"></slot></div>
        </div>
      </dialog>
    `;
  }

  static styles = css`
    dialog {
      padding: 0;
      border: 0;
      border-radius: 28px;
      background: var(--ha-dialog-surface-background, var(--card-background-color));
      color: var(--primary-text-color);
      width: min(440px, calc(100vw - 32px));
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    }
    dialog::backdrop {
      background: rgba(0, 0, 0, 0.45);
    }
    .surface {
      padding: 24px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 22px;
      font-weight: 400;
      line-height: 28px;
    }
    .body {
      color: var(--secondary-text-color);
      font-size: 14px;
      line-height: 20px;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-dialog": GmDialog;
  }
}
