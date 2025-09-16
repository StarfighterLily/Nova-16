#!/usr/bin/env python3
"""
Font Template Generator for Nova System
Creates template characters and character sets
"""

def create_number_templates():
    """Create template patterns for numbers 0-9"""
    number_patterns = {
        ord('0'): [
            0b00111100,  # "  ****  "
            0b01100110,  # " **  ** "
            0b01100110,  # " **  ** "
            0b01100110,  # " **  ** "
            0b01100110,  # " **  ** "
            0b01100110,  # " **  ** "
            0b01100110,  # " **  ** "
            0b00111100,  # "  ****  "
        ],
        ord('1'): [
            0b00011000,  # "   **   "
            0b00111000,  # "  ***   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b01111110,  # " ****** "
        ],
        ord('2'): [
            0b00111100,  # "  ****  "
            0b01100110,  # " **  ** "
            0b00000110,  # "     ** "
            0b00001100,  # "    **  "
            0b00011000,  # "   **   "
            0b00110000,  # "  **    "
            0b01100000,  # " **     "
            0b01111110,  # " ****** "
        ],
        # Add more number patterns as needed
    }
    return number_patterns

def create_letter_templates():
    """Create template patterns for letters A-Z"""
    letter_patterns = {
        ord('A'): [
            0b00011000,  # "   **   "
            0b00100100,  # "  *  *  "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
            0b01111110,  # " ****** "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
        ],
        ord('B'): [
            0b01111100,  # " *****  "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
            0b01111100,  # " *****  "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
            0b01000010,  # " *    * "
            0b01111100,  # " *****  "
        ],
        # Add more letter patterns as needed
    }
    return letter_patterns

def create_symbol_templates():
    """Create template patterns for common symbols"""
    symbol_patterns = {
        ord('!'): [
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00011000,  # "   **   "
            0b00000000,  # "        "
            0b00000000,  # "        "
            0b00011000,  # "   **   "
        ],
        ord('?'): [
            0b00111100,  # "  ****  "
            0b01100110,  # " **  ** "
            0b00000110,  # "     ** "
            0b00001100,  # "    **  "
            0b00011000,  # "   **   "
            0b00000000,  # "        "
            0b00000000,  # "        "
            0b00011000,  # "   **   "
        ],
        ord('@'): [
            0b00111100,  # "  ****  "
            0b01000010,  # " *    * "
            0b01011010,  # " * ** * "
            0b01010110,  # " * * ** "
            0b01011110,  # " * **** "
            0b01000000,  # " *      "
            0b01000010,  # " *    * "
            0b00111100,  # "  ****  "
        ],
        # Add more symbol patterns as needed
    }
    return symbol_patterns

def create_box_drawing_templates():
    """Create template patterns for box drawing characters"""
    box_patterns = {
        # Single line box drawing
        0x2500: [  # ─ Horizontal line
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111111,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x2502: [  # │ Vertical line
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        0x250C: [  # ┌ Top-left corner
            0b00000000,
            0b00000000,
            0b00000000,
            0b00011111,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        0x2510: [  # ┐ Top-right corner
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111000,
            0b00001000,
            0b00001000,
            0b00001000,
            0b00001000,
        ],
        0x2514: [  # └ Bottom-left corner
            0b00010000,
            0b00010000,
            0b00010000,
            0b00011111,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x2518: [  # ┘ Bottom-right corner
            0b00001000,
            0b00001000,
            0b00001000,
            0b11111000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x251C: [  # ├ Left T-junction
            0b00010000,
            0b00010000,
            0b00010000,
            0b11111111,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        0x2524: [  # ┤ Right T-junction
            0b00001000,
            0b00001000,
            0b00001000,
            0b11111111,
            0b00001000,
            0b00001000,
            0b00001000,
            0b00001000,
        ],
        0x252C: [  # ┬ Top T-junction
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111111,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        0x2534: [  # ┴ Bottom T-junction
            0b00010000,
            0b00010000,
            0b00010000,
            0b11111111,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x253C: [  # ┼ Cross junction
            0b00010000,
            0b00010000,
            0b00010000,
            0b11111111,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
    }
    return box_patterns

def create_block_templates():
    """Create template patterns for block characters"""
    block_patterns = {
        0x2580: [  # ▀ Upper half block
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x2584: [  # ▄ Lower half block
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
        ],
        0x2588: [  # █ Full block
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
            0b11111111,
        ],
        0x258C: [  # ▌ Left half block
            0b11110000,
            0b11110000,
            0b11110000,
            0b11110000,
            0b11110000,
            0b11110000,
            0b11110000,
            0b11110000,
        ],
        0x2590: [  # ▐ Right half block
            0b00001111,
            0b00001111,
            0b00001111,
            0b00001111,
            0b00001111,
            0b00001111,
            0b00001111,
            0b00001111,
        ],
        0x2591: [  # ░ Light shade
            0b10001000,
            0b00100010,
            0b10001000,
            0b00100010,
            0b10001000,
            0b00100010,
            0b10001000,
            0b00100010,
        ],
        0x2592: [  # ▒ Medium shade
            0b10101010,
            0b01010101,
            0b10101010,
            0b01010101,
            0b10101010,
            0b01010101,
            0b10101010,
            0b01010101,
        ],
        0x2593: [  # ▓ Dark shade
            0b11101110,
            0b10111011,
            0b11101110,
            0b10111011,
            0b11101110,
            0b10111011,
            0b11101110,
            0b10111011,
        ],
    }
    return block_patterns

def create_arrow_templates():
    """Create template patterns for arrow characters"""
    arrow_patterns = {
        0x2190: [  # ← Left arrow
            0b00000000,
            0b00001000,
            0b00011000,
            0b00111111,
            0b01111111,
            0b00111111,
            0b00011000,
            0b00001000,
        ],
        0x2191: [  # ↑ Up arrow
            0b00010000,
            0b00111000,
            0b01111100,
            0b11111110,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        0x2192: [  # → Right arrow
            0b00000000,
            0b00010000,
            0b00011000,
            0b11111100,
            0b11111110,
            0b11111100,
            0b00011000,
            0b00010000,
        ],
        0x2193: [  # ↓ Down arrow
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b11111110,
            0b01111100,
            0b00111000,
            0b00010000,
        ],
        0x2196: [  # ↖ Northwest arrow
            0b11111110,
            0b11100000,
            0b11010000,
            0b10001000,
            0b00000100,
            0b00000010,
            0b00000001,
            0b00000000,
        ],
        0x2197: [  # ↗ Northeast arrow
            0b01111111,
            0b00000111,
            0b00001011,
            0b00010001,
            0b00100000,
            0b01000000,
            0b10000000,
            0b00000000,
        ],
        0x2198: [  # ↘ Southeast arrow
            0b00000000,
            0b10000000,
            0b01000000,
            0b00100000,
            0b00010001,
            0b00001011,
            0b00000111,
            0b01111111,
        ],
        0x2199: [  # ↙ Southwest arrow
            0b00000000,
            0b00000001,
            0b00000010,
            0b00000100,
            0b10001000,
            0b11010000,
            0b11100000,
            0b11111110,
        ],
    }
    return arrow_patterns

def create_playing_card_templates():
    """Create template patterns for playing card suits"""
    card_patterns = {
        0x2660: [  # ♠ Spade
            0b00010000,
            0b00111000,
            0b01111100,
            0b11111110,
            0b11111110,
            0b01111100,
            0b00111000,
            0b01111100,
        ],
        0x2663: [  # ♣ Club
            0b00010000,
            0b00111000,
            0b01111100,
            0b01111100,
            0b11111110,
            0b11111110,
            0b00010000,
            0b00111000,
        ],
        0x2665: [  # ♥ Heart
            0b01100110,
            0b11111111,
            0b11111111,
            0b11111111,
            0b01111110,
            0b00111100,
            0b00011000,
            0b00000000,
        ],
        0x2666: [  # ♦ Diamond
            0b00010000,
            0b00111000,
            0b01111100,
            0b11111110,
            0b01111100,
            0b00111000,
            0b00010000,
            0b00000000,
        ],
    }
    return card_patterns

def create_math_symbol_templates():
    """Create template patterns for mathematical symbols"""
    math_patterns = {
        ord('+'): [
            0b00000000,
            0b00010000,
            0b00010000,
            0b01111100,
            0b00010000,
            0b00010000,
            0b00000000,
            0b00000000,
        ],
        ord('-'): [
            0b00000000,
            0b00000000,
            0b00000000,
            0b01111100,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        ord('*'): [
            0b00000000,
            0b01000100,
            0b00101000,
            0b00010000,
            0b00101000,
            0b01000100,
            0b00000000,
            0b00000000,
        ],
        ord('/'): [
            0b00000010,
            0b00000100,
            0b00001000,
            0b00010000,
            0b00100000,
            0b01000000,
            0b10000000,
            0b00000000,
        ],
        ord('='): [
            0b00000000,
            0b00000000,
            0b01111100,
            0b00000000,
            0b01111100,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        0x00B1: [  # ± Plus-minus
            0b00000000,
            0b00010000,
            0b01111100,
            0b00010000,
            0b00000000,
            0b01111100,
            0b00000000,
            0b00000000,
        ],
        0x00D7: [  # × Multiplication
            0b00000000,
            0b01000100,
            0b00101000,
            0b00010000,
            0b00101000,
            0b01000100,
            0b00000000,
            0b00000000,
        ],
        0x00F7: [  # ÷ Division
            0b00000000,
            0b00010000,
            0b00000000,
            0b01111100,
            0b00000000,
            0b00010000,
            0b00000000,
            0b00000000,
        ],
        0x221A: [  # √ Square root
            0b00000011,
            0b00000101,
            0b00001001,
            0b00010001,
            0b00100001,
            0b01000001,
            0b10000001,
            0b11111111,
        ],
        0x221E: [  # ∞ Infinity
            0b00000000,
            0b00000000,
            0b01100110,
            0b10011001,
            0b10011001,
            0b01100110,
            0b00000000,
            0b00000000,
        ],
    }
    return math_patterns

def create_emoji_templates():
    """Create simple emoji-style templates"""
    emoji_patterns = {
        0x263A: [  # ☺ Smiley face
            0b00111100,
            0b01000010,
            0b10100101,
            0b10000001,
            0b10100101,
            0b10011001,
            0b01000010,
            0b00111100,
        ],
        0x2639: [  # ☹ Frowny face
            0b00111100,
            0b01000010,
            0b10100101,
            0b10000001,
            0b10011001,
            0b10100101,
            0b01000010,
            0b00111100,
        ],
        0x2661: [  # ♡ Heart outline
            0b01100110,
            0b10011001,
            0b10000001,
            0b10000001,
            0b01000010,
            0b00100100,
            0b00011000,
            0b00000000,
        ],
        0x2605: [  # ★ Star
            0b00010000,
            0b00010000,
            0b01111100,
            0b00111000,
            0b01111100,
            0b01101100,
            0b11000110,
            0b00000000,
        ],
    }
    return emoji_patterns

def get_all_templates():
    """Get all template patterns"""
    templates = {}
    
    templates.update(create_number_templates())
    templates.update(create_letter_templates())
    templates.update(create_symbol_templates())
    templates.update(create_box_drawing_templates())
    templates.update(create_block_templates())
    templates.update(create_arrow_templates())
    templates.update(create_playing_card_templates())
    templates.update(create_math_symbol_templates())
    templates.update(create_emoji_templates())
    
    return templates

def export_templates_to_json(filename="font_templates.json"):
    """Export all templates to JSON file"""
    import json
    templates = get_all_templates()
    
    # Convert to string keys for JSON compatibility
    json_templates = {str(k): v for k, v in templates.items()}
    
    with open(filename, 'w') as f:
        json.dump(json_templates, f, indent=2)
    
    print(f"Exported {len(templates)} templates to {filename}")

if __name__ == "__main__":
    export_templates_to_json()
    
    print("Available template categories:")
    print("- Numbers (0-9)")
    print("- Letters (A-Z, partial)")
    print("- Symbols (!, ?, @, etc.)")
    print("- Box drawing characters")
    print("- Block characters")
    print("- Arrow characters")
    print("- Playing card suits")
    print("- Mathematical symbols")
    print("- Simple emoji")
    
    templates = get_all_templates()
    print(f"\nTotal templates created: {len(templates)}")
