/** Typed calls to the integration's websocket API and HA services. */
import type {
  DeviceConfig,
  GeekMagicConfig,
  HomeAssistant,
  PreviewResponse,
  ViewConfig,
} from "./types";

export type ViewDraft = Pick<ViewConfig, "layout" | "theme" | "widgets">;

export class GeekMagicApi {
  constructor(private readonly hass: () => HomeAssistant) {}

  private send<T>(message: Record<string, unknown> & { type: string }): Promise<T> {
    return this.hass().connection.sendMessagePromise<T>(message);
  }

  config(): Promise<GeekMagicConfig> {
    return this.send({ type: "geekmagic/config" });
  }

  async views(): Promise<ViewConfig[]> {
    return (await this.send<{ views: ViewConfig[] }>({ type: "geekmagic/views/list" })).views;
  }

  async devices(): Promise<DeviceConfig[]> {
    return (await this.send<{ devices: DeviceConfig[] }>({ type: "geekmagic/devices/list" }))
      .devices;
  }

  async createView(name: string): Promise<ViewConfig> {
    const result = await this.send<{ view: ViewConfig }>({
      type: "geekmagic/views/create",
      name,
      layout: "grid_2x2",
      theme: "watchos",
      widgets: [],
    });
    return result.view;
  }

  updateView(view: ViewConfig): Promise<unknown> {
    return this.send({
      type: "geekmagic/views/update",
      view_id: view.id,
      name: view.name,
      layout: view.layout,
      theme: view.theme,
      widgets: view.widgets,
    });
  }

  deleteView(viewId: string): Promise<unknown> {
    return this.send({ type: "geekmagic/views/delete", view_id: viewId });
  }

  async duplicateView(viewId: string): Promise<ViewConfig> {
    return (
      await this.send<{ view: ViewConfig }>({ type: "geekmagic/views/duplicate", view_id: viewId })
    ).view;
  }

  assignViews(entryId: string, viewIds: string[]): Promise<unknown> {
    return this.send({
      type: "geekmagic/devices/assign_views",
      entry_id: entryId,
      view_ids: viewIds,
    });
  }

  showView(entryId: string, viewId: string): Promise<unknown> {
    return this.send({ type: "geekmagic/devices/show_view", entry_id: entryId, view_id: viewId });
  }

  render(view: ViewDraft): Promise<PreviewResponse> {
    return this.send({
      type: "geekmagic/preview/render",
      view_config: { layout: view.layout, theme: view.theme, widgets: view.widgets },
    });
  }

  callService(domain: string, service: string, data: Record<string, unknown>): Promise<unknown> {
    return this.hass().callService(domain, service, data);
  }
}

/** Run ``tasks`` with at most ``limit`` in flight. */
export async function limited<T>(
  items: T[],
  limit: number,
  task: (item: T) => Promise<void>
): Promise<void> {
  const queue = [...items];
  const workers = Array.from({ length: Math.min(limit, queue.length) }, async () => {
    while (queue.length) await task(queue.shift() as T);
  });
  await Promise.all(workers);
}

export const pngUrl = (base64: string) => `data:image/png;base64,${base64}`;
