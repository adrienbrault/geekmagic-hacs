"""One band policy: what a cell still shows when it runs out of room.

Every card-shaped widget asks the same question before it builds any
markup — *does this cell still show its name, and which optional bands
survive?* — and four widgets used to answer it with the same four lines
copied verbatim, each carrying its own private ``40.0``. Six adapters
around one rule, and no seam: a change to the rule meant six edits and a
hope that none of them drifted.

This module is that seam. :func:`plan_bands` answers the question once
and returns a :class:`BandPlan` the widget spends: three booleans it
budgets height against, and the three hide classes the markup needs.
The leverage is in the locality — the identity floor
(:data:`IDENTITY_MIN_H`) and the rule that reads it live here, so the
widgets keep only the decisions that are genuinely theirs (entity's
feature-vs-chip icon, clock's meridiem, progress's row pitch).

**Two dialects, one question.** The kit sheds bands with CSS media
queries (``.hide-short`` at :data:`~._cellkit.HIDE_SHORT_H`,
``.hide-small`` at :data:`~._cellkit.HIDE_SMALL`), and this plan is the
Python mirror of those breakpoints plus the compact-identity floor
underneath them. The gauge family answers the same question in Python
alone — ``_gauge.caption_band`` gates on ``CAPTION_MIN_CELL_H`` (46) and
``STACK_MIN_CELL_H`` (64), measured against the raw cell height rather
than a content box — because a gauge's value and bar need room the kit's
100px cliff would hand to a caption. That divergence is deliberate; it is
cross-referenced here so a reader finds both dialects from one place.

**Hide classes are not decoration.** A widget that decides in Python to
keep a band the kit would shed MUST drop the hide class, or the media
rule re-hides the row the widget just shrank for it. That is why every
hide string in the plan is ``""`` exactly when the kit would have hidden
the band.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._cellkit import caption_visible, cell_box, small_visible

if TYPE_CHECKING:
    from ..htmldoc import CellContext

# Content height below which even a compact identity row would crowd the
# value out of the cell entirely. Above it, a hero-layout footer (~65px
# of cell) still has room for a 10px name over its value — and an
# unlabeled "85" is noise, not a reading.
IDENTITY_MIN_H = 40.0


@dataclass(frozen=True)
class BandPlan:
    """Which bands a cell keeps, and the classes that say so in markup.

    Widgets read the booleans to budget height and the strings to build
    the fragment. A widget with a band-specific policy of its own
    overrides the one field it owns with :func:`dataclasses.replace` —
    the plan stays the default, the exception stays visible.
    """

    caption: bool
    """The caption band survives at kit size (the kit keeps ``.hide-short``)."""

    compact_identity: bool
    """Too short for the band, tall enough to keep a shrunk identity caption."""

    show_caption: bool
    """A name exists and one of the two caption modes applies."""

    small: bool
    """``.hide-small`` bands (chip strips) survive at kit size."""

    caption_hide: str
    """``"hide-short"`` or ``""`` — the class the caption row carries."""

    icon_hide: str
    """The same, for a feature-icon band above the caption."""

    chips_hide: str
    """``"hide-small"`` or ``""`` — the class the chip strip carries."""


def plan_bands(
    ctx: CellContext,
    *,
    has_name: bool,
    box_h: float | None = None,
    identity_min_h: float = IDENTITY_MIN_H,
) -> BandPlan:
    """Decide which bands this cell keeps.

    ``box_h`` is the content height the identity floor is measured
    against; it defaults to :func:`._cellkit.cell_box`'s, which is the
    box the card widgets fit their heroes into. A widget laying itself
    out against a different box (status budgets in px padding, not
    percentages) passes its own so the floor means the same thing there.

    ``identity_min_h`` is the floor itself, defaulting to
    :data:`IDENTITY_MIN_H`. Pass another only for a layout whose identity
    row genuinely costs less than a card's.
    """
    if box_h is None:
        box_h = cell_box(ctx)[1]
    caption = caption_visible(ctx)
    small = small_visible(ctx)
    compact_identity = not caption and box_h >= identity_min_h
    return BandPlan(
        caption=caption,
        compact_identity=compact_identity,
        show_caption=has_name and (caption or compact_identity),
        small=small,
        # A band the widget kept below the kit's breakpoint must not
        # carry the class that would hide it again.
        caption_hide="hide-short" if caption else "",
        icon_hide="hide-short" if caption else "",
        chips_hide="hide-small" if small else "",
    )
