"""Tests for emoji detection and text segmentation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.emoji import (
    SegmentType,
    TextSegment,
    extract_emoji,
    has_emoji,
    is_emoji_char,
    is_emoji_codepoint,
    segment_text,
    strip_emoji,
)


class TestEmojiDetection:
    """Tests for emoji detection functions."""

    def test_is_emoji_codepoint_basic_emoji(self):
        """Test detecting basic emoji codepoints."""
        # Grinning face
        assert is_emoji_codepoint(0x1F600) is True
        # Red heart
        assert is_emoji_codepoint(0x2764) is True
        # Sun
        assert is_emoji_codepoint(0x2600) is True
        # Fire
        assert is_emoji_codepoint(0x1F525) is True

    def test_is_emoji_codepoint_not_emoji(self):
        """Test that regular characters are not detected as emoji."""
        # ASCII letters
        assert is_emoji_codepoint(ord("A")) is False
        assert is_emoji_codepoint(ord("z")) is False
        # Numbers
        assert is_emoji_codepoint(ord("5")) is False
        # Common punctuation
        assert is_emoji_codepoint(ord("!")) is False
        assert is_emoji_codepoint(ord(" ")) is False

    def test_is_emoji_char(self):
        """Test emoji character detection."""
        assert is_emoji_char("😀") is True
        assert is_emoji_char("🔥") is True
        assert is_emoji_char("❤") is True
        assert is_emoji_char("A") is False
        assert is_emoji_char("1") is False
        assert is_emoji_char("") is False

    def test_has_emoji_positive(self):
        """Test has_emoji returns True for text with emoji."""
        assert has_emoji("Hello 👋") is True
        assert has_emoji("🎉") is True
        assert has_emoji("Temperature: 72°F 🌡️") is True
        assert has_emoji("😀😃😄") is True

    def test_has_emoji_negative(self):
        """Test has_emoji returns False for text without emoji."""
        assert has_emoji("Hello World") is False
        assert has_emoji("Temperature: 72°F") is False
        assert has_emoji("12345") is False
        assert has_emoji("") is False
        assert has_emoji("Special chars: @#$%^&*()") is False


class TestTextSegmentation:
    """Tests for text segmentation into regular text and emoji."""

    def test_segment_text_no_emoji(self):
        """Test segmenting text without emoji."""
        segments = segment_text("Hello World")
        assert len(segments) == 1
        assert segments[0].text == "Hello World"
        assert segments[0].segment_type == SegmentType.TEXT

    def test_segment_text_only_emoji(self):
        """Test segmenting text that is only emoji."""
        segments = segment_text("😀")
        assert len(segments) == 1
        assert segments[0].text == "😀"
        assert segments[0].segment_type == SegmentType.EMOJI

    def test_segment_text_emoji_at_start(self):
        """Test segmenting text with emoji at start."""
        segments = segment_text("👋 Hello")
        assert len(segments) == 2
        assert segments[0].text == "👋"
        assert segments[0].segment_type == SegmentType.EMOJI
        assert segments[1].text == " Hello"
        assert segments[1].segment_type == SegmentType.TEXT

    def test_segment_text_emoji_at_end(self):
        """Test segmenting text with emoji at end."""
        segments = segment_text("Hello 👋")
        assert len(segments) == 2
        assert segments[0].text == "Hello "
        assert segments[0].segment_type == SegmentType.TEXT
        assert segments[1].text == "👋"
        assert segments[1].segment_type == SegmentType.EMOJI

    def test_segment_text_emoji_in_middle(self):
        """Test segmenting text with emoji in middle."""
        segments = segment_text("Hello 😀 World")
        assert len(segments) == 3
        assert segments[0].text == "Hello "
        assert segments[0].segment_type == SegmentType.TEXT
        assert segments[1].text == "😀"
        assert segments[1].segment_type == SegmentType.EMOJI
        assert segments[2].text == " World"
        assert segments[2].segment_type == SegmentType.TEXT

    def test_segment_text_multiple_emoji(self):
        """Test segmenting text with multiple emoji."""
        segments = segment_text("🎉 Party 🎊")
        assert len(segments) == 3
        assert segments[0].segment_type == SegmentType.EMOJI
        assert segments[1].segment_type == SegmentType.TEXT
        assert segments[2].segment_type == SegmentType.EMOJI

    def test_segment_text_consecutive_emoji(self):
        """Test segmenting consecutive emoji."""
        segments = segment_text("😀😃😄")
        assert len(segments) == 3
        for seg in segments:
            assert seg.segment_type == SegmentType.EMOJI

    def test_segment_text_empty(self):
        """Test segmenting empty string."""
        segments = segment_text("")
        assert len(segments) == 0

    def test_segment_text_with_skin_tone(self):
        """Test segmenting emoji with skin tone modifier."""
        # Waving hand with skin tone modifier
        text = "Hello 👋🏽"
        segments = segment_text(text)
        # Should have text + emoji (with modifier as part of emoji)
        assert len(segments) == 2
        assert segments[0].text == "Hello "
        assert segments[0].segment_type == SegmentType.TEXT
        assert segments[1].segment_type == SegmentType.EMOJI
        # The emoji should include the skin tone modifier
        assert "👋" in segments[1].text

    def test_segment_text_flag_emoji(self):
        """Test segmenting flag emoji (regional indicators)."""
        # US flag is two regional indicator symbols
        text = "USA: 🇺🇸"
        segments = segment_text(text)
        assert len(segments) == 2
        assert segments[0].text == "USA: "
        assert segments[0].segment_type == SegmentType.TEXT
        assert segments[1].segment_type == SegmentType.EMOJI


class TestEmojiUtilities:
    """Tests for emoji utility functions."""

    def test_strip_emoji(self):
        """Test removing emoji from text."""
        assert strip_emoji("Hello 👋 World") == "Hello  World"
        assert strip_emoji("😀😃😄") == ""
        assert strip_emoji("No emoji here") == "No emoji here"
        assert strip_emoji("") == ""

    def test_extract_emoji(self):
        """Test extracting emoji from text."""
        emojis = extract_emoji("Hello 👋 World 🎉")
        assert len(emojis) == 2
        assert "👋" in emojis
        assert "🎉" in emojis

    def test_extract_emoji_none(self):
        """Test extracting emoji from text with none."""
        emojis = extract_emoji("Hello World")
        assert len(emojis) == 0

    def test_extract_emoji_consecutive(self):
        """Test extracting consecutive emoji."""
        emojis = extract_emoji("😀😃😄")
        assert len(emojis) == 3


class TestCommonEmoji:
    """Tests for commonly used emoji in Home Assistant contexts."""

    def test_weather_emoji(self):
        """Test weather-related emoji."""
        weather_text = "☀️ Sunny 🌤️ Partly Cloudy ⛈️ Storm"
        assert has_emoji(weather_text) is True
        segments = segment_text(weather_text)
        emoji_count = sum(1 for s in segments if s.segment_type == SegmentType.EMOJI)
        assert emoji_count >= 3

    def test_temperature_emoji(self):
        """Test temperature-related emoji."""
        assert has_emoji("🌡️ 72°F") is True
        assert has_emoji("🔥 Hot") is True
        assert has_emoji("❄️ Cold") is True

    def test_status_emoji(self):
        """Test status indicator emoji."""
        assert has_emoji("✅ Online") is True
        assert has_emoji("❌ Offline") is True
        assert has_emoji("⚠️ Warning") is True
        assert has_emoji("🔴 Critical") is True
        assert has_emoji("🟢 OK") is True

    def test_device_emoji(self):
        """Test device-related emoji."""
        assert has_emoji("💡 Light On") is True
        assert has_emoji("🔌 Plug") is True
        assert has_emoji("📱 Phone") is True
        assert has_emoji("💻 Computer") is True

    def test_mixed_real_world_text(self):
        """Test real-world mixed text scenarios."""
        # Typical Home Assistant dashboard text
        texts = [
            "Living Room 💡 On",
            "🌡️ 72°F | 💧 45%",
            "Front Door 🔒 Locked",
            "Garage 🚗 Closed",
            "Battery 🔋 85%",
        ]
        for text in texts:
            assert has_emoji(text) is True
            segments = segment_text(text)
            assert len(segments) >= 2  # At least text + emoji
