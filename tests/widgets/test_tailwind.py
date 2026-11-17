"""Tailwind-syntax utility classes in the HTML widget (widgets/_tailwind.py)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.htmldoc import (
    CellContext,
    build_cell_document,
    css_rgb,
    render_document,
)
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets._tailwind import class_tokens, compile_utilities
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import (
    DEFAULT_THEME,
    THEME_LIGHT,
    THEME_NIGHT,
)
from scripts.generate_html_samples import EXAMPLES_DIR, widget_state

FIXTURES = Path(__file__).parent.parent / "fixtures" / "tailwind"
CTX = CellContext(width=240, height=240, theme=DEFAULT_THEME)
requires_engine = pytest.mark.skipif(get_engine() is None, reason="blitz-py not installed")


def css_for(classes: str, ctx: CellContext = CTX) -> tuple[str, list[str]]:
    quote = "'" if '"' in classes else '"'
    return compile_utilities(f"<div class={quote}{classes}{quote}></div>", ctx)


def rule(css: str, selector: str) -> str:
    """The declarations of the rule for ``selector``."""
    match = re.search(re.escape(selector) + r" \{ ([^}]*) \}", css)
    assert match, f"no rule for {selector} in:\n{css}"
    return match.group(1).rstrip(";")


def html_widget(source: str, *, tailwind: bool) -> HtmlWidget:
    options: dict[str, object] = {"html": source}
    if tailwind:
        options["tailwind"] = True
    return HtmlWidget(WidgetConfig(widget_type="html", slot=0, options=options))


STATE = WidgetState(entity=EntityState("sensor.x", "on", {}), entities={})


class TestOptIn:
    def test_off_by_default_leaves_the_fragment_alone(self) -> None:
        """A template written before the option may use .ring or .grid itself."""
        source = '<div class="ring grid p-4">x</div>'
        assert html_widget(source, tailwind=False).render_html(CTX, STATE) == source

    def test_on_prepends_reset_and_utilities(self) -> None:
        fragment = html_widget('<div class="p-4">x</div>', tailwind=True).render_html(CTX, STATE)
        assert fragment.startswith("<style>")
        assert "box-sizing: border-box" in fragment
        assert ".p-4 { padding: 16px; }" in fragment
        assert fragment.endswith('<div class="p-4">x</div>')

    def test_classes_built_in_jinja_compile(self) -> None:
        source = "<div class=\"{{ 'text-success' if state == 'on' else 'text-muted' }}\"></div>"
        fragment = html_widget(source, tailwind=True).render_html(CTX, STATE)
        assert ".text-success { color: rgb(" in fragment

    def test_option_must_be_true(self) -> None:
        widget = HtmlWidget(
            WidgetConfig(widget_type="html", slot=0, options={"html": "x", "tailwind": "false"})
        )
        assert widget.tailwind is False


class TestValues:
    @pytest.mark.parametrize(
        ("cls", "declarations"),
        [
            ("p-4", "padding: 16px"),
            ("gap-0.75", "gap: 3px"),
            ("pt-2.5", "padding-top: 10px"),
            ("-mt-2", "margin-top: calc(8px * -1)"),
            ("mx-auto", "margin-left: auto; margin-right: auto"),
            ("w-1/2", "width: 50%"),
            ("size-[112px]", "width: 112px; height: 112px"),
            ("max-w-xs", "max-width: 320px"),
            ("inset-0", "top: 0; right: 0; bottom: 0; left: 0"),
            ("-translate-x-1/2", "--tw-translate-x: calc(50% * -1)"),
            ("text-[82px]", "font-size: 82px"),
            ("text-sm/6", "font-size: 14px; line-height: 24px"),
            ("tracking-[0.08em]", "letter-spacing: 0.08em"),
            ("tracking-widest", "letter-spacing: 0.1em"),
            ("font-extrabold", "font-weight: 800"),
            ("leading-none", "--tw-leading: 1; line-height: 1"),
            ("rounded-2xl", "border-radius: 16px"),
            ("border-t-2", "border-top-style: var(--tw-border-style); border-top-width: 2px"),
            ("opacity-40", "opacity: 40%"),
            ("rotate-45", "rotate: 45deg"),
            ("grid-cols-3", "grid-template-columns: repeat(3, minmax(0, 1fr))"),
            ("col-span-2", "grid-column: span 2 / span 2"),
            ("aspect-3/2", "aspect-ratio: 3 / 2"),
            ("[mask-image:linear-gradient(#000,transparent)]", "mask-image: linear-gradient"),
            ("[animation-delay:-0.5s]", "animation-delay: -0.5s"),
            ("bg-[url(a_b.png)]", "background-image: url(a_b.png)"),
            ("bg-radial", "--tw-gradient-position: ellipse at center"),
            ("bg-conic-90", "--tw-gradient-position: from 90deg"),
            ("bg-linear-to-tr", "--tw-gradient-position: to top right"),
            ("bg-repeat-x", "background-repeat: repeat-x"),
            ("bg-[url(data:image/png;base64,AAAA)]", "url(data:image/png;base64,AAAA)"),
            ("content-['a;b']", "--tw-content: 'a;b'"),
            ("bg-red-500/[35%]", "35%, transparent)"),
        ],
    )
    def test_value(self, cls: str, declarations: str) -> None:
        css, unknown = css_for(cls)
        assert unknown == []
        assert declarations in css

    def test_named_text_size_leaves_line_height_to_leading(self) -> None:
        """v4: text-sm's line height yields to leading-* on the same element."""
        css, _ = css_for("text-sm")
        assert "line-height: var(--tw-leading, 20px)" in css
        assert '@property --tw-leading { syntax: "*"; inherits: false; }' in css

    def test_spacing_off_the_quarter_step_is_unknown(self) -> None:
        assert css_for("p-2.3")[1] == ["p-2.3"]

    def test_shorthands_come_before_longhands(self) -> None:
        css, _ = css_for("px-2 rounded-t-none p-4 rounded-xl")
        assert css.index(".p-4 ") < css.index(".px-2 ")
        assert css.index(".rounded-xl ") < css.index(".rounded-t-none ")

    def test_via_comes_after_from_and_to(self) -> None:
        css, _ = css_for("via-info from-success to-error bg-linear-to-r")
        assert css.index(".via-info ") > css.index(".to-error ")
        assert css.index(".via-info ") > css.index(".from-success ")

    def test_selector_escaping(self) -> None:
        css, _ = css_for("w-[40px] sm:p-1 bg-warning/50 w-1/2")
        for selector in (r".w-\[40px\]", r".sm\:p-1", r".bg-warning\/50", r".w-1\/2"):
            assert selector + " {" in css


class TestColors:
    def test_roles_resolve_to_the_theme(self) -> None:
        css, _ = css_for("text-warning bg-fg-2 border-accent")
        assert "color: rgb(255, 159, 10)" in rule(css, ".text-warning")
        assert rule(css, ".bg-fg-2") == f"background-color: {css_rgb(DEFAULT_THEME.text_secondary)}"

    def test_text_secondary_is_the_accent_role(self) -> None:
        """fg-2 is the secondary text tone; secondary is the theme's accent."""
        css, _ = css_for("text-secondary text-fg-2")
        assert rule(css, ".text-secondary") != rule(css, ".text-fg-2")

    def test_opacity_modifier(self) -> None:
        css, _ = css_for("bg-warning/20 ring-success/[0.35]")
        assert "color-mix(in oklab, rgb(255, 159, 10) 20%, transparent)" in css
        assert f"{css_rgb(DEFAULT_THEME.success)} 35%" in css

    def test_palette_is_srgb(self) -> None:
        """Out-of-gamut shadow colours paint red in blitz-py <= 0.6.0: palette colours are rgb()."""
        css, _ = css_for("text-sky-400 shadow-emerald-400")
        assert rule(css, ".text-sky-400") == "color: rgb(0, 188, 255)"
        assert "oklch" not in css

    def test_monochrome_theme_maps_palette_onto_its_ramp(self) -> None:
        night = CellContext(width=240, height=240, theme=THEME_NIGHT)
        css, _ = css_for("text-sky-400 bg-white text-[#00ff00] bg-slate-950", night)
        sky = re.search(r"rgb\((\d+), (\d+), (\d+)\)", rule(css, ".text-sky-400"))
        assert sky
        red, _, blue = (int(c) for c in sky.groups())
        assert red > blue  # warm, not sky blue
        assert rule(css, ".bg-white") == f"background-color: {css_rgb(THEME_NIGHT.text_primary)}"
        dark = re.search(r"rgb\((\d+), (\d+), (\d+)\)", rule(css, ".bg-slate-950"))
        assert dark
        assert max(int(c) for c in dark.groups()) < 60  # stays a dark fill


class TestVariants:
    def test_interaction_variants_are_dropped_silently(self) -> None:
        css, unknown = css_for("hover:bg-error focus:ring-2 group-hover:hidden")
        assert unknown == []
        assert css == ""

    def test_cell_size_variants(self) -> None:
        css, _ = css_for("small:hidden not-small:flex short:text-xs")
        assert r"@media (max-height: 129px), (max-width: 129px) { .small\:hidden" in css
        assert (
            "@media not all and (max-height: 129px) { "
            "@media not all and (max-width: 129px) {" in css
        )
        assert "@media (max-height: 99px)" in css

    def test_dark_follows_the_theme(self) -> None:
        light = CellContext(width=240, height=240, theme=THEME_LIGHT)
        assert ".dark\\:text-white" in css_for("dark:text-white")[0]
        assert css_for("dark:text-white", light) == ("", [])

    def test_pseudo_and_child_variants(self) -> None:
        css, _ = css_for("odd:bg-chip *:p-1 before:content-['x'] [&_span]:font-bold")
        assert r".odd\:bg-chip:nth-child(odd)" in css
        assert r":is(.\*\:p-1 > *)" in css
        assert "::before { content: var(--tw-content)" not in css  # content-[] sets its own
        assert "--tw-content: 'x'; content: var(--tw-content)" in css
        assert "span { font-weight: 700; }" in css

    def test_important(self) -> None:
        assert "padding: 4px !important" in css_for("p-1!")[0]


class TestUnknown:
    @pytest.mark.parametrize(
        "cls",
        ["blur-sm", "drop-shadow-lg", "backdrop-blur", "bg-clip-text", "text-shadow-lg", "card"],
    )
    def test_unpaintable_or_unknown(self, cls: str) -> None:
        assert css_for(cls) == ("", [cls])

    def test_kit_classes_are_not_unknown(self) -> None:
        assert css_for("icon t-hero hide-small cell")[1] == []

    def test_class_tokens(self) -> None:
        html = "<div class=\"a  b\"><svg class='c a'></svg></div>"
        assert class_tokens(html) == ["a", "b", "c"]

    def test_class_tokens_read_like_the_html_parser(self) -> None:
        """Character references decoded, split on ASCII whitespace only."""
        html = '<div class="bg-[url(&quot;x.png&quot;)] a\u00a0b\tc"></div>'
        assert class_tokens(html) == ['bg-[url("x.png")]', "a\u00a0b", "c"]


# Malformed classes, each of which used to break the whole generated <style>
# (unbalanced brackets, quotes or comments, a ``;`` or ``}`` ending the rule,
# ``</style>``) or raise. The maintainer's reports first, then fuzz finds.
MALFORMED = [
    "w-[(]",
    "grid-cols-[[]",
    "text-[{]/50",
    "shadow-[a'#]",
    "bg-[;]",
    "p-[/*]",
    "rotate-[</*/]",
    "h-[4\\;]",
    "m-[]2\\;]",
    "content-['a]",
    "stroke-[[`]",
    'bg-radial-["0*/]',
    "inset-[^(]",
    "odd:p-[url(]",
    "bg-(--a;})",
    "to-(--7var(4)",
    "[color:red;}]",
    "[color:red]}]",
    "[&{]:p-1",
    "[&]:z-[?\\]+]",
    "min-[(]:p-1",
    "max-[1px)_,_(all]:p-1",
    "*:row-[]</style>)b#ff0000{]",
    "dark:row-[;]/[,1_0a)--\\]",
    "bg-red-500/[5%;}]",
    "bg-red-500/nan",
    "bg-red-500/" + "9" * 400,
    "w-\u00b2/3",
    "grid-cols-\u00b2",
    "opacity-\u00b2",
    "bg-accent-" + "9" * 5000,
    "p-1_0",
    "w-[a\x0bb]",
]


# Odd but self-contained: they compile (to CSS the engine ignores) and must
# neither raise nor disturb the rest of the block
ODD = ["text-[rgb(1.2.3_4_5)]", "w-[(;)]", "content-['}{;']"]


class TestMalformed:
    @pytest.mark.parametrize("cls", MALFORMED)
    def test_is_unknown(self, cls: str) -> None:
        assert css_for(cls) == ("", [cls])

    @requires_engine
    @pytest.mark.parametrize("cls", MALFORMED + ODD)
    def test_leaves_the_other_utilities_working(self, cls: str) -> None:
        """A malformed class next to working ones: the cell still paints red."""
        quote = "'" if '"' in cls else '"'
        widget = html_widget(
            f"<div class={quote}{cls} w-[120px] h-[120px] bg-[#ff0000]{quote}></div>",
            tailwind=True,
        )
        doc = build_cell_document(widget.render_html(CTX, STATE), DEFAULT_THEME)
        img = render_document(doc, 160, 160)
        assert img is not None
        assert img.convert("RGB").getpixel((60, 60)) == (255, 0, 0)


def _render(source: str, entity_id: str, *, tailwind: bool) -> bytes:
    layout = FullscreenLayout()
    options: dict[str, object] = {"html": source}
    if tailwind:
        options["tailwind"] = True
    layout.set_widget(
        0,
        HtmlWidget(WidgetConfig(widget_type="html", slot=0, entity_id=entity_id, options=options)),
    )
    renderer = Renderer()
    img, draw = renderer.create_canvas()
    layout.render(renderer, draw, {0: widget_state(entity_id)})
    return renderer.finalize(img).tobytes()


@requires_engine
@pytest.mark.parametrize(
    ("stem", "entity_id"),
    [("bedside", "lock.front_door"), ("power_trend", "sensor.house_power")],
)
def test_rewrite_renders_byte_identical(stem: str, entity_id: str) -> None:
    """A gallery template rewritten with utilities paints the same pixels.

    The guard against utility CSS drifting from what it claims to be: the
    fixtures keep the originals' exact values, and the light reset must
    not move the drawing helpers' markup (ring(), sparkline(), icon()).
    """
    original = (EXAMPLES_DIR / f"{stem}.html").read_text()
    rewrite = (FIXTURES / f"{stem}.html").read_text()
    assert "<style" not in rewrite
    assert _render(rewrite, entity_id, tailwind=True) == _render(
        original, entity_id, tailwind=False
    )


@requires_engine
def test_palette_glow_paints_its_colour() -> None:
    """A palette glow paints its colour (out-of-gamut shadows paint red in blitz-py <= 0.6.0)."""
    widget = html_widget(
        '<div class="mt-[60px] ml-[60px] size-[40px] bg-black shadow-[0_0_20px_8px] '
        'shadow-emerald-400"></div>',
        tailwind=True,
    )
    doc = build_cell_document(widget.render_html(CTX, STATE), DEFAULT_THEME)
    img = render_document(doc, 160, 160)
    assert img is not None
    pixel = img.convert("RGB").getpixel((54, 80))
    assert isinstance(pixel, tuple)
    red, green, _ = pixel
    assert green > 100
    assert green > red
