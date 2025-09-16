#!/usr/bin/env python3
"""
Simple test for FORTH word definition - hardcoded
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_hardcoded_definition():
    """Test with hardcoded word definition"""
    forth = ForthInterpreter()

    print("Testing hardcoded word definition...")

    # Manually define a word
    def execute_forty_two():
        print("DEBUG: execute_forty_two called!")
        forth.push_param(42)
        print("DEBUG: Pushed 42")

    forth.define_word("FORTY_TWO", execute_forty_two)

    # Test it
    print("Calling FORTY_TWO...")
    forth.interpret("FORTY_TWO")
    result = forth.pop_param()
    print(f"FORTY_TWO = {result} (should be 42)")

if __name__ == "__main__":
    test_hardcoded_definition()
