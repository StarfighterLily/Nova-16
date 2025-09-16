# Nova Enhanced Font System

The Nova Enhanced Font System provides comprehensive tools for creating, editing, and managing fonts for the Nova CPU system. This expanded toolset allows you to quickly and easily create fonts for the entire printable character range.

## Files Overview

### Core Files
- `font.py` - Original font data (ASCII 32-127 + some extended characters)
- `fontmaker.py` - Original simple font editor

### Enhanced Tools
- `enhanced_fontmaker.py` - Advanced font editor with full feature set
- `font_manager.py` - Command-line font management utilities
- `font_templates.py` - Template generator for common character patterns
- `demo_fontmaker.py` - Demo script showing usage examples

### Generated Files
- `font_templates.json` - Pre-made character templates
- `demo_font.py` - Example font created programmatically

## Enhanced Font Maker Features

### Character Editor
- **8x8 pixel grid editor** with intuitive click-to-toggle interface
- **Multiple editing modes**: Left-click to set, right-click to clear, drag to paint
- **Editing tools**: Clear All, Fill All, Invert, Shift operations (up/down/left/right)
- **Real-time preview** of current character

### Navigation & Character Management
- **Character input**: Enter character directly or by ASCII code
- **Navigation buttons**: Previous/Next character
- **Quick jumps**: Direct navigation to character ranges (numbers, letters, etc.)
- **Character list**: Scrollable list of all defined characters

### Live Text Preview
- **Multi-line text preview** showing how your font looks in actual text
- **Customizable preview text** - type anything to test your font
- **Real-time updates** as you edit characters

### File Operations
- **Export formats**:
  - Raw font data (hex values)
  - Python code (ready to use in Nova system)
- **Import capabilities**: Load existing font data
- **Project save/load**: Save your work and resume later
- **Template system**: Load pre-made character patterns

### Extended Character Support
- **Full ASCII range**: 0-255 character codes
- **Unicode support**: Box drawing, mathematical symbols, arrows
- **Special characters**: Playing card suits, emoji-style faces
- **Accented letters**: Common European character sets

## Font Manager Utilities

The `font_manager.py` script provides command-line tools for batch operations:

```bash
# Generate full printable character set with templates
python font_manager.py --generate

# Export font to Python code
python font_manager.py --export-python my_font.py

# Export font to JSON
python font_manager.py --export-json my_font.json

# Import font from JSON
python font_manager.py --import-json my_font.json

# Show character map
python font_manager.py --char-map

# Validate font data integrity
python font_manager.py --validate
```

## Font Templates

The template system includes pre-made patterns for:

- **Basic characters**: Numbers (0-9), Letters (A-Z)
- **Symbols**: !, ?, @, mathematical operators
- **Box drawing**: ┌─┐│└┘├┤┬┴┼ (Unicode 0x2500-0x253C)
- **Block elements**: ▀▄█▌▐░▒▓ (Unicode 0x2580-0x2593)
- **Arrows**: ←↑→↓↖↗↘↙ (Unicode 0x2190-0x2199)
- **Playing cards**: ♠♣♥♦ (Unicode 0x2660-0x2666)
- **Math symbols**: ±×÷√∞ (Various Unicode ranges)
- **Simple emoji**: ☺☹♡★ (Unicode 0x2605, 0x263A, etc.)

## Usage Examples

### Quick Start - Enhanced Font Maker
```bash
# Launch the enhanced font maker
python enhanced_fontmaker.py
```

### Create Templates
```bash
# Generate template file
python font_templates.py
```

### Run Demo
```bash
# Launch demo with templates loaded
python demo_fontmaker.py

# Create minimal demo font programmatically
python demo_fontmaker.py --minimal
```

### Batch Operations
```bash
# Create complete character set
python font_manager.py --generate --export-python complete_font.py

# Validate existing font
python font_manager.py --validate --char-map
```

## Integration with Nova System

The enhanced font system is fully compatible with the Nova CPU:

### Font Data Format
- **8x8 pixel characters**: Each character is 8 bytes (one per row)
- **Bit format**: MSB is leftmost pixel, LSB is rightmost
- **Character mapping**: ASCII codes map directly to array indices

### Usage in Nova Graphics
```python
# The nova_gfx.py system can use the enhanced fonts
from nova_gfx import NovaGraphics
from enhanced_font import font_data_extended

# Draw character with enhanced font
gfx.draw_char('A', x=10, y=20, color=0xFF)
gfx.draw_string("Hello World!", x=0, y=0, color=0xFF)
```

### Memory Layout
- **Original font**: ASCII 32-127 (96 characters × 8 bytes = 768 bytes)
- **Enhanced font**: ASCII 0-255 (256 characters × 8 bytes = 2048 bytes)
- **Custom ranges**: Support for any character code range

## Character Code Ranges

### Standard ASCII
- **0-31**: Control characters
- **32-126**: Printable ASCII (space through tilde)
- **127**: DEL character

### Extended ASCII
- **128-255**: Extended character set including:
  - Latin accented letters (À, Á, Ç, etc.)
  - Currency symbols (£, ¥, ¤)
  - Mathematical symbols (±, ×, ÷)
  - Box drawing and block characters

### Unicode Support
The system supports Unicode character codes for special symbols:
- **0x2500-0x257F**: Box drawing
- **0x2580-0x259F**: Block elements  
- **0x2190-0x21FF**: Arrows
- **0x2660-0x26FF**: Miscellaneous symbols

## Tips for Font Creation

### Design Guidelines
1. **Consistency**: Keep similar stroke widths across characters
2. **Readability**: Ensure characters are distinguishable at small sizes
3. **Spacing**: Leave appropriate space between character elements
4. **Alignment**: Align characters to a consistent baseline

### Workflow Recommendations
1. **Start with templates**: Use provided templates as starting points
2. **Test frequently**: Use the preview feature to test readability
3. **Create families**: Design uppercase, lowercase, and symbols together
4. **Export regularly**: Save your work frequently
5. **Validate**: Use the validation tools to check font integrity

### Performance Considerations
- **Memory usage**: Extended fonts use more memory
- **Load time**: Larger fonts take longer to load
- **Compatibility**: Ensure your Nova system supports the character range you need

## Troubleshooting

### Common Issues
1. **Template loading fails**: Ensure `font_templates.json` exists
2. **Export errors**: Check file permissions in target directory
3. **Character display issues**: Verify character codes are in supported range
4. **Preview not updating**: Try clicking in the character grid to refresh

### Error Messages
- **"Character X not found"**: Add the character using the editor
- **"Invalid byte value"**: Font data must be 0-255
- **"Pattern must be 64 characters"**: Binary patterns need exactly 64 bits

## Future Enhancements

Possible future improvements:
- **Import from image files**: Convert bitmap images to font data
- **Vector font support**: Support for scalable fonts
- **Font metrics**: Kerning and spacing adjustments
- **Multi-size fonts**: Support for different character sizes
- **Font families**: Manage related fonts together

## Technical Details

### Font Data Structure
```python
# Character data format
character_data = [
    0b10000001,  # Row 0: "*      *"
    0b01000010,  # Row 1: " *    * "
    0b00100100,  # Row 2: "  *  *  "
    0b00011000,  # Row 3: "   **   "
    0b00011000,  # Row 4: "   **   "
    0b00100100,  # Row 5: "  *  *  "
    0b01000010,  # Row 6: " *    * "
    0b10000001,  # Row 7: "*      *"
]
```

### Coordinate System
- **Origin**: Top-left (0,0)
- **X-axis**: Left to right (0-7)
- **Y-axis**: Top to bottom (0-7)
- **Bit order**: MSB is leftmost pixel

### File Formats
- **JSON**: Human-readable project format
- **Python**: Direct code integration
- **Binary**: Compact storage format (future)

This enhanced font system provides everything needed to create professional-quality fonts for the Nova system, from simple character editing to complete font family creation.
