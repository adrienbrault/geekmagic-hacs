"""Tests for MDI icon mapping."""

import pytest

from custom_components.geekmagic.icons import (
    FALLBACK_ICON,
    LEGACY_ALIASES,
    MDI_CODEPOINTS,
    get_mdi_char,
    is_valid_icon,
)


class TestMDICodepoints:
    """Tests for MDI codepoint mapping."""

    def test_codepoints_not_empty(self) -> None:
        """Verify MDI codepoints dict is populated."""
        assert len(MDI_CODEPOINTS) > 7000, "Should have 7000+ MDI icons"

    def test_common_icons_exist(self) -> None:
        """Verify common icons are in the mapping."""
        common_icons = [
            "thermometer",
            "water",
            "home",
            "lightbulb",
            "battery",
            "wifi",
            "play",
            "pause",
            "check",
            "alert",
            "fire",
            "heart",
        ]
        for icon in common_icons:
            assert icon in MDI_CODEPOINTS, f"Missing common icon: {icon}"

    def test_codepoints_are_valid_hex(self) -> None:
        """Verify all codepoints are valid hex strings."""
        for name, codepoint in MDI_CODEPOINTS.items():
            try:
                value = int(codepoint, 16)
                assert value > 0, f"Codepoint for '{name}' is zero"
            except ValueError:
                pytest.fail(f"Invalid hex codepoint for '{name}': {codepoint}")

    def test_codepoints_in_private_use_area(self) -> None:
        """Verify codepoints are in expected range (MDI uses PUA starting at F0xxx)."""
        for name, codepoint in MDI_CODEPOINTS.items():
            value = int(codepoint, 16)
            # MDI uses codepoints in F0000-FFFFF range
            assert 0xF0000 <= value <= 0xFFFFF, (
                f"Codepoint for '{name}' outside expected range: {codepoint}"
            )


class TestLegacyAliases:
    """Tests for legacy icon name aliases."""

    def test_all_legacy_aliases_have_targets(self) -> None:
        """Verify all legacy aliases point to valid MDI icons."""
        for legacy_name, mdi_name in LEGACY_ALIASES.items():
            assert mdi_name in MDI_CODEPOINTS, (
                f"Legacy alias '{legacy_name}' -> '{mdi_name}' not in MDI codepoints"
            )

    def test_legacy_icons_exist(self) -> None:
        """Verify all expected legacy icon names are aliased."""
        expected_legacy = [
            "cpu",
            "memory",
            "disk",
            "temp",
            "power",
            "bolt",
            "network",
            "home",
            "sun",
            "drop",
            "cloud",
            "rain",
            "moon",
            "wind",
            "play",
            "pause",
            "skip_prev",
            "skip_next",
            "music",
            "arrow_up",
            "arrow_down",
            "check",
            "warning",
            "heart",
            "steps",
            "flame",
            "location",
            "building",
            "lock",
            "unlock",
            "motion",
            "bell",
            "battery",
            "lightbulb",
        ]
        for icon in expected_legacy:
            assert icon in LEGACY_ALIASES, f"Missing legacy alias: {icon}"


class TestGetMdiChar:
    """Tests for get_mdi_char function."""

    def test_returns_unicode_char(self) -> None:
        """Test that get_mdi_char returns a single Unicode character."""
        char = get_mdi_char("home")
        assert len(char) == 1, "Should return single character"
        assert ord(char) >= 0xF0000, "Should be in MDI codepoint range"

    def test_legacy_name(self) -> None:
        """Test legacy icon names work."""
        char = get_mdi_char("temp")
        expected = get_mdi_char("thermometer")
        assert char == expected, "Legacy 'temp' should map to 'thermometer'"

    def test_mdi_prefix_format(self) -> None:
        """Test HA MDI format (mdi:xxx) is parsed correctly."""
        char_with_prefix = get_mdi_char("mdi:thermometer")
        char_without_prefix = get_mdi_char("thermometer")
        assert char_with_prefix == char_without_prefix

    def test_mdi_prefix_with_legacy(self) -> None:
        """Test mdi: prefix combined with legacy alias."""
        # "mdi:temp" isn't a real MDI icon, but we strip prefix first
        # then check legacy aliases, so this should still work
        char = get_mdi_char("mdi:temp")
        expected = get_mdi_char("thermometer")
        assert char == expected

    def test_unknown_icon_returns_fallback(self) -> None:
        """Test unknown icons return fallback character."""
        char = get_mdi_char("definitely_not_a_real_icon_12345")
        fallback_char = get_mdi_char(FALLBACK_ICON)
        assert char == fallback_char

    def test_fallback_icon_exists(self) -> None:
        """Verify fallback icon exists in MDI codepoints."""
        assert FALLBACK_ICON in MDI_CODEPOINTS, "Fallback icon must exist"


class TestIsValidIcon:
    """Tests for is_valid_icon function."""

    def test_valid_mdi_icon(self) -> None:
        """Test valid MDI icons return True."""
        assert is_valid_icon("home") is True
        assert is_valid_icon("thermometer") is True
        assert is_valid_icon("wifi") is True

    def test_valid_legacy_icon(self) -> None:
        """Test legacy icon names return True."""
        assert is_valid_icon("temp") is True
        assert is_valid_icon("cpu") is True
        assert is_valid_icon("drop") is True

    def test_valid_mdi_prefix(self) -> None:
        """Test mdi: prefix format returns True."""
        assert is_valid_icon("mdi:home") is True
        assert is_valid_icon("mdi:thermometer") is True

    def test_invalid_icon(self) -> None:
        """Test unknown icons return False."""
        assert is_valid_icon("not_a_real_icon") is False
        assert is_valid_icon("mdi:fake_icon_12345") is False
