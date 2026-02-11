"""Emoji detection and text segmentation utilities.

Provides functions to detect emoji characters and split text into
segments for rendering with appropriate fonts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class SegmentType(Enum):
    """Type of text segment for font selection."""

    TEXT = auto()  # Regular text - use primary font
    EMOJI = auto()  # Emoji - use emoji font


@dataclass
class TextSegment:
    """A segment of text with its type for rendering."""

    text: str
    segment_type: SegmentType


# Emoji detection pattern covering:
# - Emoticons (1F600-1F64F)
# - Dingbats (2702-27B0)
# - Transport/map symbols (1F680-1F6FF)
# - Miscellaneous symbols (2600-26FF)
# - Symbols & Pictographs (1F300-1F5FF)
# - Supplemental Symbols (1F900-1F9FF)
# - Food & Drink, Animals, etc. (1F32D-1F9C0)
# - Regional indicators for flags (1F1E0-1F1FF)
# - Various other emoji ranges
# - Variation selectors and ZWJ sequences
#
# This pattern handles:
# - Simple emoji (single codepoint)
# - Emoji with skin tone modifiers (1F3FB-1F3FF)
# - Emoji with variation selectors (FE0E/FE0F)
# - ZWJ sequences (family, profession emoji)
# - Flag sequences (regional indicators)
# - Keycap sequences (#, *, 0-9 + FE0F + 20E3)

# Core emoji codepoint ranges
_EMOJI_RANGES = [
    (0x1F300, 0x1F9FF),  # Misc Symbols, Emoticons, Ornamental, Transport, Maps, etc.
    (0x1FA00, 0x1FA6F),  # Chess Symbols, Extended-A
    (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
    (0x2600, 0x26FF),  # Misc Symbols (sun, cloud, etc.)
    (0x2700, 0x27BF),  # Dingbats
    (0x231A, 0x231B),  # Watch, Hourglass
    (0x23E9, 0x23F3),  # Media control symbols
    (0x23F8, 0x23FA),  # Media control symbols
    (0x25AA, 0x25AB),  # Small squares
    (0x25B6, 0x25B6),  # Play button
    (0x25C0, 0x25C0),  # Reverse button
    (0x25FB, 0x25FE),  # Squares
    (0x2614, 0x2615),  # Umbrella, hot beverage
    (0x2648, 0x2653),  # Zodiac
    (0x267F, 0x267F),  # Wheelchair
    (0x2693, 0x2693),  # Anchor
    (0x26A1, 0x26A1),  # High voltage
    (0x26AA, 0x26AB),  # Circles
    (0x26BD, 0x26BE),  # Soccer, baseball
    (0x26C4, 0x26C5),  # Snowman, sun behind cloud
    (0x26CE, 0x26CE),  # Ophiuchus
    (0x26D4, 0x26D4),  # No entry
    (0x26EA, 0x26EA),  # Church
    (0x26F2, 0x26F3),  # Fountain, golf
    (0x26F5, 0x26F5),  # Sailboat
    (0x26FA, 0x26FA),  # Tent
    (0x26FD, 0x26FD),  # Fuel pump
    (0x2702, 0x2702),  # Scissors
    (0x2705, 0x2705),  # Check mark
    (0x2708, 0x270D),  # Airplane, etc.
    (0x270F, 0x270F),  # Pencil
    (0x2712, 0x2712),  # Black nib
    (0x2714, 0x2714),  # Check mark
    (0x2716, 0x2716),  # X mark
    (0x271D, 0x271D),  # Latin cross
    (0x2721, 0x2721),  # Star of David
    (0x2728, 0x2728),  # Sparkles
    (0x2733, 0x2734),  # Eight spoked asterisk
    (0x2744, 0x2744),  # Snowflake
    (0x2747, 0x2747),  # Sparkle
    (0x274C, 0x274C),  # Cross mark
    (0x274E, 0x274E),  # Cross mark
    (0x2753, 0x2755),  # Question marks
    (0x2757, 0x2757),  # Exclamation mark
    (0x2763, 0x2764),  # Heart exclamation, heart
    (0x2795, 0x2797),  # Plus, minus, divide
    (0x27A1, 0x27A1),  # Right arrow
    (0x27B0, 0x27B0),  # Curly loop
    (0x27BF, 0x27BF),  # Double curly loop
    (0x2934, 0x2935),  # Arrows
    (0x2B05, 0x2B07),  # Arrows
    (0x2B1B, 0x2B1C),  # Squares
    (0x2B50, 0x2B50),  # Star
    (0x2B55, 0x2B55),  # Circle
    (0x3030, 0x3030),  # Wavy dash
    (0x303D, 0x303D),  # Part alternation mark
    (0x3297, 0x3297),  # Circled Ideograph Congratulation
    (0x3299, 0x3299),  # Circled Ideograph Secret
    (0x1F004, 0x1F004),  # Mahjong red dragon
    (0x1F0CF, 0x1F0CF),  # Playing card black joker
    (0x1F170, 0x1F171),  # A/B buttons
    (0x1F17E, 0x1F17F),  # O/P buttons
    (0x1F18E, 0x1F18E),  # AB button
    (0x1F191, 0x1F19A),  # Square buttons
    (0x1F1E0, 0x1F1FF),  # Regional indicators (flags)
    (0x1F201, 0x1F202),  # Japanese buttons
    (0x1F21A, 0x1F21A),  # Japanese button
    (0x1F22F, 0x1F22F),  # Japanese button
    (0x1F232, 0x1F23A),  # Japanese buttons
    (0x1F250, 0x1F251),  # Japanese buttons
]

# Build a set of emoji codepoints for O(1) lookup
_EMOJI_CODEPOINTS: set[int] = set()
for start, end in _EMOJI_RANGES:
    _EMOJI_CODEPOINTS.update(range(start, end + 1))

# Skin tone modifiers (Fitzpatrick scale)
_SKIN_TONE_MODIFIERS = set(range(0x1F3FB, 0x1F400))

# Variation selectors
_VARIATION_SELECTOR_TEXT = 0xFE0E  # Text presentation
_VARIATION_SELECTOR_EMOJI = 0xFE0F  # Emoji presentation

# Zero-width joiner for compound emoji
_ZWJ = 0x200D

# Keycap combining character
_COMBINING_ENCLOSING_KEYCAP = 0x20E3

# Characters that can be keycaps (# * 0-9)
_KEYCAP_BASE = {ord("#"), ord("*")} | set(range(ord("0"), ord("9") + 1))


def is_emoji_codepoint(codepoint: int) -> bool:
    """Check if a single codepoint is an emoji.

    Args:
        codepoint: Unicode codepoint to check

    Returns:
        True if the codepoint is an emoji
    """
    return (
        codepoint in _EMOJI_CODEPOINTS
        or codepoint in _SKIN_TONE_MODIFIERS
        or codepoint == _VARIATION_SELECTOR_EMOJI
    )


def is_emoji_char(char: str) -> bool:
    """Check if a single character is an emoji.

    Args:
        char: Single character string to check

    Returns:
        True if the character is an emoji
    """
    if not char:
        return False
    return is_emoji_codepoint(ord(char[0]))


def _is_emoji_sequence_char(codepoint: int) -> bool:
    """Check if codepoint is part of an emoji sequence (modifiers, ZWJ, etc)."""
    return (
        codepoint in _EMOJI_CODEPOINTS
        or codepoint in _SKIN_TONE_MODIFIERS
        or codepoint
        in {
            _ZWJ,
            _VARIATION_SELECTOR_EMOJI,
            _VARIATION_SELECTOR_TEXT,
            _COMBINING_ENCLOSING_KEYCAP,
        }
    )


def segment_text(text: str) -> list[TextSegment]:
    """Split text into segments of regular text and emoji.

    Handles:
    - Simple single-codepoint emoji
    - Emoji with skin tone modifiers
    - Emoji with variation selectors
    - ZWJ sequences (compound emoji like family, profession)
    - Flag sequences (regional indicators)
    - Keycap sequences

    Args:
        text: Text to segment

    Returns:
        List of TextSegment objects with type annotations
    """
    if not text:
        return []

    segments: list[TextSegment] = []
    current_text = ""
    current_emoji = ""
    i = 0

    while i < len(text):
        char = text[i]
        codepoint = ord(char)

        # Check if this starts an emoji sequence
        if is_emoji_codepoint(codepoint):
            # Flush any pending regular text
            if current_text:
                segments.append(TextSegment(current_text, SegmentType.TEXT))
                current_text = ""

            # Collect the full emoji sequence
            current_emoji = char
            i += 1

            # Continue collecting modifiers, ZWJ, variation selectors
            while i < len(text):
                next_codepoint = ord(text[i])

                if next_codepoint == _ZWJ:
                    # ZWJ - include it and the next character
                    current_emoji += text[i]
                    i += 1
                    if i < len(text):
                        current_emoji += text[i]
                        i += 1
                elif next_codepoint in _SKIN_TONE_MODIFIERS:
                    # Skin tone modifier
                    current_emoji += text[i]
                    i += 1
                elif next_codepoint == _VARIATION_SELECTOR_EMOJI:
                    # Emoji variation selector
                    current_emoji += text[i]
                    i += 1
                elif next_codepoint == _VARIATION_SELECTOR_TEXT:
                    # Text variation selector - skip it for emoji rendering
                    i += 1
                elif (
                    next_codepoint >= 0x1F1E0
                    and next_codepoint <= 0x1F1FF
                    and codepoint >= 0x1F1E0
                    and codepoint <= 0x1F1FF
                ):
                    # Flag sequence - two regional indicators
                    current_emoji += text[i]
                    i += 1
                else:
                    break

            segments.append(TextSegment(current_emoji, SegmentType.EMOJI))
            current_emoji = ""

        elif codepoint in _KEYCAP_BASE and i + 2 < len(text):
            # Potential keycap sequence: digit/# + FE0F + 20E3
            if (
                ord(text[i + 1]) == _VARIATION_SELECTOR_EMOJI
                and ord(text[i + 2]) == _COMBINING_ENCLOSING_KEYCAP
            ):
                # Flush regular text
                if current_text:
                    segments.append(TextSegment(current_text, SegmentType.TEXT))
                    current_text = ""

                # Collect keycap sequence
                current_emoji = text[i : i + 3]
                segments.append(TextSegment(current_emoji, SegmentType.EMOJI))
                i += 3
                continue

            # Not a keycap sequence, treat as regular text
            current_text += char
            i += 1

        else:
            # Regular text character
            current_text += char
            i += 1

    # Flush remaining text
    if current_text:
        segments.append(TextSegment(current_text, SegmentType.TEXT))
    if current_emoji:
        segments.append(TextSegment(current_emoji, SegmentType.EMOJI))

    return segments


def has_emoji(text: str) -> bool:
    """Check if text contains any emoji characters.

    This is a quick check that's faster than full segmentation
    when you just need to know if emoji handling is needed.

    Args:
        text: Text to check

    Returns:
        True if text contains at least one emoji
    """
    return any(is_emoji_codepoint(ord(char)) for char in text)


def strip_emoji(text: str) -> str:
    """Remove all emoji from text, keeping only regular text.

    Args:
        text: Text to process

    Returns:
        Text with emoji removed
    """
    segments = segment_text(text)
    return "".join(seg.text for seg in segments if seg.segment_type == SegmentType.TEXT)


def extract_emoji(text: str) -> list[str]:
    """Extract all emoji from text as a list.

    Args:
        text: Text to process

    Returns:
        List of emoji strings (including compound emoji)
    """
    segments = segment_text(text)
    return [seg.text for seg in segments if seg.segment_type == SegmentType.EMOJI]
