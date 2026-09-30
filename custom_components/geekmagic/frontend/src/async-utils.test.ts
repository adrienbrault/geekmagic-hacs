import { describe, it, expect } from "vitest";
import { RequestSequence, SerialQueue, errorMessage } from "./async-utils";

describe("RequestSequence", () => {
  it("only the latest token is current", () => {
    const seq = new RequestSequence();
    const first = seq.next();
    expect(seq.isCurrent(first)).toBe(true);
    const second = seq.next();
    expect(seq.isCurrent(first)).toBe(false);
    expect(seq.isCurrent(second)).toBe(true);
  });

  it("drops a slow older response that resolves after a newer one", async () => {
    const seq = new RequestSequence();
    const shown: string[] = [];
    const render = async (label: string, delay: number) => {
      const token = seq.next();
      await new Promise((r) => setTimeout(r, delay));
      if (seq.isCurrent(token)) shown.push(label);
    };
    await Promise.all([render("old", 20), render("new", 1)]);
    expect(shown).toEqual(["new"]);
  });

  it("cancel invalidates in-flight tokens", () => {
    const seq = new RequestSequence();
    const token = seq.next();
    seq.cancel();
    expect(seq.isCurrent(token)).toBe(false);
  });
});

describe("SerialQueue", () => {
  it("runs tasks one at a time in submission order", async () => {
    const queue = new SerialQueue();
    const log: string[] = [];
    const task = (label: string, delay: number) => () =>
      new Promise<string>((resolve) => {
        log.push(`start ${label}`);
        setTimeout(() => {
          log.push(`end ${label}`);
          resolve(label);
        }, delay);
      });
    const results = await Promise.all([
      queue.run(task("a", 20)),
      queue.run(task("b", 1)),
    ]);
    expect(results).toEqual(["a", "b"]);
    expect(log).toEqual(["start a", "end a", "start b", "end b"]);
  });

  it("keeps going after a failed task", async () => {
    const queue = new SerialQueue();
    const failed = queue.run(() => Promise.reject(new Error("nope")));
    const next = queue.run(() => Promise.resolve("ok"));
    await expect(failed).rejects.toThrow("nope");
    await expect(next).resolves.toBe("ok");
  });
});

describe("errorMessage", () => {
  it("reads HA websocket errors", () => {
    expect(errorMessage({ code: "render_error", message: "boom" })).toBe("boom");
  });

  it("reads Error instances and strings", () => {
    expect(errorMessage(new Error("bad"))).toBe("bad");
    expect(errorMessage("plain")).toBe("plain");
  });

  it("falls back for anything else", () => {
    expect(errorMessage(undefined)).toBe("Unknown error");
    expect(errorMessage({ code: "x" })).toBe("Unknown error");
  });
});
