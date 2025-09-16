#!/usr/bin/env python3
"""
Quick test of FORTH functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def quick_test():
    forth = ForthInterpreter()

    print("=== Quick FORTH Test ===")

    # Test basic arithmetic
    print("Testing arithmetic...")
    forth.interpret("5 3 +")
    result = forth.pop_param()
    print(f"5 + 3 = {result}")

    # Test word definition
    print("Testing word definition...")
    forth.interpret(": SQUARE DUP * ;")
    forth.interpret("7 SQUARE")
    result = forth.pop_param()
    print(f"7 SQUARE = {result}")

    # Test recursion
    print("Testing recursion...")
    forth.interpret(": FACT DUP 1 > IF DUP 1 - RECURSE * ELSE DROP 1 THEN ;")
    forth.interpret("5 FACT")
    result = forth.pop_param()
    print(f"5! = {result}")

    # Test control flow
    print("Testing control flow...")
    forth.interpret(": TEST 10 5 > IF 42 . CR ELSE 24 . CR THEN ;")
    print("Should print 42:")
    forth.interpret("TEST")

    print("=== Test Complete ===")

if __name__ == "__main__":
    quick_test()
