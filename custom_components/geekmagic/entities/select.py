"""Select entities for GeekMagic integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    CONF_LAYOUT,
    CONF_SCREEN_THEME,
    CONF_SCREENS,
    CONF_WIDGETS,
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
    LAYOUT_HERO,
    LAYOUT_SLOT_COUNTS,
    LAYOUT_SPLIT,
    LAYOUT_THREE_COLUMN,
    THEME_CLASSIC,
    THEME_OPTIONS,
    WIDGET_TYPE_NAMES,
)
from .entity import GeekMagicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from ..coordinator import GeekMagicCoordinator

LAYOUT_OPTIONS = {
    LAYOUT_GRID_2X2: "Grid 2x2 (4 slots)",
    LAYOUT_GRID_2X3: "Grid 2x3 (6 slots)",
    LAYOUT_GRID_3X2: "Grid 3x2 (6 slots)",
    LAYOUT_HERO: "Hero (4 slots)",
    LAYOUT_SPLIT: "Split (2 slots)",
    LAYOUT_THREE_COLUMN: "Three Column (3 slots)",
}

WIDGET_OPTIONS = {
    "empty": "Empty",
    **WIDGET_TYPE_NAMES,
}


@dataclass(frozen=True, kw_only=True)
class GeekMagicSelectEntityDescription(SelectEntityDescription):
    """Describes a GeekMagic select entity."""

    screen_index: int | None = None
    slot_index: int | None = None
    select_type: str = ""  # "current_screen", "layout", "widget_type"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeekMagic select entities."""
    coordinator: GeekMagicCoordinator = hass.data[DOMAIN][entry.entry_id]
    ent_reg = er.async_get(hass)
    host = entry.data[CONF_HOST]

    # Track created entity keys
    current_entity_keys: set[str] = set()

    def _get_required_keys() -> set[str]:
        """Calculate which entity keys should exist based on current config."""
        required: set[str] = {"current_screen"}  # Always exists

        screens = coordinator.options.get(CONF_SCREENS, [])
        for screen_idx, screen_config in enumerate(screens):
            # Screen layout and theme selectors
            required.add(f"screen_{screen_idx + 1}_layout")
            required.add(f"screen_{screen_idx + 1}_theme")

            # Per-slot selectors
            layout_type = screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
            slot_count = LAYOUT_SLOT_COUNTS.get(layout_type, 4)

            for slot_idx in range(slot_count):
                required.add(f"screen_{screen_idx + 1}_slot_{slot_idx + 1}_widget")
                required.add(f"screen_{screen_idx + 1}_slot_{slot_idx + 1}_entity")

        return required

    @callback
    def async_update_entities() -> None:
        """Update entities when coordinator data changes."""
        nonlocal current_entity_keys

        required_keys = _get_required_keys()
        entities_to_add: list[GeekMagicSelectEntity] = []

        # Remove entities that are no longer needed
        keys_to_remove = current_entity_keys - required_keys
        for key in keys_to_remove:
            unique_id = f"{host}_{key}"
            entity_id = ent_reg.async_get_entity_id("select", DOMAIN, unique_id)
            if entity_id:
                ent_reg.async_remove(entity_id)
        current_entity_keys -= keys_to_remove

        # Add new entities
        keys_to_add = required_keys - current_entity_keys

        # Current screen selector (always exists)
        if "current_screen" in keys_to_add:
            current_entity_keys.add("current_screen")
            entities_to_add.append(
                GeekMagicCurrentScreenSelect(
                    coordinator,
                    GeekMagicSelectEntityDescription(
                        key="current_screen",
                        name="Current Screen",
                        icon="mdi:monitor",
                        entity_category=EntityCategory.CONFIG,
                        select_type="current_screen",
                    ),
                )
            )

        # Per-screen entities
        screens = coordinator.options.get(CONF_SCREENS, [])
        for screen_idx, screen_config in enumerate(screens):
            # Screen layout selector
            layout_key = f"screen_{screen_idx + 1}_layout"
            if layout_key in keys_to_add:
                current_entity_keys.add(layout_key)
                entities_to_add.append(
                    GeekMagicScreenLayoutSelect(
                        coordinator,
                        GeekMagicSelectEntityDescription(
                            key=layout_key,
                            name=f"Screen {screen_idx + 1} Layout",
                            icon="mdi:view-grid",
                            entity_category=EntityCategory.CONFIG,
                            select_type="layout",
                            screen_index=screen_idx,
                        ),
                    )
                )

            # Screen theme selector
            theme_key = f"screen_{screen_idx + 1}_theme"
            if theme_key in keys_to_add:
                current_entity_keys.add(theme_key)
                entities_to_add.append(
                    GeekMagicScreenThemeSelect(
                        coordinator,
                        GeekMagicSelectEntityDescription(
                            key=theme_key,
                            name=f"Screen {screen_idx + 1} Theme",
                            icon="mdi:palette",
                            entity_category=EntityCategory.CONFIG,
                            select_type="theme",
                            screen_index=screen_idx,
                        ),
                    )
                )

            # Per-slot widget type and entity selectors
            layout_type = screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
            slot_count = LAYOUT_SLOT_COUNTS.get(layout_type, 4)

            for slot_idx in range(slot_count):
                # Widget type selector
                widget_key = f"screen_{screen_idx + 1}_slot_{slot_idx + 1}_widget"
                if widget_key in keys_to_add:
                    current_entity_keys.add(widget_key)
                    entities_to_add.append(
                        GeekMagicSlotWidgetSelect(
                            coordinator,
                            GeekMagicSelectEntityDescription(
                                key=widget_key,
                                name=f"Screen {screen_idx + 1} Slot {slot_idx + 1} Display",
                                icon="mdi:widgets",
                                entity_category=EntityCategory.CONFIG,
                                select_type="widget_type",
                                screen_index=screen_idx,
                                slot_index=slot_idx,
                            ),
                        )
                    )

                # Entity selector (dropdown with all available entities)
                entity_key = f"screen_{screen_idx + 1}_slot_{slot_idx + 1}_entity"
                if entity_key in keys_to_add:
                    current_entity_keys.add(entity_key)
                    entities_to_add.append(
                        GeekMagicSlotEntitySelect(
                            coordinator,
                            hass,
                            GeekMagicSelectEntityDescription(
                                key=entity_key,
                                name=f"Screen {screen_idx + 1} Slot {slot_idx + 1} Entity",
                                icon="mdi:identifier",
                                entity_category=EntityCategory.CONFIG,
                                select_type="entity",
                                screen_index=screen_idx,
                                slot_index=slot_idx,
                            ),
                        )
                    )

        if entities_to_add:
            async_add_entities(entities_to_add)

    # Initial setup
    async_update_entities()

    # Listen for coordinator updates to add/remove entities
    entry.async_on_unload(coordinator.async_add_listener(async_update_entities))


class GeekMagicSelectEntity(GeekMagicEntity, SelectEntity):
    """Base class for GeekMagic select entities."""

    entity_description: GeekMagicSelectEntityDescription

    def __init__(
        self,
        coordinator: GeekMagicCoordinator,
        description: GeekMagicSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, description)


class GeekMagicCurrentScreenSelect(GeekMagicSelectEntity):
    """Select entity for current screen."""

    @property
    def options(self) -> list[str]:
        """Return available options."""
        screens = self.coordinator.options.get(CONF_SCREENS, [])
        return [screen.get("name", f"Screen {i + 1}") for i, screen in enumerate(screens)] or [
            "Screen 1"
        ]

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        return self.coordinator.current_screen_name

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        screens = self.coordinator.options.get(CONF_SCREENS, [])
        for i, screen in enumerate(screens):
            if screen.get("name", f"Screen {i + 1}") == option:
                await self.coordinator.async_set_screen(i)
                break


class GeekMagicScreenLayoutSelect(GeekMagicSelectEntity):
    """Select entity for screen layout."""

    @property
    def options(self) -> list[str]:
        """Return available layout options."""
        return list(LAYOUT_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current layout."""
        screen_idx = self.entity_description.screen_index
        if screen_idx is None:
            return None

        screens = self.coordinator.options.get(CONF_SCREENS, [])
        if screen_idx < len(screens):
            layout = screens[screen_idx].get(CONF_LAYOUT, LAYOUT_GRID_2X2)
            return LAYOUT_OPTIONS.get(layout, "Grid 2x2 (4 slots)")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the screen layout."""
        screen_idx = self.entity_description.screen_index
        if screen_idx is None:
            return

        # Find layout key from display name
        layout_key = None
        for key, name in LAYOUT_OPTIONS.items():
            if name == option:
                layout_key = key
                break

        if layout_key:
            entry = self._get_config_entry()
            new_options = dict(entry.options)
            screens = list(new_options.get(CONF_SCREENS, []))

            if screen_idx < len(screens):
                screens[screen_idx] = dict(screens[screen_idx])
                screens[screen_idx][CONF_LAYOUT] = layout_key
                new_options[CONF_SCREENS] = screens

                self.hass.config_entries.async_update_entry(
                    entry,
                    options=new_options,
                )


class GeekMagicScreenThemeSelect(GeekMagicSelectEntity):
    """Select entity for screen theme."""

    @property
    def options(self) -> list[str]:
        """Return available theme options."""
        return list(THEME_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current theme."""
        screen_idx = self.entity_description.screen_index
        if screen_idx is None:
            return None

        screens = self.coordinator.options.get(CONF_SCREENS, [])
        if screen_idx < len(screens):
            theme = screens[screen_idx].get(CONF_SCREEN_THEME, THEME_CLASSIC)
            return THEME_OPTIONS.get(theme, "Classic")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the screen theme."""
        screen_idx = self.entity_description.screen_index
        if screen_idx is None:
            return

        # Find theme key from display name
        theme_key = None
        for key, name in THEME_OPTIONS.items():
            if name == option:
                theme_key = key
                break

        if theme_key:
            entry = self._get_config_entry()
            new_options = dict(entry.options)
            screens = list(new_options.get(CONF_SCREENS, []))

            if screen_idx < len(screens):
                screens[screen_idx] = dict(screens[screen_idx])
                screens[screen_idx][CONF_SCREEN_THEME] = theme_key
                new_options[CONF_SCREENS] = screens

                self.hass.config_entries.async_update_entry(
                    entry,
                    options=new_options,
                )


class GeekMagicSlotWidgetSelect(GeekMagicSelectEntity):
    """Select entity for slot widget type."""

    @property
    def options(self) -> list[str]:
        """Return available widget options."""
        return list(WIDGET_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current widget type."""
        screen_idx = self.entity_description.screen_index
        slot_idx = self.entity_description.slot_index
        if screen_idx is None or slot_idx is None:
            return None

        screens = self.coordinator.options.get(CONF_SCREENS, [])
        if screen_idx < len(screens):
            widgets = screens[screen_idx].get(CONF_WIDGETS, [])
            for widget in widgets:
                if widget.get("slot") == slot_idx:
                    widget_type = widget.get("type", "empty")
                    return WIDGET_OPTIONS.get(widget_type, "Empty")
        return "Empty"

    async def async_select_option(self, option: str) -> None:
        """Change the slot widget type."""
        screen_idx = self.entity_description.screen_index
        slot_idx = self.entity_description.slot_index
        if screen_idx is None or slot_idx is None:
            return

        # Find widget type key from display name
        widget_type = None
        for key, name in WIDGET_OPTIONS.items():
            if name == option:
                widget_type = key
                break

        if widget_type is None:
            return

        entry = self._get_config_entry()
        new_options = dict(entry.options)
        screens = list(new_options.get(CONF_SCREENS, []))

        if screen_idx < len(screens):
            screens[screen_idx] = dict(screens[screen_idx])
            widgets = list(screens[screen_idx].get(CONF_WIDGETS, []))

            # Find existing widget for this slot
            found = False
            for i, widget in enumerate(widgets):
                if widget.get("slot") == slot_idx:
                    if widget_type == "empty":
                        # Remove the widget
                        widgets.pop(i)
                    else:
                        # Update the widget type
                        widgets[i] = dict(widget)
                        widgets[i]["type"] = widget_type
                    found = True
                    break

            if not found and widget_type != "empty":
                # Add new widget
                widgets.append({"type": widget_type, "slot": slot_idx})

            screens[screen_idx][CONF_WIDGETS] = widgets
            new_options[CONF_SCREENS] = screens

            self.hass.config_entries.async_update_entry(
                entry,
                options=new_options,
            )


# Domain filters for each widget type
# Only show entities from these domains when the widget type is set
WIDGET_DOMAIN_FILTERS: dict[str, list[str]] = {
    "camera": ["camera"],
    "weather": ["weather"],
    "media": ["media_player"],
    "entity": ["sensor", "binary_sensor", "input_number", "input_boolean", "counter"],
    "gauge": ["sensor", "input_number", "counter", "number"],
    "chart": ["sensor", "input_number", "counter", "number"],
    "progress": ["sensor", "input_number", "counter", "number"],
    "status": ["binary_sensor", "switch", "light", "lock", "device_tracker", "input_boolean"],
    "text": ["sensor", "input_text", "input_number"],
    # clock and empty don't need entities
}


class GeekMagicSlotEntitySelect(GeekMagicSelectEntity):
    """Select entity for slot entity_id with dropdown picker.

    This provides a filtered dropdown of Home Assistant entities
    based on the widget type for easier selection.
    """

    def __init__(
        self,
        coordinator: GeekMagicCoordinator,
        hass: HomeAssistant,
        description: GeekMagicSelectEntityDescription,
    ) -> None:
        """Initialize the entity selector."""
        super().__init__(coordinator, description)
        self._hass_ref = hass

    def _get_widget_config(self) -> dict | None:
        """Get the widget configuration for this slot."""
        screen_idx = self.entity_description.screen_index
        slot_idx = self.entity_description.slot_index
        if screen_idx is None or slot_idx is None:
            return None

        screens = self.coordinator.options.get(CONF_SCREENS, [])
        if screen_idx >= len(screens):
            return None

        widgets = screens[screen_idx].get(CONF_WIDGETS, [])
        for widget in widgets:
            if widget.get("slot") == slot_idx:
                return widget
        return None

    def _get_widget_type(self) -> str | None:
        """Get the current widget type for this slot."""
        widget = self._get_widget_config()
        if widget:
            return widget.get("type")
        return None

    def _format_entity_option(self, entity_id: str) -> str:
        """Format entity option with name, value, and area.

        Format: "entity_id │ Name │ Value │ Area"
        """
        state = self._hass_ref.states.get(entity_id)
        if state is None:
            return entity_id

        # Get friendly name (truncate if too long)
        name = state.attributes.get("friendly_name", "")
        if len(name) > 25:
            name = name[:22] + "..."

        # Get current value (truncate if too long)
        value = state.state
        if len(value) > 15:
            value = value[:12] + "..."

        # Get unit if available
        unit = state.attributes.get("unit_of_measurement", "")
        if unit:
            value = f"{value} {unit}"

        # Get area name
        area = ""
        entity_registry = self._hass_ref.data.get("entity_registry")
        device_registry = self._hass_ref.data.get("device_registry")
        area_registry = self._hass_ref.data.get("area_registry")

        if entity_registry and area_registry:
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry:
                # Check entity's direct area assignment
                if entity_entry.area_id:
                    area_entry = area_registry.async_get_area(entity_entry.area_id)
                    if area_entry:
                        area = area_entry.name
                # Fall back to device's area
                elif entity_entry.device_id and device_registry:
                    device_entry = device_registry.async_get(entity_entry.device_id)
                    if device_entry and device_entry.area_id:
                        area_entry = area_registry.async_get_area(device_entry.area_id)
                        if area_entry:
                            area = area_entry.name

        # Build formatted string
        parts = [entity_id]
        if name:
            parts.append(name)
        if value and value not in ("unknown", "unavailable"):
            parts.append(value)
        if area:
            parts.append(f"[{area}]")

        return " │ ".join(parts)

    def _extract_entity_id(self, option: str) -> str:
        """Extract entity_id from option string."""
        if option == "none":
            return ""
        return option

    @property
    def options(self) -> list[str]:
        """Return available entity options filtered by widget type.

        Returns plain entity IDs to avoid exceeding the 16KB state attribute limit.
        The current_option property shows the formatted display with extra info.
        """
        widget_type = self._get_widget_type()

        # Get domain filter for this widget type
        allowed_domains = WIDGET_DOMAIN_FILTERS.get(widget_type) if widget_type else None

        if allowed_domains:
            # Filter entities by domain
            entity_ids = [
                eid
                for eid in self._hass_ref.states.async_entity_ids()
                if eid.split(".")[0] in allowed_domains
            ]
        else:
            # No filter - show common sensor-like entities
            common_domains = ["sensor", "binary_sensor", "input_number", "input_boolean"]
            entity_ids = [
                eid
                for eid in self._hass_ref.states.async_entity_ids()
                if eid.split(".")[0] in common_domains
            ]

        # Sort by entity_id for consistency
        entity_ids = sorted(entity_ids)

        # Return plain entity IDs (not formatted) to stay under 16KB attribute limit
        # Add "none" option at the start to allow clearing
        return ["none", *entity_ids]

    @property
    def current_option(self) -> str | None:
        """Return the current entity_id (plain, matching options list)."""
        widget = self._get_widget_config()
        if widget:
            entity_id = widget.get("entity_id", "")
            if entity_id:
                return entity_id
        return "none"

    async def async_select_option(self, option: str) -> None:
        """Set the entity_id."""
        screen_idx = self.entity_description.screen_index
        slot_idx = self.entity_description.slot_index

        if screen_idx is None or slot_idx is None:
            return

        entry = self._get_config_entry()
        new_options = dict(entry.options)
        screens = list(new_options.get(CONF_SCREENS, []))

        if screen_idx >= len(screens):
            return

        screens[screen_idx] = dict(screens[screen_idx])
        widgets = list(screens[screen_idx].get(CONF_WIDGETS, []))

        # Extract entity_id from formatted option
        entity_id = self._extract_entity_id(option)

        # Find or update widget for this slot
        found = False
        for i, widget in enumerate(widgets):
            if widget.get("slot") == slot_idx:
                widgets[i] = dict(widget)
                if entity_id:
                    widgets[i]["entity_id"] = entity_id
                elif "entity_id" in widgets[i]:
                    del widgets[i]["entity_id"]
                found = True
                break

        if not found and entity_id:
            # Widget doesn't exist yet - can't set entity_id without type
            return

        screens[screen_idx][CONF_WIDGETS] = widgets
        new_options[CONF_SCREENS] = screens

        self._hass_ref.config_entries.async_update_entry(
            entry,
            options=new_options,
        )
