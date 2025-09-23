# NoBASIC Color System Documentation

## Overview

NoBASIC now supports the full Nova-16 color palette system with 256 colors organized as 16 ramps × 16 shades. This provides rich color capabilities for graphics programming.

## Color System Architecture

### Color Representation
- **256 total colors** (0-255)
- **16 color ramps** (0-15): Base hues like black, red, green, blue, etc.
- **16 shades per ramp** (0-15): From darkest to lightest within each ramp

### Color Value Calculation
```
color_value = (ramp_index × 16) + shade_index
```

## Color Constants

NoBASIC provides 17 named color constants for common colors:

| Constant | Value | Description |
|----------|-------|-------------|
| BLACK    | 0     | Pure black |
| WHITE    | 15    | Pure white |
| RED      | 20    | Base red |
| GREEN    | 36    | Base green |
| BLUE     | 52    | Base blue |
| YELLOW   | 68    | Base yellow |
| MAGENTA  | 84    | Base magenta |
| CYAN     | 100   | Base cyan |
| ORANGE   | 116   | Base orange |
| PURPLE   | 132   | Base purple |
| LIME     | 148   | Base lime |
| PINK     | 164   | Base pink |
| TEAL     | 180   | Base teal |
| BROWN    | 196   | Base brown |
| LIGHTBLUE| 212   | Base light blue |
| LIGHTGREEN|228   | Base light green |
| LIGHTRED | 244   | Base light red |

## Color Functions

### COLOR(ramp, shade)
Creates a color value from ramp and shade indices.

**Parameters:**
- `ramp`: 0-15 (color family)
- `shade`: 0-15 (brightness level)

**Returns:** Color value (0-255)

**Example:**
```basic
REM Create bright red
BRIGHT_RED = COLOR(1, 12)

REM Create dark blue
DARK_BLUE = COLOR(3, 4)
```

### RAMP(color)
Extracts the ramp index from a color value.

**Parameters:**
- `color`: Color value (0-255)

**Returns:** Ramp index (0-15)

**Example:**
```basic
C = RED
R = RAMP(C)  REM R = 1 (red ramp)
```

### SHADE(color)
Extracts the shade index from a color value.

**Parameters:**
- `color`: Color value (0-255)

**Returns:** Shade index (0-15)

**Example:**
```basic
C = GREEN
S = SHADE(C)  REM S = 4 (medium shade)
```

## Graphics Functions with Colors

All graphics functions now accept color parameters:

### PXLON(x, y, color)
Draw a pixel with specified color.

### PXLOFF(x, y)
Turn off a pixel (sets to black).

### LINE(x1, y1, x2, y2, color)
Draw a line with specified color.

### RECT(x, y, width, height, color)
Draw a filled rectangle with specified color.

### CIRCLE(x, y, radius, color)
Draw a filled circle with specified color.

## Color Arithmetic

Colors support basic arithmetic operations:

```basic
REM Color addition (may overflow)
MIXED = RED + BLUE

REM Color subtraction
DIFFERENCE = LIGHT_RED - RED

REM Color scaling (use with caution)
BRIGHTER = GREEN * 2
```

## Testing and Validation

### Running Color Tests

Use the specialized color test runner:

```powershell
python nobasic_color_test_runner.py
```

This will run all color-specific tests:
- `test_colors_constants.nob` - Validates named color constants
- `test_colors_functions.nob` - Tests COLOR(), RAMP(), SHADE() functions
- `test_colors_graphics.nob` - Tests graphics operations with colors
- `test_colors_validation.nob` - Comprehensive validation test

### Test Output

Each test provides:
- ✅ Compilation success
- ✅ Assembly success
- ✅ Execution success
- ✅ Color validation results
- Pixel counts and color distributions
- Pass/fail status with detailed error messages

### Graphics Monitor Integration

The color test runner uses a specialized graphics monitor configuration (`color_validation_config.json`) that:

- Detects validation pixels (green = pass, red = fail)
- Analyzes color distributions
- Validates expected color patterns
- Provides detailed color usage statistics

## Example Programs

### Color Palette Display
```basic
REM Display all 256 colors in a grid
CLRHOME

FOR RAMP = 0 TO 15
    FOR SHADE = 0 TO 15
        X = SHADE * 10
        Y = RAMP * 10
        C = COLOR(RAMP, SHADE)
        PXLON(X, Y, C)
    NEXT SHADE
NEXT RAMP

PAUSE
```

### Color Cycling Animation
```basic
REM Animate through color ramps
CLRHOME

WHILE TRUE
    FOR RAMP = 0 TO 15
        FOR X = 0 TO 255 STEP 10
            FOR Y = 0 TO 255 STEP 10
                C = COLOR(RAMP, (X + Y) / 32)
                PXLON(X, Y, C)
            NEXT Y
        NEXT X
        PAUSE 100
    NEXT RAMP
WEND
```

### Color Extraction Demo
```basic
REM Demonstrate color extraction functions
CLRHOME

TEST_COLOR = YELLOW
DISP "Original color: " + STR(TEST_COLOR)
DISP "Ramp: " + STR(RAMP(TEST_COLOR))
DISP "Shade: " + STR(SHADE(TEST_COLOR))

REM Reconstruct the color
RECONSTRUCTED = COLOR(RAMP(TEST_COLOR), SHADE(TEST_COLOR))
DISP "Reconstructed: " + STR(RECONSTRUCTED)
DISP "Match: " + STR(TEST_COLOR = RECONSTRUCTED)

PAUSE
```

## Best Practices

1. **Use named constants** for common colors to improve code readability
2. **Validate color ranges** before using COLOR() function (0-15 for both parameters)
3. **Test color extraction** functions to ensure round-trip conversion works
4. **Use graphics monitor** to verify color output during development
5. **Run color tests** after any compiler changes to ensure stability

## Troubleshooting

### Common Issues

**Compilation Error: "Unknown identifier"**
- Check that color constants are spelled correctly
- Ensure COLOR(), RAMP(), SHADE() functions are used properly

**Wrong Colors Displayed**
- Verify color value ranges (0-255)
- Check graphics function parameters
- Use graphics monitor to inspect actual pixel values

**Color Functions Not Working**
- Ensure ramp and shade parameters are integers 0-15
- Check for arithmetic overflow in color calculations

### Debug Tools

```powershell
# Run graphics monitor on your program
python nova_graphics_monitor.py program.bin --cycles 1000 --export debug_output

# Check color distribution in output files
# Look for *_graphics_debug.json files
```

## Integration with Existing Code

The color system is fully backward compatible. Existing programs that don't use colors will continue to work unchanged. Graphics functions default to appropriate colors when none are specified.