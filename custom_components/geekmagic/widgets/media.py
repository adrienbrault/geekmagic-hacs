"""Media player widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar
from unicodedata import east_asian_width

from ..htmldoc import css_rgb, image_data_uri, mdi_span

if TYPE_CHECKING:
    from PIL import Image

    from ..htmldoc import CellContext
    from ._textfit import TextMetrics
    from .state import EntityState, WidgetState

from ._cardfit import cell_box, fit_caption_sized
from ._cellkit import chrome_inset
from ._textfit import metrics_for
from .base import Widget, WidgetConfig
from .helpers import truncate_text
from .state import DataNeeds

# Weight names for :mod:`._textfit` matching the markup below: the title
# is 700, everything supporting it is 600.
_TITLE_WEIGHT = "bold"
_SUPPORT_WEIGHT = "semibold"

# Advance of a CJK / Kana / Hangul glyph: one em square. ``_textfit``
# measures with the *embedded* faces, and neither Nunito nor DejaVu Sans
# covers those scripts — PIL reports the narrow .notdef box while Blitz
# falls back to a system face and draws full-width glyphs. A Japanese
# track title is common enough that the difference has to be reserved.
_FULLWIDTH_EM = 1.0
_FULLWIDTH_CLASSES = ("W", "F")

# Shared inset for the album-art overlay: text, progress bar and label all
# align to the same optical margin on every cell size.
_INSET = "clamp(5px, 5.5vmin, 14px)"
_ART_BAR_H = "clamp(2px, 1.4vmin, 4px)"


def _chrome_px(ctx: CellContext) -> float:
    """Width the theme's ``.root`` chrome takes off this cell, both sides.

    The theme declares its inset (``Theme.chrome_inset``), so this is
    the real number rather than the worst case every theme used to pay.
    """
    return 2 * chrome_inset(ctx.theme)


def _clamp_px(min_px: float, vmin_ratio: float, max_px: float, vmin: float) -> float:
    """Python mirror of ``clamp(min_px, <ratio>vmin, max_px)``."""
    return min(max_px, max(min_px, vmin_ratio * vmin))


def _inset_px(ctx: CellContext) -> float:
    """Python mirror of :data:`_INSET`."""
    return _clamp_px(5.0, 0.055, 14.0, min(ctx.width, ctx.height))


def _artist_px(vmin: float) -> float:
    """Artist band size in the text-only card."""
    return _clamp_px(10.0, 0.10, 18.0, vmin)


def _album_px(vmin: float) -> float:
    """Album band size in the text-only card."""
    return _clamp_px(9.0, 0.085, 14.0, vmin)


def _title_metrics(ctx: CellContext) -> TextMetrics:
    """Measurer for the widget's own text bands.

    ``metrics_for`` reports the uppercasing a theme applies to the *kit*
    classes (retro uppercases ``.t-hero``/``.t-label``/…). The title,
    artist and album bands are plain divs, so they keep their case —
    measuring them as caps would needlessly cost a character or two.
    """
    return replace(metrics_for(ctx.theme), uppercase=False)


def _measure(metrics: TextMetrics, text: str, px: float, weight: str) -> float:
    """Rendered width of ``text``, correcting for uncovered scripts.

    Falls through to :mod:`._textfit` for anything the embedded faces
    actually contain; see :data:`_FULLWIDTH_EM` for the rest.
    """
    wide = sum(1 for char in text if east_asian_width(char) in _FULLWIDTH_CLASSES)
    if not wide:
        return metrics.width(text, px, weight)
    narrow = "".join(c for c in text if east_asian_width(c) not in _FULLWIDTH_CLASSES)
    return metrics.width(narrow, px, weight) + wide * px * _FULLWIDTH_EM


def _fit_width(metrics: TextMetrics, text: str, px: float, width: float, weight: str) -> str:
    """Truncate ``text`` with an ellipsis until it fits ``width``."""
    if not text or _measure(metrics, text, px, weight) <= width:
        return text
    for length in range(len(text) - 1, 2, -1):
        candidate = truncate_text(text, length)
        if _measure(metrics, candidate, px, weight) <= width:
            return candidate
    return truncate_text(text, 2)


def _fit_lines(
    text: str, metrics: TextMetrics, width_px: float, font_px: float, max_lines: int
) -> tuple[str, int]:
    """Greedy-wrap ``text`` and hard-truncate it to ``max_lines`` lines.

    Returns the fitted string (the engine re-wraps it at the same width)
    and the number of lines it occupies, so callers can budget height
    against the lines the title will really claim.
    """
    words = text.split()
    if not words:
        return "", 0
    lines: list[str] = []
    current = ""
    overflowed = False
    for word in words:
        # A single word can be wider than a whole line.
        chunk = _fit_width(metrics, word, font_px, width_px, _TITLE_WEIGHT)
        candidate = f"{current} {chunk}" if current else chunk
        if _measure(metrics, candidate, font_px, _TITLE_WEIGHT) <= width_px:
            current = candidate
        elif len(lines) + 1 < max_lines:
            lines.append(current)
            current = chunk
        else:
            overflowed = True
            break
    lines.append(current)
    if overflowed:
        lines[-1] = _fit_width(metrics, f"{lines[-1]}…", font_px, width_px, _TITLE_WEIGHT)
    return " ".join(lines), len(lines)


def _fit_title(
    text: str,
    metrics: TextMetrics,
    avail_px: float,
    *,
    max_px: float,
    max_lines: int,
    min_px: float = 11.0,
) -> tuple[str, float, int]:
    """Pick a font size and wrap/truncate a title to fill ``avail_px``.

    Short titles grow to ``max_px`` (hero dominance); long ones drop to
    two lines before they shrink, and only shrink to ``min_px`` before
    being truncated. A title that nearly fits one line stays on one line
    rather than leaving a one-word widow below it. Returns the fitted
    text, its font size in px, and the number of lines it occupies.
    """
    text = " ".join(text.split())
    if not text:
        return "", min_px, 0
    # Size at which the whole title would fit on a single line.
    single_px = avail_px / (_measure(metrics, text, 1.0, _TITLE_WEIGHT) or 1.0)
    if max_lines < 2 or single_px >= max_px * 0.8:
        allowed = 1
        font_px = min(max_px, max(min_px, single_px))
    else:
        allowed = 2
        # Two lines double the usable width, less a margin for the uneven
        # split a real word-wrap produces.
        font_px = min(max_px, max(min_px, 2 * single_px * 0.92))
    fitted, lines = _fit_lines(text, metrics, avail_px, font_px, allowed)
    return fitted, font_px, lines


def _art_scrim(cell_h: int, block_px: float) -> str:
    """Gradient scrim for the album-art overlay, sized to its text block.

    The scrim is anchored to the bottom and its ramp is derived from where
    the metadata actually starts, so the overlay carries the same contrast
    whether it holds one line or four. The ramp is a sampled smoothstep
    ease rather than straight stop-to-stop segments: linear segments put
    slope discontinuities in the alpha curve, and the eye reads those as
    hard horizontal bands across the artwork (Mach bands). Guarantees:
    the top of the cover stays untouched (the scrim starts at 30% at the
    very earliest and eases in from zero), and the text always sits on
    ~46% black or deeper.
    """
    text_top = 1.0 - block_px / max(1, cell_h)
    start = min(0.62, max(0.30, text_top - 0.26))
    p_text = min(0.9, max(0.30, (text_top - start) / (1.0 - start)))

    def smooth(t: float) -> float:
        return t * t * (3.0 - 2.0 * t)

    stops: list[tuple[float, float]] = [(0.0, 0.0)]
    stops += [(p_text * t, 0.46 * smooth(t)) for t in (0.25, 0.5, 0.75)]
    stops.append((p_text, 0.46))
    stops += [(p_text + (1.0 - p_text) * t, 0.46 + 0.48 * smooth(t)) for t in (0.33, 0.66)]
    stops.append((1.0, 0.94))
    ramp = ", ".join(f"rgba(0,0,0,{a:.2f}) {p * 100:.0f}%" for p, a in stops)
    return (
        '<div style="position: absolute; left: 0; right: 0; bottom: 0; '
        f"height: {(1.0 - start) * 100:.0f}%; "
        f'background: linear-gradient(to bottom, {ramp})"></div>'
    )


def _calculate_media_position(
    entity: EntityState | None,
    now: datetime | None,
) -> float:
    """Calculate current media position accounting for elapsed playback time.

    Home Assistant's media_position only updates on state changes (play/pause/seek).
    To get the actual current position, we need to add elapsed time since the
    last update when the player is actively playing.

    Args:
        entity: Media player entity state
        now: Current datetime (timezone-aware)

    Returns:
        Current position in seconds
    """
    if entity is None:
        return 0.0

    # Get base position
    position = float(entity.get("media_position", 0) or 0)

    # Only calculate elapsed time if playing and we have timing info
    if entity.state != "playing" or now is None:
        return position

    # Get the timestamp when position was last updated
    updated_at = entity.get("media_position_updated_at")
    if updated_at is None:
        return position

    # Parse the datetime if it's a string (HA stores as ISO format)
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except (ValueError, TypeError):
            return position

    # Calculate elapsed time since last update
    if hasattr(updated_at, "timestamp"):
        elapsed = now.timestamp() - updated_at.timestamp()
        if elapsed > 0:
            # Add elapsed time, but cap at duration if available
            duration = float(entity.get("media_duration", 0) or 0)
            new_position = position + elapsed
            return min(new_position, duration) if duration > 0 else new_position

    return position


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def _progress_bar_html(percent: float, color: str, *, height_css: str, track: str) -> str:
    """A slim rounded progress bar on a neutral track."""
    percent = max(0.0, min(100.0, percent))
    return (
        f'<div style="width: 100%; height: {height_css}; border-radius: 999px; '
        f'background: {track}">'
        f'<div style="width: {percent:.1f}%; height: 100%; border-radius: 999px; '
        f'background: {color}"></div></div>'
    )


class MediaWidget(Widget):
    """Widget that displays media player information."""

    WIDGET_TYPE: ClassVar[str] = "media"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Media Player",
        "needs_entity": True,
        "entity_domains": ["media_player"],
        "options": [
            {"key": "show_artist", "type": "boolean", "label": "Show Artist", "default": True},
            {"key": "show_album", "type": "boolean", "label": "Show Album", "default": False},
            {"key": "show_progress", "type": "boolean", "label": "Show Progress", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the media widget."""
        super().__init__(config)
        self.show_artist = config.options.get("show_artist", True)
        self.show_album = config.options.get("show_album", False)
        self.show_progress = config.options.get("show_progress", True)
        self.show_album_art = config.options.get("show_album_art", True)

    def data_needs(self) -> DataNeeds:
        """Album art comes from the player's ``entity_picture``."""
        return DataNeeds(image_source=self.config.entity_id)

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the media player widget."""
        entity = state.entity

        # Paused WITH a track keeps the full now-playing layout (frozen
        # progress, PAUSED caption) — a near-empty pause tile wastes the
        # cell when we know exactly what's on. Paused without a track,
        # and every off/idle state, get the quiet placeholder.
        paused = entity is not None and entity.state == "paused"
        has_track = entity is not None and bool(entity.get("media_title"))
        if (
            entity is None
            or entity.state in ("off", "unavailable", "unknown", "idle")
            or (paused and not has_track)
        ):
            return self._render_idle(ctx, entity)

        # Calculate current position (accounts for elapsed playback time)
        position = _calculate_media_position(entity, state.now)
        duration = float(entity.get("media_duration", 0) or 0)

        accent = css_rgb(self.config.color) if self.config.color else ctx.accent()

        # Use album art if available and enabled
        if self.show_album_art and state.image is not None:
            return self._render_album_art(
                ctx, entity, state.image, position=position, duration=duration, accent=accent
            )

        return self._render_now_playing(ctx, entity, position, duration, accent)

    def _render_idle(self, ctx: CellContext, entity: EntityState | None) -> str:
        """Idle / paused / off placeholder — quiet, centered, never loud.

        Still an identity-bearing cell: the player's NAME captions the
        card (two idle speakers in one grid must not render identically),
        the state keeps its own glyph + word, and the label survives
        short cells at a shrunk size instead of hiding — a lone grey
        glyph says nothing.
        """
        state = entity.state if entity is not None else ""
        if state == "paused":
            icon, label = "pause", "PAUSED"
        elif state == "off":
            icon, label = "power", "OFF"
        elif state in ("unavailable", "unknown"):
            icon, label = "music-off", "UNAVAILABLE"
        else:
            icon, label = "music", "NO MEDIA"

        avail_w, avail_h = cell_box(ctx)
        bands: list[str] = []
        name = self.label_for(entity, fallback="") if entity is not None else ""
        if name and avail_h >= 60:
            text, px = fit_caption_sized(name, ctx, avail_w)
            if text:
                bands.append(
                    f'<div class="t-label" style="font-size: {px:.1f}px">{escape(text)}</div>'
                )
        bands.append(mdi_span(icon, "icon i-md", "color: var(--text-secondary)"))
        if avail_h >= 40:
            text, px = fit_caption_sized(label, ctx, avail_w)
            bands.append(
                '<div class="t-label" style="color: var(--text-secondary); '
                f'font-size: {px:.1f}px">{escape(text or label[:3])}</div>'
            )
        # A medium glyph in secondary over a tertiary caption: present but
        # recessive, so an idle cell reads as resting rather than broken.
        return (
            '<div class="cell" style="justify-content: center; gap: 3.5vmin">'
            f"{''.join(bands)}</div>"
        )

    def _render_album_art(
        self,
        ctx: CellContext,
        entity: EntityState,
        image: Image.Image,
        *,
        position: float,
        duration: float,
        accent: str,
    ) -> str:
        """Full-bleed album art with a bottom scrim and track info.

        Apple-Music / Spotify now-playing pattern: the art fills the cell,
        the top ~45% stays completely unobstructed, and a gradient scrim
        ramps in below it to carry left-aligned metadata. A hairline
        progress bar sits on the shared bottom inset — never flush to the
        physical edge.

        Overlay text and scrim deliberately use fixed white/black rgba,
        NOT theme tokens: they render over photographic content and need
        the same contrast in every theme. This is the documented
        exception to "use theme tokens for everything".
        """
        if image.mode != "RGB":
            image = image.convert("RGB")
        uri = image_data_uri(image)

        vmin = min(ctx.width, ctx.height)
        metrics = _title_metrics(ctx)
        text_width = ctx.width - 2 * _inset_px(ctx) - _chrome_px(ctx)

        show_bar = self.show_progress and duration > 0
        # Height budget, in px, of everything stacked above the bottom
        # inset — it drives where the scrim has to start.
        gap_px = 0.2 * _clamp_px(11.0, 0.105, 24.0, vmin)
        block_px = 0.0

        lines: list[str] = []
        raw_title = entity.get("media_title", "")
        title_lines = 0
        paused = entity.state == "paused"
        if raw_title:
            pause_reserve = 1.4 if paused else 0.0
            title, title_px, title_lines = _fit_title(
                raw_title,
                metrics,
                text_width - pause_reserve * _clamp_px(11.0, 0.105, 24.0, vmin),
                max_px=_clamp_px(11.0, 0.105, 24.0, vmin),
                max_lines=2 if ctx.height >= 170 else 1,
            )
            block_px += title_lines * title_px * 1.16
            # A small pause glyph rides the title line when frozen — the
            # only visible difference from playing besides the still bar.
            pause_glyph = (
                f'<span class="icon" style="font-size: {title_px * 0.9:.0f}px; '
                'color: rgba(255,255,255,0.75); margin-right: 0.3em">&#xF03E4;</span>'
                if paused
                else ""
            )
            lines.append(
                f'<div style="font-size: {title_px:.1f}px; font-weight: 700; '
                'line-height: 1.16; letter-spacing: -0.01em; color: rgba(255,255,255,0.98)">'
                f"{pause_glyph}{escape(title)}</div>"
            )
        if paused and not raw_title:
            # No title line to carry the pause glyph — the state still
            # needs a visible carrier over the art.
            badge_px = _clamp_px(12.0, 0.12, 22.0, vmin)
            block_px += badge_px * 1.1
            lines.append(
                f'<span class="icon" style="font-size: {badge_px:.0f}px; '
                'color: rgba(255,255,255,0.85)">&#xF03E4;</span>'
            )
        artist = entity.get("media_artist", "")
        if artist and self.show_artist and ctx.height >= 100 and ctx.width >= 100:
            artist_px = _clamp_px(9.0, 0.072, 15.0, vmin)
            artist = _fit_width(metrics, artist, artist_px, text_width, _SUPPORT_WEIGHT)
            block_px += artist_px * 1.2 + gap_px
            lines.append(
                f'<div style="font-size: {artist_px:.1f}px; font-weight: 600; '
                'line-height: 1.2; color: rgba(255,255,255,0.6); white-space: nowrap">'
                f"{escape(artist)}</div>"
            )
        # The bar already shows elapsed position graphically, so the
        # numeric readout only earns its place when the title is a single
        # line and there is real room left.
        if duration > 0 and ctx.height >= 190 and ctx.width >= 100 and title_lines <= 1:
            time_px = _clamp_px(9.0, 0.055, 12.0, vmin)
            time_str = f"{_format_time(position)} / {_format_time(duration)}"
            block_px += time_px * 1.2 + gap_px
            lines.append(
                f'<div style="font-size: {time_px:.1f}px; font-weight: 600; '
                "line-height: 1.2; letter-spacing: 0.02em; "
                'color: rgba(255,255,255,0.5); white-space: nowrap">'
                f"{escape(time_str)}</div>"
            )

        bar_zone = _inset_px(ctx) + (_clamp_px(2.0, 0.014, 4.0, vmin) + 6.0 if show_bar else 0.0)

        text_block = ""
        if lines:
            bottom = (
                f"calc({_INSET} + {_ART_BAR_H} + clamp(4px, 3vmin, 9px))" if show_bar else _INSET
            )
            # Two engine constraints shape this wrapper: Blitz resolves an
            # absolutely positioned box against its *parent* box (a
            # zero-height wrapper would collapse the overlay away), and it
            # paints non-positioned subtrees before positioned siblings (a
            # static wrapper would put the text UNDER the scrim). So the
            # wrapper is itself absolute and fills the cell. It carries NO
            # hide-narrow: narrow cells keep the title (fitted to their
            # real width) — art with an anonymous progress bar says
            # nothing, and paused would be indistinguishable from playing.
            text_block = (
                '<div style="position: absolute; inset: 0">'
                f'<div style="position: absolute; left: {_INSET}; right: {_INSET}; '
                f"bottom: {bottom}; display: flex; flex-direction: column; "
                'align-items: flex-start; gap: 0.2em; text-align: left">'
                f"{''.join(lines)}</div></div>"
            )

        bar = ""
        if show_bar:
            percent = min(100.0, position / duration * 100)
            bar = (
                f'<div style="position: absolute; left: {_INSET}; right: {_INSET}; '
                f"bottom: {_INSET}; height: {_ART_BAR_H}; border-radius: 999px; "
                'background: rgba(255,255,255,0.28)">'
                f'<div style="width: {percent:.1f}%; height: 100%; border-radius: 999px; '
                f'background: {accent}"></div></div>'
            )

        # ``border-radius: inherit`` picks up the theme's card rounding
        # (light/classic/soft) and stays square on the chromeless themes.
        return (
            '<div style="position: relative; width: 100%; height: 100%; '
            'overflow: hidden; border-radius: inherit">'
            f'<img src="{uri}" style="position: absolute; inset: 0; width: 100%; '
            'height: 100%; object-fit: cover">'
            f"{_art_scrim(ctx.height, block_px + bar_zone)}"
            f"{text_block}"
            f"{bar}"
            "</div>"
        )

    def _title_height_budget(self, ctx: CellContext, entity: EntityState, duration: float) -> float:
        """Vertical space the title may claim in the text-only card.

        Everything else in the cell has a known height (the fluid kit's
        clamps are mirrored here), and the ``.hide-*`` breakpoints decide
        which bands exist at this size — so what is left over is the
        title's. Without this the card silently overflows the cell,
        because Blitz never clips.
        """
        vmin = min(ctx.width, ctx.height)
        short = ctx.height < 100  # .hide-short
        small = ctx.height < 130 or ctx.width < 130  # .hide-small
        available = ctx.height * 0.90 - _chrome_px(ctx)  # 5% padding top and bottom

        reserved = 0.10 * ctx.height  # space-evenly needs slack to breathe
        # The caption survives every height (it names the play state) —
        # shrunk to the 10px floor in short cells.
        reserved += 10.0 if short else max(12.0, min(0.12 * vmin, 0.09 * ctx.width, 18.0))
        if not short and self.show_artist and entity.get("media_artist", ""):
            reserved += _artist_px(vmin) * 1.2
        if not small and self.show_album and entity.get("media_album_name", ""):
            reserved += _album_px(vmin) * 1.2
        if self.show_progress and duration > 0:
            reserved += _clamp_px(3.0, 0.02, 5.0, vmin)
            if not short:  # elapsed / total row plus its top margin
                reserved += _clamp_px(9.0, 0.065, 12.0, vmin) * 1.2
                reserved += _clamp_px(4.0, 0.025, 8.0, vmin)
        return max(13.0, available - reserved)

    def _render_now_playing(
        self,
        ctx: CellContext,
        entity: EntityState,
        position: float,
        duration: float,
        accent: str,
    ) -> str:
        """Text-only now-playing card (no album art)."""
        vmin = min(ctx.width, ctx.height)
        metrics = _title_metrics(ctx)
        text_width = ctx.width * 0.88 - _chrome_px(ctx)  # 6% padding each side

        # The caption is the only carrier of the play state in this path —
        # it survives short cells at a shrunk size instead of hiding
        # ("PAUSED" gone means paused and playing render identically).
        # Narrow cells get the shorter word so it fits whole.
        paused = entity.state == "paused"
        caption = "PAUSED" if paused else ("PLAYING" if ctx.width < 100 else "NOW PLAYING")
        cap_text, cap_px = fit_caption_sized(caption, ctx, text_width)
        bands: list[str] = [
            f'<div class="t-label" style="font-size: {cap_px:.1f}px">'
            f"{escape(cap_text or caption[:3])}</div>"
        ]

        # Title / artist / album are one unit: they read as a single
        # block of "what is playing", so they get a tight internal gap and
        # the cell's space-evenly only separates caption | track | progress.
        track: list[str] = []

        artist_px = _artist_px(vmin)
        album_px = _album_px(vmin)
        title_budget = self._title_height_budget(ctx, entity, duration)
        max_lines = 2 if ctx.height >= 90 else 1
        title_args = (entity.get("media_title", "Unknown"), metrics, text_width)
        title, title_px, title_lines = _fit_title(
            *title_args,
            max_px=min(_clamp_px(13.0, 0.20, 40.0, vmin), title_budget / 1.14),
            max_lines=max_lines,
        )
        # Blitz does not clip, so a title that wrapped has to be re-sized
        # against the height it actually claims, not the height one line
        # would have claimed. Dense scripts (CJK) hit this where Latin
        # does not.
        if title_lines > 1 and title_px * title_lines * 1.14 > title_budget:
            title, title_px, title_lines = _fit_title(
                *title_args,
                max_px=max(11.0, title_budget / (title_lines * 1.14)),
                max_lines=max_lines,
            )
        track.append(
            f'<div style="font-size: {title_px:.1f}px; font-weight: 700; '
            'line-height: 1.14; letter-spacing: -0.015em">'
            f"{escape(title)}</div>"
        )

        artist = entity.get("media_artist", "")
        if self.show_artist and artist:
            artist = _fit_width(metrics, artist, artist_px, text_width, _SUPPORT_WEIGHT)
            track.append(
                f'<div class="hide-short" style="font-size: {artist_px:.1f}px; '
                "font-weight: 600; line-height: 1.2; color: var(--text-secondary); "
                f'white-space: nowrap">{escape(artist)}</div>'
            )

        album = entity.get("media_album_name", "")
        if self.show_album and album:
            album = _fit_width(metrics, album, album_px, text_width, _SUPPORT_WEIGHT)
            track.append(
                f'<div class="hide-small" style="font-size: {album_px:.1f}px; '
                "font-weight: 600; line-height: 1.2; color: var(--text-tertiary); "
                f'white-space: nowrap">{escape(album)}</div>'
            )

        bands.append(
            '<div style="display: flex; flex-direction: column; align-items: center; '
            f'width: 100%; gap: 0.35em">{"".join(track)}</div>'
        )

        if self.show_progress and duration > 0:
            percent = min(100.0, position / duration * 100)
            bands.append(
                '<div style="width: 100%">'
                + _progress_bar_html(
                    percent,
                    accent,
                    height_css="clamp(3px, 2vmin, 5px)",
                    track="var(--track)",
                )
                # hide-short must sit on an element without an inline
                # display (inline style would beat the media query).
                + '<div class="hide-short">'
                '<div style="display: flex; justify-content: space-between; '
                "color: var(--text-secondary); font-size: clamp(9px, 6.5vmin, 12px); "
                'font-weight: 600; letter-spacing: 0.02em; margin-top: clamp(4px, 2.5vmin, 8px)">'
                f"<span>{escape(_format_time(position))}</span>"
                f"<span>{escape(_format_time(duration))}</span>"
                "</div></div></div>"
            )

        return f'<div class="cell" style="padding: 5% 6%">{"".join(bands)}</div>'
