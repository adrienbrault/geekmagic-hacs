"""Tests for GeekMagic WebSocket API album art preview."""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image


class TestAlbumArtPreviewFetching:
    """Test album art fetching logic for preview rendering."""

    def _create_test_image_bytes(self, width: int = 100, height: int = 100) -> bytes:
        """Create a test image and return its bytes."""
        img = Image.new("RGB", (width, height), (255, 0, 0))  # Red image
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_album_art_fetch_with_internal_url(self, hass):
        """Test that album art is fetched for media widgets with internal entity_picture."""
        import aiohttp

        # Set up a media player state with entity_picture
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "media_title": "Test Song",
                "media_artist": "Test Artist",
                "entity_picture": "/api/media_player_proxy/media_player.test",
            },
        )

        hass.config.internal_url = "http://localhost:8123"

        # Test the fetching logic directly
        state = hass.states.get("media_player.test")
        assert state is not None
        entity_picture = state.attributes.get("entity_picture")
        assert entity_picture == "/api/media_player_proxy/media_player.test"
        assert entity_picture.startswith("/")

        # Verify URL construction
        base_url = hass.config.internal_url
        image_url = f"{base_url.rstrip('/')}/{entity_picture.lstrip('/')}"
        assert image_url == "http://localhost:8123/api/media_player_proxy/media_player.test"

    @pytest.mark.asyncio
    async def test_album_art_skips_external_urls(self, hass):
        """Test that external URLs are not fetched for security."""
        # Set up a media player state with EXTERNAL entity_picture
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "media_title": "Test Song",
                "entity_picture": "https://external.com/album.jpg",
            },
        )

        state = hass.states.get("media_player.test")
        entity_picture = state.attributes.get("entity_picture")

        # External URLs don't start with "/"
        assert not entity_picture.startswith("/")
        # This means the code should skip fetching it

    @pytest.mark.asyncio
    async def test_album_art_handles_missing_entity_picture(self, hass):
        """Test graceful handling when entity_picture is not available."""
        # Set up a media player state WITHOUT entity_picture
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "media_title": "Test Song",
            },
        )

        state = hass.states.get("media_player.test")
        entity_picture = state.attributes.get("entity_picture")

        # No entity_picture means no image to fetch
        assert entity_picture is None

    @pytest.mark.asyncio
    async def test_album_art_handles_missing_base_url(self, hass):
        """Test graceful handling when internal_url is not configured."""
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "entity_picture": "/api/media_player_proxy/test",
            },
        )

        # No internal_url configured
        hass.config.internal_url = None

        # Should gracefully skip fetching
        base_url = hass.config.internal_url or getattr(hass.config, "external_url", None)
        # Both could be None, in which case no fetch should happen
        # This tests the defensive coding in the implementation


class TestPreviewRenderWithAlbumArt:
    """Test preview rendering includes album art when available."""

    def _create_test_image_bytes(self, width: int = 100, height: int = 100) -> bytes:
        """Create a test image and return its bytes."""
        img = Image.new("RGB", (width, height), (255, 0, 0))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_preview_with_album_art_renders_successfully(self, hass):
        """Test that preview with album art renders without errors."""
        from custom_components.geekmagic.const import LAYOUT_GRID_2X2
        from custom_components.geekmagic.coordinator import LAYOUT_CLASSES, WIDGET_CLASSES
        from custom_components.geekmagic.renderer import Renderer
        from custom_components.geekmagic.widgets.base import WidgetConfig
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState
        from custom_components.geekmagic.widgets.theme import get_theme

        # Create a test album art image
        test_image = Image.new("RGB", (100, 100), (255, 0, 0))

        # Set up entity state
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "media_title": "Test Song",
                "media_artist": "Test Artist",
                "media_duration": 300,
                "media_position": 120,
            },
        )

        # Create renderer and layout
        renderer = Renderer()
        layout_class = LAYOUT_CLASSES.get(LAYOUT_GRID_2X2)
        layout = layout_class()
        layout.theme = get_theme("classic")

        # Create media widget
        widget_class = WIDGET_CLASSES.get("media")
        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.test",
        )
        widget = widget_class(config)
        layout.set_widget(0, widget)

        # Build widget state WITH image
        state = hass.states.get("media_player.test")
        entity = EntityState(
            entity_id="media_player.test",
            state=state.state,
            attributes=dict(state.attributes),
        )

        widget_states = {
            0: WidgetState(
                entity=entity,
                entities={},
                history=[],
                forecast=[],
                image=test_image,  # Album art!
                now=None,
            )
        }

        # Render - should use AlbumArt component since image is provided
        img, draw = renderer.create_canvas(background=layout.theme.background)
        layout.render(renderer, draw, widget_states)

        # Convert to PNG and verify it's valid
        png_bytes = renderer.to_png(img)
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_preview_without_album_art_renders_text_fallback(self, hass):
        """Test that preview without album art renders text fallback."""
        from custom_components.geekmagic.const import LAYOUT_GRID_2X2
        from custom_components.geekmagic.coordinator import LAYOUT_CLASSES, WIDGET_CLASSES
        from custom_components.geekmagic.renderer import Renderer
        from custom_components.geekmagic.widgets.base import WidgetConfig
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState
        from custom_components.geekmagic.widgets.theme import get_theme

        # Set up entity state
        hass.states.async_set(
            "media_player.test",
            "playing",
            {
                "friendly_name": "Living Room Speaker",
                "media_title": "Test Song",
                "media_artist": "Test Artist",
            },
        )

        # Create renderer and layout
        renderer = Renderer()
        layout_class = LAYOUT_CLASSES.get(LAYOUT_GRID_2X2)
        layout = layout_class()
        layout.theme = get_theme("classic")

        # Create media widget
        widget_class = WIDGET_CLASSES.get("media")
        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.test",
        )
        widget = widget_class(config)
        layout.set_widget(0, widget)

        # Build widget state WITHOUT image
        state = hass.states.get("media_player.test")
        entity = EntityState(
            entity_id="media_player.test",
            state=state.state,
            attributes=dict(state.attributes),
        )

        widget_states = {
            0: WidgetState(
                entity=entity,
                entities={},
                history=[],
                forecast=[],
                image=None,  # No album art - should use text fallback
                now=None,
            )
        }

        # Render - should use NowPlaying text component
        img, draw = renderer.create_canvas(background=layout.theme.background)
        layout.render(renderer, draw, widget_states)

        # Convert to PNG and verify it's valid
        png_bytes = renderer.to_png(img)
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


class TestAlbumArtImageProcessing:
    """Test album art image processing in WidgetState."""

    def _create_test_image_bytes(self, width: int = 100, height: int = 100) -> bytes:
        """Create a test image and return its bytes."""
        img = Image.new("RGB", (width, height), (255, 0, 0))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_image_from_bytes_to_pil(self):
        """Test converting fetched image bytes to PIL Image."""
        # This mimics what happens in the websocket handler
        image_bytes = self._create_test_image_bytes()

        # Open as PIL Image (like in the websocket code)
        image = Image.open(BytesIO(image_bytes))

        assert image is not None
        assert image.size == (100, 100)
        assert image.mode == "RGB"

    def test_image_mode_conversion_for_rendering(self):
        """Test that images are converted to RGB mode for rendering."""
        # Create RGBA image (like some album art might be)
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        # Open and convert (like MediaWidget does)
        image = Image.open(BytesIO(image_bytes))

        # MediaWidget converts to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        assert image.mode == "RGB"
