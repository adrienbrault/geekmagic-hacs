"""Constants for GeekMagic integration."""

DOMAIN = "geekmagic"

# Device models
MODEL_ULTRA = "ultra"
MODEL_PRO = "pro"
MODEL_UNKNOWN = "unknown"

# Display dimensions
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

# Default settings
DEFAULT_REFRESH_INTERVAL = 10  # seconds
DEFAULT_JPEG_QUALITY = 92  # High quality for crisp display

# Backoff settings for offline device handling
# When device is unreachable, increase update interval exponentially
# to reduce log spam and resource usage
MAX_BACKOFF_MULTIPLIER = 16  # Max 160s (~2.7 min) between retries (10s * 2^4)
BACKOFF_LOG_INTERVAL = 30  # Log summary every 30 failures (~5 min at max backoff)
DEFAULT_DISPLAY_ROTATION = 0  # No rotation
MAX_IMAGE_SIZE = 400 * 1024  # 400KB max size for device uploads

# Config keys
CONF_HOST = "host"
CONF_NAME = "name"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_JPEG_QUALITY = "jpeg_quality"
CONF_DISPLAY_ROTATION = "display_rotation"
CONF_LAYOUT = "layout"
CONF_WIDGETS = "widgets"

# Multi-screen config keys
CONF_SCREENS = "screens"
CONF_SCREEN_NAME = "screen_name"
CONF_SCREEN_CYCLE_INTERVAL = "screen_cycle_interval"
CONF_CURRENT_SCREEN = "current_screen"
CONF_SCREEN_THEME = "theme"
DEFAULT_SCREEN_CYCLE_INTERVAL = 0  # 0 = manual only, >0 = seconds between screens

# Theme types
THEME_CLASSIC = "classic"
THEME_MINIMAL = "minimal"
THEME_NEON = "neon"
THEME_RETRO = "retro"
THEME_SOFT = "soft"
THEME_LIGHT = "light"
THEME_OCEAN = "ocean"
THEME_SUNSET = "sunset"
THEME_FOREST = "forest"
THEME_CANDY = "candy"

# Theme display names for UI
THEME_OPTIONS = {
    THEME_CLASSIC: "Classic",
    THEME_MINIMAL: "Minimal",
    THEME_NEON: "Neon",
    THEME_RETRO: "Retro",
    THEME_SOFT: "Soft",
    THEME_LIGHT: "Light",
    THEME_OCEAN: "Ocean",
    THEME_SUNSET: "Sunset",
    THEME_FOREST: "Forest",
    THEME_CANDY: "Candy",
}

# Layout types
LAYOUT_GRID_2X2 = "grid_2x2"
LAYOUT_GRID_2X3 = "grid_2x3"
LAYOUT_GRID_3X2 = "grid_3x2"
LAYOUT_GRID_3X3 = "grid_3x3"
LAYOUT_HERO = "hero"
LAYOUT_SPLIT_H = "split_horizontal"  # Side by side (left/right)
LAYOUT_SPLIT_V = "split_vertical"  # Stacked (top/bottom)
LAYOUT_THREE_COLUMN = "three_column"
LAYOUT_THREE_ROW = "three_row"
LAYOUT_SPLIT_H_1_2 = "split_h_1_2"  # Narrow left (1/3), wide right (2/3)
LAYOUT_SPLIT_H_2_1 = "split_h_2_1"  # Wide left (2/3), narrow right (1/3)
LAYOUT_SIDEBAR_LEFT = "sidebar_left"  # Wide left + 3 right rows
LAYOUT_SIDEBAR_RIGHT = "sidebar_right"  # 3 left rows + wide right
LAYOUT_HERO_TL = "hero_corner_tl"  # 2x2 hero top-left
LAYOUT_HERO_TR = "hero_corner_tr"  # 2x2 hero top-right
LAYOUT_HERO_BL = "hero_corner_bl"  # 2x2 hero bottom-left
LAYOUT_HERO_BR = "hero_corner_br"  # 2x2 hero bottom-right
LAYOUT_HERO_SIMPLE = "hero_simple"  # 1 large hero + 1 footer
LAYOUT_FULLSCREEN = "fullscreen"  # Single widget, full display, no padding

# Widget types
WIDGET_CAMERA = "camera"
WIDGET_CLOCK = "clock"
WIDGET_ENTITY = "entity"
WIDGET_MEDIA = "media"
WIDGET_CHART = "chart"
WIDGET_TEXT = "text"
WIDGET_GAUGE = "gauge"
WIDGET_PROGRESS = "progress"
WIDGET_MULTI_PROGRESS = "multi_progress"
WIDGET_STATUS = "status"
WIDGET_STATUS_LIST = "status_list"
WIDGET_WEATHER = "weather"

# Layout slot counts
LAYOUT_SLOT_COUNTS = {
    LAYOUT_GRID_2X2: 4,
    LAYOUT_GRID_2X3: 6,
    LAYOUT_GRID_3X2: 6,
    LAYOUT_GRID_3X3: 9,
    LAYOUT_HERO: 4,
    LAYOUT_SPLIT_H: 2,
    LAYOUT_SPLIT_V: 2,
    LAYOUT_THREE_COLUMN: 3,
    LAYOUT_THREE_ROW: 3,
    LAYOUT_SPLIT_H_1_2: 2,
    LAYOUT_SPLIT_H_2_1: 2,
    LAYOUT_SIDEBAR_LEFT: 4,
    LAYOUT_SIDEBAR_RIGHT: 4,
    LAYOUT_HERO_TL: 6,
    LAYOUT_HERO_TR: 6,
    LAYOUT_HERO_BL: 6,
    LAYOUT_HERO_BR: 6,
    LAYOUT_HERO_SIMPLE: 2,
    LAYOUT_FULLSCREEN: 1,
}

# Widget type display names for UI
WIDGET_TYPE_NAMES = {
    WIDGET_CAMERA: "Camera",
    WIDGET_CLOCK: "Clock",
    WIDGET_ENTITY: "Entity",
    WIDGET_MEDIA: "Media Player",
    WIDGET_CHART: "Chart",
    WIDGET_TEXT: "Text",
    WIDGET_GAUGE: "Gauge",
    WIDGET_PROGRESS: "Progress",
    WIDGET_MULTI_PROGRESS: "Multi Progress",
    WIDGET_STATUS: "Status",
    WIDGET_STATUS_LIST: "Status List",
    WIDGET_WEATHER: "Weather",
}

# Colors (RGB tuples) - Using palettable Bold and Dark2 palettes
# These are colorblind-friendly and professionally curated

# Base colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (150, 150, 150)  # Increased from 100 for WCAG AA contrast (4.7x vs 3.5x)
COLOR_DARK_GRAY = (50, 50, 50)  # Increased from 40 for better visibility
COLOR_PANEL = (18, 18, 18)
COLOR_PANEL_BORDER = (60, 60, 60)  # Increased from 50 for better contrast

# Primary UI colors from Bold_6 palette (vibrant, distinguishable)
# Bold_6: Purple, Teal, Blue, Yellow, Pink, Green
COLOR_PURPLE = (127, 60, 141)
COLOR_TEAL = (17, 165, 121)
COLOR_BLUE = (57, 105, 172)
COLOR_YELLOW = (242, 183, 1)
COLOR_PINK = (231, 63, 116)
COLOR_GREEN = (128, 186, 90)

# Accent colors from Dark2_8 palette (colorblind-friendly)
COLOR_CYAN = (27, 158, 119)  # Teal variant
COLOR_ORANGE = (217, 95, 2)
COLOR_LAVENDER = (117, 112, 179)
COLOR_MAGENTA = (231, 41, 138)
COLOR_LIME = (102, 166, 30)
COLOR_GOLD = (230, 171, 2)
COLOR_BROWN = (166, 118, 29)
COLOR_RED = (231, 76, 60)  # Custom red for alerts/errors

# Standard placeholder strings for missing data
PLACEHOLDER_VALUE = "--"
PLACEHOLDER_TEXT = "No data"
PLACEHOLDER_NAME = "Unknown"

# Spacing constants for consistent layout (in pixels)
# Use these in component helpers and widgets for uniform spacing
# Increased from original values for better readability per user feedback
SPACING_XS = 4  # Extra small - tight spacing between related items (was 2)
SPACING_SM = 6  # Small - default gap between small elements (was 4)
SPACING_MD = 8  # Medium - standard gap between components (was 6)
SPACING_LG = 10  # Large - padding around content (was 8)
SPACING_XL = 14  # Extra large - major section separation (was 12)

# Responsive padding percentages (as decimals)
# Multiply by container width to get pixel value
PADDING_COMPACT = 0.04  # 4% for dense layouts (3x3 grids)
PADDING_STANDARD = 0.06  # 6% for normal layouts (2x2 grids)
PADDING_SPACIOUS = 0.08  # 8% for layouts with breathing room (1x1, split)

# Icon sizing constants
ICON_SIZE_XS = 12  # Extra small icons (status dots)
ICON_SIZE_SM = 14  # Small icons (inline with text)
ICON_SIZE_MD = 16  # Medium icons (headers, labels)
ICON_SIZE_LG = 20  # Large icons (primary display)
ICON_SIZE_XL = 24  # Extra large icons (hero widgets)
ICON_SIZE_MAX = 32  # Maximum auto-size bound
