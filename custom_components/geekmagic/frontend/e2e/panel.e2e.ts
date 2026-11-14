/**
 * The redesigned panel's interactions, each asserting an effect that can't
 * already be true before the action: on the stored view, on the device's
 * reported state, or on the fake device itself.
 */
import type { Page } from "@playwright/test";
import {
  callService,
  entityState,
  expect,
  fakeDevice,
  openEditor,
  openPanel,
  saveButton,
  selectSlot,
  slotLabel,
  test,
  toast,
  ws,
  type View,
} from "./fixtures";

interface PanelDevice {
  entry_id: string;
  assigned_views: string[];
  current_view_id: string | null;
  entities: Record<string, string>;
}

async function device(page: Page): Promise<PanelDevice> {
  const { devices } = await ws<{ devices: PanelDevice[] }>(page, { type: "geekmagic/devices/list" });
  return devices[0];
}

async function storedView(page: Page, id: string): Promise<View> {
  return (await ws<{ view: View }>(page, { type: "geekmagic/views/get", view_id: id })).view;
}

const thumb = (page: Page, viewId: string) => page.locator(`gm-device-card .thumb[data-view-id="${viewId}"]`);

test.describe("the editor", () => {
  test("edits the cell you pick on the screen", async ({ page, view }) => {
    await openEditor(page, view.name);
    await selectSlot(page, 1);
    await expect(page.locator(".widget-head h3")).toHaveText("Entity");
    await expect(slotLabel(page)).toHaveValue("Room");

    await selectSlot(page, 0);
    await expect(page.locator(".widget-head h3")).toHaveText("Clock");
    await expect(slotLabel(page)).toHaveValue("");
  });

  test("previews each widget at the size of the slot", async ({ page, view }) => {
    await openEditor(page, view.name);
    await selectSlot(page, 1);
    await page.getByRole("button", { name: "Change" }).click();
    // The fixture view is a 2×2 grid: its cells preview the 2×2 renders.
    const preview = page.getByRole("button", { name: "Entity", exact: true }).locator("img");
    await expect(preview).toHaveAttribute("src", /\/entity_icon_2x2\.png\?v=/);
    await expect
      .poll(() => preview.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth))
      .toBe(108);
  });

  test("shows only the options that apply", async ({ page, view }) => {
    await openEditor(page, view.name);
    await selectSlot(page, 2);
    await page.getByRole("button", { name: "Gauge", exact: true }).click();
    const orientation = page.locator("ha-select", { hasText: "Bar Orientation" });
    await expect(orientation).toBeVisible();

    await page.locator("ha-select", { hasText: "Style" }).first().click();
    await page.getByRole("menuitem", { name: "ring", exact: true }).click();
    await expect(orientation).toBeHidden();

    await saveButton(page).click();
    await expect(toast(page, `Saved "${view.name}"`)).toBeVisible();
    const gauge = (await storedView(page, view.id)).widgets.find((w) => w.slot === 2);
    expect(gauge).toMatchObject({ type: "gauge", options: { style: "ring" } });
  });

  test("warns about widgets a smaller layout hides, and removes them on request", async ({ page, view }) => {
    await openEditor(page, view.name);
    await page.getByRole("tab", { name: "Layout & theme" }).click();
    await page.getByRole("radio", { name: "Fullscreen" }).click();

    const alert = page.locator("ha-alert", { hasText: "doesn't fit this layout" });
    await expect(alert).toBeVisible();
    await alert.getByRole("button", { name: "Remove hidden widgets" }).click();
    await expect(alert).toBeHidden();

    await saveButton(page).click();
    await expect(toast(page, `Saved "${view.name}"`)).toBeVisible();
    const stored = await storedView(page, view.id);
    expect(stored.layout).toBe("fullscreen");
    expect(stored.widgets.map((w) => w.slot)).toEqual([0]);
  });
});

test.describe("the views gallery", () => {
  test("deletes a view only once confirmed", async ({ page, view }) => {
    const card = page.locator("ha-card.view-card", { hasText: view.name });
    const remaining = async () =>
      (await ws<{ views: View[] }>(page, { type: "geekmagic/views/list" })).views.map((v) => v.id);

    await card.getByRole("button", { name: `${view.name} actions` }).click();
    await page.getByRole("menuitem", { name: "Delete" }).click();
    await expect(page.getByRole("dialog", { name: `Delete "${view.name}"?` })).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    expect(await remaining()).toContain(view.id);

    await card.getByRole("button", { name: `${view.name} actions` }).click();
    await page.getByRole("menuitem", { name: "Delete" }).click();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(card).toBeHidden();
    expect(await remaining()).not.toContain(view.id);
  });
});

test.describe("the display card", () => {
  test.beforeEach(async ({ page }) => {
    await openPanel(page);
    await expect(page.locator("gm-device-card .thumb").first()).toBeVisible();
  });

  test("shows a view now when its thumbnail is tapped", async ({ page }) => {
    const before = await device(page);
    const target = before.assigned_views.find((id) => id !== before.current_view_id)!;
    try {
      await thumb(page, target).getByRole("button", { name: /^Show .* now$/ }).click();
      await expect.poll(async () => (await device(page)).current_view_id).toBe(target);
      await expect(thumb(page, target).locator("[aria-current=true]")).toBeVisible();
    } finally {
      if (before.current_view_id) {
        await ws(page, {
          type: "geekmagic/devices/show_view",
          entry_id: before.entry_id,
          view_id: before.current_view_id,
        });
      }
    }
  });

  test("reorders the rotation and keeps the view on screen", async ({ page }) => {
    const before = await device(page);
    const [first, second] = before.assigned_views;
    try {
      await thumb(page, first).getByRole("button", { name: /actions$/ }).click();
      await page.getByRole("menuitem", { name: "Move later" }).click();
      await expect
        .poll(async () => (await device(page)).assigned_views.slice(0, 2))
        .toEqual([second, first]);
      expect((await device(page)).current_view_id).toBe(before.current_view_id);
    } finally {
      await ws(page, {
        type: "geekmagic/devices/assign_views",
        entry_id: before.entry_id,
        view_ids: before.assigned_views,
      });
    }
  });

  test("removes a view from the rotation and adds it back", async ({ page }) => {
    const before = await device(page);
    const last = before.assigned_views[before.assigned_views.length - 1];
    const { view } = await ws<{ view: { name: string } }>(page, {
      type: "geekmagic/views/get",
      view_id: last,
    });
    const card = page.locator("gm-device-card");
    try {
      await thumb(page, last).getByRole("button", { name: /actions$/ }).click();
      await page.getByRole("menuitem", { name: "Remove from rotation" }).click();
      await expect
        .poll(async () => (await device(page)).assigned_views)
        .toEqual(before.assigned_views.slice(0, -1));

      await card.locator(".add-thumb").click();
      await expect(page.getByRole("dialog", { name: /^Add to / })).toBeVisible();
      // The dialog's content is slotted from the card, so look it up there.
      await card.getByRole("checkbox", { name: view.name }).check();
      await card.getByRole("button", { name: "Add 1 view" }).click();
      await expect
        .poll(async () => (await device(page)).assigned_views)
        .toEqual(before.assigned_views);
    } finally {
      await ws(page, {
        type: "geekmagic/devices/assign_views",
        entry_id: before.entry_id,
        view_ids: before.assigned_views,
      });
    }
  });

  test("resumes a paused display", async ({ page }) => {
    const entity = (await device(page)).entities.active;
    const resume = page.locator("gm-device-card").getByRole("button", { name: "Resume" });
    try {
      await callService(page, "switch", "turn_off", { entity_id: entity });
      await expect.poll(() => entityState(page, entity)).toBe("off");
      await resume.click();
      await expect.poll(() => entityState(page, entity)).toBe("on");
      await expect(resume).toHaveCount(0);
    } finally {
      await callService(page, "switch", "turn_on", { entity_id: entity });
    }
  });

  test("sets the brightness on the device", async ({ page }) => {
    const before = await device(page);
    const entity = before.entities.brightness;
    const original = Number(await entityState(page, entity));
    const target = original >= 50 ? 0 : 100;
    try {
      const slider = page.locator("gm-device-card ha-slider").first();
      const box = (await slider.boundingBox())!;
      // Release at one end of the track: the slider commits on release.
      await slider.click({ position: { x: target === 0 ? 1 : box.width - 1, y: box.height / 2 } });
      // The entity reports percent; the Ultra itself stores 0-255.
      await expect.poll(() => entityState(page, entity), { timeout: 15_000 }).toBe(String(target));
      await expect
        .poll(async () => (await fakeDevice()).brightness, { timeout: 15_000 })
        .toBe(target === 0 ? 0 : 255);
    } finally {
      await ws(page, {
        type: "call_service",
        domain: "number",
        service: "set_value",
        service_data: { entity_id: entity, value: original },
      });
    }
  });
});
