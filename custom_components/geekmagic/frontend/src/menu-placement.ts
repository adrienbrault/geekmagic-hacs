/**
 * Where a fixed-position popover menu opens relative to its button.
 *
 * Below the button when it fits, else above it when that fits, else on the
 * roomier side with its height capped to that side (the menu scrolls).
 * Fixed-position, so it must stay inside the viewport: scrolling the page
 * can't bring an overflowing part into view.
 */

export interface MenuAnchor {
  top: number;
  bottom: number;
  right: number;
}

export interface MenuPlacement {
  /** Exactly one of top / bottom is set: the edge the menu hangs from. */
  top?: number;
  bottom?: number;
  right: number;
  maxHeight: number;
}

/** Gap kept between the menu and the viewport edges. */
export const MENU_MARGIN = 8;

export function placeMenu(
  anchor: MenuAnchor,
  menuHeight: number,
  viewport: { width: number; height: number },
  margin = MENU_MARGIN
): MenuPlacement {
  const right = Math.max(margin, viewport.width - anchor.right);
  const below = Math.max(0, viewport.height - anchor.bottom - margin);
  const above = Math.max(0, anchor.top - margin);
  if (menuHeight <= below || below >= above) {
    return { top: anchor.bottom, right, maxHeight: below };
  }
  return { bottom: viewport.height - anchor.top, right, maxHeight: above };
}
