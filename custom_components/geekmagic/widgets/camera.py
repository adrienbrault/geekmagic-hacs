"""Camera widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import css_rgb, image_data_uri, mdi_span

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ._textfit import TextMetrics
    from .state import WidgetState

from ._cardfit import fit_caption_sized
from ._textfit import metrics_for
from .base import Widget, WidgetConfig

# Both strings this widget draws are rendered uppercase, so they are
# measured uppercase too — Blitz has no text-overflow, and caps are the
# widest form of a name.
_CAPSULE_TRACKING = 0.10
_LABEL_WEIGHT = "bold"

# Every shipped theme paints ``.root`` with up to 6px of padding plus a
# 1px border, so the fragment is up to 7px per side narrower than
# ``ctx.width``. That inset lives in ``theme.chrome_css``, which widgets
# cannot parse — reserve the worst case rather than clip on a chromed
# theme. (Matches ``_cardfit._CHROME_INSET``.)
_CHROME_PX = 14.0

# Shared optical margin for the label capsule — matches the media widget's
# album-art overlay so a camera and a media cell sit on the same grid.
_INSET = "clamp(5px, 5.5vmin, 14px)"


def _caps_metrics(ctx: CellContext) -> TextMetrics:
    """Measurer for this widget's always-uppercase text."""
    return replace(metrics_for(ctx.theme), uppercase=True)


class CameraWidget(Widget):
    """Widget that displays a camera snapshot or an ``image`` entity's picture.

    ``image.*`` entities (e.g. Frigate's latest-detection snapshot) are the
    same thing to the cell — a picture of the entity — so they share this
    widget rather than adding a type; only the fetch differs (the
    coordinator reads them through the shared image cache).
    """

    WIDGET_TYPE: ClassVar[str] = "camera"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Camera",
        "icon": "mdi:cctv",
        "category": "pictures",
        "description": "A camera snapshot",
        "needs_entity": True,
        "entity_domains": ["camera", "image"],
        "options": [
            {
                "key": "fit",
                "type": "select",
                "label": "Fit Mode",
                "options": ["cover", "contain"],
                "default": "cover",
            },
            {"key": "show_label", "type": "boolean", "label": "Show Label", "default": False},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the camera widget."""
        super().__init__(config)
        self.show_label = config.options.get("show_label", False)
        # Default matches the SCHEMA: a fresh camera fills its cell
        # instead of letterboxing non-square cells with black bands.
        self.fit = config.options.get("fit", "cover")

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the camera widget."""
        if state.image is None:
            name = self.label_for(state.entity, state=state, fallback="No Image")
            entity_id = self.config.entity_id or ""
            icon = "image-outline" if entity_id.startswith("image.") else "camera"
            return placeholder_html(ctx, icon, name)

        image = state.image.convert("RGB") if state.image.mode != "RGB" else state.image
        fit = self.fit if self.fit in ("cover", "contain") else "contain"
        chip = ""
        if self.show_label:
            name = self.label_for(state.entity, state=state, fallback="Camera")
            chip = label_capsule_html(ctx, name, self.config.color)
        return picture_html(image_data_uri(image), fit, chip)


def picture_html(uri: str, fit: str, overlay: str = "") -> str:
    """An image filling its cell edge to edge, with an optional overlay.

    ``fit`` is a CSS ``object-fit`` value. ``border-radius: inherit``
    picks up the theme's card rounding (light/classic/soft) and stays
    square on the chromeless themes.
    """
    return (
        '<div style="position: relative; width: 100%; height: 100%; '
        'overflow: hidden; border-radius: inherit">'
        f'<img src="{uri}" style="width: 100%; height: 100%; '
        f'object-fit: {fit}; display: block">'
        f"{overlay}"
        "</div>"
    )


def placeholder_html(ctx: CellContext, icon: str, name: str) -> str:
    """No-picture state — a quiet glyph and caption, not an alarm.

    The caption names the source (an offline "Front Door" must not
    render identically to an offline "Backyard"), and survives short
    cells at a shrunk size instead of hiding — a bare grey glyph says
    nothing.
    """
    label, font_px = fit_caption_sized(name, ctx, ctx.width * 0.88 - _CHROME_PX)
    caption = ""
    if label and ctx.height >= 44:
        caption = (
            f'<div class="t-label" style="font-size: {font_px:.1f}px; '
            f'text-transform: uppercase">{escape(label)}</div>'
        )
    return (
        '<div class="cell" style="justify-content: center; gap: 3.5vmin">'
        f"{mdi_span(icon, 'icon i-md', 'color: var(--text-secondary)')}"
        f"{caption}"
        "</div>"
    )


def label_capsule_html(
    ctx: CellContext, name: str, color: tuple[int, int, int] | None = None
) -> str:
    """Small caps capsule naming the picture, top-left over the frame.

    Fixed black/white rgba by design: the capsule floats on
    photographic content, so its contrast must not follow the theme.
    A user-set widget colour still wins for the text.
    """
    vmin = min(ctx.width, ctx.height)
    font_px = min(12.0, max(8.0, 0.062 * vmin))
    inset_px = min(14.0, max(5.0, 0.055 * vmin))
    # Subtract the two insets, the capsule's 0.72em side padding, its
    # 1px borders and the theme chrome before fitting glyphs.
    usable = ctx.width - 2 * inset_px - 1.44 * font_px - 2 - _CHROME_PX
    label = _caps_metrics(ctx).truncate(
        name,
        font_px,
        max(12.0, usable),
        _LABEL_WEIGHT,
        tracking=_CAPSULE_TRACKING,
    )
    text_color = css_rgb(color) if color else "rgba(255,255,255,0.95)"
    return (
        f'<div style="position: absolute; top: {_INSET}; left: {_INSET}; '
        "background: rgba(0,0,0,0.55); border: 1px solid rgba(255,255,255,0.12); "
        f"border-radius: 999px; padding: 0.3em 0.72em; font-size: {font_px:.1f}px; "
        "font-weight: 700; letter-spacing: 0.10em; line-height: 1.25; "
        f'text-transform: uppercase; color: {text_color}; white-space: nowrap">'
        f"{escape(label)}</div>"
    )
