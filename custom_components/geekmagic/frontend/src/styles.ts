/** Styles shared by the panel's components (HA theme variables only). */
import { css } from "lit";

export const shared = css`
  :host {
    --gm-radius: var(--ha-card-border-radius, 12px);
    --gm-bezel: #121212;
    --gm-gap: 16px;
    --gm-muted: var(--secondary-text-color);
    --gm-tint: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }

  * {
    box-sizing: border-box;
  }

  h1,
  h2,
  h3,
  p {
    margin: 0;
  }

  .muted {
    color: var(--gm-muted);
  }

  .section-title {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 20px;
    font-weight: 400;
    line-height: 28px;
    color: var(--primary-text-color);
    margin: 0 0 12px;
  }

  .section-title .count {
    font-size: 14px;
    color: var(--gm-muted);
  }

  .icon-badge {
    --size: 40px;
    flex: none;
    width: var(--size);
    height: var(--size);
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    background: var(--badge-color, var(--primary-color));
    --mdc-icon-size: calc(var(--size) * 0.55);
  }

  .skeleton {
    background: linear-gradient(
      100deg,
      var(--secondary-background-color) 30%,
      var(--divider-color) 50%,
      var(--secondary-background-color) 70%
    );
    background-size: 300% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }

  @keyframes shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: 0 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
    }
  }

  /* Zero specificity: component classes restyle these freely. */
  :where(button.reset) {
    font: inherit;
    color: inherit;
    background: none;
    border: 0;
    padding: 0;
    margin: 0;
    cursor: pointer;
    text-align: inherit;
  }

  :where(button.reset):focus-visible,
  .focus-ring:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .grow {
    flex: 1;
    min-width: 0;
  }

  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

/** One colour per widget category, for the picker's icon badges. */
export const CATEGORY_COLORS: Record<string, string> = {
  values: "#0a84ff",
  home: "#30a14e",
  time: "#ff9f0a",
  history: "#8e5cf6",
  pictures: "#e0436b",
  custom: "#5f6b7a",
};

export const CATEGORY_TITLES: Record<string, string> = {
  values: "Values",
  home: "Home",
  time: "Time & weather",
  history: "History",
  pictures: "Pictures",
  custom: "Custom",
};

export const mdi = {
  back: "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z",
  dots: "M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",
  prev: "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  up: "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",
  down: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  delete: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
};
