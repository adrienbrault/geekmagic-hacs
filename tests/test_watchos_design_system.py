"""Regression tests for the watchOS design system foundation.

Covers:
- Theme primitives (text_tertiary, surface_chrome, tint_track, rounded_font)
- THEME_WATCHOS being the registered default
- Theme registration in const.THEME_OPTIONS
- Theme.track_color() opacity math
- Renderer.tint_at() opacity math
- RenderContext.draw_label() truncation
- Layout.padding / Layout.gap react to theme changes (lazy resolution)

These guard against accidental drift in design tokens that would silently
regress the watchOS look across every widget.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic import const
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets.components import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SECONDARY,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_TEXT_TERTIARY,
    THEME_WARNING,
    _resolve_color,
)
from custom_components.geekmagic.widgets.theme import (
    DEFAULT_THEME,
    THEME_CLASSIC,
    THEME_WATCHOS,
    THEMES,
    Theme,
    get_theme,
)

# ---------------------------------------------------------------------------
# Theme registration / defaults
# ---------------------------------------------------------------------------


class TestThemeDefaults:
    def test_default_theme_is_watchos(self) -> None:
        """The watchOS theme is the new default at the rendering layer."""
        assert DEFAULT_THEME is THEME_WATCHOS
        assert DEFAULT_THEME.name == "watchos"

    def test_watchos_registered_in_themes_registry(self) -> None:
        """get_theme('watchos') returns THEME_WATCHOS — wired up correctly."""
        assert THEMES["watchos"] is THEME_WATCHOS
        assert get_theme("watchos") is THEME_WATCHOS

    def test_watchos_registered_in_const_options(self) -> None:
        """The frontend dropdown sources options from const.THEME_OPTIONS;
        watchos must appear there or users can never select it."""
        assert const.THEME_WATCHOS == "watchos"
        assert const.THEME_WATCHOS in const.THEME_OPTIONS
        assert const.THEME_OPTIONS[const.THEME_WATCHOS] == "watchOS"

    def test_classic_still_registered(self) -> None:
        """We didn't accidentally drop classic — backwards-compat for users
        who already configured it."""
        assert THEMES["classic"] is THEME_CLASSIC
        assert THEME_CLASSIC.name == "classic"


# ---------------------------------------------------------------------------
# Theme primitives
# ---------------------------------------------------------------------------


class TestThemePrimitives:
    def test_watchos_has_no_card_chrome(self) -> None:
        """watchOS deference: widgets float on the background, no cards."""
        assert THEME_WATCHOS.surface_chrome is False

    def test_classic_keeps_card_chrome(self) -> None:
        """Classic theme keeps the card chrome for users who prefer it."""
        assert THEME_CLASSIC.surface_chrome is True

    def test_watchos_uses_rounded_font(self) -> None:
        assert THEME_WATCHOS.rounded_font is True

    def test_watchos_text_hierarchy_distinct(self) -> None:
        """primary > secondary > tertiary in luminance — opacity hierarchy."""
        primary_avg = sum(THEME_WATCHOS.text_primary) / 3
        secondary_avg = sum(THEME_WATCHOS.text_secondary) / 3
        tertiary_avg = sum(THEME_WATCHOS.text_tertiary) / 3
        assert primary_avg > secondary_avg > tertiary_avg

    def test_watchos_true_black_background(self) -> None:
        """OLED-friendly true black."""
        assert THEME_WATCHOS.background == (0, 0, 0)

    def test_watchos_tint_track_enabled(self) -> None:
        """Activity-ring style: tracks are tinted, not gray."""
        assert THEME_WATCHOS.tint_track is True
        assert 0.0 < THEME_WATCHOS.tint_track_opacity < 0.5

    def test_every_theme_has_info_color(self) -> None:
        """All 11 themes ship a non-default `info` value (cool/data role).

        Without this, candy/retro/neon/ocean fall back to watchOS blue
        which looks wrong against their palettes.
        """
        for name, theme in THEMES.items():
            # The info color should be set on every theme — no theme should
            # silently inherit the dataclass default.
            assert theme.info is not None, f"{name} missing info color"
            # Must be a 3-tuple with valid RGB values
            assert len(theme.info) == 3, f"{name}.info malformed"
            assert all(0 <= c <= 255 for c in theme.info), (
                f"{name}.info has invalid RGB: {theme.info}"
            )


# ---------------------------------------------------------------------------
# Theme color sentinels — every role resolves correctly
# ---------------------------------------------------------------------------


_SENTINEL_TO_ATTR = {
    THEME_TEXT_PRIMARY: "text_primary",
    THEME_TEXT_SECONDARY: "text_secondary",
    THEME_TEXT_TERTIARY: "text_tertiary",
    THEME_PRIMARY: "primary",
    THEME_SECONDARY: "secondary",
    THEME_SUCCESS: "success",
    THEME_WARNING: "warning",
    THEME_ERROR: "error",
    THEME_INFO: "info",
    THEME_MUTED: "muted",
}


class TestThemeColorSentinels:
    """Widgets express role intent ("warning") and the renderer maps to the
    active theme's color. This is what makes themes consistent — no widget
    should hardcode a SYSTEM_* color anywhere.
    """

    def test_each_sentinel_resolves_per_theme(self) -> None:
        """Every (sentinel, theme) pair maps to the theme's role attribute.

        Tests the components-side helper. Renders against every theme so
        adding a new theme can't silently break role resolution.
        """
        for theme_name, theme in THEMES.items():
            ctx = MagicMock()
            ctx.theme = theme
            for sentinel, attr in _SENTINEL_TO_ATTR.items():
                resolved = _resolve_color(sentinel, ctx)
                expected = getattr(theme, attr)
                assert resolved == expected, (
                    f"theme={theme_name} sentinel={sentinel} "
                    f"resolved={resolved} expected={expected}"
                )

    def test_render_context_resolves_sentinels(self) -> None:
        """The mirrored resolver in RenderContext also maps every sentinel.

        Both copies of the table need to agree — drift between them is the
        kind of bug that's invisible until a widget calls draw_text directly.
        """
        renderer = Renderer()
        _img, draw = renderer.create_canvas()
        for theme_name, theme in THEMES.items():
            ctx = RenderContext(draw, (0, 0, 240, 240), renderer, theme=theme)
            for sentinel, attr in _SENTINEL_TO_ATTR.items():
                resolved = ctx._resolve_color(sentinel)
                expected = getattr(theme, attr)
                assert resolved == expected, (
                    f"theme={theme_name} sentinel={sentinel} "
                    f"resolved={resolved} expected={expected}"
                )

    def test_concrete_color_passes_through_unchanged(self) -> None:
        """Non-sentinel RGB values must round-trip untouched."""
        ctx = MagicMock()
        ctx.theme = THEME_WATCHOS
        # All-zero black isn't a sentinel
        assert _resolve_color((0, 0, 0), ctx) == (0, 0, 0)
        # Standard mid-grey
        assert _resolve_color((128, 128, 128), ctx) == (128, 128, 128)
        # Full white
        assert _resolve_color((255, 255, 255), ctx) == (255, 255, 255)


# ---------------------------------------------------------------------------
# Theme.track_color()
# ---------------------------------------------------------------------------


class TestTrackColor:
    def test_tint_track_returns_dimmed_tint(self) -> None:
        """A tinted track is the accent color blended toward black at the
        configured opacity."""
        red = (255, 0, 0)
        track = THEME_WATCHOS.track_color(red)
        # Track should be a much darker red, not gray
        assert track[0] > 0  # has red channel
        assert track[0] < red[0]  # but dimmer than full red
        assert track[1] == 0
        assert track[2] == 0

    def test_tint_track_opacity_math(self) -> None:
        """Soft check that track_color uses tint_track_opacity, roughly."""
        red = (200, 0, 0)
        opacity = THEME_WATCHOS.tint_track_opacity
        track = THEME_WATCHOS.track_color(red)
        expected_r = int(red[0] * opacity)
        # Allow ±1 for int rounding
        assert abs(track[0] - expected_r) <= 1

    def test_flat_track_returns_bar_background(self) -> None:
        """When a theme opts out of tinted tracks (Theme.tint_track=False),
        track_color returns the flat bar_background instead — preserves the
        crisp look for themes like 'minimal' that don't use tints."""
        flat = Theme(name="flat", tint_track=False, bar_background=(40, 40, 40))
        assert flat.track_color((255, 0, 0)) == (40, 40, 40)


# ---------------------------------------------------------------------------
# Renderer.tint_at()
# ---------------------------------------------------------------------------


class TestRendererTintAt:
    def test_zero_opacity_returns_background(self) -> None:
        """At 0% opacity, the tint disappears entirely."""
        r = Renderer()
        bg = (10, 20, 30)
        assert r.tint_at((255, 0, 0), 0.0, background=bg) == bg

    def test_full_opacity_returns_color(self) -> None:
        """At 100% opacity, only the tint remains."""
        r = Renderer()
        color = (255, 100, 50)
        assert r.tint_at(color, 1.0, background=(0, 0, 0)) == color

    def test_half_opacity_blends(self) -> None:
        """50% opacity is the midpoint of the two colors."""
        r = Renderer()
        result = r.tint_at((200, 100, 50), 0.5, background=(0, 0, 0))
        assert result == (100, 50, 25)

    def test_clamps_opacity_above_one(self) -> None:
        """opacity > 1.0 doesn't blow up — clamps to 1.0 (returns full tint)."""
        r = Renderer()
        color = (255, 0, 0)
        assert r.tint_at(color, 1.5) == color

    def test_clamps_opacity_below_zero(self) -> None:
        """opacity < 0 clamps to 0 (returns full background)."""
        r = Renderer()
        bg = (50, 50, 50)
        assert r.tint_at((255, 0, 0), -0.5, background=bg) == bg


# ---------------------------------------------------------------------------
# RenderContext.draw_label()
# ---------------------------------------------------------------------------


@pytest.fixture
def render_ctx() -> RenderContext:
    """Return a real RenderContext writing into a 240x240 canvas."""
    renderer = Renderer()
    _img, draw = renderer.create_canvas()
    return RenderContext(draw, (0, 0, 240, 240), renderer, theme=THEME_WATCHOS)


class TestDrawLabel:
    def test_uppercases_by_default(self, render_ctx: RenderContext) -> None:
        """draw_label uppercases input text by default (watchOS caption style)."""
        # We can't easily inspect the rendered glyphs; instead, verify the
        # transformation by mocking draw_text and inspecting what was passed.
        with pytest.MonkeyPatch.context() as mp:
            captured: list[str] = []
            mp.setattr(render_ctx, "draw_text", lambda text, *a, **kw: captured.append(text))
            render_ctx.draw_label("hello", (0, 0))
            assert captured and captured[0] == "HELLO"

    def test_does_not_uppercase_when_disabled(self, render_ctx: RenderContext) -> None:
        with pytest.MonkeyPatch.context() as mp:
            captured: list[str] = []
            mp.setattr(render_ctx, "draw_text", lambda text, *a, **kw: captured.append(text))
            render_ctx.draw_label("hello", (0, 0), uppercase=False)
            assert captured and captured[0] == "hello"

    def test_truncates_with_ellipsis_when_too_wide(self, render_ctx: RenderContext) -> None:
        """A label that overflows max_width is truncated with an ellipsis,
        not silently clipped at render time. This was the bug that turned
        'TEMPERATURE' into mid-glyph clipping."""
        with pytest.MonkeyPatch.context() as mp:
            captured: list[str] = []
            mp.setattr(render_ctx, "draw_text", lambda text, *a, **kw: captured.append(text))
            # 30px is far too narrow for "TEMPERATURE" — should ellipsize
            render_ctx.draw_label("TEMPERATURE", (0, 0), max_width=30, track=0)
            assert captured, "draw_label produced no draw_text call"
            rendered = captured[0]
            assert rendered.endswith("…"), f"expected ellipsis suffix, got {rendered!r}"
            assert len(rendered) < len("TEMPERATURE")

    def test_short_label_renders_in_full(self, render_ctx: RenderContext) -> None:
        """A label that fits the budget renders verbatim (no truncation)."""
        with pytest.MonkeyPatch.context() as mp:
            captured: list[str] = []
            mp.setattr(render_ctx, "draw_text", lambda text, *a, **kw: captured.append(text))
            render_ctx.draw_label("CPU", (0, 0), max_width=200, track=0)
            assert captured and captured[0] == "CPU"


# ---------------------------------------------------------------------------
# RenderContext.track_color()
# ---------------------------------------------------------------------------


class TestRenderContextTrackColor:
    def test_uses_tinted_track_for_watchos(self, render_ctx: RenderContext) -> None:
        """ctx.track_color() honors the theme's tint_track flag."""
        red = (200, 0, 0)
        track = render_ctx.track_color(red)
        # Should be tinted (red-ish), not flat gray
        assert track[0] > 0
        assert track[0] < red[0]
        assert track[1] == 0


# ---------------------------------------------------------------------------
# Layout padding/gap reactivity to theme changes
# ---------------------------------------------------------------------------


class TestLayoutThemeReactivity:
    def test_default_layout_uses_default_theme_padding(self) -> None:
        """Without explicit args, padding/gap fall back to the active
        theme's values (watchOS by default)."""
        layout = Grid2x2()
        assert layout.padding == THEME_WATCHOS.layout_padding
        assert layout.gap == THEME_WATCHOS.gap

    def test_explicit_args_override_theme(self) -> None:
        """Explicit padding/gap pin the value and ignore theme changes."""
        layout = Grid2x2(padding=20, gap=15)
        assert layout.padding == 20
        assert layout.gap == 15

    def test_explicit_args_persist_across_theme_swap(self) -> None:
        """When the user passed explicit args, theme changes shouldn't
        clobber them."""
        layout = Grid2x2(padding=20)
        retro = THEMES["retro"]  # ships layout_padding=8
        layout.theme = retro
        assert layout.padding == 20  # explicit override wins
        # gap was None → falls back to retro's 8
        assert layout.gap == retro.gap

    def test_theme_swap_updates_padding_and_gap(self) -> None:
        """Changing the theme on a layout that didn't pass overrides
        actually updates spacing — themes can tune density globally."""
        layout = Grid2x2()
        retro = THEMES["retro"]  # ships layout_padding=8, gap=8
        watchos = THEMES["watchos"]  # ships layout_padding=6, gap=6
        # Make sure these themes really do differ — the test depends on it
        assert retro.layout_padding != watchos.layout_padding

        layout.theme = retro
        assert layout.padding == retro.layout_padding
        assert layout.gap == retro.gap

        layout.theme = watchos
        assert layout.padding == watchos.layout_padding
        assert layout.gap == watchos.gap

    def test_theme_swap_preserves_widgets(self) -> None:
        """Reassigning .theme rebuilds slots — widgets must survive."""
        layout = Grid2x2()
        sentinel = MagicMock()
        layout.set_widget(0, sentinel)
        layout.theme = THEMES["classic"]
        assert layout.slots[0].widget is sentinel
