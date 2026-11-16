/**
 * Importing a view designed elsewhere (an AI, the offline renderer): paste
 * it, map the entity it reads that this Home Assistant lacks, save it.
 */
import { expect, openPanel, test, toast, ws, type View } from "./fixtures";

const DEMO_ID = "sensor.outdoor_temperature";
const HERE_ID = "sensor.dev_room_temperature";

test.describe("importing a view", () => {
  test("maps a missing entity everywhere and saves the view", async ({ page }) => {
    await openPanel(page);
    const name = `e2e import ${Date.now()}`;
    // As an AI answers: fenced, with demo-home entity ids
    const pasted = {
      name,
      layout: "grid_2x2",
      theme: "standby",
      widgets: [
        { type: "entity", slot: 0, entity_id: DEMO_ID, label: `{{ states('${DEMO_ID}') }}°` },
        { type: "clock", slot: 1 },
      ],
    };
    let saved: View | undefined;

    try {
      await page.getByRole("button", { name: "Import view" }).click();
      await expect(page.getByRole("dialog", { name: "Import a view" })).toBeVisible();
      // Slotted content isn't inside the <dialog> element: scope by the component
      const dialog = page.locator("gm-import-dialog");
      await dialog.locator("textarea").fill(`Here you go:\n\`\`\`json\n${JSON.stringify(pasted, null, 2)}\n\`\`\``);

      const row = dialog.locator(`.map-row[data-entity-id="${DEMO_ID}"]`);
      await expect(row).toBeVisible();
      await expect(dialog.locator("img.import-preview")).toBeVisible();
      await row.locator("ha-selector").click();
      // Type into the picker's own search box: stray keystrokes open HA's quick bar.
      await page.getByPlaceholder("Search", { exact: true }).fill("Dev Room Temperature");
      // The picker's virtualized list never settles for a click; Enter picks the match.
      await expect(page.locator("ha-combo-box-item", { hasText: "Dev Room Temperature" })).toBeVisible();
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Enter");

      const save = dialog.getByRole("button", { name: "Save as new view" });
      await expect(save).toBeEnabled();
      await save.click();
      await expect(toast(page, `Imported "${name}"`)).toBeVisible();
      await expect(page.locator("ha-card.view-card", { hasText: name })).toBeVisible();

      const { views } = await ws<{ views: View[] }>(page, { type: "geekmagic/views/list" });
      saved = views.find((v) => v.name === name);
      expect(saved).toMatchObject({
        layout: "grid_2x2",
        theme: "standby",
        widgets: [
          { type: "entity", slot: 0, entity_id: HERE_ID, label: `{{ states('${HERE_ID}') }}°` },
          { type: "clock", slot: 1 },
        ],
      });
    } finally {
      if (saved) await ws(page, { type: "geekmagic/views/delete", view_id: saved.id });
    }
  });
});
