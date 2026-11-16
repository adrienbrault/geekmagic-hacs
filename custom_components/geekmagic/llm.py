"""LLM platform: the GeekMagic tools in Home Assistant's own admin API.

Home Assistant 2026.11 and later collect integration tools through this
platform into the built-in "Home Assistant" API (admin-only), which
Assist and the MCP Server offer like any other. Older cores never load
it; ``llm_api`` registers a standalone API for them instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .llm_api import API_PROMPT, core_has_home_assistant_api, make_tools

if TYPE_CHECKING:
    # Both exist from Home Assistant 2026.8, the first core to load this platform
    from homeassistant.components.llm import LLMTools  # ty: ignore[import-not-found]
    from homeassistant.helpers.llm import LLMContext


@callback
def async_get_tools(hass: HomeAssistant, llm_context: LLMContext, api_id: str) -> LLMTools | None:
    """The GeekMagic tools, for the "Home Assistant" API only.

    Not for Assist: its scope is the entities a user exposed, and these
    tools configure the integration. 2026.8-2026.10 load this platform
    but have no "Home Assistant" API; they get the standalone one.
    """
    if not core_has_home_assistant_api() or "store" not in hass.data.get(DOMAIN, {}):
        return None
    from homeassistant.components.llm import LLMTools  # noqa: PLC0415  # ty: ignore[import-not-found]
    from homeassistant.helpers.llm import (  # noqa: PLC0415
        LLM_API_HOME_ASSISTANT,  # ty: ignore[import-not-found]
    )

    if api_id != LLM_API_HOME_ASSISTANT:
        return None
    return LLMTools(tools=make_tools(), prompt=API_PROMPT)
