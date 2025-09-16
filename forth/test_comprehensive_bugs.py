#!/usr/bin/env python3
"""
Comprehensive bug-finding test suite for NOVA-16 FORTH interpreter
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_stack_operations():
    """Test stack operations thoroughly"""
    print("=== Testing Stack Operations ===")
    forth = ForthInterpreter()

    bugs = []

    # Test 1: Basic stack order
    forth.interpret("1 2 3 4")
    vals = [forth.pop_param() for _ in range(4)]
    if vals != [4, 3, 2, 1]:
        bugs.append(f"Stack order wrong: got {vals}, expected [4, 3, 2, 1]")

    # Test 2: DUP
    forth.interpret("42 DUP")
    a, b = forth.pop_param(), forth.pop_param()
    if a != 42 or b != 42:
        bugs.append(f"DUP failed: got {a}, {b}, expected 42, 42")

    # Test 3: DROP
    forth.interpret("1 2 3 DROP")
    vals = [forth.pop_param() for _ in range(2)]
    if vals != [2, 1]:
        bugs.append(f"DROP failed: got {vals}, expected [2, 1]")

    # Test 4: SWAP
    forth.interpret("1 2 SWAP")
    a, b = forth.pop_param(), forth.pop_param()
    if a != 1 or b != 2:
        bugs.append(f"SWAP failed: got {a}, {b}, expected 1, 2")

    # Test 5: OVER
    forth.interpret("10 20 OVER")
    a, b, c = forth.pop_param(), forth.pop_param(), forth.pop_param()
    if a != 10 or b != 20 or c != 10:
        bugs.append(f"OVER failed: got {a}, {b}, {c}, expected 10, 20, 10")

    # Test 6: ROT
    forth.interpret("1 2 3 ROT")
    a, b, c = forth.pop_param(), forth.pop_param(), forth.pop_param()
    if a != 1 or b != 3 or c != 2:
        bugs.append(f"ROT failed: got {a}, {b}, {c}, expected 1, 3, 2")

    return bugs

def test_arithmetic():
    """Test arithmetic operations"""
    print("=== Testing Arithmetic ===")
    forth = ForthInterpreter()

    bugs = []

    # Test addition
    forth.interpret("10 5 +")
    if forth.pop_param() != 15:
        bugs.append("Addition failed")

    # Test subtraction
    forth.interpret("10 5 -")
    if forth.pop_param() != 5:
        bugs.append("Subtraction failed")

    # Test multiplication
    forth.interpret("10 5 *")
    if forth.pop_param() != 50:
        bugs.append("Multiplication failed")

    # Test division
    forth.interpret("10 5 /")
    if forth.pop_param() != 2:
        bugs.append("Division failed")

    # Test modulo
    forth.interpret("17 5 MOD")
    if forth.pop_param() != 2:
        bugs.append("Modulo failed")

    # Test negative numbers
    forth.interpret("-5 3 +")
    if forth.pop_param() != -2:
        bugs.append("Negative addition failed")

    return bugs

def test_comparison():
    """Test comparison operations"""
    print("=== Testing Comparison ===")
    forth = ForthInterpreter()

    bugs = []

    # Test equality
    forth.interpret("5 5 =")
    if forth.pop_param() != -1:
        bugs.append("Equality true failed")

    forth.interpret("5 6 =")
    if forth.pop_param() != 0:
        bugs.append("Equality false failed")

    # Test less than
    forth.interpret("5 10 <")
    if forth.pop_param() != -1:
        bugs.append("Less than true failed")

    forth.interpret("10 5 <")
    if forth.pop_param() != 0:
        bugs.append("Less than false failed")

    # Test greater than
    forth.interpret("10 5 >")
    if forth.pop_param() != -1:
        bugs.append("Greater than true failed")

    forth.interpret("5 10 >")
    if forth.pop_param() != 0:
        bugs.append("Greater than false failed")

    return bugs

def test_logic():
    """Test logic operations"""
    print("=== Testing Logic ===")
    forth = ForthInterpreter()

    bugs = []

    # Test AND
    forth.interpret("10 3 AND")
    if forth.pop_param() != 2:
        bugs.append("AND failed")

    # Test OR
    forth.interpret("10 5 OR")
    if forth.pop_param() != 15:
        bugs.append("OR failed")

    # Test XOR
    forth.interpret("10 5 XOR")
    if forth.pop_param() != 15:
        bugs.append("XOR failed")

    # Test INVERT
    forth.interpret("5 INVERT")
    result = forth.pop_param()
    if result != -6:  # Two's complement of 5 inverted
        bugs.append(f"INVERT failed: got {result}, expected -6")

    return bugs

def test_word_definition():
    """Test word definition and execution"""
    print("=== Testing Word Definition ===")
    forth = ForthInterpreter()

    bugs = []

    # Test simple word
    forth.interpret(": DOUBLE 2 * ;")
    forth.interpret("21 DOUBLE")
    if forth.pop_param() != 42:
        bugs.append("Simple word definition failed")

    # Test word with multiple operations
    forth.interpret(": TEST 5 + 10 * ;")
    forth.interpret("2 TEST")
    if forth.pop_param() != 70:  # (2+5)*10 = 70
        bugs.append("Complex word definition failed")

    return bugs

def test_control_flow():
    """Test control flow structures"""
    print("=== Testing Control Flow ===")
    forth = ForthInterpreter()

    bugs = []

    # Test IF/THEN
    forth.interpret(": TEST1 1 IF 42 ELSE 24 THEN ;")
    forth.interpret("TEST1")
    if forth.pop_param() != 42:
        bugs.append("IF/THEN true failed")

    forth.interpret(": TEST2 0 IF 42 ELSE 24 THEN ;")
    forth.interpret("TEST2")
    if forth.pop_param() != 24:
        bugs.append("IF/THEN false failed")

    # Test BEGIN/UNTIL
    forth.interpret(": COUNT 0 BEGIN 1 + DUP 5 = UNTIL ;")
    forth.interpret("COUNT")
    if forth.pop_param() != 5:
        bugs.append("BEGIN/UNTIL failed")

    # Test DO/LOOP
    forth.interpret(": SUM 0 SWAP 0 DO I + LOOP ;")
    forth.interpret("3 SUM")  # Sum 0+1+2 = 3
    if forth.pop_param() != 3:
        bugs.append("DO/LOOP failed")

    return bugs

def test_recursion():
    """Test recursive functions"""
    print("=== Testing Recursion ===")
    forth = ForthInterpreter()

    bugs = []

    # Test factorial with RECURSE
    forth.interpret(": FACT DUP 1 > IF DUP 1 - RECURSE * ELSE DROP 1 THEN ;")
    forth.interpret("5 FACT")
    if forth.pop_param() != 120:
        bugs.append("RECURSE factorial failed")

    # Test manual recursion (this should fail in current implementation)
    try:
        forth.interpret(": FACT2 DUP 1 = IF DROP 1 ELSE DUP 1 - FACT2 * THEN ;")
        forth.interpret("5 FACT2")
        result = forth.pop_param()
        if result != 120:
            bugs.append(f"Manual recursion failed: got {result}, expected 120")
    except:
        bugs.append("Manual recursion caused exception")

    return bugs

def test_memory():
    """Test memory operations"""
    print("=== Testing Memory ===")
    forth = ForthInterpreter()

    bugs = []

    # Test store and fetch
    forth.interpret("DECIMAL 42 HEX 1000 !")  # Store decimal 42 at hex address 0x1000
    forth.interpret("1000 @")         # Fetch from address 0x1000
    if forth.pop_param() != 42:
        bugs.append("Memory store/fetch failed")

    return bugs

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("=== Testing Edge Cases ===")
    forth = ForthInterpreter()

    bugs = []

    # Test stack underflow (should handle gracefully)
    try:
        forth.interpret("DROP")
        bugs.append("DROP on empty stack should cause error")
    except:
        pass  # This is expected

    # Test division by zero
    try:
        forth.interpret("10 0 /")
        result = forth.pop_param()
        if result != 0:  # Python integer division by zero raises exception
            bugs.append("Division by zero not handled")
    except:
        pass  # This is expected

    # Test very large numbers
    forth.interpret("32767 1 +")  # Max 16-bit signed + 1
    result = forth.pop_param()
    if result != -32768:  # Should wrap to negative
        bugs.append(f"16-bit overflow not handled: got {result}")

    return bugs

def run_all_tests():
    """Run all test suites"""
    print("NOVA-16 FORTH Comprehensive Bug Test Suite")
    print("=" * 50)

    all_bugs = []

    all_bugs.extend(test_stack_operations())
    all_bugs.extend(test_arithmetic())
    all_bugs.extend(test_comparison())
    all_bugs.extend(test_logic())
    all_bugs.extend(test_word_definition())
    all_bugs.extend(test_control_flow())
    all_bugs.extend(test_recursion())
    all_bugs.extend(test_memory())
    all_bugs.extend(test_edge_cases())

    print("\n" + "=" * 50)
    print("BUG REPORT:")
    print("=" * 50)

    if not all_bugs:
        print("✓ No bugs found! All tests passed.")
    else:
        print(f"✗ Found {len(all_bugs)} bugs:")
        for i, bug in enumerate(all_bugs, 1):
            print(f"{i}. {bug}")

    return all_bugs

if __name__ == "__main__":
    run_all_tests()
