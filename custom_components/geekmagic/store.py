"""Global view storage for GeekMagic integration.

Views are stored centrally and can be assigned to multiple devices.
Uses Home Assistant's built-in Store class for persistence.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LAYOUT_GRID_2X2, THEME_CLASSIC

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}.views"
STORAGE_VERSION = 1


class GeekMagicStore:
    """Store for global views shared across all GeekMagic devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"views": {}}
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Load stored data from disk."""
        data = await self._store.async_load()
        if data:
            self._data = data
            _LOGGER.debug("Loaded %d views from storage", len(self.views))
        else:
            _LOGGER.debug("No existing views in storage, starting fresh")

    async def async_save(self) -> None:
        """Save current data to disk."""
        await self._store.async_save(self._data)
        self._notify_listeners()

    def _notify_listeners(self) -> None:
        """Notify all listeners of data change."""
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                _LOGGER.exception("Error notifying store listener")

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Add a listener for store updates.

        Args:
            listener: Callback to invoke on updates

        Returns:
            Function to remove the listener
        """
        self._listeners.append(listener)

        def remove_listener() -> None:
            self._listeners.remove(listener)

        return remove_listener

    @property
    def views(self) -> dict[str, dict[str, Any]]:
        """Get all views."""
        return self._data.get("views", {})

    def get_view(self, view_id: str) -> dict[str, Any] | None:
        """Get a specific view by ID.

        Args:
            view_id: View identifier

        Returns:
            View configuration or None if not found
        """
        return self.views.get(view_id)

    def get_views_list(self) -> list[dict[str, Any]]:
        """Get all views as a list, sorted by name.

        Returns:
            List of view configurations
        """
        views = list(self.views.values())
        views.sort(key=lambda v: v.get("name", "").lower())
        return views

    async def async_create_view(
        self,
        name: str,
        layout: str = LAYOUT_GRID_2X2,
        theme: str = THEME_CLASSIC,
        widgets: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create a new view.

        Args:
            name: View display name
            layout: Layout type
            theme: Theme name
            widgets: List of widget configurations

        Returns:
            ID of the created view
        """
        view_id = f"view_{uuid4().hex[:8]}"
        now = dt_util.utcnow().isoformat()

        self._data["views"][view_id] = {
            "id": view_id,
            "name": name,
            "layout": layout,
            "theme": theme,
            "widgets": widgets or [],
            "created_at": now,
            "updated_at": now,
        }

        await self.async_save()
        _LOGGER.debug("Created view %s: %s", view_id, name)
        return view_id

    async def async_update_view(
        self,
        view_id: str,
        **updates: Any,
    ) -> bool:
        """Update an existing view.

        Args:
            view_id: View identifier
            **updates: Fields to update (name, layout, theme, widgets)

        Returns:
            True if view was updated, False if not found
        """
        if view_id not in self._data["views"]:
            _LOGGER.warning("Cannot update view %s: not found", view_id)
            return False

        view = self._data["views"][view_id]

        # Only update allowed fields
        allowed_fields = {"name", "layout", "theme", "widgets"}
        for key, value in updates.items():
            if key in allowed_fields:
                view[key] = value

        view["updated_at"] = dt_util.utcnow().isoformat()

        await self.async_save()
        _LOGGER.debug("Updated view %s", view_id)
        return True

    async def async_delete_view(self, view_id: str) -> bool:
        """Delete a view.

        Args:
            view_id: View identifier

        Returns:
            True if view was deleted, False if not found
        """
        if view_id not in self._data["views"]:
            _LOGGER.warning("Cannot delete view %s: not found", view_id)
            return False

        del self._data["views"][view_id]
        await self.async_save()
        _LOGGER.debug("Deleted view %s", view_id)
        return True

    async def async_duplicate_view(self, view_id: str, new_name: str | None = None) -> str | None:
        """Duplicate an existing view.

        Args:
            view_id: View to duplicate
            new_name: Optional name for the copy

        Returns:
            ID of the new view, or None if source not found
        """
        source = self.get_view(view_id)
        if not source:
            _LOGGER.warning("Cannot duplicate view %s: not found", view_id)
            return None

        name = new_name or f"{source['name']} (Copy)"
        return await self.async_create_view(
            name=name,
            layout=source["layout"],
            theme=source["theme"],
            widgets=source.get("widgets", []).copy(),
        )

    async def async_migrate_from_screens(
        self,
        screens: list[dict[str, Any]],
        device_name: str = "",
    ) -> list[str]:
        """Migrate old per-device screens to global views.

        Args:
            screens: List of screen configurations from old format
            device_name: Device name to prefix view names

        Returns:
            List of created view IDs
        """
        view_ids = []
        prefix = f"{device_name} - " if device_name else ""

        for i, screen in enumerate(screens):
            name = screen.get("name", f"Screen {i + 1}")
            view_id = await self.async_create_view(
                name=f"{prefix}{name}",
                layout=screen.get("layout", LAYOUT_GRID_2X2),
                theme=screen.get("theme", THEME_CLASSIC),
                widgets=screen.get("widgets", []),
            )
            view_ids.append(view_id)

        _LOGGER.info("Migrated %d screens to global views", len(view_ids))
        return view_ids
