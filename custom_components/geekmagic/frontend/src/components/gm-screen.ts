/**
 * The device's 240×240 screen in a restrained bezel.
 *
 * Shows an image (live entity picture or rendered preview) at ``size`` CSS
 * px; at 2× or more it scales with nearest-neighbour so the pixels the
 * device will show stay crisp. Children are laid over the screen (the
 * editor's click-to-select overlay).
 */
import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("gm-screen")
export class GmScreen extends LitElement {
  @property() src: string | null = null;
  @property() alt = "";
  @property({ type: Number }) size = 240;
  /** Class put on the <img> (e2e and screenshot tooling look for it). */
  @property({ attribute: "img-class" }) imgClass = "";
  @property({ type: Boolean, reflect: true }) busy = false;
  @property({ type: Boolean, reflect: true }) dim = false;

  render() {
    const pixelated = this.size >= 480;
    return html`
      <div class="bezel" style="--size: ${this.size}px">
        <div class="screen">
          ${this.src
            ? html`<img
                class=${this.imgClass}
                src=${this.src}
                alt=${this.alt}
                draggable="false"
                style=${pixelated ? "image-rendering: pixelated" : ""}
              />`
            : html`<div class="empty"><slot name="empty"></slot></div>`}
          <div class="overlay"><slot></slot></div>
          ${this.busy ? html`<div class="progress"></div>` : nothing}
        </div>
      </div>
    `;
  }

  static styles = css`
    :host {
      display: inline-block;
    }
    .bezel {
      --pad: max(6px, calc(var(--size) * 0.045));
      padding: var(--pad);
      border-radius: calc(var(--pad) * 1.15);
      background: var(--gm-bezel, #121212);
      box-shadow:
        0 0 0 1px var(--divider-color),
        0 1px 2px rgba(0, 0, 0, 0.2),
        0 8px 24px rgba(0, 0, 0, 0.12);
    }
    .screen {
      position: relative;
      width: var(--size);
      height: var(--size);
      overflow: hidden;
      border-radius: 2px;
      background: #000;
    }
    img {
      display: block;
      width: 100%;
      height: 100%;
      transition: opacity 0.2s;
    }
    :host([dim]) img {
      opacity: 0.45;
    }
    .empty {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px;
      text-align: center;
      color: rgba(255, 255, 255, 0.7);
      font-size: 13px;
    }
    .overlay {
      position: absolute;
      inset: 0;
    }
    .progress {
      position: absolute;
      left: 0;
      right: 0;
      top: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
      background-size: 50% 100%;
      background-repeat: no-repeat;
      animation: sweep 1s linear infinite;
      animation-delay: 0.4s;
      opacity: 0;
      animation-fill-mode: both;
    }
    @keyframes sweep {
      from {
        background-position: -50% 0;
        opacity: 1;
      }
      to {
        background-position: 150% 0;
        opacity: 1;
      }
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "gm-screen": GmScreen;
  }
}
