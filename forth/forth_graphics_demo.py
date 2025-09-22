#!/usr/bin/env python3
"""
FORTH Graphics Demo
Demonstrates FORTH graphics programming with the Nova-16 GUI.

Run this script to see FORTH graphics in action!
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_interpreter import ForthInterpreter

def demo_graphics():
    """Demonstrate FORTH graphics programming"""
    print("🎨 FORTH Graphics Programming Demo")
    print("=" * 40)
    print("This demo will execute graphics commands.")
    print("Type 'GUI' to view the graphics in a window.")
    print("Close the GUI window to continue the demo.")
    print()

    # Create graphics program
    graphics_program = """
    : DRAW_PIXEL
      50 50 15 PIXEL
    ;

    : DRAW_LINE
      0 VMODE 0 LAYER
      10 30 12 PIXEL
      11 30 12 PIXEL
      12 30 12 PIXEL
      13 30 12 PIXEL
      14 30 12 PIXEL
    ;

    : DRAW_BOX
      0 VMODE 0 LAYER
      20 20 10 PIXEL
      30 20 10 PIXEL
      20 30 10 PIXEL
      30 30 10 PIXEL
      25 25 9 PIXEL
    ;

    : DRAW_DIAGONAL
      0 VMODE 1 LAYER
      5 5 7 PIXEL
      10 10 7 PIXEL
      15 15 7 PIXEL
      20 20 7 PIXEL
    ;

    DRAW_PIXEL
    DRAW_LINE
    DRAW_BOX
    DRAW_DIAGONAL
    """

    print("Executing graphics program...")
    print("Graphics commands available:")
    print("  PIXEL x y color - Draw pixel at coordinates")
    print("  LAYER n - Set active layer (0-7)")
    print("  VMODE n - Set video mode (0=coordinate, 1=direct)")
    print("  SWRITE color - Write pixel at current position")
    print("  GUI - Launch graphics window")
    print()

    interpreter = ForthInterpreter(gui_enabled=True)
    interpreter.interpret(graphics_program)
    
    print("\nGraphics commands executed!")
    print("Type 'GUI' to view the graphics, or 'BYE' to exit.")
    print("You can also continue drawing with more commands.")
    print()
    
    # Start interactive mode
    interpreter.repl()

def interactive_demo():
    """Interactive FORTH graphics demo"""
    print("🎮 Interactive FORTH Graphics Demo")
    print("=" * 40)
    print("Type FORTH commands to draw graphics.")
    print("Try these commands:")
    print("  100 100 15 PIXEL    - Draw a pixel")
    print("  1 LAYER             - Switch to layer 1")
    print("  0 VMODE              - Coordinate mode")
    print("  50 50 10 SWRITE      - Write at current position")
    print("  WORDS                - List all available words")
    print("  BYE                  - Exit")
    print()

    interpreter = ForthInterpreter(gui_enabled=True)
    interpreter.repl()

def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_demo()
    else:
        demo_graphics()

if __name__ == "__main__":
    main()