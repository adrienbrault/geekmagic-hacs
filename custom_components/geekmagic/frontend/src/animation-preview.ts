/**
 * What the view editor says about playing an animated view.
 *
 * The preview plays an animation whenever asked; a display only does when
 * its Animations switch is on. Otherwise it shows the animation's first
 * frame, so the editor names the displays that would.
 */
import { errorMessage } from "./preview-queue";
import type { DeviceConfig, HomeAssistant, PreviewResponse, ViewConfig } from "./types";

/** Names of the displays showing ``viewId`` with their Animations switch off. */
export function animationsOffOn(
  devices: DeviceConfig[],
  viewId: string,
  states: HomeAssistant["states"]
): string[] {
  return devices
    .filter((device) => device.assigned_views.includes(viewId))
    .filter((device) => {
      const switchId = device.entities?.animations;
      return switchId !== undefined && states[switchId]?.state === "off";
    })
    .map((device) => device.name);
}

/** What a screen reader hears about the animation (the badge shows it). */
export function animationStatus(loading: boolean, animated: boolean): string {
  if (loading) return "Rendering the animation…";
  return animated ? "Playing the animation." : "";
}

/** The render input of a draft: equal keys render the same frame. */
export const renderKey = (view: Pick<ViewConfig, "layout" | "theme" | "widgets">): string =>
  JSON.stringify([view.layout, view.theme, view.widgets]);

/**
 * Worth keeping: a GIF, or an over-budget answer (its still and warning are
 * as definitive). A frame that failed to render may work next time.
 */
export const cacheable = (result: PreviewResponse): boolean =>
  result.animated || result.too_large;

/**
 * The last few rendered animations, by render key, so toggling one back on
 * (or undoing an edit) shows it without another render. Entries expire:
 * live content in a GIF (a clock, a reading) goes stale.
 */
export class AnimationCache<T> {
  private entries = new Map<string, { value: T; at: number }>();

  constructor(
    private readonly max = 4,
    private readonly ttlMs = 120_000,
    private readonly now: () => number = Date.now
  ) {}

  get(key: string): T | undefined {
    const entry = this.entries.get(key);
    if (!entry) return undefined;
    if (this.now() - entry.at > this.ttlMs) {
      this.entries.delete(key);
      return undefined;
    }
    return entry.value;
  }

  set(key: string, value: T): void {
    this.entries.delete(key); // re-inserted as the newest
    this.entries.set(key, { value, at: this.now() });
    while (this.entries.size > this.max) {
      const oldest = this.entries.keys().next().value as string;
      this.entries.delete(oldest);
    }
  }

  clear(): void {
    this.entries.clear();
  }
}

export interface AutoplayState<Res> {
  /** The animated render of the current draft (a GIF, or an over-budget still). */
  result: Res | null;
  loading: boolean;
  error: string | null;
}

interface AutoplayOptions<Draft, Res> {
  fetch: (draft: Draft) => Promise<Res>;
  onChange: (state: AutoplayState<Res>) => void;
  key: (draft: Draft) => string;
  cache: AnimationCache<Res>;
  keep: (result: Res) => boolean;
  /** How long a draft must stay unchanged before it is rendered. */
  delay?: number;
}

/**
 * Plays a draft's animation without being asked.
 *
 * The still always shows first. Once the still says the draft can animate
 * and the draft has stayed unchanged for ``delay``, the animation renders:
 * one render at a time, a result for a draft that has since changed is
 * dropped (cached, though), and at most one more render waits behind it,
 * for the latest draft. A draft rendered recently plays from the cache at
 * once.
 */
export class Autoplay<Draft, Res> {
  private draft: Draft | null = null;
  /** The still of the current draft has said whether it can animate. */
  private animatable: boolean | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private inFlight = false;
  private wanted = false;
  private disposed = false;
  private state: AutoplayState<Res>;

  constructor(private readonly opts: AutoplayOptions<Draft, Res>) {
    this.state = { result: null, loading: false, error: null };
  }

  /** The draft changed: show its still, play it once it settles. */
  edit(draft: Draft): void {
    if (this.draft !== null && this.opts.key(draft) === this.opts.key(this.draft)) return;
    this.draft = draft;
    this.animatable = null;
    clearTimeout(this.timer);
    this.timer = undefined;
    const cached = this.opts.cache.get(this.opts.key(draft));
    if (cached !== undefined) {
      this.set({ result: cached, error: null });
      return;
    }
    this.set({ result: null, error: null });
    this.timer = setTimeout(() => {
      this.timer = undefined;
      this.run();
    }, this.opts.delay ?? 1000);
  }

  /** The current draft's still arrived: does it have anything to play? */
  still(animatable: boolean): void {
    this.animatable = animatable;
    if (this.timer === undefined) this.run();
  }

  /** Render the current draft again now (after a failure). */
  retry(): void {
    this.run();
  }

  dispose(): void {
    clearTimeout(this.timer);
    this.disposed = true;
  }

  private run(): void {
    const draft = this.draft;
    if (draft === null || !this.animatable || this.state.result !== null) return;
    const key = this.opts.key(draft);
    const cached = this.opts.cache.get(key);
    if (cached !== undefined) {
      this.set({ result: cached, loading: false, error: null });
      return;
    }
    if (this.inFlight) {
      this.wanted = true; // one render waits, for whatever the draft is then
      return;
    }
    this.inFlight = true;
    this.set({ loading: true, error: null });
    this.opts.fetch(draft).then(
      (result) => {
        if (this.opts.keep(result)) this.opts.cache.set(key, result);
        this.settle(key, { result });
      },
      (err: unknown) => this.settle(key, { error: errorMessage(err) })
    );
  }

  private settle(key: string, outcome: Partial<AutoplayState<Res>>): void {
    this.inFlight = false;
    if (this.disposed) return;
    const current = this.draft !== null && this.opts.key(this.draft) === key;
    this.set({ loading: false, ...(current ? outcome : {}) });
    if (this.wanted) {
      this.wanted = false;
      this.run();
    }
  }

  private set(next: Partial<AutoplayState<Res>>): void {
    this.state = { ...this.state, ...next };
    this.opts.onChange(this.state);
  }
}
