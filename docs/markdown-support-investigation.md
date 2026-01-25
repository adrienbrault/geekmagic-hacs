# Markdown Support Investigation

## Executive Summary

This document investigates how markdown support could be added to the GeekMagic HACS integration. Given the display constraints (240x240 pixels), a **limited subset** of markdown would be practical.

## Current State

### Text Rendering Architecture

The integration uses a component-based rendering system with Pillow (PIL) for image generation:

1. **Text Component** (`widgets/components.py:120-178`): Single font/color per text block
2. **FillText Component** (`widgets/components.py:678-750`): Auto-sizing text with hierarchy
3. **TextDisplay** (`widgets/text.py:31-114`): Full-width text with optional label
4. **TextWidget** (`widgets/text.py:116-175`): Static or entity-bound text display

### Current Capabilities
- Font sizes: semantic (`primary`, `secondary`, `tertiary`) and legacy (`tiny` to `huge`)
- Bold/regular weight via separate font files (DejaVuSans, DejaVuSans-Bold)
- Theme-aware colors (primary text, secondary text)
- Text truncation with ellipsis
- Text alignment (left, center, right)

### Current Limitations
- **No inline formatting**: Can't mix bold/normal within a single text element
- **No word wrapping**: Text must fit on one line or be truncated
- **No italic**: Only regular and bold fonts bundled
- **Single color per text**: Can't have colored words inline

## Display Constraints

- **Resolution**: 240x240 pixels (480x480 internal with 2x supersampling)
- **Physical size**: ~4cm diagonal OLED
- **Minimum readable font**: 10-12px (scaled to 20-24px internal)
- **Practical text capacity**: ~15-20 characters per line at readable sizes

## Recommended Markdown Subset

Given the constraints, only these markdown features would be practical:

### Tier 1: Essential (Recommended to implement)

| Feature | Syntax | Rendering |
|---------|--------|-----------|
| Bold | `**text**` or `__text__` | Bold font weight |
| Line breaks | `\n` or `<br>` | New line |
| Emphasis colors | `*text*` or `_text_` | Secondary color (instead of italic) |

### Tier 2: Useful (Consider implementing)

| Feature | Syntax | Rendering |
|---------|--------|-----------|
| Headers | `# text` | Larger font size |
| Color spans | `{red}text{/red}` | Custom extension for colors |
| Icons | `:icon-name:` | MDI icon inline |

### Tier 3: Not Recommended

| Feature | Why Not |
|---------|---------|
| Links | No interaction possible on display |
| Images | Display shows one image already |
| Lists | Too space-consuming for 240px |
| Tables | Way too small for tables |
| Code blocks | Monospace would be tiny |
| Strikethrough | Minimal value, adds complexity |

## Implementation Options

### Option A: Custom Lightweight Parser (Recommended)

Create a simple markdown parser specifically for our limited subset.

**Pros:**
- No external dependencies
- Optimized for our use case
- Fast and lightweight
- Full control over behavior

**Cons:**
- Need to implement and test parser
- Can't leverage existing markdown ecosystem

**Implementation sketch:**

```python
# widgets/rich_text.py

@dataclass
class TextSpan:
    """A segment of styled text."""
    text: str
    bold: bool = False
    color: Color | None = None  # None = inherit from parent
    size: str | None = None  # None = inherit from parent

def parse_markdown(text: str) -> list[TextSpan]:
    """Parse limited markdown into styled spans.

    Supports: **bold**, *emphasis*, and newlines.
    """
    spans = []
    # ... regex-based parsing
    return spans

@dataclass
class RichText(Component):
    """Text component supporting inline formatting."""

    spans: list[TextSpan]
    align: Align = "center"
    wrap: bool = False  # Enable word wrapping

    def measure(self, ctx, max_width, max_height) -> tuple[int, int]:
        # Measure each span and calculate total size
        # Handle word wrapping if enabled
        pass

    def render(self, ctx, x, y, width, height) -> None:
        # Render each span with its styling
        # Handle line breaks and wrapping
        pass
```

### Option B: Use `mistune` Library

Use the popular [mistune](https://github.com/lepture/mistune) markdown parser.

**Pros:**
- Battle-tested markdown parser
- Handles edge cases well
- Easy to customize renderer

**Cons:**
- External dependency (need to add to manifest.json)
- May be overkill for limited subset
- Some installation complexity for HACS users

**Implementation sketch:**

```python
import mistune

class GeekMagicRenderer(mistune.HTMLRenderer):
    """Custom renderer that outputs TextSpan objects."""

    def text(self, text):
        return TextSpan(text)

    def strong(self, text):
        # text is already a TextSpan from recursive call
        text.bold = True
        return text

    def emphasis(self, text):
        text.color = THEME_TEXT_SECONDARY
        return text
```

### Option C: Template String Format

Use a custom template syntax instead of markdown.

```
{b}Bold text{/b}
{c:red}Red text{/c}
{s:large}Large text{/s}
{icon:thermometer}
```

**Pros:**
- Explicit and unambiguous
- Easy to parse
- More powerful than markdown

**Cons:**
- Not standard markdown
- Users need to learn new syntax
- Less familiar

## Recommended Approach: Option A with Progressive Enhancement

### Phase 1: Core Infrastructure

1. Create `TextSpan` dataclass for styled text segments
2. Create `RichText` component that renders multiple spans
3. Add word-wrapping support to `RichText`

**Files to create/modify:**
- Create: `widgets/rich_text.py`
- Modify: `widgets/components.py` (add RichText to exports)
- Modify: `widgets/__init__.py` (export new component)

### Phase 2: Markdown Parser

1. Implement simple regex-based parser for `**bold**` and `*emphasis*`
2. Handle escaped characters
3. Handle newlines

### Phase 3: Widget Integration

1. Create `MarkdownWidget` or add markdown mode to `TextWidget`
2. Add `markdown: true` option to widget config
3. Update frontend panel to show markdown option

### Phase 4: Documentation & Testing

1. Add tests for parser edge cases
2. Document supported syntax
3. Add sample widgets showing markdown

## Technical Details

### Word Wrapping Algorithm

Word wrapping is essential for markdown to be useful. Here's the approach:

```python
def wrap_text(spans: list[TextSpan], ctx: RenderContext, max_width: int) -> list[list[TextSpan]]:
    """Wrap styled text spans into lines that fit max_width."""
    lines = []
    current_line = []
    current_width = 0

    for span in spans:
        words = span.text.split(' ')
        for i, word in enumerate(words):
            if i > 0:
                word = ' ' + word

            word_span = TextSpan(word, bold=span.bold, color=span.color)
            font = ctx.get_font("regular", bold=span.bold)
            word_width, _ = ctx.get_text_size(word, font)

            if current_width + word_width > max_width and current_line:
                # Start new line
                lines.append(current_line)
                current_line = [TextSpan(word.lstrip(), bold=span.bold, color=span.color)]
                font = ctx.get_font("regular", bold=span.bold)
                current_width, _ = ctx.get_text_size(word.lstrip(), font)
            else:
                current_line.append(word_span)
                current_width += word_width

    if current_line:
        lines.append(current_line)

    return lines
```

### Rendering Multiple Spans on a Line

```python
def render_line(self, ctx: RenderContext, spans: list[TextSpan],
                x: int, y: int, width: int, align: str) -> None:
    """Render a line of styled text spans."""
    # Calculate total width
    total_width = sum(
        ctx.get_text_size(s.text, ctx.get_font("regular", bold=s.bold))[0]
        for s in spans
    )

    # Calculate starting x based on alignment
    if align == "center":
        current_x = x + (width - total_width) // 2
    elif align == "end":
        current_x = x + width - total_width
    else:
        current_x = x

    # Render each span
    for span in spans:
        font = ctx.get_font("regular", bold=span.bold)
        color = span.color or ctx.theme.text_primary
        ctx.draw_text(span.text, (current_x, y), font, color, anchor="lm")
        word_width, _ = ctx.get_text_size(span.text, font)
        current_x += word_width
```

### Markdown Parser Implementation

```python
import re
from dataclasses import dataclass

@dataclass
class TextSpan:
    text: str
    bold: bool = False
    emphasis: bool = False

def parse_simple_markdown(text: str) -> list[TextSpan]:
    """Parse **bold** and *emphasis* markdown."""
    spans = []

    # Pattern matches **bold**, *emphasis*, or plain text
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|([^*]+))'

    for match in re.finditer(pattern, text):
        full_match = match.group(0)

        if full_match.startswith('**') and full_match.endswith('**'):
            # Bold text
            spans.append(TextSpan(match.group(2), bold=True))
        elif full_match.startswith('*') and full_match.endswith('*'):
            # Emphasis text
            spans.append(TextSpan(match.group(3), emphasis=True))
        else:
            # Plain text
            spans.append(TextSpan(match.group(4)))

    return spans
```

## Effort Estimate

| Phase | Complexity | Key Work |
|-------|------------|----------|
| Phase 1: Infrastructure | Medium | RichText component, word wrapping |
| Phase 2: Parser | Low | Regex-based markdown parser |
| Phase 3: Integration | Medium | Widget config, frontend updates |
| Phase 4: Testing | Low-Medium | Parser tests, rendering tests |

## Open Questions

1. **Should markdown be opt-in per widget or global?**
   - Recommendation: Per-widget option, disabled by default for backward compatibility

2. **How should we handle overflow?**
   - Truncate with ellipsis on last visible line
   - Or: shrink font to fit (auto-sizing)

3. **Should we support nested formatting like `***bold and emphasis***`?**
   - Recommendation: No, keep parser simple

4. **Should emphasis render as italic or different color?**
   - Recommendation: Different color (secondary), since we don't have italic font

5. **What about entity templates with markdown?**
   - Example: `Temperature: **{{ states.sensor.temp }}°C**`
   - Would require integration with Jinja templating

## Conclusion

Markdown support is feasible with a limited feature set. The recommended approach is:

1. Start with **bold** and *emphasis* only
2. Add word wrapping as part of the infrastructure
3. Use a custom lightweight parser (no external deps)
4. Make it opt-in per widget
5. Consider color spans as a custom extension

This provides value to users while keeping complexity manageable for a 240x240 pixel display.
