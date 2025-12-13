"""Constants for GeekMagic integration."""

DOMAIN = "geekmagic"

# Display dimensions
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

# Default settings
DEFAULT_REFRESH_INTERVAL = 10  # seconds
DEFAULT_JPEG_QUALITY = 92  # High quality for crisp display
MAX_IMAGE_SIZE = 400 * 1024  # 400KB max size for device uploads

# Config keys
CONF_HOST = "host"
CONF_NAME = "name"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_LAYOUT = "layout"
CONF_WIDGETS = "widgets"

# Layout types
LAYOUT_GRID_2X2 = "grid_2x2"
LAYOUT_GRID_2X3 = "grid_2x3"
LAYOUT_HERO = "hero"
LAYOUT_SPLIT = "split"

# Widget types
WIDGET_CLOCK = "clock"
WIDGET_ENTITY = "entity"
WIDGET_MEDIA = "media"
WIDGET_CHART = "chart"
WIDGET_TEXT = "text"
WIDGET_BAR = "bar"

# Colors (RGB tuples) - Using palettable Bold and Dark2 palettes
# These are colorblind-friendly and professionally curated

# Base colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (100, 100, 100)
COLOR_DARK_GRAY = (40, 40, 40)
COLOR_PANEL = (18, 18, 18)
COLOR_PANEL_BORDER = (50, 50, 50)

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
