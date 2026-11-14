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

/** The view before/after ``current`` in the rotation, wrapping around. */
export function neighbour(rotation: string[], current: string | null, delta: 1 | -1): string | null {
  if (rotation.length === 0) return null;
  const index = current ? rotation.indexOf(current) : -1;
  if (index < 0) return rotation[delta === 1 ? 0 : rotation.length - 1];
  return rotation[(index + delta + rotation.length) % rotation.length];
}
