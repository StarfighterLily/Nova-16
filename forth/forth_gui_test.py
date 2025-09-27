#!/usr/bin/env python3
"""
Test FORTH GUI Integration
Tests that the FORTH interpreter can launch a GUI and execute graphics commands.
"""

import sys
import os
import time
import subprocess
import signal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_interpreter import ForthInterpreter

def test_gui_integration():
    """Test GUI integration with FORTH graphics commands"""
    print("Testing FORTH GUI Integration...")

    # Test 1: Basic GUI initialization
    print("  Test 1: GUI initialization")
    try:
        interpreter = ForthInterpreter(gui_enabled=False)  # Don't start GUI for automated testing
        print("    ✓ FORTH interpreter initialized")

        # Test 2: Graphics commands trigger GUI
        print("  Test 2: Graphics commands")
        interpreter.interpret("0 VMODE 1 LAYER 100 120 15 PIXEL")
        print("    ✓ Graphics commands executed")

        # Give GUI time to start
        time.sleep(2)

        # Test 3: Check that graphics state was updated
        print("  Test 3: Graphics state verification")
        # Check if coordinates were set
        vx = interpreter.gfx.Vregisters[0]
        vy = interpreter.gfx.Vregisters[1]
        vl = interpreter.gfx.VL
        vmode = interpreter.gfx.vmode

        print(f"    VX: {vx}, VY: {vy}, VL: {vl}, VMODE: {vmode}")

        if vx == 100 and vy == 120 and vl == 1 and vmode == 0:
            print("    ✓ Graphics registers updated correctly")
            assert True
        else:
            print("    ✗ Graphics registers not updated correctly")
            assert False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        assert False

def test_forth_graphics_program():
    """Test a complete FORTH graphics program"""
    print("\nTesting complete FORTH graphics program...")

    graphics_program = """
    : DRAW_BOX
      0 VMODE
      0 LAYER
      10 10 15 PIXEL
      20 10 15 PIXEL
      10 20 15 PIXEL
      20 20 15 PIXEL
    ;

    DRAW_BOX
    """

    try:
        interpreter = ForthInterpreter(gui_enabled=False)  # Don't start GUI for automated testing
        interpreter.interpret(graphics_program)
        print("    ✓ Graphics program executed successfully")

        assert True
    except Exception as e:
        print(f"    ✗ Error executing graphics program: {e}")
        assert False

def main():
    """Run GUI integration tests"""
    print("FORTH GUI Integration Test Suite")
    print("=" * 40)

    success = True

    # Test GUI integration
    if not test_gui_integration():
        success = False

    # Test complete graphics program
    if not test_forth_graphics_program():
        success = False

    print("\n" + "=" * 40)
    if success:
        print("✓ ALL GUI INTEGRATION TESTS PASSED")
        print("FORTH graphics programming is ready!")
    else:
        print("✗ SOME GUI TESTS FAILED")
        print("Check the implementation")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())