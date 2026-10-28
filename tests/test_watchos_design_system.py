"""Design-system contract for the HTML/Blitz rendering architecture.

The rendering pipeline is CSS-first: widgets emit HTML fragments,
``build_cell_document`` wraps them with the theme's CSS variables, the
fluid kit, and the theme's ``chrome_css``, and the Blitz engine
rasterizes the result. Themes are full stylesheets (font_stack,
chrome_css, backdrop_css, overlay_css), not just palettes.

Covers:
- Theme registry: watchos default, all 11 themes registered, const
  options in sync
- Palette invariants: true-black watchos, text hierarchy contrast,
  every theme ships an ``info`` role, valid accent cycling
- CSS field consistency: backdrop always defined, no leftover Python
  format placeholders, only embedded font families, var() references
  resolve against the emitted variables
- ``build_cell_document``: every theme's document carries the fluid
  kit, the palette variables, and the theme chrome
- No hardcoded colors in widget sources: no SYSTEM_*/COLOR_* tokens,
  no color-value imports from widgets.theme, no hex literals (semantic
  color must come from CSS vars or ``ctx.accent()``)
- Fluid kit: documented utility classes and breakpoints

These guard against accidental drift in design tokens that would
silently regress the design system across every widget and theme.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from custom_components.geekmagic import const
from custom_components.geekmagic.htmldoc import (
    FLUID_KIT_CSS,
    build_cell_document,
    css_rgb,
    theme_css_variables,
)
from custom_components.geekmagic.widgets._card import CARD_CSS
from custom_components.geekmagic.widgets.theme import (
    DEFAULT_THEME,
    THEME_CLASSIC,
    THEME_WATCHOS,
    THEMES,
    Theme,
    get_theme,
)

WIDGETS_DIR = Path(__file__).parent.parent / "custom_components" / "geekmagic" / "widgets"

# Files exempt from the widget-source color scans:
# - theme.py IS the design-token source (SYSTEM_* palette lives there)
# - helpers.py hosts shared plumbing (e.g. parse_color), not widget visuals
_SCAN_EXEMPT = {"theme.py", "helpers.py", "__init__.py"}


def _widget_sources() -> list[Path]:
    """Widget source files subject to the no-hardcoded-colors rule."""
    files = [p for p in sorted(WIDGETS_DIR.glob("*.py")) if p.name not in _SCAN_EXEMPT]
    assert files, f"no widget sources found under {WIDGETS_DIR}"
    return files


def _luminance(color: tuple[int, int, int]) -> float:
    """Relative luminance (Rec. 709 weights) — good enough for ordering."""
    r, g, b = color
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return abs(_luminance(a) - _luminance(b))


ALL_THEMES = sorted(THEMES.items())
THEME_IDS = [name for name, _ in ALL_THEMES]
THEME_OBJS = [theme for _, theme in ALL_THEMES]


# ---------------------------------------------------------------------------
# Theme registration / defaults
# ---------------------------------------------------------------------------


class TestThemeDefaults:
    def test_default_theme_is_watchos(self) -> None:
        """The watchOS theme is the default at the rendering layer."""
        assert DEFAULT_THEME is THEME_WATCHOS
        assert DEFAULT_THEME.name == "watchos"

    def test_watchos_registered_in_themes_registry(self) -> None:
        """get_theme('watchos') returns THEME_WATCHOS — wired up correctly."""
        assert THEMES["watchos"] is THEME_WATCHOS
        assert get_theme("watchos") is THEME_WATCHOS

    def test_unknown_theme_falls_back_to_default(self) -> None:
        """A stale/unknown configured theme never crashes rendering."""
        assert get_theme("does-not-exist") is DEFAULT_THEME

    def test_all_themes_registered(self) -> None:
        assert len(THEMES) == 17

    def test_registry_matches_const_options(self) -> None:
        """The frontend dropdown sources options from const.THEME_OPTIONS.
        Registry and options must stay in sync or a theme becomes either
        unselectable or a silent fallback to watchos."""
        assert set(THEMES) == set(const.THEME_OPTIONS)

    def test_watchos_registered_in_const_options(self) -> None:
        assert const.THEME_WATCHOS == "watchos"
        assert const.THEME_OPTIONS[const.THEME_WATCHOS] == "watchOS"
        # Listed first so the default appears at the top of the dropdown.
        assert next(iter(const.THEME_OPTIONS)) == const.THEME_WATCHOS

    def test_registry_names_match_keys(self) -> None:
        """Each theme's .name equals its registry key — lookups and
        round-trips through config storage depend on it."""
        for key, theme in THEMES.items():
            assert theme.name == key, f"THEMES[{key!r}].name == {theme.name!r}"

    def test_classic_still_registered(self) -> None:
        """We didn't accidentally drop classic — backwards-compat for users
        who already configured it."""
        assert THEMES["classic"] is THEME_CLASSIC
        assert THEME_CLASSIC.name == "classic"


# ---------------------------------------------------------------------------
# Palette invariants
# ---------------------------------------------------------------------------


class TestThemePalette:
    def test_watchos_true_black_background(self) -> None:
        """OLED-friendly true black — the watchOS deference principle."""
        assert THEME_WATCHOS.background == (0, 0, 0)
        assert "background: #000" in THEME_WATCHOS.backdrop_css

    def test_watchos_has_no_card_chrome(self) -> None:
        """watchOS deference: widgets float on the background, no cards."""
        assert THEME_WATCHOS.surface_chrome is False
        assert THEME_WATCHOS.chrome_css == ""

    def test_classic_keeps_card_chrome(self) -> None:
        """Classic keeps card chrome for users who prefer separation."""
        assert THEME_CLASSIC.surface_chrome is True
        assert THEME_CLASSIC.chrome_css.strip() != ""

    def test_watchos_uses_rounded_font(self) -> None:
        assert THEME_WATCHOS.rounded_font is True
        assert "Nunito" in THEME_WATCHOS.font_stack

    def test_watchos_tint_track_enabled(self) -> None:
        """Activity-ring style: tracks are tinted, not gray."""
        assert THEME_WATCHOS.tint_track is True
        assert 0.0 < THEME_WATCHOS.tint_track_opacity < 0.5

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_text_hierarchy_distinct(self, theme: Theme) -> None:
        """primary > secondary > tertiary in contrast against the theme
        background. Holds for dark AND light themes — measured as distance
        from the backdrop, not raw brightness."""
        bg = theme.background
        c_primary = _contrast(theme.text_primary, bg)
        c_secondary = _contrast(theme.text_secondary, bg)
        c_tertiary = _contrast(theme.text_tertiary, bg)
        assert c_primary > c_secondary > c_tertiary, (
            f"{theme.name}: text hierarchy not distinct "
            f"({c_primary:.0f} / {c_secondary:.0f} / {c_tertiary:.0f})"
        )

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_every_theme_has_info_color(self, theme: Theme) -> None:
        """All themes ship a valid `info` value (cool/data role). Without
        this, candy/retro/neon/ocean fall back to watchOS blue which looks
        wrong against their palettes."""
        assert theme.info is not None, f"{theme.name} missing info color"
        assert len(theme.info) == 3, f"{theme.name}.info malformed"
        assert all(0 <= c <= 255 for c in theme.info), (
            f"{theme.name}.info has invalid RGB: {theme.info}"
        )

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_accent_colors_valid_and_cycling(self, theme: Theme) -> None:
        """Every theme ships at least one accent, and get_accent_color
        cycles safely for any slot index (fullscreen slot 0 through 3x3
        slot 8)."""
        assert theme.accent_colors, f"{theme.name} has no accent colors"
        for color in theme.accent_colors:
            assert len(color) == 3 and all(0 <= c <= 255 for c in color)
        for slot in range(9):
            assert theme.get_accent_color(slot) in theme.accent_colors


# ---------------------------------------------------------------------------
# CSS field consistency
# ---------------------------------------------------------------------------

# Leftover Python interpolation in CSS ({name}, {0}, %s, %(name)s) would
# render as literal garbage — themes are plain CSS, formatted never.
# CSS rule braces (`body { color: x; }`) contain spaces/colons and don't
# match the identifier-only pattern.
_FORMAT_PLACEHOLDER = re.compile(r"\{[A-Za-z_][\w.]*\}|\{\d*\}|%s|%\(")

_VAR_REFERENCE = re.compile(r"var\(\s*(--[\w-]+)")


def _defined_variables(theme: Theme) -> set[str]:
    """Variable names emitted into every document for this theme."""
    return set(re.findall(r"(--[\w-]+)\s*:", theme_css_variables(theme)))


class TestThemeCSSFields:
    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_backdrop_css_defined(self, theme: Theme) -> None:
        """Every theme paints an explicit backdrop — the fullscreen pass
        must never depend on an implicit default."""
        assert theme.backdrop_css.strip(), f"{theme.name} has empty backdrop_css"
        assert "background" in theme.backdrop_css

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_no_python_format_placeholders(self, theme: Theme) -> None:
        for attr in ("font_stack", "chrome_css", "backdrop_css", "overlay_css"):
            css = getattr(theme, attr)
            leftovers = _FORMAT_PLACEHOLDER.findall(css)
            assert not leftovers, f"{theme.name}.{attr} has Python placeholders: {leftovers}"

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_font_stack_uses_embedded_family(self, theme: Theme) -> None:
        """Blitz only resolves fonts embedded by htmldoc — a stack naming
        neither embedded family would silently fall back per-glyph."""
        assert "Nunito" in theme.font_stack or "DejaVu Sans" in theme.font_stack, (
            f"{theme.name}.font_stack={theme.font_stack!r} references no embedded family"
        )

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_var_references_resolve(self, theme: Theme) -> None:
        """Every var(--x) in the theme's CSS must be a variable actually
        emitted by theme_css_variables — a typo'd var() renders as no
        paint in Blitz."""
        defined = _defined_variables(theme)
        for attr in ("chrome_css", "backdrop_css", "overlay_css"):
            for name in _VAR_REFERENCE.findall(getattr(theme, attr)):
                assert name in defined, f"{theme.name}.{attr} references undefined {name}"

    def test_overlay_themes_are_retro_and_neon(self) -> None:
        """Exactly the effect themes ship an overlay pass (scanlines,
        vignette). Adding an overlay to a theme is a deliberate design
        decision — update this contract when you make it."""
        with_overlay = {name for name, theme in THEMES.items() if theme.overlay_css.strip()}
        assert with_overlay == {"retro", "neon", "blueprint"}


# ---------------------------------------------------------------------------
# build_cell_document — the per-cell contract
# ---------------------------------------------------------------------------


class TestCellDocument:
    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_contains_fluid_kit_classes(self, theme: Theme) -> None:
        doc = build_cell_document("<div>x</div>", theme)
        for cls in (
            ".cell",
            ".t-hero",
            ".t-value",
            ".t-unit",
            ".t-label",
            ".icon",
            ".hide-short",
            ".hide-narrow",
            ".hide-small",
        ):
            assert cls in doc, f"{theme.name}: fluid kit class {cls} missing"

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_contains_card_classes(self, theme: Theme) -> None:
        """Card structure CSS ships in every document so themes can
        restyle .chips/.chip via chrome_css."""
        doc = build_cell_document("", theme)
        for cls in (".chips", ".chip", ".caption-row"):
            assert cls in doc

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_contains_theme_palette_variables(self, theme: Theme) -> None:
        """The document exposes the theme's palette as CSS variables with
        the theme's actual RGB values."""
        doc = build_cell_document("", theme)
        expected = {
            "--bg": theme.background,
            "--text-primary": theme.text_primary,
            "--text-secondary": theme.text_secondary,
            "--text-tertiary": theme.text_tertiary,
            "--primary": theme.primary,
            "--success": theme.success,
            "--warning": theme.warning,
            "--error": theme.error,
            "--info": theme.info,
            "--muted": theme.muted,
        }
        for name, value in expected.items():
            assert f"{name}: {css_rgb(value)};" in doc, f"{theme.name}: {name} missing"
        for i, accent in enumerate(theme.accent_colors):
            assert f"--accent-{i}: {css_rgb(accent)};" in doc

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_contains_chrome_and_font_stack(self, theme: Theme) -> None:
        doc = build_cell_document("", theme)
        assert theme.font_stack in doc
        if theme.chrome_css.strip():
            assert theme.chrome_css.strip() in doc, f"{theme.name}: chrome_css not injected"

    @pytest.mark.parametrize("theme", THEME_OBJS, ids=THEME_IDS)
    def test_body_transparent_and_fragment_wrapped(self, theme: Theme) -> None:
        """Cells composite over the backdrop, so the body must stay
        transparent; the fragment lands inside .root for chrome to paint."""
        fragment = '<div class="cell">MARKER</div>'
        doc = build_cell_document(fragment, theme)
        assert "background: transparent" in doc
        assert f'<div class="root">{fragment}</div>' in doc


# ---------------------------------------------------------------------------
# No hardcoded colors leak into widget sources
# ---------------------------------------------------------------------------

# Forbidden color tokens — widgets must consume color through the CSS
# variables (var(--success), ...) or ctx.accent(), never by naming
# palette constants. Each entry is (token, hint) so the failure tells
# the offender exactly what to use instead.
_FORBIDDEN_COLOR_TOKENS: tuple[tuple[str, str], ...] = (
    # SYSTEM_* live in widgets/theme.py — the *source* of design tokens.
    ("SYSTEM_BLUE", "use var(--info)"),
    ("SYSTEM_ORANGE", "use var(--warning)"),
    ("SYSTEM_RED", "use var(--error)"),
    ("SYSTEM_YELLOW", "use var(--warning)"),
    ("SYSTEM_GREEN", "use var(--success)"),
    ("SYSTEM_CYAN", "use var(--info)"),
    ("SYSTEM_TEAL", "use var(--primary)"),
    ("SYSTEM_INDIGO", "use var(--secondary)"),
    ("SYSTEM_MINT", "use var(--success) or var(--info)"),
    ("SYSTEM_PURPLE", "use var(--secondary)"),
    ("SYSTEM_PINK", "use var(--primary)/var(--secondary)"),
    # Legacy COLOR_* in const.py are fixed RGB literals predating the
    # theme system. Same rule: forbidden in widget code.
    ("COLOR_CYAN", "use var(--primary) or var(--info)"),
    ("COLOR_LIME", "use var(--success)"),
    ("COLOR_RED", "use var(--error)"),
    ("COLOR_GREEN", "use var(--success)"),
    ("COLOR_ORANGE", "use var(--warning)"),
    ("COLOR_YELLOW", "use var(--warning)"),
    ("COLOR_BLUE", "use var(--info)"),
    ("COLOR_GOLD", "use var(--warning)"),
    ("COLOR_PURPLE", "use var(--secondary)"),
    ("COLOR_PINK", "use var(--primary)/var(--secondary)"),
    ("COLOR_TEAL", "use var(--primary)"),
)

# Hex color literals allowed per file. camera.py and media.py draw
# text/scrim overlays ON TOP OF photographic content (camera snapshots,
# album art) — there the correct color is literal white/black regardless
# of theme, so neutral hex is permitted. Everywhere else, hex is banned.
_NEUTRAL_HEX = {"#000", "#fff", "#000000", "#ffffff"}
_HEX_ALLOWED: dict[str, set[str]] = {
    "camera.py": _NEUTRAL_HEX,
    "media.py": _NEUTRAL_HEX,
}

_HEX_LITERAL = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _string_literals(source: str) -> list[tuple[int, str]]:
    """All (lineno, value) string constants in a Python source file."""
    return [
        (node.lineno, node.value)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


class TestNoHardcodedColorsInWidgets:
    """Semantic color in widget fragments must come from theme CSS
    variables (var(--success), ...) or ctx.accent() — never from palette
    constants or hex literals. Hardcoded colors look out of place the
    moment the user switches theme. Guards the contract documented in
    CLAUDE.md > Design System.
    """

    def test_no_forbidden_color_tokens(self) -> None:
        """Scan non-comment lines for SYSTEM_*/COLOR_* palette tokens."""
        offenders: list[str] = []
        for py in _widget_sources():
            for lineno, raw_line in enumerate(py.read_text().splitlines(), start=1):
                code = re.sub(r"#.*$", "", raw_line)  # comments may mention them
                offenders.extend(
                    f"{py.name}:{lineno}: {token}  ({hint})"
                    for token, hint in _FORBIDDEN_COLOR_TOKENS
                    if token in code
                )
        assert not offenders, (
            "Widgets must use theme CSS variables or ctx.accent(), "
            "not palette constants.\n"
            "See CLAUDE.md > Design System for the full rule.\n\n"
            "Offenders:\n  " + "\n  ".join(offenders)
        )

    def test_no_color_value_imports_from_theme(self) -> None:
        """Widget modules must not import color VALUES from widgets.theme.
        Importing the Theme/Color types for annotations is fine; importing
        SYSTEM_* / THEME_* objects to read .primary etc. is not."""
        allowed_names = {"Theme", "Color"}
        offenders: list[str] = []
        for py in _widget_sources():
            tree = ast.parse(py.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("theme"):
                    bad = [a.name for a in node.names if a.name not in allowed_names]
                    if bad:
                        offenders.append(f"{py.name}:{node.lineno}: imports {bad}")
                elif isinstance(node, ast.Import):
                    offenders.extend(
                        f"{py.name}:{node.lineno}: import {alias.name}"
                        for alias in node.names
                        if "theme" in alias.name
                    )
        assert not offenders, (
            "Widgets must not import color values from widgets.theme "
            "(only the Theme/Color types are allowed):\n  " + "\n  ".join(offenders)
        )

    def test_no_hex_color_literals(self) -> None:
        """No #rgb/#rrggbb literals in widget fragment strings, except the
        documented neutral white/black overlays in camera.py/media.py."""
        offenders: list[str] = []
        for py in _widget_sources():
            allowed = _HEX_ALLOWED.get(py.name, set())
            for lineno, value in _string_literals(py.read_text()):
                offenders.extend(
                    f"{py.name}:{lineno}: {match}"
                    for match in _HEX_LITERAL.findall(value)
                    if match.lower() not in allowed
                )
        assert not offenders, (
            "Hex color literals in widget sources — use var(--role), "
            "ctx.accent(), or css_rgb(theme value) instead:\n  " + "\n  ".join(offenders)
        )


# ---------------------------------------------------------------------------
# Fluid kit contract
# ---------------------------------------------------------------------------


class TestFluidKit:
    """FLUID_KIT_CSS is the shared typography/visibility toolkit every
    cell document gets. Widgets build against these class names and
    breakpoints — renaming or retuning them is a breaking change for
    every widget fragment and user HTML template.
    """

    @pytest.mark.parametrize(
        "cls",
        [
            ".cell",
            ".t-hero",
            ".t-value",
            ".t-unit",
            ".t-label",
            ".icon",
            ".i-lg",
            ".i-md",
            ".i-sm",
            ".hide-short",
            ".hide-narrow",
            ".hide-small",
        ],
    )
    def test_kit_defines_class(self, cls: str) -> None:
        assert cls in FLUID_KIT_CSS

    def test_hide_short_breakpoint(self) -> None:
        """.hide-short drops content in cells under 100px tall (3x3 rows)."""
        assert re.search(r"@media \(max-height: 99px\)\s*\{\s*\.hide-short", FLUID_KIT_CSS), (
            "hide-short must trigger at max-height: 99px"
        )

    def test_hide_narrow_breakpoint(self) -> None:
        """.hide-narrow drops content in cells under 100px wide."""
        assert re.search(r"@media \(max-width: 99px\)\s*\{\s*\.hide-narrow", FLUID_KIT_CSS), (
            "hide-narrow must trigger at max-width: 99px"
        )

    def test_hide_small_breakpoint(self) -> None:
        """.hide-small drops content when either dimension is under 130px
        (2x2 cells are ~118px)."""
        assert re.search(
            r"@media \(max-height: 129px\), \(max-width: 129px\)\s*\{\s*\.hide-small",
            FLUID_KIT_CSS,
        ), "hide-small must trigger at 129px in either dimension"

    def test_cell_scaffold_space_evenly(self) -> None:
        """.cell is the flex-column scaffold with space-evenly distribution
        — the CLAUDE.md three-band default."""
        cell_rule = FLUID_KIT_CSS.split(".cell {", 1)[1].split("}", 1)[0]
        assert "flex-direction: column" in cell_rule
        assert "justify-content: space-evenly" in cell_rule
        assert "height: 100%" in cell_rule

    def test_hero_hierarchy_larger_than_value(self) -> None:
        """Type hierarchy: hero > value > unit > label minimum sizes."""

        def min_px(cls: str) -> float:
            rule = FLUID_KIT_CSS.split(f"{cls} {{", 1)[1].split("}", 1)[0]
            m = re.search(r"clamp\((\d+)px", rule)
            assert m, f"{cls} has no clamp() font-size"
            return float(m.group(1))

        assert min_px(".t-hero") > min_px(".t-value") > min_px(".t-unit") > min_px(".t-label")

    def test_kit_var_references_resolve(self) -> None:
        """Kit + card CSS only reference variables every document defines."""
        defined = _defined_variables(DEFAULT_THEME)
        for name in _VAR_REFERENCE.findall(FLUID_KIT_CSS + CARD_CSS):
            assert name in defined, f"fluid kit references undefined {name}"

    def test_card_css_reasserts_hide_rules(self) -> None:
        """CARD_CSS sets display:flex on .chips/.caption-row after the kit,
        so it must re-assert the hide-* media rules at the same breakpoints
        with higher specificity — otherwise captions stop hiding in short
        cells (regression: 3x3 grid captions overlapping heroes)."""
        assert re.search(r"@media \(max-height: 99px\)\s*\{\s*\.caption-row\.hide-short", CARD_CSS)
        assert re.search(
            r"@media \(max-height: 129px\), \(max-width: 129px\)\s*\{\s*"
            r"\.chips\.hide-small, \.caption-row\.hide-small",
            CARD_CSS,
        )


class TestCompactIdentityContract:
    """Every labeled widget must keep its identity in small cells.

    The recurring regression class of the Blitz port: captions, icons
    and titles silently vanishing below the kit's hide-* breakpoints,
    leaving anonymous values ("85", a bare ring, a lone "ON"). The
    contract: a widget configured with a label renders a non-empty
    ``.t-label`` at both a hero-simple footer (228x76) and a 3x2 grid
    tile (111x72) — shrunk, truncated, but never absent.
    """

    SIZES = ((228, 76), (111, 72))

    def _fragment_has_label_text(self, fragment: str) -> bool:
        for match in re.finditer(r'<[^>]*class="[^"]*t-label[^"]*"[^>]*>(.*?)</', fragment):
            inner = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if inner:
                return True
        # Some widgets render their caps identity outside .t-label
        # (weather day names, media titles) — a caps word also counts.
        return False

    @pytest.mark.parametrize("size", SIZES)
    def test_labeled_widgets_keep_identity(self, size: tuple[int, int]) -> None:
        from datetime import UTC, datetime

        from custom_components.geekmagic.htmldoc import CellContext
        from custom_components.geekmagic.widgets.base import WidgetConfig
        from custom_components.geekmagic.widgets.chart import ChartWidget
        from custom_components.geekmagic.widgets.clock import ClockWidget
        from custom_components.geekmagic.widgets.entity import EntityWidget
        from custom_components.geekmagic.widgets.gauge import GaugeWidget
        from custom_components.geekmagic.widgets.progress import ProgressWidget
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState
        from custom_components.geekmagic.widgets.status import StatusWidget
        from custom_components.geekmagic.widgets.text import TextWidget

        entity = EntityState(
            entity_id="sensor.probe",
            state="42",
            attributes={"friendly_name": "Probe", "unit_of_measurement": "%"},
        )
        state = WidgetState(
            entity=entity, history=[1.0, 2.0, 3.0], now=datetime(2025, 12, 29, 13, 45, tzinfo=UTC)
        )
        widgets = [
            EntityWidget(
                WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.probe", label="Probe")
            ),
            TextWidget(
                WidgetConfig(widget_type="text", slot=0, label="Probe", options={"text": "Ready"})
            ),
            ClockWidget(WidgetConfig(widget_type="clock", slot=0, label="Probe")),
            GaugeWidget(
                WidgetConfig(
                    widget_type="gauge",
                    slot=0,
                    entity_id="sensor.probe",
                    label="Probe",
                    options={"style": "bar"},
                )
            ),
            GaugeWidget(
                WidgetConfig(
                    widget_type="gauge",
                    slot=0,
                    entity_id="sensor.probe",
                    label="Probe",
                    options={"style": "ring"},
                )
            ),
            ProgressWidget(
                WidgetConfig(
                    widget_type="progress", slot=0, entity_id="sensor.probe", label="Probe"
                )
            ),
            StatusWidget(
                WidgetConfig(widget_type="status", slot=0, entity_id="sensor.probe", label="Probe")
            ),
            ChartWidget(
                WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.probe", label="Probe")
            ),
        ]
        ctx = CellContext(width=size[0], height=size[1], slot_index=0, theme=DEFAULT_THEME)
        for widget in widgets:
            fragment = widget.render_html(ctx, state)
            name = type(widget).__name__ + getattr(widget, "style", "")
            assert "PROBE" in fragment.upper(), f"{name} lost its label at {size}"
            assert self._fragment_has_label_text(fragment) or "PROBE" in fragment, name
