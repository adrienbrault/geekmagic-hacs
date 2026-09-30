/**
 * Small async helpers for the panel's websocket calls.
 */

/**
 * Hands out increasing tokens so only the latest request may apply its
 * result: a slow older response (or its error / finally) must not
 * overwrite what a newer request is about to show.
 */
export class RequestSequence {
  private _latest = 0;

  /** Start a request, invalidating every earlier token. */
  next(): number {
    this._latest += 1;
    return this._latest;
  }

  /** Invalidate in-flight requests without starting a new one. */
  cancel(): void {
    this._latest += 1;
  }

  isCurrent(token: number): boolean {
    return token === this._latest;
  }
}

/**
 * Runs async tasks one at a time, in submission order. A failed task
 * does not block the ones queued after it.
 */
export class SerialQueue {
  private _tail: Promise<unknown> = Promise.resolve();

  run<T>(task: () => Promise<T>): Promise<T> {
    const result = this._tail.then(task);
    this._tail = result.catch(() => undefined);
    return result;
  }
}

/**
 * Human-readable message from a rejected websocket call. HA rejects
 * `sendMessagePromise` with `{ code, message }`, not an Error.
 */
export function errorMessage(err: unknown): string {
  if (typeof err === "string" && err) return err;
  if (err && typeof err === "object" && "message" in err) {
    const message = (err as { message: unknown }).message;
    if (typeof message === "string" && message) return message;
  }
  return "Unknown error";
}
