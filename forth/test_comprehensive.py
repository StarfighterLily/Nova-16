#!/usr/bin/env python3
"""
Comprehensive test of NOVA-16 FORTH interpreter
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_comprehensive():
    """Comprehensive test of FORTH features"""
    forth = ForthInterpreter()

    print("=== NOVA-16 FORTH Comprehensive Test ===\n")

    # Test 1: Basic arithmetic
    print("1. Basic Arithmetic:")
    forth.interpret("5 3 +")
    result = forth.pop_param()
    print(f"   5 + 3 = {result} {'✓' if result == 8 else '✗'}")

    forth.interpret("10 4 -")
    result = forth.pop_param()
    print(f"   10 - 4 = {result} {'✓' if result == 6 else '✗'}")

    forth.interpret("6 7 *")
    result = forth.pop_param()
    print(f"   6 * 7 = {result} {'✓' if result == 42 else '✗'}")

    forth.interpret("42 6 /")
    result = forth.pop_param()
    print(f"   42 / 6 = {result} {'✓' if result == 7 else '✗'}")

    forth.interpret("17 5 MOD")
    result = forth.pop_param()
    print(f"   17 MOD 5 = {result} {'✓' if result == 2 else '✗'}")

    # Test 2: Stack manipulation
    print("\n2. Stack Manipulation:")
    forth.interpret("5 DUP")
    a = forth.pop_param()
    b = forth.pop_param()
    print(f"   5 DUP: {b} {a} {'✓' if a == b == 5 else '✗'}")

    forth.interpret("1 2 3 SWAP")
    a = forth.pop_param()
    b = forth.pop_param()
    c = forth.pop_param()
    print(f"   1 2 3 SWAP: {c} {b} {a} {'✓' if (c, b, a) == (1, 3, 2) else '✗'}")

    forth.interpret("10 20 OVER")
    a = forth.pop_param()
    b = forth.pop_param()
    c = forth.pop_param()
    print(f"   10 20 OVER: {c} {b} {a} {'✓' if (c, b, a) == (10, 20, 10) else '✗'}")

    # Test 3: Comparison
    print("\n3. Comparison Operations:")
    forth.interpret("5 5 =")
    result = forth.pop_param()
    print(f"   5 = 5: {result} {'✓' if result == -1 else '✗'}")

    forth.interpret("5 3 <")
    result = forth.pop_param()
    print(f"   5 < 3: {result} {'✓' if result == 0 else '✗'}")

    forth.interpret("10 5 >")
    result = forth.pop_param()
    print(f"   10 > 5: {result} {'✓' if result == -1 else '✗'}")

    # Test 4: Logic operations
    print("\n4. Logic Operations:")
    forth.interpret("10 3 AND")
    result = forth.pop_param()
    print(f"   10 AND 3: {result} {'✓' if result == 2 else '✗'}")

    forth.interpret("10 5 OR")
    result = forth.pop_param()
    print(f"   10 OR 5: {result} {'✓' if result == 15 else '✗'}")

    forth.interpret("10 5 XOR")
    result = forth.pop_param()
    print(f"   10 XOR 5: {result} {'✓' if result == 15 else '✗'}")

    # Test 5: Math operations
    print("\n5. Math Operations:")
    forth.interpret("5 NEGATE")
    result = forth.pop_param()
    print(f"   5 NEGATE: {result} {'✓' if result == -5 else '✗'}")

    forth.interpret("10 20 MIN")
    result = forth.pop_param()
    print(f"   10 20 MIN: {result} {'✓' if result == 10 else '✗'}")

    forth.interpret("10 20 MAX")
    result = forth.pop_param()
    print(f"   10 20 MAX: {result} {'✓' if result == 20 else '✗'}")

    # Test 6: Number bases
    print("\n6. Number Bases:")
    forth.interpret("HEX")
    print(f"   Switched to HEX base")
    forth.interpret("FF")
    result = forth.pop_param()
    print(f"   FF (hex) = {result} {'✓' if result == 255 else '✗'}")

    forth.interpret("DECIMAL")
    print(f"   Switched back to DECIMAL base")
    forth.interpret("255")
    result = forth.pop_param()
    print(f"   255 (decimal) = {result} {'✓' if result == 255 else '✗'}")

    # Test 7: Hardcoded word definition
    print("\n7. Word Definition (Hardcoded):")
    def execute_square():
        val = forth.pop_param()
        forth.push_param(val * val)

    forth.define_word("SQUARE", execute_square)
    forth.interpret("5 SQUARE")
    result = forth.pop_param()
    print(f"   5 SQUARE = {result} {'✓' if result == 25 else '✗'}")

    # Test 8: I/O operations
    print("\n8. I/O Operations:")
    print("   Should print: 42")
    print("   ", end="")
    forth.interpret("42 .")
    print()

    print("   Should print: ABC")
    print("   ", end="")
    forth.interpret('65 EMIT 66 EMIT 67 EMIT')
    print()

    # Test 9: Words listing
    print("\n9. Dictionary:")
    print("   Defined words:")
    if hasattr(forth, 'word_dict'):
        words = [w for w in sorted(forth.word_dict.keys()) if not w.startswith('word_')]
        print(f"   {len(words)} words defined")
        print(f"   Sample: {words[:10]}...")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_comprehensive()
