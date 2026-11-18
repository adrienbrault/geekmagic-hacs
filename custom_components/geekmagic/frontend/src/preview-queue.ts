/**
 * Latest-only preview requests.
 *
 * Edits fire faster than renders return, and renders can return out of
 * order. The queue debounces requests and only ever reports the result of
 * the newest one; on failure the last good image stays and the error is
 * reported alongside it.
 */

export interface PreviewState<T> {
  result: T | null;
  loading: boolean;
  error: string | null;
}

export class PreviewQueue<Req, Res> {
  private seq = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private state: PreviewState<Res> = { result: null, loading: false, error: null };

  constructor(
    private readonly fetch: (request: Req) => Promise<Res>,
    private readonly onChange: (state: PreviewState<Res>) => void,
    private readonly delay = 250
  ) {}

  /** Request a render after the debounce delay (cancels a pending one). */
  request(req: Req): void {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = undefined;
      void this.run(req);
    }, this.delay);
  }

  /** Render now, skipping the debounce. */
  now(req: Req): Promise<void> {
    clearTimeout(this.timer);
    this.timer = undefined;
    return this.run(req);
  }

  /**
   * Re-render in the background (live data moved on): no loading state, and
   * a failure keeps the current image silently. Skipped while a render is
   * due or running, which will be at least as fresh.
   */
  async refresh(req: Req): Promise<void> {
    if (this.timer !== undefined || this.state.loading) return;
    const mine = ++this.seq;
    try {
      const result = await this.fetch(req);
      if (mine === this.seq) this.set({ result, error: null });
    } catch {
      // Keep the current image; the next refresh or edit retries.
    }
  }

  dispose(): void {
    clearTimeout(this.timer);
    this.seq += 1; // in-flight results are dropped
  }

  private set(next: Partial<PreviewState<Res>>): void {
    this.state = { ...this.state, ...next };
    this.onChange(this.state);
  }

  private async run(req: Req): Promise<void> {
    const mine = ++this.seq;
    this.set({ loading: true });
    try {
      const result = await this.fetch(req);
      if (mine !== this.seq) return;
      this.set({ result, loading: false, error: null });
    } catch (err) {
      if (mine !== this.seq) return;
      this.set({ loading: false, error: errorMessage(err) });
    }
  }
}

/** A readable message from a websocket error ({code, message}) or anything else. */
export function errorMessage(err: unknown): string {
  if (err && typeof err === "object" && "message" in err) {
    return String((err as { message: unknown }).message);
  }
  return String(err);
}
