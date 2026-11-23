/** A device's rotation (its ordered assigned views), as pure list edits. */

export function moveItem<T>(items: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (index < 0 || index >= items.length || target < 0 || target >= items.length) {
    return items;
  }
  const next = [...items];
  const [moved] = next.splice(index, 1);
  next.splice(target, 0, moved);
  return next;
}

/** Move the item at ``from`` to position ``to`` (drag and drop). */
export function moveTo<T>(items: T[], from: number, to: number): T[] {
  return moveItem(items, from, to - from);
}

export function addViews(rotation: string[], viewIds: string[]): string[] {
  return [...rotation, ...viewIds.filter((id) => !rotation.includes(id))];
}

export function removeView(rotation: string[], viewId: string): string[] {
  return rotation.filter((id) => id !== viewId);
}

/** The views View Cycling stops at: the rotation without the skipped ones. */
export function cycled(rotation: string[], skipped: readonly string[] = []): string[] {
  return rotation.filter((id) => !skipped.includes(id));
}

/**
 * The view before/after ``current`` in the rotation, wrapping around and
 * stepping over skipped views, as the device's next/previous do. From a
 * skipped view on screen it steps to the nearest cycled one. When no other
 * view cycles, ``current`` itself (or null without one).
 */
export function neighbour(
  rotation: string[],
  current: string | null,
  delta: 1 | -1,
  skipped: readonly string[] = []
): string | null {
  const stops = cycled(rotation, skipped);
  const index = current ? rotation.indexOf(current) : -1;
  if (index < 0) {
    const pool = stops.length ? stops : rotation;
    return pool.length ? pool[delta === 1 ? 0 : pool.length - 1] : null;
  }
  for (let step = 1; step < rotation.length; step++) {
    const id = rotation[(index + delta * step + rotation.length * step) % rotation.length];
    if (!skipped.includes(id)) return id;
  }
  return current;
}
