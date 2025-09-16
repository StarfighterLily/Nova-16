#!/usr/bin/env python3
"""
Simple test for FORTH word definition
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_simple_definition():
    """Test simple word definition"""
    forth = ForthInterpreter()

    print("Testing simple word definition...")

    # First test direct number
    print("Testing direct number...")
    forth.interpret("42")
    result = forth.pop_param()
    print(f"Direct 42 = {result}")

    # Define a word that just pushes 42
    print("Defining FORTY_TWO...")
    forth.interpret(": FORTY_TWO 42 ;")
    print("Defined FORTY_TWO")

    # Check if the word is in the dictionary
    if hasattr(forth, 'word_dict') and 'FORTY_TWO' in forth.word_dict:
        print("FORTY_TWO is in dictionary")
    else:
        print("FORTY_TWO is NOT in dictionary")

    # Test it
    print("Calling FORTY_TWO...")
    if 'FORTY_TWO' in forth.word_dict:
        print("Manually calling FORTY_TWO...")
        forth.word_dict['FORTY_TWO']()
        result = forth.pop_param()
        print(f"Manual call result: {result}")
    else:
        print("FORTY_TWO not found in word_dict")

    # Also try through interpret
    forth.interpret("FORTY_TWO")
    result = forth.pop_param()
    print(f"Interpret call result: {result} (should be 42)")

if __name__ == "__main__":
    test_simple_definition()
