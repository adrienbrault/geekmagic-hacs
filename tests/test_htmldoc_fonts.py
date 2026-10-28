"""Font-state guarantees of the layered render path.

Measurement (``_textfit``) and rendering must always see the same font
collection: measuring with the embedded faces while the render falls
back to different fonts is how Python-fitted text overflows its cell.
When the process-wide registry is live, layers inherit it; when
registration failed, the embedded font bytes must ride every html layer
instead.
"""

from __future__ import annotations

from unittest.mock import patch

from custom_components.geekmagic import htmldoc


class TestLayerFonts:
    """render_layers_image keeps measure and render on the same fonts."""

    def _captured_layers(self, layers):
        captured = {}

        def fake_render_layers(layers, *, width, height, background):
            captured["layers"] = layers
            return (width, height, bytes(width * height * 4))

        with (
            patch.object(htmldoc.blitz_py, "render_layers", fake_render_layers),
            patch.object(htmldoc, "HAS_ENGINE", True),
        ):
            assert htmldoc.render_layers_image(layers, 10, 10) is not None
        return captured["layers"]

    def test_registry_live_layers_untouched(self):
        with patch.object(htmldoc, "font_param", return_value=None):
            layers = self._captured_layers([{"html": "<body>x</body>", "width": 5, "height": 5}])
        assert "fonts" not in layers[0]

    def test_registry_down_fonts_ride_each_layer(self):
        font_bytes = [b"fake-font"]
        with patch.object(htmldoc, "font_param", return_value=font_bytes):
            layers = self._captured_layers(
                [
                    {"html": "<body>x</body>", "width": 5, "height": 5},
                    {"html": "<body>y</body>", "width": 5, "height": 5, "fonts": [b"own"]},
                ]
            )
        assert layers[0]["fonts"] == font_bytes
        # A layer that already carries fonts keeps them.
        assert layers[1]["fonts"] == [b"own"]

    def test_fonts_registered_is_thread_safe_and_sticky(self):
        """Concurrent first calls register exactly once."""
        import threading

        calls = []

        def fake_register(fonts, *, default_family=None):
            calls.append(default_family)
            return ["Nunito"]

        registry = htmldoc._FontRegistry()
        with patch.object(htmldoc.blitz_py, "register_fonts", fake_register):
            threads = [threading.Thread(target=registry.registered) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        assert calls == ["Nunito"]
        assert registry.registered() is True
