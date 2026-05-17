"""Declarative widget-layout primitive: ``DataCard``.

Most "complication"-style widgets (status, entity, text, progress,
climate, gauges, clock, ...) display the same conceptual three-band
shape:

  caption   ← caps-tracked tertiary label, top
  hero      ← primary big number/text, middle (auto-fit)
  support   ← optional row of small label/value chips
  indicator ← optional Bar / VerticalBar / Sparkline / Ring / Arc

Before this primitive existed, every widget hand-rolled its own
``int(width * 0.05)`` padding, ``current_y +=`` cursor, and
``is_narrow / is_compact / is_expanded`` cell-shape branching. Same
shape, seven slightly different implementations.

``DataCard`` lets a widget *list its data* in a single dataclass and
delegates layout to one shared policy:

  - **vertical** (``height > width x 1.8`` AND indicator is a
    ``VerticalBar``): stacked text column on the left, vertical bar on
    the right (or value-over-bar in very narrow cells).
  - **ring** (indicator is a ``Ring`` or ``Arc``): caption above, ring
    fills the rest, hero centred inside the ring.
  - **stacked** (``0.7 ≤ aspect ≤ 1.5`` AND ``min(w,h) ≥ 100``): three
    watchOS bands — caption row, hero row (auto-fit), supporting strip
    above the indicator. Justified ``space-evenly`` so the bands breathe.
  - **compact** (everything else — wide+short, tiny grids): an
    ``Adaptive([icon, caption, hero])`` header pinned to the top, the
    indicator pinned to the bottom.

The thresholds match ``component_helpers._pick_bar_mode`` (already
validated against the gauges samples). ``BarGauge`` / ``RingGauge`` /
``ArcGauge`` will be re-expressed as thin wrappers around ``DataCard``
in a later commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Literal

from .colors import (
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
)
from .components import (
    Adaptive,
    Arc,
    Column,
    Component,
    Flex,
    Icon,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
    VerticalBar,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext


CardMode = Literal["auto", "stacked", "compact", "vertical", "ring"]


# =============================================================================
# Cell metrics — replaces the 12+ scattered ``int(width * 0.0X)`` calls.
# =============================================================================


@dataclass(frozen=True)
class CellMetrics:
    """Shared sizing rules derived from a cell's ``(width, height)``.

    Internal to ``data_card.py`` for now — kept here so a single tweak
    rebalances every card-style widget.
    """

    padding: int
    gap: int
    icon_size: int
    chip_icon_size: int
    bar_height: int


def cell_metrics(width: int, height: int) -> CellMetrics:
    """Return the sizing rules for a cell of the given dimensions."""
    short = min(width, height)
    return CellMetrics(
        padding=max(2, int(short * 0.05)),
        gap=max(2, int(height * 0.04)),
        # Feature icons get their own band in stacked mode and share a
        # ~half-cell header in compact mode, so they can comfortably
        # fill more pixels than the old 48-clamp allowed. 0.55 of the
        # short side, capped at 80, lets the icon grow into roomy
        # sidebar / hero cells while staying readable in 3x3 grids.
        icon_size=max(16, min(80, int(short * 0.55))),
        chip_icon_size=max(10, min(18, int(height * 0.08))),
        bar_height=max(4, int(height * 0.08)),
    )


# =============================================================================
# Mode picker — reuses BarGauge's validated thresholds.
# =============================================================================


def pick_card_mode(width: int, height: int, indicator: Component | None = None) -> CardMode:
    """Pick a layout mode for the given cell shape and indicator.

    The stacked threshold is mirror-symmetric with vertical: any cell
    where the long side is at most 1.8x the short side and the short
    side is at least 100 px gets the watchOS three-band stacked
    treatment. This pulls in shapes like 240x156 (HeroLayout
    upper region) and 240x130 that the previous 1.5 cap pushed into
    compact mode and rendered with a too-small hero.

    - ``Ring`` / ``Arc`` indicator -> ``ring`` mode (label above,
      value inside the ring).
    - ``VerticalBar`` indicator on a tall+narrow cell -> ``vertical``
      mode (thermometer / level-meter look).
    """
    if isinstance(indicator, (Ring, Arc)):
        return "ring"
    if isinstance(indicator, VerticalBar) and height > width * 1.8:
        return "vertical"
    short_side = min(width, height)
    # Any cell with a short side >= 65 px goes stacked. This covers
    # most realistic grids — ``Grid2x3(padding=8, gap=8)`` produces
    # 69-px-wide cells, which would otherwise fall into the
    # icon-on-side compact layout and crowd icon and text. Band-aware
    # icon sizing in ``_build_stacked`` keeps the watchOS three-band
    # card readable at small sizes.
    if short_side >= 65:
        return "stacked"
    return "compact"


# =============================================================================
# Chip — structured supporting metric.
# =============================================================================


@dataclass
class Chip(Component):
    """A small icon+text supporting metric (target temp, humidity, ...).

    Renders as a tight ``Row[Icon?, Text]``. Used inside
    ``DataCard.supporting=[Chip(...), Chip(...)]`` to populate the
    third watchOS band — the supporting strip below the hero value.
    """

    text: str
    icon: str | None = None
    color: Color = THEME_TEXT_SECONDARY  # text colour; icon shares it

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return self._build(max_height).measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        self._build(height).render(ctx, x, y, width, height)

    def _build(self, height: int) -> Component:
        """Return the underlying Row tree, sized for the row height."""
        # Icon size scales with the row height; cap raised to 28 so
        # chips inside a roomy supporting strip (e.g. 240x240 climate
        # cell) get a legible glyph rather than a 10-px miniature.
        icon_px = max(10, min(28, int(height * 0.85)))
        children: list[Component] = []
        if self.icon:
            children.append(Icon(self.icon, size=icon_px, color=self.color))
        # Start auto-fit from ``tertiary`` (~11% of cell height) so
        # the chip text stays a supporting accent. ``secondary``
        # (18%) made chips compete with the hero in roomy cells —
        # 240x240 climate showed "22°" at ~48 px, almost a sibling of
        # the temp hero. Tertiary still shrinks to ``tiny`` for long
        # strings like "Wed, Jan 15".
        children.append(
            Text(self.text, font="tertiary", color=self.color, truncate=True, auto_fit=True)
        )
        return Row(children=children, gap=4, justify="center", align="center")


# =============================================================================
# DataCard — the primitive.
# =============================================================================


@dataclass
class DataCard(Component):
    """Declarative complication-card layout.

    See module docstring for the layout policy. Any band may be ``None``
    or empty; missing bands collapse out of the flex tree without
    leaving zero-height spacers.
    """

    caption: str | None = None
    icon: str | None = None
    icon_color: Color = THEME_PRIMARY
    # ``"chip"`` keeps the icon inline beside the caption (small,
    # decorative). ``"feature"`` promotes it to its own band above
    # the caption — bigger, the way ``IconValueDisplay`` rendered
    # entity icons. Pick "feature" when the icon is the widget's
    # main visual identifier (entity, gauge), "chip" otherwise.
    icon_role: Literal["chip", "feature"] = "chip"
    hero: str = ""
    hero_color: Color = THEME_TEXT_PRIMARY
    supporting: list[Chip] = field(default_factory=list)
    indicator: Component | None = None
    mode: CardMode = "auto"
    # Optional override; ``None`` means "use cell_metrics(width, height)".
    padding: int | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        chosen = self.mode if self.mode != "auto" else pick_card_mode(width, height, self.indicator)
        metrics = cell_metrics(width, height)
        pad = self.padding if self.padding is not None else metrics.padding
        # Drop the supporting chip strip when the cell is too tight
        # to show it cleanly. Multi-chip strips need ~140 px of
        # height (otherwise two chips either overlap or stack
        # vertically and crowd the card). A single chip — clock date,
        # standalone unit — fits down to ~80 px before it crowds the
        # hero. Heroes always win the priority fight when room runs
        # out.
        if self.supporting:
            min_height = 140 if len(self.supporting) > 1 else 80
            drop_supporting = height < min_height
        else:
            drop_supporting = False
        card = replace(self, supporting=[]) if drop_supporting else self
        # Override: stacked mode with both a chip strip AND a hero
        # band needs at least ~90 px of height to lay out four bands
        # without overlap. In a wide-and-short cell (e.g. 120x80
        # climate row) demote to compact, which puts the icon on the
        # side and the chips below, fitting comfortably in 80 px.
        if (
            chosen == "stacked"
            and card.mode == "auto"
            and card.supporting
            and card.hero
            and height < 90
            and width >= height * 1.3
        ):
            chosen = "compact"

        if chosen == "ring":
            tree = card._build_ring(metrics, pad, width, height)  # noqa: SLF001
        elif chosen == "vertical":
            tree = card._build_vertical(metrics, pad, width)  # noqa: SLF001
        elif chosen == "stacked":
            tree = card._build_stacked(metrics, pad, width, height)  # noqa: SLF001
        else:
            tree = card._build_compact(metrics, pad, width, height)  # noqa: SLF001
        tree.render(ctx, x, y, width, height)

    # ------------------------------------------------------------------
    # Mode builders
    # ------------------------------------------------------------------

    def _hero_text(self, font: str = "primary") -> Component:
        # ``font="primary"`` starts the auto-fit chain at the largest
        # semantic size (35% of container height) rather than "huge",
        # so hero values fill roomy cells the way watchOS does.
        return Text(
            self.hero,
            font=font,
            bold=True,
            color=self.hero_color,
            auto_fit=True,
        )

    def _caption_text(self) -> Text:
        # ``tertiary`` (12% of container height) scales with the cell;
        # ``tiny`` is a fixed bucket that won't grow into roomy cells.
        # ``auto_fit`` will still shrink it when the band is tight.
        return Text(
            (self.caption or "").upper(),
            font="tertiary",
            color=THEME_TEXT_SECONDARY,
            truncate=True,
            auto_fit=True,
        )

    def _supporting_row(self) -> Component | None:
        """Build the supporting strip, or ``None`` if no chips.

        Chips are grouped at the centre with a moderate gap rather
        than pushed to opposite edges (Adaptive's ``space-between``
        default), which read as awkwardly far apart in wide climate
        cells. The ``Row`` with ``justify="center"`` keeps them tight
        together; auto-fit text inside each chip handles overflow in
        narrow cells.
        """
        if not self.supporting:
            return None
        return Row(
            children=list(self.supporting),
            gap=12,
            justify="center",
            align="center",
        )

    def _build_stacked(
        self, metrics: CellMetrics, pad: int, width: int = 0, height: int = 0
    ) -> Component:
        """Three watchOS bands — caption / hero / (supporting + indicator).

        With ``icon_role="feature"`` and an icon set, the icon gets
        its own band on top — the ``IconValueDisplay`` look that
        entity / gauge widgets relied on.
        """
        bands: list[Component] = []
        # Truthy check (not ``is not None``): the icon-picker frontend
        # writes ``""`` when the user clears it, and a blank name resolves
        # to ``help-circle`` in ``get_mdi_char`` — which would surface as a
        # stray question-mark glyph instead of "no icon".
        feature_icon = self.icon_role == "feature" and bool(self.icon)
        # Count bands up front so the icon can be sized to fit its
        # share of the cell — preventing overflow when the watchOS
        # three-band layout has to coexist with a chip strip in a
        # tight 120x120 grid.
        # Inline icon+caption only when:
        #   (a) the cell is clearly landscape (width >= height x 1.3),
        #   (b) the cell is also wide enough for "[icon] CAPTION" to
        #       still leave room for a big hero (width >= 200), and
        #   (c) there's no chip strip competing for vertical room.
        # Without the width >= 200 floor, narrow cells like 120x80
        # (2x3 grid) get inline icon+caption that crowd the hero;
        # users expect those cells to use the watchOS three-band stack.
        inline = (
            feature_icon
            and self.caption is not None
            and width >= 200
            and width >= height * 1.3
            and not self.supporting
        )
        n_bands = 0
        if feature_icon and not inline:
            n_bands += 1  # icon band
            if self.caption:
                n_bands += 1  # caption band
        elif inline:
            n_bands += 1  # icon+caption combined
        elif self.caption or self.icon:
            n_bands += 1  # chip-mode caption row
        if self.hero:
            n_bands += 1
        if self.indicator is not None:
            n_bands += 1
        if self.supporting:
            n_bands += 1
        n_bands = max(n_bands, 1)
        # Band-aware icon cap: the icon should fit comfortably in its
        # share of the cell height. Without this, a 240x240 icon at
        # 80 px steals the supporting strip's room and "HEATING"
        # text overlaps the hero in 120x120 climate cells.
        icon_band_budget = int((height - 2 * pad) * 0.85 / n_bands)
        icon_size = min(metrics.icon_size, icon_band_budget)
        # Hero font also scales with band count: "primary" (35% of
        # cell height) is right when there's room (≤3 bands), but in
        # a crowded 4-5 band card it dwarfs the other bands and they
        # all crowd against the hero. Drop to "secondary" (20%) so
        # bands keep proportional sizing.
        hero_font = "primary" if n_bands <= 3 else "secondary"
        if feature_icon:
            assert self.icon is not None  # ty narrow
            if inline and self.caption:
                bands.append(
                    Row(
                        children=[
                            Icon(self.icon, size=icon_size, color=self.icon_color),
                            self._caption_text(),
                        ],
                        gap=metrics.gap,
                        justify="center",
                        align="center",
                    )
                )
            else:
                bands.append(
                    Row(
                        children=[Icon(self.icon, size=icon_size, color=self.icon_color)],
                        justify="center",
                        align="center",
                    )
                )
                if self.caption:
                    bands.append(
                        Row(children=[self._caption_text()], justify="center", align="center")
                    )
        elif self.caption or self.icon:
            # chip role: icon and caption share one row.
            caption_children: list[Component] = []
            if self.icon:
                caption_children.append(
                    Icon(self.icon, size=metrics.chip_icon_size, color=self.icon_color)
                )
            if self.caption:
                caption_children.append(self._caption_text())
            bands.append(Row(children=caption_children, gap=4, justify="center", align="center"))
        # Hero band — the big value, sized by ``hero_font`` (above).
        if self.hero:
            bands.append(
                Row(children=[self._hero_text(font=hero_font)], justify="center", align="center")
            )
        # Indicator (bar / sparkline) sits above the supporting strip:
        # for a progress card the supporting text reads as a footer
        # under the bar (e.g. "85%" / [bar] / "8.5k/10k steps") rather
        # than a sibling band wedged between hero and bar.
        if self.indicator is not None:
            bands.append(self.indicator)
        support = self._supporting_row()
        if support is not None:
            bands.append(support)
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=bands,
        )

    def _build_compact(
        self, metrics: CellMetrics, pad: int, width: int = 0, height: int = 0
    ) -> Component:
        """Header row pinned to top (icon + caption + hero); indicator at the
        bottom. The header uses ``Adaptive`` so it stacks vertically when too
        narrow to lay out horizontally.
        """
        feature_icon = self.icon_role == "feature" and bool(self.icon)
        rows: list[Component] = []
        if feature_icon and (self.caption or self.hero):
            # Feature icon in compact mode: place the icon on the left
            # and stack caption + hero to its right. Without this, a
            # tight cell falls through Adaptive's Column path and the
            # icon, caption, and hero all stack vertically — wasting
            # the icon's chance to anchor the side and leaving each
            # text band tiny.
            assert self.icon is not None
            # Cap icon by width (so the right column has room for text)
            # and by height (so the icon doesn't tower past the cell
            # bounds in a tall+narrow cell).
            icon_size = min(
                metrics.icon_size,
                int(width * 0.40),
                int((height - 2 * pad) * 0.85),
            )
            text_column_children: list[Component] = []
            if self.caption:
                # Use ``secondary`` (20% of container height) for the
                # caption so it reads at a reasonable size next to the
                # icon — ``tertiary`` (12%) would leave it tiny.
                text_column_children.append(
                    Text(
                        (self.caption or "").upper(),
                        font="secondary",
                        color=THEME_TEXT_SECONDARY,
                        truncate=True,
                        auto_fit=True,
                    )
                )
            if self.hero:
                # ``font="primary"`` (35% of container height) lets the
                # hero scale into the column's available height — without
                # this, ``font="medium"`` caps growth and leaves the
                # value tiny next to a roomy icon.
                text_column_children.append(
                    Text(
                        self.hero,
                        font="primary",
                        bold=True,
                        color=self.hero_color,
                        auto_fit=True,
                    )
                )
            rows.append(
                Row(
                    children=[
                        Icon(self.icon, size=icon_size, color=self.icon_color),
                        Column(
                            children=text_column_children,
                            gap=2,
                            align="start",
                            justify="center",
                        ),
                    ],
                    # Floor the icon→text gap at ~8% of width / 8 px so
                    # the icon doesn't crash into the caption on tight
                    # cells.
                    gap=max(8, int(width * 0.08)),
                    justify="start",
                    align="center",
                )
            )
        else:
            icon_px = metrics.icon_size if self.icon_role == "feature" else metrics.chip_icon_size
            header_children: list[Component] = []
            if self.icon:
                header_children.append(Icon(self.icon, size=icon_px, color=self.icon_color))
            if self.caption:
                header_children.append(self._caption_text())
            if self.hero:
                if header_children:
                    header_children.append(Spacer())
                header_children.append(
                    Text(
                        self.hero,
                        font="medium",
                        bold=True,
                        color=self.hero_color,
                        auto_fit=True,
                    )
                )

            if header_children:
                if len(header_children) == 1:
                    # Lone element (typically a bare hero like the clock):
                    # centre it instead of letting Adaptive default to a
                    # start-aligned Row, which pins the value to the left
                    # edge and reads as misaligned next to caption-anchored
                    # neighbours.
                    rows.append(Row(children=header_children, justify="center", align="center"))
                else:
                    rows.append(Adaptive(children=header_children, gap=metrics.gap))
        support = self._supporting_row()
        if support is not None:
            rows.append(support)
        if self.indicator is not None:
            rows.append(self.indicator)
        # If the header is the only band, let it fill the cell — without
        # this, ``space-evenly`` centres the natural-height header (~icon
        # height) and wastes the remaining vertical space, which is most
        # of the cell in a 240x80 wide-short row.
        if len(rows) == 1:
            rows = [Flex(rows[0])]
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=rows,
        )

    def _build_vertical(self, metrics: CellMetrics, pad: int, width: int) -> Component:
        """Tall+narrow cells with a ``VerticalBar`` indicator.

        Mirrors ``BarGauge._build_vertical``: very narrow cells stack
        everything (value, caption, then the bar fills the rest);
        wider verticals show value+caption on the left and the bar on
        the right.
        """
        text_column = Column(
            gap=2,
            padding=2,
            align="center",
            justify="center",
            children=[
                self._hero_text(font="medium"),
                self._caption_text(),
            ],
        )
        if width < 90:
            # Stack everything vertically; bar swallows the remaining
            # height at full cell width.
            return Column(
                gap=metrics.gap,
                padding=pad,
                align="stretch",
                justify="start",
                children=[
                    Row(
                        children=[self._hero_text(font="medium")], justify="center", align="center"
                    ),
                    Row(children=[self._caption_text()], justify="center", align="center"),
                    Flex(self.indicator) if self.indicator is not None else Spacer(),
                ],
            )
        children: list[Component] = [text_column]
        if self.indicator is not None:
            children.append(self.indicator)
        return Row(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="start",
            children=children,
        )

    def _build_ring(self, metrics: CellMetrics, pad: int, width: int, height: int) -> Component:
        """Ring/Arc indicator: hero centred inside the ring.

        Caption sits on its own band above the ring whenever the cell
        is at least 65 px on its short side (matches the stacked-mode
        floor); only very tight cells drop it.
        """
        # ring mode is only entered when self.indicator is a Ring/Arc
        # (pick_card_mode guarantees this). Build a Stack[ring/arc,
        # hero centred inside] — same shape RingGauge / ArcGauge use.
        # The hero is wrapped in a Column with horizontal padding so
        # the ``auto_fit`` text auto-shrinks to fit the ring's interior
        # diameter (~55% of cell short side) rather than the full cell
        # width, which caused "73%" to spill out of narrow ring cells.
        assert self.indicator is not None
        ring_diameter = min(width, height) - 2 * pad
        hero_h_pad = max(0, (width - int(ring_diameter * 0.55)) // 2)
        inner = Stack(
            children=[
                self.indicator,
                Column(
                    align="center",
                    justify="center",
                    padding=hero_h_pad,
                    children=[self._hero_text(font="primary")],
                ),
            ]
        )
        roomy = min(width, height) >= 65
        if roomy and self.caption:
            return Column(
                gap=metrics.gap,
                padding=pad,
                align="stretch",
                justify="space-evenly",
                children=[
                    Row(children=[self._caption_text()], justify="center", align="center"),
                    Flex(inner),
                ],
            )
        # Tight cell: drop the caption, ring gets the whole cell.
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=[Flex(inner)],
        )


__all__ = [
    "CardMode",
    "CellMetrics",
    "Chip",
    "DataCard",
    "cell_metrics",
    "pick_card_mode",
]
