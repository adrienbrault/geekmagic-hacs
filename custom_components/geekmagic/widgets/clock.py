"""Clock widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar
from zoneinfo import ZoneInfo

from ..htmldoc import css_rgb
from ._bands import plan_bands
from ._card import card_html, chip_html
from ._cellkit import cell_box, chip_band_px, label_px
from ._fit import (
    HERO_SHARE_SOLO,
    HERO_SHARE_STACKED,
    fit_hero,
    hero_block,
)
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# Digits carry more optical space than letters, so the time can take
# tighter tracking than the kit's default -0.035em without touching —
# and the width it buys back goes straight into the type size.
_TIME_TRACKING = -0.05

# The meridiem is a label on the time, not part of it: smaller than a
# unit suffix and set well clear of the digits.
_MERIDIEM_SCALE = 0.38

_MAX_HERO_PX = 124.0
_MIN_HERO_PX = 13.0

# Tall, narrow slots (split-v) get the stacked watch-face treatment:
# hours over minutes, twice the size of a single centred line.
_STACK_ASPECT = 1.45  # split-v/3-col cells land at ~1.5 after insets


class ClockWidget(Widget):
    """Widget that displays current time and date.

    The watchOS three-band pattern: caption (label), hero (time), chip
    strip (date). In 12-hour mode the meridiem rides the time's baseline
    as a smaller secondary suffix — the digits are the message.
    """

    WIDGET_TYPE: ClassVar[str] = "clock"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Clock",
        "needs_entity": False,
        "options": [
            {"key": "show_date", "type": "boolean", "label": "Show Date", "default": True},
            {"key": "show_seconds", "type": "boolean", "label": "Show Seconds", "default": False},
            {
                "key": "time_format",
                "type": "select",
                "label": "Time Format",
                "options": ["24h", "12h"],
                "default": "24h",
            },
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the clock widget."""
        super().__init__(config)
        self.show_date = config.options.get("show_date", True)
        self.show_seconds = config.options.get("show_seconds", False)
        self.time_format = config.options.get("time_format", "24h")
        self.timezone = config.options.get("timezone")

    def get_entities(self) -> list[str]:
        """Clock widget doesn't depend on entities."""
        return []

    def _now(self, state: WidgetState) -> datetime:
        """Resolve the instant to display, in this clock's timezone.

        The timezone option is the widget's own business, not the
        pipeline's: callers hand every widget the same HA-local
        ``state.now`` and this converts it. Same instant, different wall
        clock — so a grid of city clocks works without the coordinator
        or the preview knowing what a clock is. An unusable zone name
        falls back to the instant as given rather than failing the cell.

        A naive ``state.now`` is read as UTC before converting.
        ``astimezone`` would otherwise reinterpret it as the *host's*
        local time, so a naive instant would silently shift by the
        offset between the host and UTC — the same instant rendering as
        a different wall clock depending on where Home Assistant runs.
        """
        now = state.now or datetime.now(tz=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if self.timezone:
            with contextlib.suppress(Exception):
                return now.astimezone(ZoneInfo(self.timezone))
        return now

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the clock widget."""
        now = self._now(state)

        # A 3x3 slot is better spent on legible hours and minutes than on
        # seconds and a meridiem nobody can read at that size.
        seconds = self.show_seconds and not ctx.is_compact
        if self.time_format == "12h":
            fmt = "%I:%M:%S" if seconds else "%I:%M"
            # Compact 3x3 tiles drop the meridiem; wide strips keep it —
            # "07:42" without PM reads as morning on a 228x74 slot with
            # plenty of horizontal room. Tall narrow columns keep it too:
            # the stacked layout has height to spare, and a 12h clock
            # without AM/PM is unreadable as a 12h clock.
            drop_meridiem = ctx.height < 100 and ctx.width < 170
            meridiem = "" if drop_meridiem else now.strftime("%p")
        else:
            fmt = "%H:%M:%S" if seconds else "%H:%M"
            meridiem = ""
        time_str = now.strftime(fmt)
        date_str = now.strftime("%a, %b %d") if self.show_date else None

        box_w, box_h = cell_box(ctx)
        # Short cells keep a shrunk label row instead of an anonymous
        # time — a "Tokyo" and a "London" clock in one grid must not
        # render identically. The shared band plan decides that.
        plan = plan_bands(ctx, has_name=bool(self.config.label), box_h=box_h)
        # The date is the clock's supporting band, so it follows the
        # caption breakpoint rather than the chip strip's: a tall 114px
        # column has plenty of room for it.
        plan = replace(plan, chips_hide="hide-short")
        show_caption = plan.show_caption
        show_date = bool(date_str) and plan.caption

        caption_band = label_px(ctx) * 1.25 if show_caption else 0.0
        date_band = chip_band_px(ctx) if show_date else 0.0
        share = HERO_SHARE_SOLO if not (show_caption or show_date) else HERO_SHARE_STACKED

        # A tall column can't spend its height on one line of digits, so
        # stack hours over minutes (over seconds) instead of stranding
        # half the cell — one line of HH:MM:SS collapses to ~23px in a
        # 111x228 column.
        stack = None
        if box_h >= _STACK_ASPECT * box_w:
            stack = time_str.split(":")

        hero = fit_hero(
            time_str,
            ctx,
            box_w,
            max(16.0, (box_h - caption_band - date_band) * share),
            suffix=meridiem,
            suffix_scale=_MERIDIEM_SCALE,
            tracking=_TIME_TRACKING,
            lines=stack,
            max_px=_MAX_HERO_PX,
            min_px=_MIN_HERO_PX,
        )

        return card_html(
            # card_html measures, shrinks, and truncates the caption.
            caption=self.config.label if show_caption else None,
            hero=hero_block(
                hero,
                suffix=meridiem,
                suffix_scale=_MERIDIEM_SCALE,
                tracking=_TIME_TRACKING,
            ),
            hero_is_html=True,
            hero_color=css_rgb(self.config.color) if self.config.color else None,
            chips=[chip_html(date_str or "")] if show_date else None,
            plan=plan,
            ctx=ctx,
        )
