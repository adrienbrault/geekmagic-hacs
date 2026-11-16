/**
 * Copying a view out of the panel: for an AI (with the entity data it
 * reads, minus pictures, tokens and locations), or as JSON by hand when the
 * browser won't copy.
 */
import type { Page } from "@playwright/test";
import { entityAttribute, expect, openPanel, test, ws, type View } from "./fixtures";

// Dev entities that really carry what an export must leave out
const CAMERA = "camera.geekmagic_dev_camera"; // access_token, entity_picture
const TRACKER = "device_tracker.demo_paulus"; // latitude, longitude, gps_accuracy
const STRIPPED = ["access_token", "entity_picture", "latitude", "longitude", "gps_accuracy"];

interface Export {
  version: number;
  integration_version: string;
  timezone: string;
  view: Record<string, unknown>;
  entities: Record<string, { state: string; attributes: Record<string, unknown> }>;
  templates: Record<string, Record<string, string>>;
}

async function cardMenu(page: Page, name: string, item: string): Promise<void> {
  const card = page.locator("ha-card.view-card", { hasText: name });
  await card.getByRole("button", { name: `${name} actions` }).click();
  await page.getByRole("menuitem", { name: item }).click();
}

test.describe("copying a view", () => {
  test("for AI: the data it reads, nothing private", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await openPanel(page);
    for (const attribute of ["access_token", "entity_picture"]) {
      expect(await entityAttribute(page, CAMERA, attribute)).toBeTruthy();
    }
    expect(await entityAttribute(page, TRACKER, "latitude")).toBeDefined();

    const name = `e2e export ${Date.now()}`;
    const widgets = [
      { slot: 0, type: "camera", entity_id: CAMERA },
      { slot: 1, type: "entity", entity_id: TRACKER },
      {
        slot: 2,
        type: "entity",
        entity_id: "sensor.dev_room_temperature",
        label: "{{ states('sensor.dev_room_temperature') }}",
      },
    ];
    const { view } = await ws<{ view: View }>(page, {
      type: "geekmagic/views/create",
      name,
      layout: "grid_2x2",
      theme: "standby",
      widgets,
    });
    try {
      await page.reload();
      await cardMenu(page, name, "Copy for AI (includes entity data)");
      const confirm = page.getByRole("dialog", { name: "Copy for AI?" });
      await expect(confirm).toBeVisible();
      await expect(page.locator("gm-dialog .export-entities li")).toHaveText([
        CAMERA,
        TRACKER,
        "sensor.dev_room_temperature",
      ]);
      await page.getByRole("button", { name: "Copy", exact: true }).click();
      await expect(confirm).toBeHidden();

      const copied = JSON.parse(await page.evaluate(() => navigator.clipboard.readText())) as Export;
      expect(copied.version).toBe(1);
      expect(copied.integration_version).toMatch(/^\d+\.\d+\.\d+/);
      expect(copied.timezone).toBeTruthy();
      expect(copied.view).toEqual({ name, layout: "grid_2x2", theme: "standby", widgets });
      expect(Object.keys(copied.entities).sort()).toEqual(
        [CAMERA, TRACKER, "sensor.dev_room_temperature"].sort()
      );
      for (const entity of Object.values(copied.entities)) {
        for (const attribute of STRIPPED) expect(entity.attributes).not.toHaveProperty(attribute);
        expect(entity).not.toHaveProperty("picture");
      }
      expect(Object.keys(copied.templates["2"])).toEqual([widgets[2].label]);
    } finally {
      await ws(page, { type: "geekmagic/views/delete", view_id: view.id });
    }
  });

  test("as JSON, by hand when the browser won't copy", async ({ page, view }) => {
    // Plain-http Home Assistant: no navigator.clipboard
    await page.addInitScript(() => {
      Object.defineProperty(Navigator.prototype, "clipboard", { get: () => undefined });
    });
    await openPanel(page);
    await cardMenu(page, view.name, "Copy view JSON");

    const text = page.locator("textarea.manual-copy");
    await expect(text).toBeVisible();
    const copied = JSON.parse(await text.inputValue()) as Record<string, unknown>;
    expect(copied).toEqual({
      name: view.name,
      layout: view.layout,
      theme: view.theme,
      widgets: view.widgets,
    });
    await page.getByRole("button", { name: "Done" }).click();
    await expect(text).toBeHidden();
  });
});
