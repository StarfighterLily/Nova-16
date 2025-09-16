#!/usr/bin/env python3
"""
Font Utilities for Nova System
Provides batch operations and font management tools
"""

import os
import json
import argparse
from font import font_data

class FontManager:
    def __init__(self):
        self.font_data = {}
        self.load_existing_font()
        
    def load_existing_font(self):
        """Load existing font data from font.py"""
        for i, char_code in enumerate(range(32, len(font_data) // 8 + 32)):
            if i * 8 + 8 <= len(font_data):
                char_bytes = font_data[i * 8:(i + 1) * 8]
                self.font_data[char_code] = list(char_bytes)
                
    def add_character(self, char_code, pattern):
        """Add a character with a specific pattern"""
        if isinstance(pattern, str):
            # Convert string pattern like "10101010" to bytes
            if len(pattern) == 64:  # 8x8 grid as string
                char_bytes = []
                for i in range(0, 64, 8):
                    row = pattern[i:i+8]
                    byte_val = int(row, 2)
                    char_bytes.append(byte_val)
                self.font_data[char_code] = char_bytes
            else:
                raise ValueError("Pattern must be 64 characters (8x8 grid)")
        elif isinstance(pattern, list) and len(pattern) == 8:
            # List of 8 bytes
            self.font_data[char_code] = pattern
        else:
            raise ValueError("Pattern must be list of 8 bytes or 64-char string")
            
    def copy_character(self, source_code, dest_code):
        """Copy character from source to destination"""
        if source_code in self.font_data:
            self.font_data[dest_code] = self.font_data[source_code].copy()
        else:
            raise ValueError(f"Source character {source_code} not found")
            
    def mirror_character(self, char_code, horizontal=True, vertical=False):
        """Mirror a character horizontally and/or vertically"""
        if char_code not in self.font_data:
            raise ValueError(f"Character {char_code} not found")
            
        char_bytes = self.font_data[char_code].copy()
        
        if horizontal:
            # Mirror each row horizontally
            for i in range(8):
                byte_val = char_bytes[i]
                mirrored = 0
                for bit in range(8):
                    if byte_val & (1 << bit):
                        mirrored |= (1 << (7 - bit))
                char_bytes[i] = mirrored
                
        if vertical:
            # Mirror rows vertically
            char_bytes.reverse()
            
        self.font_data[char_code] = char_bytes
        
    def create_box_drawing_chars(self):
        """Create box drawing characters"""
        # Box drawing character codes and their patterns (as byte lists)
        box_chars = {
            # Light box drawing
            0x2500: [0x00, 0x00, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00],  # ─
            0x2502: [0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18],  # │
            0x250C: [0x00, 0x00, 0x00, 0x1F, 0x18, 0x18, 0x18, 0x18],  # ┌
            0x2510: [0x00, 0x00, 0x00, 0xF8, 0x18, 0x18, 0x18, 0x18],  # ┐
            0x2514: [0x18, 0x18, 0x18, 0x1F, 0x00, 0x00, 0x00, 0x00],  # └
            0x2518: [0x18, 0x18, 0x18, 0xF8, 0x00, 0x00, 0x00, 0x00],  # ┘
            0x251C: [0x18, 0x18, 0x18, 0xFF, 0x18, 0x18, 0x18, 0x18],  # ├
            0x2524: [0x18, 0x18, 0x18, 0xFF, 0x18, 0x18, 0x18, 0x18],  # ┤
            0x252C: [0x00, 0x00, 0x00, 0xFF, 0x18, 0x18, 0x18, 0x18],  # ┬
            0x2534: [0x18, 0x18, 0x18, 0xFF, 0x00, 0x00, 0x00, 0x00],  # ┴
            0x253C: [0x18, 0x18, 0x18, 0xFF, 0x18, 0x18, 0x18, 0x18],  # ┼
        }
        
        for code, pattern in box_chars.items():
            self.add_character(code, pattern)
            
    def create_block_chars(self):
        """Create block characters"""
        block_chars = {
            # Block elements
            0x2580: [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00],  # ▀ Upper half
            0x2584: [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF],  # ▄ Lower half
            0x2588: [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],  # █ Full block
            0x258C: [0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0],  # ▌ Left half
            0x2590: [0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F],  # ▐ Right half
            0x2591: [0x88, 0x22, 0x88, 0x22, 0x88, 0x22, 0x88, 0x22],  # ░ Light shade
            0x2592: [0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55],  # ▒ Medium shade
            0x2593: [0xEE, 0xBB, 0xEE, 0xBB, 0xEE, 0xBB, 0xEE, 0xBB],  # ▓ Dark shade
        }
        
        for code, pattern in block_chars.items():
            self.add_character(code, pattern)
            
    def create_arrow_chars(self):
        """Create arrow characters"""
        arrow_chars = {
            # Arrows
            0x2190: [0x00, 0x08, 0x18, 0x3F, 0x7F, 0x3F, 0x18, 0x08],  # ← Left arrow
            0x2191: [0x10, 0x38, 0x7C, 0xFE, 0x10, 0x10, 0x10, 0x10],  # ↑ Up arrow
            0x2192: [0x00, 0x10, 0x18, 0xFC, 0xFE, 0xFC, 0x18, 0x10],  # → Right arrow
            0x2193: [0x10, 0x10, 0x10, 0x10, 0xFE, 0x7C, 0x38, 0x10],  # ↓ Down arrow
        }
        
        for code, pattern in arrow_chars.items():
            self.add_character(code, pattern)
            
    def create_math_symbols(self):
        """Create mathematical symbols"""
        math_chars = {
            # Math symbols
            0x00B1: [0x00, 0x10, 0x7C, 0x10, 0x7C, 0x00, 0x00, 0x00],  # ± Plus-minus
            0x00B2: [0x60, 0x90, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00],  # ² Superscript 2
            0x00B3: [0x60, 0x90, 0x60, 0x90, 0x60, 0x00, 0x00, 0x00],  # ³ Superscript 3
            0x00B5: [0x00, 0x84, 0x84, 0x8C, 0xB4, 0x84, 0x84, 0x80],  # µ Micro sign
            0x00F7: [0x00, 0x10, 0x00, 0x7C, 0x00, 0x10, 0x00, 0x00],  # ÷ Division sign
            0x00D7: [0x00, 0x44, 0x28, 0x10, 0x28, 0x44, 0x00, 0x00],  # × Multiplication sign
        }
        
        for code, pattern in math_chars.items():
            self.add_character(code, pattern)
            
    def generate_full_printable_set(self):
        """Generate a complete printable character set"""
        print("Generating full printable character set...")
        
        # Add box drawing characters
        self.create_box_drawing_chars()
        print("Added box drawing characters")
        
        # Add block characters
        self.create_block_chars()
        print("Added block characters")
        
        # Add arrow characters
        self.create_arrow_chars()
        print("Added arrow characters")
        
        # Add math symbols
        self.create_math_symbols()
        print("Added math symbols")
        
        # Add empty placeholders for common extended ASCII
        for code in range(128, 256):
            if code not in self.font_data:
                self.font_data[code] = [0] * 8
                
        print(f"Total characters: {len(self.font_data)}")
        
    def export_to_python(self, filename="extended_font.py"):
        """Export font data to Python file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Extended Nova Font Data\n")
            f.write("# Generated by Font Manager\n")
            f.write("# 8x8 pixel characters, 8 bytes per character\n\n")
            f.write("extended_font_data = {\n")
            
            for char_code in sorted(self.font_data.keys()):
                char_bytes = self.font_data[char_code]
                hex_bytes = ", ".join(f"0x{b:02X}" for b in char_bytes)
                
                if 32 <= char_code <= 126:
                    char_display = repr(chr(char_code))
                elif char_code < 32:
                    char_display = f"'Control-{char_code}'"
                else:
                    try:
                        char_display = f"'\\u{char_code:04x}'"
                    except:
                        char_display = f"'Code-{char_code}'"
                        
                f.write(f"    {char_code}: [{hex_bytes}],  # {char_display}\n")
                
            f.write("}\n\n")
            f.write("# Convert to flat list for compatibility\n")
            f.write("font_data_extended = []\n")
            f.write("for code in sorted(extended_font_data.keys()):\n")
            f.write("    font_data_extended.extend(extended_font_data[code])\n")
            
        print(f"Exported to {filename}")
        
    def export_to_json(self, filename="font_data.json"):
        """Export font data to JSON file"""
        with open(filename, 'w') as f:
            json.dump({str(k): v for k, v in self.font_data.items()}, f, indent=2)
        print(f"Exported to {filename}")
        
    def import_from_json(self, filename):
        """Import font data from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
            self.font_data = {int(k): v for k, v in data.items()}
        print(f"Imported from {filename}")
        
    def print_character_map(self):
        """Print a visual character map"""
        print("Character Map:")
        print("=" * 60)
        
        for start in range(32, 256, 16):
            line = f"{start:3d}-{start+15:3d}: "
            for code in range(start, min(start + 16, 256)):
                if code in self.font_data:
                    if 32 <= code <= 126:
                        line += chr(code)
                    else:
                        line += "?"
                else:
                    line += " "
            print(line)
            
    def validate_font_data(self):
        """Validate font data integrity"""
        errors = []
        
        for char_code, char_bytes in self.font_data.items():
            if not isinstance(char_bytes, list):
                errors.append(f"Character {char_code}: data is not a list")
            elif len(char_bytes) != 8:
                errors.append(f"Character {char_code}: expected 8 bytes, got {len(char_bytes)}")
            else:
                for i, byte_val in enumerate(char_bytes):
                    if not isinstance(byte_val, int) or not (0 <= byte_val <= 255):
                        errors.append(f"Character {char_code}, byte {i}: invalid byte value {byte_val}")
                        
        if errors:
            print("Validation errors found:")
            for error in errors:
                print(f"  {error}")
        else:
            print("Font data validation passed")
            
        return len(errors) == 0

def main():
    parser = argparse.ArgumentParser(description="Nova Font Manager")
    parser.add_argument("--generate", action="store_true", help="Generate full printable character set")
    parser.add_argument("--export-python", type=str, help="Export to Python file")
    parser.add_argument("--export-json", type=str, help="Export to JSON file")
    parser.add_argument("--import-json", type=str, help="Import from JSON file")
    parser.add_argument("--char-map", action="store_true", help="Print character map")
    parser.add_argument("--validate", action="store_true", help="Validate font data")
    
    args = parser.parse_args()
    
    fm = FontManager()
    
    if args.import_json:
        fm.import_from_json(args.import_json)
        
    if args.generate:
        fm.generate_full_printable_set()
        
    if args.export_python:
        fm.export_to_python(args.export_python)
        
    if args.export_json:
        fm.export_to_json(args.export_json)
        
    if args.char_map:
        fm.print_character_map()
        
    if args.validate:
        fm.validate_font_data()
        
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main()
