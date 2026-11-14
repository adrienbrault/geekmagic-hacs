import { afterEach, describe, expect, it, vi } from "vitest";
import { everyMinute, msUntilNextMinute } from "./minute-timer";

describe("minute timer", () => {
  afterEach(() => vi.useRealTimers());

  it("waits until just past the next minute", () => {
    expect(msUntilNextMinute(0)).toBe(1_500);
    expect(msUntilNextMinute(10_000)).toBe(51_500);
    expect(msUntilNextMinute(59_000)).toBe(2_500);
    expect(msUntilNextMinute(1_000)).toBe(500); // still before :01.5
  });

  it("fires once a minute until stopped", () => {
    vi.useFakeTimers();
    vi.setSystemTime(30_000);
    const tick = vi.fn();
    const stop = everyMinute(tick);
    vi.advanceTimersByTime(31_400);
    expect(tick).not.toHaveBeenCalled();
    vi.advanceTimersByTime(200); // 01:01.6
    expect(tick).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(60_000);
    expect(tick).toHaveBeenCalledTimes(2);
    stop();
    vi.advanceTimersByTime(120_000);
    expect(tick).toHaveBeenCalledTimes(2);
  });
});
