# AI agents

An AI agent can build and edit your views for you: "make a view with the
living room temperature as a ring and the time below it, and put it on the
desk display". It uses the same views the panel edits, so you can open
anything it made in the panel and keep going by hand.

Two kinds of agent can do it:

- **Assist**, Home Assistant's own assistant, when its conversation agent
  is an LLM (Anthropic, OpenAI, Google Generative AI, Ollama...).
- **Any MCP client** (Claude Desktop, Claude Code, Cursor...), through
  Home Assistant's [Model Context Protocol Server](https://www.home-assistant.io/integrations/mcp_server/)
  integration.

The tools are for **administrators only**, like the panel. A voice
satellite has no user, so it doesn't get them.

## Setup

Which API to tick depends on your Home Assistant version:

| Home Assistant | Tick this API | The tools appear as |
|----------------|---------------|---------------------|
| 2026.11 and later | **Home Assistant** (Home Assistant's own admin API) | `geekmagic__set_widget`... next to Home Assistant's own admin tools |
| Before 2026.11 | **GeekMagic displays** | `geekmagic__set_widget`... |

### Assist

1. Set up an LLM conversation agent (Settings > Devices & services > Add
   integration > Anthropic, OpenAI, Google Generative AI, Ollama...).
2. In the agent's options, under **Control Home Assistant**, tick the API
   from the table above (keep **Device control** / **Assist** ticked too if
   you also want it to control your devices).
3. Ask it from Assist while logged in as an administrator.

### MCP clients

1. Add the **Model Context Protocol Server** integration, and tick the API
   from the table above.
2. Connect your client to `http://<home-assistant>:8123/api/mcp` with a
   long-lived access token from an administrator's profile. With Claude
   Code, for example:

   ```bash
   claude mcp add --transport http home-assistant \
     http://homeassistant.local:8123/api/mcp \
     --header "Authorization: Bearer <token>"
   ```

## Tools

| Tool | What it does |
|------|--------------|
| `geekmagic__get_catalog` | Layouts (with each slot's pixel size), themes, and every widget type with its options and allowed values |
| `geekmagic__get_views` | Every view, and every display with its assigned views and the one on screen |
| `geekmagic__find_entities` | Entities to put in widgets, by words, domain, or the widget type that will show them |
| `geekmagic__create_view` | A new, empty view with a layout and theme |
| `geekmagic__duplicate_view` | Copy a view, to rework it without changing what displays show |
| `geekmagic__update_view` | Rename a view, or change its layout or theme |
| `geekmagic__set_widget` | Put a widget in a slot, replacing what is there |
| `geekmagic__clear_widget` | Empty a slot |
| `geekmagic__assign_views` | Set the views a display cycles through |
| `geekmagic__show_view` | Switch a display to one of its views now |
| `geekmagic__render_view` | Render a view exactly as a display shows it, with a report of each slot's problems and a link to the image |

There is no tool to delete a view: deleting stays in the panel.

A display shows every change to a view assigned to it at once, so agents
are told to rework such a view on a copy (`geekmagic__duplicate_view`) and
assign the copy when it's done, unless you ask for the change in place.

Views and displays can be named by id or by name. Every write is checked
against the widget's options before it is saved, and a refused write says
what was wrong and what is accepted, so the agent can fix it and try again
instead of saving a view that shows nothing.

## Can the agent see the screen?

Not directly: tool results are text. So `geekmagic__render_view` returns
two things:

- **A report for every slot**: its pixel size, its widget, and its
  problems (an entity that doesn't exist or is unavailable, options the
  widget can't use, an empty slot). Every agent can read this.
- **`image_url`**: a link to the rendered 240x240 PNG, signed for the
  agent's own token and valid for 10 minutes. An agent that can fetch URLs
  (Claude Code can download it and look at it) sees exactly what the
  display will show. The link points to the address the agent used to
  reach Home Assistant, so it has to be able to reach that address too.

## Entities

`geekmagic__find_entities` lists every entity, like the panel's entity
picker, not only those exposed to Assist: these are administrator tools for
configuring displays, and Home Assistant's own administrator tools aren't
limited to exposed entities either.
