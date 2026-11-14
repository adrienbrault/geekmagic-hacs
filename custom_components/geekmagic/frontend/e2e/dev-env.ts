/** Where scripts/dev-ha put the dev Home Assistant and the fake device. */
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../../..");
const PORTS_FILE = resolve(REPO_ROOT, "dev/.state/ports.env");

function ports(): Record<string, string> {
  if (!existsSync(PORTS_FILE)) return {};
  return Object.fromEntries(
    readFileSync(PORTS_FILE, "utf8")
      .split("\n")
      .filter((line) => line.includes("="))
      .map((line) => line.split("=", 2) as [string, string])
  );
}

export const haUrl = (): string =>
  process.env.HA_URL ?? `http://127.0.0.1:${ports().HA_PORT ?? "8123"}`;

export const fakeDeviceUrl = (): string =>
  process.env.FAKE_DEVICE_URL ?? `http://127.0.0.1:${ports().FAKE_PORT ?? "8124"}`;
