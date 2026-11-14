"""Tests for the Image widget (static picture from a URL or local file)."""

from datetime import UTC, datetime

import pytest
from PIL import Image

from custom_components.geekmagic.const import (
    IMAGE_SOURCE_DEFAULT_REFRESH,
    IMAGE_SOURCE_REFRESH_SECONDS,
)
from custom_components.geekmagic.htmldoc import HAS_ENGINE, CellContext
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.image import ImageWidget
from custom_components.geekmagic.widgets.state import WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

GREEN, RED, BLUE = (0, 200, 0), (220, 0, 0), (0, 0, 220)


def widget(label: str | None = None, **options) -> ImageWidget:
    return ImageWidget(WidgetConfig(widget_type="image", slot=0, label=label, options=options))


def state(image: Image.Image | None = None) -> WidgetState:
    return WidgetState(image=image, now=datetime(2026, 11, 14, tzinfo=UTC))


def banded_picture() -> Image.Image:
    """A 2:1 picture: green left quarter, red middle half, blue right quarter."""
    image = Image.new("RGB", (200, 100), RED)
    image.paste(GREEN, (0, 0, 50, 100))
    image.paste(BLUE, (150, 0, 200, 100))
    return image


def render(fit: str) -> Image.Image:
    layout = FullscreenLayout()
    layout.theme = DEFAULT_THEME
    layout.set_widget(0, widget(source="/local/x.png", fit=fit))
    renderer = Renderer()
    img, draw = renderer.create_canvas(background=layout.theme.background)
    layout.render(renderer, draw, {0: state(banded_picture())})
    return renderer.finalize(img).convert("RGB")


def close(pixel, color, tol=40) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(pixel, color, strict=True))


class TestRegistration:
    def test_registered(self):
        assert WIDGET_CLASSES["image"] is ImageWidget

    def test_schema(self):
        schema = WIDGET_TYPE_SCHEMAS["image"]
        assert schema["needs_entity"] is False
        options = {o["key"]: o for o in schema["options"]}
        assert options["source"]["type"] == "text"
        assert options["source"]["label"]
        assert options["fit"]["options"] == ["contain", "cover", "stretch"]
        assert options["refresh"]["default"] == IMAGE_SOURCE_DEFAULT_REFRESH
        assert set(options["refresh"]["options"]) == set(IMAGE_SOURCE_REFRESH_SECONDS)


class TestOptions:
    def test_defaults(self):
        w = widget(source=" https://example.com/a.png ")
        assert w.source == "https://example.com/a.png"
        assert w.fit == "contain"
        assert w.show_label is False
        assert w.refresh_seconds == IMAGE_SOURCE_REFRESH_SECONDS[IMAGE_SOURCE_DEFAULT_REFRESH]

    def test_refresh_option(self):
        assert widget(refresh="5 min").refresh_seconds == 300

    def test_unknown_refresh_falls_back(self):
        assert widget(refresh="bogus").refresh_seconds == 3600

    def test_tracks_no_entity(self):
        assert widget(source="www/a.png").get_entities() == []


class TestRenderHtml:
    def test_placeholder_names_the_file(self):
        fragment = widget(source="https://example.com/pics/doorbell.gif?v=2").render_html(
            CTX, state()
        )
        assert "DOORBELL.GIF" in fragment.upper()
        assert "<img" not in fragment

    def test_placeholder_prefers_label(self):
        fragment = widget(label="Logo", source="www/a.png").render_html(CTX, state())
        assert "LOGO" in fragment

    def test_placeholder_uses_rendered_label_template(self):
        """A templated label shows its rendered value, not the raw source."""
        label = "{{ states('sensor.camera_name') }}"
        templated = WidgetState(
            now=datetime(2026, 11, 14, tzinfo=UTC), templates={label: "Front Door"}
        )
        fragment = widget(label=label, source="www/a.png").render_html(CTX, templated)
        assert "FRONT DOOR" in fragment
        assert "states(" not in fragment

    def test_placeholder_without_source(self):
        assert "NO IMAGE" in widget().render_html(CTX, state())

    @pytest.mark.parametrize(
        ("fit", "css"), [("contain", "contain"), ("cover", "cover"), ("stretch", "fill")]
    )
    def test_fit_maps_to_object_fit(self, fit, css):
        fragment = widget(source="a/b.png", fit=fit).render_html(
            CTX, state(Image.new("RGB", (4, 4)))
        )
        assert f"object-fit: {css}" in fragment
        assert "data:image/png;base64," in fragment

    def test_unknown_fit_falls_back_to_contain(self):
        fragment = widget(fit="zoom").render_html(CTX, state(Image.new("RGB", (4, 4))))
        assert "object-fit: contain" in fragment

    def test_label_capsule(self):
        fragment = widget(label="Front", show_label=True).render_html(
            CTX, state(Image.new("RGB", (4, 4)))
        )
        assert "FRONT" in fragment.upper()
        assert "border-radius: 999px" in fragment

    def test_transparency_kept_in_data_uri(self):
        """RGBA pictures are not flattened to black (logos on the theme bg)."""
        import base64
        from io import BytesIO

        fragment = widget().render_html(CTX, state(Image.new("RGBA", (4, 4), (0, 0, 0, 0))))
        payload = fragment.split("base64,", 1)[1].split('"', 1)[0]
        decoded = Image.open(BytesIO(base64.b64decode(payload)))
        assert decoded.mode == "RGBA"


@pytest.mark.skipif(not HAS_ENGINE, reason="blitz-py engine required")
class TestFitPixels:
    """The fit modes as the engine actually paints them (240x240 cell)."""

    def test_contain_letterboxes(self):
        img = render("contain")
        assert close(img.getpixel((120, 120)), RED)
        assert close(img.getpixel((10, 120)), GREEN)  # whole width visible
        assert close(img.getpixel((120, 15)), DEFAULT_THEME.background)  # band above

    def test_cover_crops_sides(self):
        img = render("cover")
        assert close(img.getpixel((120, 15)), RED)  # fills the height
        assert close(img.getpixel((10, 120)), RED)  # green quarter cropped away

    def test_stretch_fills_distorted(self):
        img = render("stretch")
        assert close(img.getpixel((120, 15)), RED)
        assert close(img.getpixel((10, 120)), GREEN)
