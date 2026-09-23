"""Date/time entity widget for GeekMagic displays.

A thin specialisation of :class:`EntityWidget` for sensors whose value is
a date/time (``device_class: timestamp`` and friends). It surfaces the
timestamp-formatting options — relative ("in 1 hour"), time-only
("14:33"), or a custom ``strftime`` pattern — that would be noise on every
other entity, and defaults to a relative display so it's useful the moment
it's added. See issue 167.
"""

from __future__ import annotations

from typing import Any, ClassVar

from .entity import EntityWidget


class DateTimeWidget(EntityWidget):
    """Entity widget tuned for timestamp sensors.

    Inherits all of :class:`EntityWidget`'s rendering (card, hero, icon,
    caption) and its timestamp-formatting pipeline; only the widget type,
    editor schema, and default format differ.
    """

    WIDGET_TYPE: ClassVar[str] = "datetime"
    DEFAULT_TIMESTAMP_FORMAT: ClassVar[str] = "relative"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Date / Time",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with a datetime value
        "options": [
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_icon", "type": "boolean", "label": "Show Icon", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon Override"},
            {"key": "attribute", "type": "text", "label": "Entity Attribute"},
            {
                "key": "timestamp_format",
                "type": "select",
                "label": "Format",
                "options": ["relative", "time", "date", "datetime", "custom", "default"],
                "default": "relative",
            },
            {
                "key": "timestamp_custom_format",
                "type": "text",
                "label": "Custom Format (strftime)",
                "placeholder": "%H:%M",
            },
        ],
    }
