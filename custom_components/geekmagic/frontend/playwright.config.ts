/**
 * End-to-end tests against the local dev Home Assistant (scripts/dev-ha):
 * the real panel, the real backend and the fake device.
 *
 *   npm run e2e        starts (or reuses) the dev HA, then runs the tests
 */
import { defineConfig } from "@playwright/test";
import { haUrl } from "./e2e/dev-env";

export default defineConfig({
  testDir: "e2e",
  testMatch: "*.e2e.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // One Home Assistant and one fake device are shared by every test.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: haUrl(),
    viewport: { width: 1280, height: 900 },
    // A stuck action fails on its own line instead of eating the test timeout.
    actionTimeout: 15_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
