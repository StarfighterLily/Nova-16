#!/usr/bin/env python3
"""
Test script for NOVA-16 FORTH interpreter
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_basic_operations():
    """Test basic FORTH operations"""
    forth = ForthInterpreter()

    print("Testing basic operations...")

    # Test numbers
    forth.interpret("5 3")
    print(f"Stack after '5 3': {forth.pop_param()} {forth.pop_param()}")

    # Test DUP
    forth.interpret("5 DUP")
    a = forth.pop_param()
    b = forth.pop_param()
    print(f"Stack after '5 DUP': {a} {b} (should be 5 5)")

    # Test arithmetic
    forth.interpret("10 3 +")
    result = forth.pop_param()
    print(f"10 + 3 = {result}")

    # Test stack manipulation
    forth.interpret("1 2 3 SWAP")
    a = forth.pop_param()
    b = forth.pop_param()
    c = forth.pop_param()
    print(f"Stack after '1 2 3 SWAP': {a} {b} {c} (should be 1 3 2)")

    # Test new words
    forth.interpret("10 5 MIN")
    result = forth.pop_param()
    print(f"MIN(10, 5) = {result}")

    forth.interpret("10 5 MAX")
    result = forth.pop_param()
    print(f"MAX(10, 5) = {result}")

    forth.interpret("5 NEGATE")
    result = forth.pop_param()
    print(f"NEGATE(5) = {result}")

    forth.interpret("10 3 AND")
    result = forth.pop_param()
    print(f"10 AND 3 = {result}")

def test_word_definition():
    """Test word definition"""
    forth = ForthInterpreter()

    print("\nTesting word definition...")

    # Define a simple word
    forth.interpret(": SQUARE DUP * ;")
    print("Defined SQUARE word")

    # Test the defined word
    forth.interpret("5 SQUARE")
    result = forth.pop_param()
    print(f"5 SQUARE = {result} (should be 25)")

    # Define a more complex word
    forth.interpret(": DOUBLE 2 * ;")
    forth.interpret("10 DOUBLE")
    result = forth.pop_param()
    print(f"10 DOUBLE = {result} (should be 20)")

def test_output():
    """Test output words"""
    forth = ForthInterpreter()

    print("\nTesting output...")
    print("Should print: 42")
    forth.interpret("42 . CR")

    print("Should print: HELLO")
    forth.interpret('72 EMIT 69 EMIT 76 EMIT 76 EMIT 79 EMIT CR')

if __name__ == "__main__":
    test_basic_operations()
    test_word_definition()
    test_output()
