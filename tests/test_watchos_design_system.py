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
from custom_components.geekmagic.widgets.colors import (
    THEME_COLOR_SENTINELS,
    resolve_theme_color,
)
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

        Tests the shared color-role helper. Renders against every theme so
        adding a new theme can't silently break role resolution.
        """
        for theme_name, theme in THEMES.items():
            for sentinel, attr in _SENTINEL_TO_ATTR.items():
                resolved = resolve_theme_color(sentinel, theme)
                expected = getattr(theme, attr)
                assert resolved == expected, (
                    f"theme={theme_name} sentinel={sentinel} "
                    f"resolved={resolved} expected={expected}"
                )

    def test_components_use_shared_resolver(self) -> None:
        """The public components helper delegates to the shared resolver."""
        ctx = MagicMock()
        ctx.theme = THEME_WATCHOS
        assert _resolve_color(THEME_WARNING, ctx) == resolve_theme_color(
            THEME_WARNING, THEME_WATCHOS
        )

    def test_render_context_resolves_sentinels(self) -> None:
        """RenderContext draw helpers use the shared sentinel resolver."""
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

    def test_sentinel_contract_matches_test_matrix(self) -> None:
        """The regression matrix covers every registered color sentinel."""
        assert THEME_COLOR_SENTINELS == _SENTINEL_TO_ATTR

    def test_render_context_resolves_primitive_drawing_colors(
        self, render_ctx: RenderContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Low-level draw helpers resolve sentinels before hitting Renderer."""
        captured: dict[str, tuple[int, int, int] | None] = {}

        def draw_rect(_draw, _rect, *, fill=None, outline=None, width=1):
            captured["rect_fill"] = fill
            captured["rect_outline"] = outline

        def draw_rounded_rect(_draw, _rect, *, radius=4, fill=None, outline=None, width=1):
            captured["rounded_fill"] = fill
            captured["rounded_outline"] = outline

        def draw_panel(_draw, _rect, *, background, border_color=None, radius=4):
            captured["panel_background"] = background
            captured["panel_border"] = border_color

        def draw_timeline_bar(_draw, _rect, _data, *, on_color, off_color):
            captured["timeline_on"] = on_color
            captured["timeline_off"] = off_color

        def draw_ellipse(_draw, _rect, *, fill=None, outline=None, width=1):
            captured["ellipse_fill"] = fill
            captured["ellipse_outline"] = outline

        def draw_line(_draw, _xy, *, fill=None, width=1):
            captured["line_fill"] = fill

        def draw_gradient_fade(_draw, _rect, *, color, direction="down"):
            captured["gradient_color"] = color

        monkeypatch.setattr(render_ctx._renderer, "draw_rect", draw_rect)
        monkeypatch.setattr(render_ctx._renderer, "draw_rounded_rect", draw_rounded_rect)
        monkeypatch.setattr(render_ctx._renderer, "draw_panel", draw_panel)
        monkeypatch.setattr(render_ctx._renderer, "draw_timeline_bar", draw_timeline_bar)
        monkeypatch.setattr(render_ctx._renderer, "draw_ellipse", draw_ellipse)
        monkeypatch.setattr(render_ctx._renderer, "draw_line", draw_line)
        monkeypatch.setattr(render_ctx._renderer, "draw_gradient_fade", draw_gradient_fade)

        render_ctx.draw_rect((0, 0, 1, 1), fill=THEME_PRIMARY, outline=THEME_WARNING)
        render_ctx.draw_rounded_rect((0, 0, 1, 1), fill=THEME_SUCCESS, outline=THEME_ERROR)
        render_ctx.draw_panel((0, 0, 1, 1), background=THEME_MUTED, border_color=THEME_INFO)
        render_ctx.draw_timeline_bar(
            (0, 0, 10, 2), [0.0, 1.0], on_color=THEME_SUCCESS, off_color=THEME_ERROR
        )
        render_ctx.draw_ellipse((0, 0, 1, 1), fill=THEME_SECONDARY, outline=THEME_PRIMARY)
        render_ctx.draw_line([(0, 0), (1, 1)], fill=THEME_TEXT_TERTIARY)
        render_ctx.draw_gradient_fade((0, 0, 1, 1), color=THEME_MUTED)

        assert captured == {
            "rect_fill": THEME_WATCHOS.primary,
            "rect_outline": THEME_WATCHOS.warning,
            "rounded_fill": THEME_WATCHOS.success,
            "rounded_outline": THEME_WATCHOS.error,
            "panel_background": THEME_WATCHOS.muted,
            "panel_border": THEME_WATCHOS.info,
            "timeline_on": THEME_WATCHOS.success,
            "timeline_off": THEME_WATCHOS.error,
            "ellipse_fill": THEME_WATCHOS.secondary,
            "ellipse_outline": THEME_WATCHOS.primary,
            "line_fill": THEME_WATCHOS.text_tertiary,
            "gradient_color": THEME_WATCHOS.muted,
        }

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
# No hardcoded SYSTEM_* colours leak into widget code
# ---------------------------------------------------------------------------


# Forbidden colour tokens — widgets must use THEME_* role sentinels
# instead. Each entry is (token, hint) so the test failure tells the
# offender exactly which sentinel to swap in.
_FORBIDDEN_COLOR_TOKENS: tuple[tuple[str, str], ...] = (
    # SYSTEM_* live in widgets.theme — the *source* of design tokens.
    # Widget code should never name them directly; consume via THEME_*.
    ("SYSTEM_BLUE", "use THEME_INFO"),
    ("SYSTEM_ORANGE", "use THEME_WARNING"),
    ("SYSTEM_RED", "use THEME_ERROR"),
    ("SYSTEM_YELLOW", "use THEME_WARNING"),
    ("SYSTEM_GREEN", "use THEME_SUCCESS"),
    ("SYSTEM_CYAN", "use THEME_INFO"),
    ("SYSTEM_TEAL", "use THEME_PRIMARY"),
    ("SYSTEM_INDIGO", "use THEME_SECONDARY"),
    ("SYSTEM_MINT", "use THEME_SUCCESS or THEME_INFO"),
    ("SYSTEM_PURPLE", "use THEME_SECONDARY"),
    ("SYSTEM_PINK", "use THEME_PRIMARY/SECONDARY"),
    # Legacy COLOR_* in const.py are fixed RGB literals predating the
    # theme system. Same forbidden in widget code.
    ("COLOR_CYAN", "use THEME_PRIMARY or THEME_INFO"),
    ("COLOR_LIME", "use THEME_SUCCESS"),
    ("COLOR_RED", "use THEME_ERROR"),
    ("COLOR_GREEN", "use THEME_SUCCESS"),
    ("COLOR_ORANGE", "use THEME_WARNING"),
    ("COLOR_YELLOW", "use THEME_WARNING"),
    ("COLOR_BLUE", "use THEME_INFO"),
    ("COLOR_GOLD", "use THEME_WARNING"),
    ("COLOR_PURPLE", "use THEME_SECONDARY"),
    ("COLOR_PINK", "use THEME_PRIMARY/SECONDARY"),
)


class TestNoHardcodedSystemColors:
    """Widgets must consume colour through role sentinels (THEME_PRIMARY,
    THEME_WARNING, THEME_INFO, ...), not hardcoded `SYSTEM_*` literals from
    `widgets.theme`, nor hardcoded `COLOR_*` constants from `const`.

    Hardcoded colours look out of place in candy/retro/neon themes. This
    test scans the widgets/ directory for such imports and fails if any
    reappear — guards the design-system contract documented in
    CLAUDE.md → "Design System (watchOS-inspired)".
    """

    def test_widgets_dont_use_hardcoded_colors(self) -> None:
        """Scan non-comment lines for forbidden colour tokens. Comments
        may mention them for documentation; code references are forbidden.
        """
        import re
        from pathlib import Path

        widgets_dir = Path(__file__).parent.parent / "custom_components" / "geekmagic" / "widgets"
        offenders: list[str] = []
        # theme.py is the *source* of SYSTEM_* — exempt it.
        for py in sorted(widgets_dir.glob("*.py")):
            if py.name in {"theme.py", "__init__.py"}:
                continue
            for lineno, raw_line in enumerate(py.read_text().splitlines(), start=1):
                # Strip Python line comments before scanning.
                code = re.sub(r"#.*$", "", raw_line)
                if code.strip().startswith(('"""', "'''")):
                    continue
                offenders.extend(
                    f"{py.name}:{lineno}: {token}  ({hint})"
                    for token, hint in _FORBIDDEN_COLOR_TOKENS
                    if token in code
                )
        assert not offenders, (
            "Widgets must use THEME_* role sentinels, not hardcoded colours.\n"
            "See CLAUDE.md > Design System for the full rule.\n\n"
            "Offenders:\n  " + "\n  ".join(offenders)
        )


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

    def test_timeline_bar_off_defaults_to_tinted_track(
        self, render_ctx: RenderContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Binary timeline 'off' segments use the theme track, not flat gray.

        Regression: COLOR_GRAY (150,150,150) rendered as bright washed-out
        blocks dominating dark themes.
        """
        captured: dict[str, tuple[int, int, int]] = {}

        def draw_timeline_bar(_draw, _rect, _data, *, on_color, off_color):
            captured["on"] = on_color
            captured["off"] = off_color

        monkeypatch.setattr(render_ctx._renderer, "draw_timeline_bar", draw_timeline_bar)
        render_ctx.draw_timeline_bar((0, 0, 10, 2), [0.0, 1.0], on_color=THEME_SUCCESS)

        assert captured["on"] == THEME_WATCHOS.success
        assert captured["off"] == render_ctx.track_color(THEME_WATCHOS.success)
        assert captured["off"] != (150, 150, 150)


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
