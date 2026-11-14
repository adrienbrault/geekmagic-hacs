/**
 * Test fixtures: a logged-in panel page, Home Assistant API access through
 * that page's own connection, and a throwaway view per test.
 */
import { test as base, expect, type Page } from "@playwright/test";
import { fakeDeviceUrl } from "./dev-env";

export interface View {
  id: string;
  name: string;
  layout: string;
  theme: string;
  widgets: Record<string, unknown>[];
}

export interface Device {
  entry_id: string;
  name: string;
  assigned_views: string[];
}

export interface FakeDeviceState {
  image: string | null;
  frame_version: number;
  /** Frames received since the fake started (each refresh uploads one). */
  uploads: number;
  log: { path: string; status: number }[];
}

/** Call the Home Assistant websocket API as the logged-in panel user. */
export async function ws<T>(page: Page, message: Record<string, unknown>): Promise<T> {
  return page.evaluate(async (msg) => {
    const ha = document.querySelector("home-assistant") as unknown as {
      hass: { connection: { sendMessagePromise: (m: unknown) => Promise<unknown> } };
    };
    return ha.hass.connection.sendMessagePromise(msg);
  }, message) as Promise<T>;
}

export async function callService(
  page: Page,
  domain: string,
  service: string,
  data: Record<string, unknown>
): Promise<void> {
  await ws(page, { type: "call_service", domain, service, service_data: data });
}

export async function entityState(page: Page, entityId: string): Promise<string | undefined> {
  return page.evaluate((id) => {
    const ha = document.querySelector("home-assistant") as unknown as {
      hass: { states: Record<string, { state: string }> };
    };
    return ha.hass.states[id]?.state;
  }, entityId);
}

export async function entityAttribute(
  page: Page,
  entityId: string,
  attribute: string
): Promise<unknown> {
  return page.evaluate(
    ([id, attr]) => {
      const ha = document.querySelector("home-assistant") as unknown as {
        hass: { states: Record<string, { attributes: Record<string, unknown> }> };
      };
      return ha.hass.states[id]?.attributes[attr];
    },
    [entityId, attribute] as const
  );
}

export async function fakeDevice(): Promise<FakeDeviceState> {
  const response = await fetch(`${fakeDeviceUrl()}/_fake/state`);
  return (await response.json()) as FakeDeviceState;
}

export async function openPanel(page: Page): Promise<void> {
  await page.goto("/geekmagic");
  await expect(page.locator("ha-card.view-card").first()).toBeVisible();
}

export async function openEditor(page: Page, viewName: string): Promise<void> {
  await page.locator("ha-card.view-card", { hasText: viewName }).click();
  await expect(editorName(page)).toHaveValue(viewName);
}

export const editorName = (page: Page) => page.locator(".editor-header ha-input input");

export const slotLabel = (page: Page, slot: number) =>
  page.locator("ha-card.slot-card").nth(slot).locator("ha-input").first().locator("input");

/** A Home Assistant toast (its text is rendered twice, once for screen readers). */
export const toast = (page: Page, text: string) => page.getByText(text).first();

export const backButton = (page: Page) =>
  page.locator(".editor-header ha-icon-button").first();

export const saveButton = (page: Page) =>
  page.locator(".editor-header").getByRole("button", { name: /^Sav(e|ing)/ });

interface Fixtures {
  /** A fresh 2x2 view (clock + labelled entity), deleted after the test. */
  view: View;
}

export const test = base.extend<Fixtures>({
  view: async ({ page }, use, testInfo) => {
    await openPanel(page);
    const name = `e2e ${testInfo.title}`.slice(0, 60);
    const { view } = await ws<{ view: View }>(page, {
      type: "geekmagic/views/create",
      name,
      layout: "grid_2x2",
      theme: "watchos",
      widgets: [
        { slot: 0, type: "clock" },
        { slot: 1, type: "entity", entity_id: "sensor.dev_room_temperature", label: "Room" },
      ],
    });
    await page.reload();
    await expect(page.locator("ha-card.view-card", { hasText: name })).toBeVisible();

    await use(view);

    await ws(page, { type: "geekmagic/views/delete", view_id: view.id }).catch(() => undefined);
  },
});

export { expect };
