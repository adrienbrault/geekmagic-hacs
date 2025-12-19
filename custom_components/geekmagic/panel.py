"""Custom panel registration for GeekMagic integration.

Registers a sidebar panel for the GeekMagic configuration UI.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Panel configuration
PANEL_NAME = "geekmagic-panel"
PANEL_TITLE = "GeekMagic"
PANEL_ICON = "mdi:monitor-dashboard"
PANEL_URL_PATH = "geekmagic"
PANEL_MODULE_URL_BASE = "/geekmagic_panel/geekmagic-panel.js"

# Frontend files location
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"


async def async_register_panel(hass: HomeAssistant) -> bool:
    """Register the GeekMagic configuration panel.

    Args:
        hass: Home Assistant instance

    Returns:
        True if panel was registered successfully
    """
    # Check if panel_custom integration is available
    try:
        from homeassistant.components import panel_custom
        from homeassistant.components.http import StaticPathConfig
    except ImportError:
        _LOGGER.warning(
            "panel_custom or http component not available. Custom panel will not be registered."
        )
        return False

    # Issue: does not register automatically in the side-nav

    # Check if panel_custom is loaded
    # if "panel_custom" not in hass.config.components:
    #     _LOGGER.debug(
    #         "panel_custom component not loaded. "
    #         "Panel will be registered when frontend is available."
    #     )
    #     # Don't fail - panel_custom might not be needed in test environments
    #     return True

    # Check if frontend files exist
    panel_js = FRONTEND_DIR / "geekmagic-panel.js"
    if not panel_js.exists():
        _LOGGER.warning(
            "Frontend panel not found at %s. Panel UI will not be available. "
            "Run 'npm run build' in the frontend directory to build the panel.",
            panel_js,
        )
        # Create a placeholder so the integration doesn't fail
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
        panel_js.write_text(_get_placeholder_panel())
        _LOGGER.info("Created placeholder panel at %s", panel_js)

    # Generate content hash for cache busting
    # This ensures browsers fetch new JS when the file changes (on any commit)
    try:
        content_hash = await hass.async_add_executor_job(_get_file_hash, panel_js)
    except Exception:
        content_hash = "dev"
    module_url = f"{PANEL_MODULE_URL_BASE}?h={content_hash}"

    # Register static path for frontend files
    try:
        if hasattr(hass, "http") and hass.http is not None:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        url_path="/geekmagic_panel",
                        path=str(FRONTEND_DIR),
                        cache_headers=False,  # Disable caching during development
                    )
                ]
            )
            _LOGGER.debug("Registered static path for frontend files")
        else:
            _LOGGER.debug("HTTP component not available, skipping static path registration")
            return True
    except Exception:
        _LOGGER.exception("Failed to register static path")
        return False

    # Register the custom panel
    try:
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name=PANEL_NAME,
            frontend_url_path=PANEL_URL_PATH,
            module_url=module_url,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=True,
            config={
                "domain": DOMAIN,
            },
        )
        _LOGGER.info("Registered GeekMagic panel at /%s (h=%s)", PANEL_URL_PATH, content_hash)
    except Exception:
        _LOGGER.exception("Failed to register panel")
        return False
    else:
        return True


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the GeekMagic panel.

    Args:
        hass: Home Assistant instance
    """
    try:
        from homeassistant.components import frontend

        if "frontend" in hass.config.components:
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
            _LOGGER.debug("Unregistered GeekMagic panel")
    except Exception as err:
        _LOGGER.warning("Failed to unregister panel: %s", err)


def _get_file_hash(path: Path) -> str:
    """Get short hash of file content for cache busting."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:8]


def _get_placeholder_panel() -> str:
    """Generate a placeholder panel JS that shows build instructions."""
    return """
// GeekMagic Panel - Placeholder
// Run 'npm run build' in the frontend directory to build the actual panel.

class GeekMagicPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    set hass(hass) {
        this._hass = hass;
        this._render();
    }

    set panel(panel) {
        this._panel = panel;
    }

    set narrow(narrow) {
        this._narrow = narrow;
    }

    _render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    padding: 24px;
                    box-sizing: border-box;
                    background: var(--primary-background-color);
                    color: var(--primary-text-color);
                }
                .container {
                    max-width: 600px;
                    text-align: center;
                }
                h1 {
                    margin: 0 0 16px;
                    font-size: 24px;
                    font-weight: 500;
                }
                p {
                    margin: 0 0 16px;
                    opacity: 0.8;
                }
                code {
                    background: var(--secondary-background-color);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-family: monospace;
                }
                .icon {
                    font-size: 64px;
                    margin-bottom: 16px;
                }
            </style>
            <div class="container">
                <div class="icon">🔧</div>
                <h1>GeekMagic Panel</h1>
                <p>The panel frontend needs to be built.</p>
                <p>Run the following commands:</p>
                <p><code>cd custom_components/geekmagic/frontend</code></p>
                <p><code>npm install && npm run build</code></p>
                <p>Then reload this page.</p>
            </div>
        `;
    }
}

customElements.define('geekmagic-panel', GeekMagicPanel);
"""
