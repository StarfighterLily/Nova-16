#!/usr/bin/env python3
"""
Test control flow implementation     # T    # Test 6: Factorial using DO/LOOP
    print("6. Factorial with DO/LOOP:")
    forth.interpret(": FACT 1 SWAP 1 + 1 DO I * LOOP ;")
    print("   Defined FACT")
    print("   5! should be 120")
    forth.interpret("5 FACT")
    result = forth.pop_param()
    print(f"   5 FACT = {result} {'✓' if result == 120 else '✗'}")actorial using DO/LOOP
    print("6. Factorial with DO/LOOP:")
    forth.interpret(": FACT 1 SWAP 1 + 1 DO I * LOOP ;")
    print("   Defined FACT")
    print("   5! should be 120")
    forth.interpret("5 FACT")
    result = forth.pop_param()
    print(f"   5 FACT = {result} {'✓' if result == 120 else '✗'}")-16 FORTH interpreter
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_control_flow():
    """Test control flow structures"""
    forth = ForthInterpreter()

    print("=== Testing Control Flow ===\n")

    # Test 1: Simple IF/THEN
    print("1. Simple IF/THEN:")
    forth.interpret(": TEST1 5 0 > IF 42 . THEN ;")
    print("   Defined TEST1")
    print("   Should print: 42")
    print("   ", end="")
    forth.interpret("TEST1")
    print()

    # Test 2: IF/ELSE/THEN
    print("2. IF/ELSE/THEN:")
    forth.interpret(": TEST2 3 5 > IF 100 . ELSE 200 . THEN ;")
    print("   Defined TEST2")
    print("   Should print: 200")
    print("   ", end="")
    forth.interpret("TEST2")
    print()

    # Test 3: Nested IF
    print("3. Nested IF:")
    forth.interpret(": TEST3 10 5 > IF 15 10 > IF 300 . THEN THEN ;")
    print("   Defined TEST3")
    print("   Should print: 300")
    print("   ", end="")
    forth.interpret("TEST3")
    print()

    # Test 4: BEGIN/UNTIL loop
    print("4. BEGIN/UNTIL loop:")
    forth.interpret(": TEST4 0 BEGIN DUP . 1 + DUP 5 > UNTIL DROP ;")
    print("   Defined TEST4")
    print("   Should print: 0 1 2 3 4 5")
    print("   ", end="")
    forth.interpret("TEST4")
    print()

    # Test 5: DO/LOOP
    print("5. DO/LOOP:")
    forth.interpret(": TEST5 3 0 DO I . LOOP ;")
    print("   Defined TEST5")
    print("   Should print: 0 1 2")
    print("   ", end="")
    forth.interpret("TEST5")
    print()

    # Test 6: Factorial using DO/LOOP
    print("6. Factorial with DO/LOOP:")
    forth.interpret(": FACT DUP 1 = IF DROP 1 ELSE DUP 1 - RECURSE * THEN ;")
    print("   Defined recursive FACT")
    print("   5! should be 120")
    forth.interpret("5 FACT")
    result = forth.pop_param()
    print(f"   5 FACT = {result} {'✓' if result == 120 else '✗'}")

    print("\n=== Control Flow Test Complete ===")

if __name__ == "__main__":
    test_control_flow()
