"""Image widget: a static picture from a URL or a local file."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import IMAGE_SOURCE_DEFAULT_REFRESH, IMAGE_SOURCE_REFRESH_SECONDS
from ..htmldoc import image_data_uri
from .base import Widget, WidgetConfig
from .camera import label_capsule_html, picture_html, placeholder_html

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# Option value -> CSS object-fit. "stretch" is the friendlier name for fill.
_FITS = {"contain": "contain", "cover": "cover", "stretch": "fill"}


class ImageWidget(Widget):
    """Widget that displays a picture from a URL or a local file.

    The coordinator (and the panel preview) load ``source`` through the
    shared image cache (``image_source.py``) and hand the decoded picture
    in ``state.image`` — this widget never does I/O. Animated GIFs show
    their first frame.
    """

    WIDGET_TYPE: ClassVar[str] = "image"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Image",
        "needs_entity": False,
        "options": [
            {
                "key": "source",
                "type": "text",
                "label": "Image URL or Path",
                "placeholder": "https://… or /local/logo.png",
            },
            {
                "key": "fit",
                "type": "select",
                "label": "Fit Mode",
                "options": list(_FITS),
                "default": "contain",
            },
            {
                "key": "refresh",
                "type": "select",
                "label": "Reload Every",
                "options": list(IMAGE_SOURCE_REFRESH_SECONDS),
                "default": IMAGE_SOURCE_DEFAULT_REFRESH,
            },
            {"key": "show_label", "type": "boolean", "label": "Show Label", "default": False},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the image widget."""
        super().__init__(config)
        self.source = str(config.options.get("source") or "").strip()
        # Default "contain": a logo or GIF is shown whole, letterboxed on
        # the theme background, rather than cropped.
        self.fit = config.options.get("fit", "contain")
        self.refresh = config.options.get("refresh", IMAGE_SOURCE_DEFAULT_REFRESH)
        self.show_label = config.options.get("show_label", False)

    @property
    def refresh_seconds(self) -> float:
        """How long a loaded picture is reused before it is fetched again."""
        return IMAGE_SOURCE_REFRESH_SECONDS.get(
            self.refresh, IMAGE_SOURCE_REFRESH_SECONDS[IMAGE_SOURCE_DEFAULT_REFRESH]
        )

    def get_entities(self) -> list[str]:
        """The image widget tracks no entity."""
        return []

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the picture edge to edge, or a placeholder naming it."""
        if state.image is None:
            return placeholder_html(ctx, "image-off-outline", self._name("No Image"))

        chip = ""
        if self.show_label:
            chip = label_capsule_html(ctx, self._name("Image"), self.config.color)
        fit = _FITS.get(self.fit, "contain")
        return picture_html(image_data_uri(state.image), fit, chip)

    def _name(self, fallback: str) -> str:
        """The label, else the source's file name, else ``fallback``."""
        if self.config.label:
            return self.config.label
        if self.source:
            name = PurePosixPath(self.source.split("?", 1)[0]).name
            if name:
                return name
        return fallback
