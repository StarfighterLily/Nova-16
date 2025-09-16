#!/usr/bin/env python3
"""
Aggressive bug-finding test suite for NOVA-16 FORTH interpreter
Tests edge cases, error conditions, and stress scenarios
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_stack_underflow_overflow():
    """Test stack underflow and overflow conditions"""
    print("=== Testing Stack Underflow/Overflow ===")
    forth = ForthInterpreter()

    bugs = []

    # Test stack underflow on DROP
    initial_sp = forth.cpu.Pregisters[8]
    forth.interpret("DROP")
    if forth.cpu.Pregisters[8] != initial_sp:  # SP should not move on underflow
        bugs.append("DROP on empty stack doesn't prevent underflow")

    # Test stack underflow on arithmetic
    forth.interpret("+")
    # Should not crash, but result is undefined

    # Test deep stack
    forth = ForthInterpreter()
    for i in range(100):  # Fill stack
        forth.interpret(str(i))

    # Check if all values are preserved
    values = []
    for i in range(100):
        try:
            values.append(forth.pop_param())
        except:
            bugs.append(f"Stack overflow at depth {i}")
            break

    if len(values) < 100:
        bugs.append(f"Stack only held {len(values)} values, expected 100")

    return bugs

def test_number_parsing():
    """Test number parsing edge cases"""
    print("=== Testing Number Parsing ===")
    forth = ForthInterpreter()

    bugs = []

    # Test decimal
    forth.interpret("123")
    if forth.pop_param() != 123:
        bugs.append("Decimal parsing failed")

    # Test hex
    forth.interpret("HEX FF")
    if forth.pop_param() != 255:
        bugs.append("Hex parsing failed")

    # Test binary (if supported)
    try:
        forth.interpret("DECIMAL 2 BASE ! 101")  # This might not work
        result = forth.pop_param()
        if result != 5:  # 101 binary = 5 decimal
            bugs.append(f"Binary parsing failed: got {result}")
    except:
        pass  # Binary might not be supported

    # Test negative numbers
    forth.interpret("DECIMAL -42")
    if forth.pop_param() != -42:
        bugs.append("Negative number parsing failed")

    # Test large numbers (should wrap)
    forth.interpret("70000")  # Larger than 16-bit
    result = forth.pop_param()
    if result != 70000 & 0xFFFF:  # Should be masked
        bugs.append(f"Large number not wrapped: got {result}")

    return bugs

def test_word_definition_edge_cases():
    """Test word definition edge cases"""
    print("=== Testing Word Definition Edge Cases ===")
    forth = ForthInterpreter()

    bugs = []

    # Test empty definition
    forth.interpret(": EMPTY ;")
    forth.interpret("EMPTY")  # Should do nothing

    # Test recursive definition
    forth.interpret(": RECURSE-TEST DUP 0 > IF 1 - RECURSE-TEST THEN ;")
    forth.interpret("5 RECURSE-TEST")
    # Should not crash

    # Test very long word name
    long_name = "VERY_LONG_WORD_NAME_THAT_MIGHT_CAUSE_ISSUES"
    forth.interpret(f": {long_name} 42 ;")
    forth.interpret(long_name)
    if forth.pop_param() != 42:
        bugs.append("Long word name failed")

    # Test word redefinition
    forth.interpret(": TEST 1 ;")
    forth.interpret(": TEST 2 ;")  # Redefine
    forth.interpret("TEST")
    if forth.pop_param() != 2:
        bugs.append("Word redefinition failed")

    return bugs

def test_control_flow_edge_cases():
    """Test control flow edge cases"""
    print("=== Testing Control Flow Edge Cases ===")
    forth = ForthInterpreter()

    bugs = []

    # Test nested IF without ELSE
    forth.interpret(": NESTED-IF 1 IF 2 IF 42 . THEN THEN ;")
    # Should work

    # Test BEGIN/UNTIL with false condition
    forth.interpret(": INFINITE 0 BEGIN 1 . UNTIL ;")
    # This would infinite loop if broken, so don't execute it

    # Test DO/LOOP with zero iterations
    forth.interpret(": ZERO-LOOP 5 5 DO I . LOOP ;")
    forth.interpret("ZERO-LOOP")
    # Should not print anything

    # Test DO/LOOP with negative limits
    forth.interpret(": NEG-LOOP -2 2 DO I . LOOP ;")
    forth.interpret("NEG-LOOP")
    # Should print -2 -1 0 1

    return bugs

def test_arithmetic_edge_cases():
    """Test arithmetic edge cases"""
    print("=== Testing Arithmetic Edge Cases ===")
    forth = ForthInterpreter()

    bugs = []

    # Test division by zero
    try:
        forth.interpret("10 0 /")
        result = forth.pop_param()
        bugs.append(f"Division by zero should raise exception, got {result}")
    except:
        pass  # This is correct

    # Test multiplication overflow
    forth.interpret("300 200 *")  # 60000, should wrap to -5536 in signed 16-bit
    result = forth.pop_param()
    if result != -5536:
        bugs.append(f"Multiplication overflow not handled: got {result}")

    # Test subtraction underflow
    forth.interpret("0 1 -")  # Should be -1
    if forth.pop_param() != -1:
        bugs.append("Subtraction underflow failed")

    return bugs

def test_memory_edge_cases():
    """Test memory access edge cases"""
    print("=== Testing Memory Edge Cases ===")
    forth = ForthInterpreter()

    bugs = []

    # Test access to system memory areas
    forth.interpret("0 @")  # Read from address 0
    # Should not crash

    forth.interpret("42 0 !")  # Write to address 0
    forth.interpret("0 @")
    if forth.pop_param() != 42:
        bugs.append("Memory write/read failed")

    # Test access beyond memory bounds
    try:
        forth.interpret("65535 @")  # Last valid address
        # Should not crash
    except:
        bugs.append("Access to valid memory address crashed")

    return bugs

def test_string_handling():
    """Test string and character handling"""
    print("=== Testing String/Character Handling ===")
    forth = ForthInterpreter()

    bugs = []

    # Test character literals (if supported)
    # FORTH typically uses 'A' for character literals

    # Test EMIT with various values
    forth.interpret("65 EMIT")  # Should print 'A'
    forth.interpret("10 EMIT")  # Should print newline

    # Test large EMIT values
    forth.interpret("256 EMIT")  # Should wrap to 0
    forth.interpret("257 EMIT")  # Should wrap to 1

    return bugs

def test_performance_stress():
    """Test performance and stress scenarios"""
    print("=== Testing Performance/Stress ===")
    forth = ForthInterpreter()

    bugs = []

    # Test many word definitions
    for i in range(100):
        forth.interpret(f": WORD{i} {i} ;")

    # Test calling many words
    forth.interpret("WORD50")
    if forth.pop_param() != 50:
        bugs.append("Many word definitions failed")

    # Test deep recursion (if supported)
    forth.interpret(": DEEP DUP 1 > IF 1 - DEEP THEN ;")
    forth.interpret("10 DEEP")
    # Should not crash with stack overflow

    return bugs

def test_error_recovery():
    """Test error recovery"""
    print("=== Testing Error Recovery ===")
    forth = ForthInterpreter()

    bugs = []

    # Test invalid word
    forth.interpret("INVALID_WORD")
    # Should print error but not crash

    # Test incomplete definition
    forth.interpret(": INCOMPLETE")
    # Should handle gracefully

    # Test mismatched control flow
    forth.interpret(": BROKEN IF 42 THEN ELSE ;")
    # Should detect mismatch

    return bugs

def run_aggressive_tests():
    """Run all aggressive tests"""
    print("NOVA-16 FORTH Aggressive Bug Test Suite")
    print("=" * 50)

    all_bugs = []

    all_bugs.extend(test_stack_underflow_overflow())
    all_bugs.extend(test_number_parsing())
    all_bugs.extend(test_word_definition_edge_cases())
    all_bugs.extend(test_control_flow_edge_cases())
    all_bugs.extend(test_arithmetic_edge_cases())
    all_bugs.extend(test_memory_edge_cases())
    all_bugs.extend(test_string_handling())
    all_bugs.extend(test_performance_stress())
    all_bugs.extend(test_error_recovery())

    print("\n" + "=" * 50)
    print("AGGRESSIVE BUG REPORT:")
    print("=" * 50)

    if not all_bugs:
        print("✓ No bugs found in aggressive testing!")
    else:
        print(f"✗ Found {len(all_bugs)} bugs in aggressive testing:")
        for i, bug in enumerate(all_bugs, 1):
            print(f"{i}. {bug}")

    return all_bugs

if __name__ == "__main__":
    run_aggressive_tests()
