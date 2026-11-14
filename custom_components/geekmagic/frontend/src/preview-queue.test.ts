import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PreviewQueue, errorMessage, type PreviewState } from "./preview-queue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("PreviewQueue", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("debounces bursts into one render", async () => {
    const fetch = vi.fn(async (n: number) => `img${n}`);
    const states: PreviewState<string>[] = [];
    const queue = new PreviewQueue(fetch, (s) => states.push(s), 250);
    queue.request(1);
    queue.request(2);
    queue.request(3);
    await vi.advanceTimersByTimeAsync(300);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(3);
    expect(states.at(-1)).toEqual({ result: "img3", loading: false, error: null });
  });

  it("drops a slow response that a newer request overtook", async () => {
    const slow = deferred<string>();
    const fast = deferred<string>();
    const fetch = vi.fn().mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);
    const states: PreviewState<string>[] = [];
    const queue = new PreviewQueue<number, string>(fetch, (s) => states.push(s), 0);

    const first = queue.now(1);
    const second = queue.now(2);
    fast.resolve("new");
    await second;
    slow.resolve("old");
    await first;

    expect(states.at(-1)?.result).toBe("new");
    expect(states.some((s) => s.result === "old")).toBe(false);
  });

  it("keeps the last image when a render fails", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce("good")
      .mockRejectedValueOnce({ code: "render_error", message: "boom" });
    const states: PreviewState<string>[] = [];
    const queue = new PreviewQueue<number, string>(fetch, (s) => states.push(s), 0);
    await queue.now(1);
    await queue.now(2);
    expect(states.at(-1)).toEqual({ result: "good", loading: false, error: "boom" });
  });

  it("a success clears a previous error", async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new Error("x")).mockResolvedValueOnce("ok");
    const states: PreviewState<string>[] = [];
    const queue = new PreviewQueue<number, string>(fetch, (s) => states.push(s), 0);
    await queue.now(1);
    await queue.now(2);
    expect(states.at(-1)).toEqual({ result: "ok", loading: false, error: null });
  });

  it("dispose drops in-flight results", async () => {
    const pending = deferred<string>();
    const onChange = vi.fn();
    const queue = new PreviewQueue<number, string>(() => pending.promise, onChange, 0);
    const run = queue.now(1);
    queue.dispose();
    pending.resolve("late");
    await run;
    expect(onChange).toHaveBeenCalledTimes(1); // only the loading state
  });

  it("refreshes quietly: no loading state, and a failure keeps the image", async () => {
    const fetch = vi.fn<(n: number) => Promise<string>>();
    const states: PreviewState<string>[] = [];
    const queue = new PreviewQueue(fetch, (s) => states.push(s), 0);
    fetch.mockResolvedValueOnce("first");
    await queue.now(1);
    states.length = 0;

    fetch.mockResolvedValueOnce("fresher");
    await queue.refresh(1);
    expect(states).toEqual([{ result: "fresher", loading: false, error: null }]);

    fetch.mockRejectedValueOnce(new Error("offline"));
    await queue.refresh(1);
    expect(states).toHaveLength(1);
  });

  it("skips a refresh while an edit's render is due or running", async () => {
    const slow = deferred<string>();
    const fetch = vi.fn().mockReturnValueOnce(slow.promise);
    const queue = new PreviewQueue<number, string>(fetch, () => {}, 250);
    queue.request(1);
    await queue.refresh(0); // due: skipped
    await vi.advanceTimersByTimeAsync(300); // now running
    await queue.refresh(0); // running: skipped
    expect(fetch.mock.calls).toEqual([[1]]);
    slow.resolve("img");
  });
});

describe("errorMessage", () => {
  it("reads websocket errors and anything else", () => {
    expect(errorMessage({ code: "x", message: "Nope" })).toBe("Nope");
    expect(errorMessage(new Error("E"))).toBe("E");
    expect(errorMessage("plain")).toBe("plain");
  });
});
