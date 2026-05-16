"""Display mode (custom/builtin) and pause/wake state for a GeekMagic device.

Two small state machines that the coordinator used to manage as four
loose fields:

  - mode: "custom" (integration renders + uploads) vs "builtin" (device
    handles its own display via its native themes 0-2)
  - paused: when True, the render/upload cycle is skipped entirely; the
    device is dimmed to 0 and the pre-pause brightness is remembered so
    resume can restore it

The invariants that used to live nowhere are now this module's contract:
- `pre_pause_brightness` is captured exactly once per pause and cleared
  exactly once per resume.
- `builtin_theme` is only meaningful when `mode == "builtin"`.
- `pre_pause_brightness` is private; callers ask for what to restore via
  `exit_pause()`.
"""

from __future__ import annotations


class DisplayState:
    """Holds the display-mode + pause state. Pure in-memory, no I/O."""

    def __init__(self) -> None:
        self._mode: str = "custom"
        self._builtin_theme: int = 0
        self._paused: bool = False
        self._pre_pause_brightness: int | None = None

    # --- mode (custom vs builtin) ---

    @property
    def mode(self) -> str:
        """'custom' (integration renders) or 'builtin' (device themes)."""
        return self._mode

    @property
    def builtin_theme(self) -> int:
        """The device theme number (0-2) currently active in builtin mode.

        Value is meaningless when `mode == "custom"`.
        """
        return self._builtin_theme

    def set_custom(self) -> None:
        """Switch to integration-driven rendering."""
        self._mode = "custom"

    def set_builtin(self, theme: int) -> None:
        """Switch to a device built-in theme (0-2)."""
        self._mode = "builtin"
        self._builtin_theme = theme

    def sync_from_device_theme(self, device_theme: int) -> bool:
        """Adopt a device-reported builtin theme if we currently think we're custom.

        Returns True if the mode flipped (caller may want to log). Themes
        ≥ 3 are the integration's own "custom image" mode and don't
        trigger a flip.
        """
        if device_theme < 3 and self._mode == "custom":
            self._mode = "builtin"
            self._builtin_theme = device_theme
            return True
        return False

    # --- pause / wake ---

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_active(self) -> bool:
        """Inverse of is_paused — convenience for entities."""
        return not self._paused

    def enter_pause(self, current_brightness: int | None) -> None:
        """Mark paused and remember the pre-pause brightness for resume.

        Idempotent: re-pausing doesn't overwrite the remembered brightness,
        so a double-pause + resume still restores the original value.
        """
        if not self._paused:
            self._pre_pause_brightness = current_brightness
        self._paused = True

    def exit_pause(self) -> int | None:
        """Mark resumed and return the brightness the caller should restore.

        Returns None if nothing was remembered (e.g. resume without a
        prior pause).
        """
        self._paused = False
        restore = self._pre_pause_brightness
        self._pre_pause_brightness = None
        return restore
