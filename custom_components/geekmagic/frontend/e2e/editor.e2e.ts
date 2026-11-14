/**
 * The View Editor must never lose or silently fail to save work, and what
 * it saves must reach the device.
 */
import {
  backButton,
  callService,
  editorName,
  entityAttribute,
  entityState,
  expect,
  fakeDevice,
  openEditor,
  saveButton,
  slotLabel,
  test,
  toast,
  ws,
  type Device,
  type View,
} from "./fixtures";

test.describe("leaving the editor", () => {
  test("asks before discarding unsaved edits", async ({ page, view }) => {
    await openEditor(page, view.name);
    await slotLabel(page, 1).fill("Living room");

    await backButton(page).click();
    const dialog = page.getByRole("dialog", { name: "Discard unsaved changes?" });
    await expect(dialog).toBeVisible();

    await dialog.getByRole("button", { name: "Keep editing" }).click();
    await expect(dialog).toBeHidden();
    await expect(slotLabel(page, 1)).toHaveValue("Living room");

    await backButton(page).click();
    await dialog.getByRole("button", { name: "Discard" }).click();
    await expect(editorName(page)).toBeHidden();

    await openEditor(page, view.name);
    await expect(slotLabel(page, 1)).toHaveValue("Room");
  });

  test("leaves straight away when nothing changed", async ({ page, view }) => {
    await openEditor(page, view.name);
    await backButton(page).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(editorName(page)).toBeHidden();
  });

  test("opens at the top even when the list was scrolled", async ({ page, view }) => {
    const card = page.locator("ha-card.view-card", { hasText: view.name });
    await card.scrollIntoViewIfNeeded();
    await card.click();
    await expect(editorName(page)).toHaveValue(view.name);
    await expect(editorName(page)).toBeInViewport();
  });
});

test.describe("saving", () => {
  test("stays in the editor and confirms", async ({ page, view }) => {
    await openEditor(page, view.name);
    await slotLabel(page, 1).fill("Living room");
    await saveButton(page).click();

    await expect(toast(page, `Saved "${view.name}"`)).toBeVisible();
    await expect(editorName(page)).toBeVisible();

    const { view: stored } = await ws<{ view: View }>(page, {
      type: "geekmagic/views/get",
      view_id: view.id,
    });
    expect(stored.widgets.find((w) => w.slot === 1)?.label).toBe("Living room");

    // Saved, so nothing to discard on the way out.
    await backButton(page).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(editorName(page)).toBeHidden();
  });

  test("says so when the save fails, and keeps the edits", async ({ page, view }) => {
    await openEditor(page, view.name);
    await slotLabel(page, 1).fill("Living room");
    // Deleted elsewhere (another tab, another user) while being edited.
    await ws(page, { type: "geekmagic/views/delete", view_id: view.id });

    await saveButton(page).click();
    await expect(toast(page, `Couldn't save "${view.name}"`)).toBeVisible();
    await expect(editorName(page)).toBeVisible();
    await expect(slotLabel(page, 1)).toHaveValue("Living room");
  });
});

test.describe("a Status List built in the editor", () => {
  test("is saved in the panel's row shape and reaches the device", async ({ page, view }) => {
    const devices = await ws<{ devices: Device[] }>(page, { type: "geekmagic/devices/list" });
    const device = devices.devices[0];
    const originalViews = device.assigned_views;

    try {
      await openEditor(page, view.name);
      const slot = page.locator("ha-card.slot-card").nth(2);
      await slot.locator("ha-select").first().click();
      await page.getByRole("menuitem", { name: "Status List", exact: true }).click();
      await expect(slot.getByText("Add Status Entity")).toBeVisible();
      await slot.getByText("Add Status Entity").click();
      await slot.locator(".array-item-content ha-selector").first().click();
      // Type into the picker's own search box: stray keystrokes open HA's quick bar.
      const search = page.getByPlaceholder("Search", { exact: true });
      await search.fill("Bed Light");
      // The picker's virtualized list never settles for a click; Enter picks the match.
      await expect(page.locator("ha-combo-box-item", { hasText: "Bed Light" })).toBeVisible();
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Enter");
      await saveButton(page).click();
      await expect(toast(page, `Saved "${view.name}"`)).toBeVisible();

      const { view: stored } = await ws<{ view: View }>(page, {
        type: "geekmagic/views/get",
        view_id: view.id,
      });
      const statusList = stored.widgets.find((w) => w.slot === 2) as {
        options: { entities: { entity_id: string }[] };
      };
      expect(statusList.options.entities).toEqual([{ entity_id: "light.bed_light" }]);

      // Put it on the screen.
      await ws(page, {
        type: "geekmagic/devices/assign_views",
        entry_id: device.entry_id,
        view_ids: [...originalViews, view.id],
      });
      await expect
        .poll(() => entityAttribute(page, "select.fake_display_display", "options"), {
          timeout: 20_000,
        })
        .toContain(view.name);
      const before = (await fakeDevice()).uploads;
      await callService(page, "select", "select_option", {
        entity_id: "select.fake_display_display",
        option: view.name,
      });

      // Two frames after the switch: the new view renders, refresh after
      // refresh. (One could be the previous screen's refresh in flight.)
      await expect
        .poll(async () => (await fakeDevice()).uploads, { timeout: 30_000 })
        .toBeGreaterThanOrEqual(before + 2);
      expect(await entityState(page, "select.fake_display_display")).toBe(view.name);
      expect(await entityState(page, "sensor.fake_display_status")).toBe("Connected");
    } finally {
      await ws(page, {
        type: "geekmagic/devices/assign_views",
        entry_id: device.entry_id,
        view_ids: originalViews,
      });
    }
  });
});
