/**
 * Call back at the start of every minute (plus a small delay), so clocks in
 * re-rendered previews show the time the device shows.
 */

/** Milliseconds from ``now`` until ``offsetMs`` past the next whole minute. */
export function msUntilNextMinute(now: number, offsetMs = 1500): number {
  const sinceMinute = now % 60_000;
  const wait = 60_000 - sinceMinute + offsetMs;
  return wait > 60_000 ? wait - 60_000 : wait;
}

/** Run ``callback`` each minute until the returned function is called. */
export function everyMinute(callback: () => void, offsetMs = 1500): () => void {
  let timer: ReturnType<typeof setTimeout>;
  const schedule = () => {
    timer = setTimeout(() => {
      schedule();
      callback();
    }, msUntilNextMinute(Date.now(), offsetMs));
  };
  schedule();
  return () => clearTimeout(timer);
}
