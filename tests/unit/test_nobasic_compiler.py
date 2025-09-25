#!/usr/bin/env python3
"""
Unit tests for NoBASIC compiler
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from nobasic_compiler import NoBasicCompiler


class TestNoBasicCompiler(unittest.TestCase):
    """Test cases for NoBASIC compiler"""

    def setUp(self):
        """Set up test fixtures"""
        self.compiler = NoBasicCompiler()

    def test_initialization(self):
        """Test compiler initialization"""
        self.assertIsInstance(self.compiler.assembly_lines, list)
        self.assertEqual(self.compiler.PROGRAM_START, 0x1000)
        self.assertEqual(self.compiler.VARIABLE_START, 0x2000)
        self.assertEqual(len(self.compiler.variables), 26)  # A-Z
        self.assertIn('A', self.compiler.variables)
        self.assertIn('Z', self.compiler.variables)

    def test_tokenize_simple(self):
        """Test basic tokenization"""
        code = 'ClrHome\nDisp "Hello"'
        tokens = self.compiler._tokenize(code)

        # Should contain the tokens we expect
        self.assertIn('ClrHome', tokens)
        self.assertIn('"Hello"', tokens)
        self.assertIn('Disp', tokens)
        self.assertEqual(tokens.count('\n'), 1)  # One newline between statements

    def test_tokenize_with_spaces(self):
        """Test tokenization with various spacing"""
        code = 'A = 5 + 3'
        tokens = self.compiler._tokenize(code)

        self.assertIn('A', tokens)
        self.assertIn('=', tokens)
        self.assertIn('5', tokens)
        self.assertIn('+', tokens)
        self.assertIn('3', tokens)

    def test_tokenize_strings(self):
        """Test string tokenization"""
        code = 'Disp "Hello World"'
        tokens = self.compiler._tokenize(code)

        self.assertIn('"Hello World"', tokens)

    def test_compile_clrhome(self):
        """Test ClrHome compilation"""
        lines = self.compiler._compile_clrhome()

        self.assertIn("    ; ClrHome - clear screen (optimized)", lines)
        self.assertIn("    MOV P0,0", lines)
        self.assertIn("    SFILL P0", lines)

    def test_compile_disp_string(self):
        """Test Disp with string compilation"""
        tokens = ['Disp', '"Hello World"', '\n']
        lines, new_i = self.compiler._compile_disp(tokens, 0)

        # Should generate TEXT instruction for longer strings
        text_lines = [line for line in lines if 'TEXT' in line]
        self.assertTrue(len(text_lines) > 0)
        
        # Should also store the string in memory
        string_lines = [line for line in lines if 'Hello World' in line and 'string' in line.lower()]
        self.assertTrue(len(string_lines) > 0)

    def test_compile_disp_short_string(self):
        """Test Disp with short string still uses CHAR instructions"""
        tokens = ['Disp', '"Hi"', '\n']
        lines, new_i = self.compiler._compile_disp(tokens, 0)

        # Should generate CHAR instructions for short strings
        char_lines = [line for line in lines if 'CHAR' in line]
        self.assertEqual(len(char_lines), 2)  # 'H' and 'i'

    def test_compile_len_function(self):
        """Test LEN() function compilation"""
        tokens = ['LEN', '(', '"Hello"', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate STRLEN instruction
        strlen_lines = [line for line in lines if 'STRLEN' in line]
        self.assertTrue(len(strlen_lines) > 0)

    def test_compile_upper_function(self):
        """Test UPPER() function compilation"""
        tokens = ['UPPER', '(', '"hello"', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate STRUPR instruction
        strupr_lines = [line for line in lines if 'STRUPR' in line]
        self.assertTrue(len(strupr_lines) > 0)

    def test_compile_left_function(self):
        """Test LEFT() function compilation"""
        tokens = ['LEFT', '(', '"Hello"', ',', '3', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate CALL to left_substr
        call_lines = [line for line in lines if 'CALL left_substr' in line]
        self.assertTrue(len(call_lines) > 0)

    def test_compile_right_function(self):
        """Test RIGHT() function compilation"""
        tokens = ['RIGHT', '(', '"Hello"', ',', '2', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate CALL to right_substr
        call_lines = [line for line in lines if 'CALL right_substr' in line]
        self.assertTrue(len(call_lines) > 0)

    def test_compile_mid_function(self):
        """Test MID() function compilation"""
        tokens = ['MID', '(', '"Hello"', ',', '1', ',', '3', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate CALL to mid_substr
        call_lines = [line for line in lines if 'CALL mid_substr' in line]
        self.assertTrue(len(call_lines) > 0)

    def test_compile_instr_function(self):
        """Test INSTR() function compilation"""
        tokens = ['INSTR', '(', '"Hello"', ',', '"ll"', ')']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should generate STREXT instruction
        strext_lines = [line for line in lines if 'STREXT' in line]
        self.assertTrue(len(strext_lines) > 0)

    def test_compile_assignment_simple(self):
        """Test simple variable assignment"""
        tokens = ['A', '=', '42', '\n']
        lines, new_i = self.compiler._compile_assignment(tokens, 0)

        self.assertIn("    ; A = ", lines)
        self.assertIn("    MOV P0,42", lines)
        # Should store directly to memory address
        store_lines = [line for line in lines if 'MOV [0x2000],P0' in line]
        self.assertTrue(len(store_lines) > 0)

    def test_variable_addresses(self):
        """Test variable address assignment"""
        # Check that variables are assigned sequential addresses
        self.assertEqual(self.compiler.variables['A'], 0x2000)
        self.assertEqual(self.compiler.variables['B'], 0x2002)
        self.assertEqual(self.compiler.variables['Z'], 0x2032)

    def test_expression_parsing_simple(self):
        """Test simple expression parsing"""
        tokens = ['5', '+', '3', '\n']
        lines, new_idx = self.compiler._parse_expression(tokens, 0)

        # Should push 5, push 3, add them
        self.assertTrue(len(lines) > 0)
        self.assertEqual(new_idx, 3)  # Should consume 3 tokens

    def test_expression_parsing_variable(self):
        """Test variable expression parsing"""
        tokens = ['A', '+', 'B', '\n']
        lines, new_idx = self.compiler._parse_expression(tokens, 0)

        # Should load A, load B, add them
        self.assertTrue(len(lines) > 0)
        self.assertEqual(new_idx, 3)

    def test_compile_to_lines_basic(self):
        """Test full compilation to assembly lines"""
        nobasic_code = 'ClrHome\nDisp "Test"'
        lines = self.compiler.compile_to_lines(nobasic_code)

        self.assertIsInstance(lines, list)
        self.assertTrue(len(lines) > 0)
        # Should contain header
        self.assertIn("; NoBASIC Program - Generated by nobasic_compiler.py", lines)

    # def test_string_storage(self):
    #     """Test string storage in memory"""
    #     test_string = "Hello World"
    #     addr = self.compiler._store_string_in_memory(test_string)

    #     self.assertIsInstance(addr, int)
    #     self.assertGreater(addr, 0)

    #     # Check that string was added to assembly
    #     string_lines = [line for line in self.compiler.assembly_lines if f'"{test_string}"' in line]
    #     self.assertTrue(len(string_lines) > 0)

    # def test_if_compilation(self):
    #     """Test If statement compilation"""
    #     lines = self.compiler._compile_if([], 0)

    #     self.assertIn("    ; IF", lines)
    #     # Should pop condition and jump if zero
    #     jz_lines = [line for line in lines if 'JZ' in line]
    #     self.assertTrue(len(jz_lines) > 0)

    # def test_then_compilation(self):
    #     """Test Then statement compilation"""
    #     # First push an IF context
    #     self.compiler.control_stack.append(("IF", "if_0"))
    #     lines = self.compiler._compile_then()

    #     self.assertIn("    ; THEN", lines)
    #     # Should have the label
    #     label_lines = [line for line in lines if 'if_0:' in line]
    #     self.assertTrue(len(label_lines) > 0)

    # def test_for_compilation(self):
    #     """Test For loop compilation"""
    #     lines = self.compiler._compile_for([], 0)

    #     self.assertIn("    ; FOR (unrecognized format)", lines)
    #     # Should have start label
    #     start_lines = [line for line in lines if '_start:' in line]
    #     self.assertTrue(len(start_lines) > 0)

    # def test_end_compilation(self):
    #     """Test End statement compilation"""
    #     # Push a FOR context
    #     self.compiler.control_stack.append(("FOR", "for_0"))
    #     lines = self.compiler._compile_end()

    #     self.assertIn("    ; END FOR", lines)
    #     # Should jump back to start
    #     jmp_lines = [line for line in lines if 'JMP' in line and '_start' in line]
    #     self.assertTrue(len(jmp_lines) > 0)

    # def test_print_number_from_stack(self):
    #     """Test printing number from stack"""
    #     lines = self.compiler._compile_print_number_from_stack()

    #     self.assertIn("    ; Print number from stack (optimized)", lines)
    #     # Should pop from stack and call print_number
    #     call_lines = [line for line in lines if 'CALL print_number' in line]
    #     self.assertTrue(len(call_lines) > 0)

    def test_compile_struct_definition(self):
        """Test STRUCT definition compilation"""
        tokens = ['STRUCT', 'PLAYER', 'X', 'Y', 'HEALTH', 'SCORE', 'END', 'STRUCT']
        lines, new_i = self.compiler._compile_struct(tokens, 0)

        # Should define struct with correct fields
        self.assertIn("    ; Struct PLAYER defined with 4 fields, total size 8 bytes", lines)
        self.assertIn("    ;   X: offset 0, size 2", lines)
        self.assertIn("    ;   Y: offset 2, size 2", lines)
        self.assertIn("    ;   HEALTH: offset 4, size 2", lines)
        self.assertIn("    ;   SCORE: offset 6, size 2", lines)

        # Check struct was stored
        self.assertIn('PLAYER', self.compiler.structs)
        struct_info = self.compiler.structs['PLAYER']
        self.assertEqual(struct_info['size'], 8)
        self.assertEqual(len(struct_info['fields']), 4)
        self.assertEqual(struct_info['fields']['X']['offset'], 0)
        self.assertEqual(struct_info['fields']['SCORE']['offset'], 6)

    def test_compile_dim_struct_instance(self):
        """Test DIM var AS struct_name compilation"""
        # First define a struct
        self.compiler._compile_struct(['STRUCT', 'POINT', 'X', 'Y', 'END', 'STRUCT'], 0)
        
        # Create instance
        tokens = ['DIM', 'MYPOINT', 'AS', 'POINT']
        lines, new_i = self.compiler._compile_dim(tokens, 0)

        # Should create struct instance
        self.assertIn("    ; Create struct instance MYPOINT of type POINT", lines)
        self.assertIn("    ; Struct size: 4 bytes", lines)

        # Check instance was stored
        self.assertIn('MYPOINT', self.compiler.struct_instances)
        instance_info = self.compiler.struct_instances['MYPOINT']
        self.assertEqual(instance_info['struct_name'], 'POINT')

    def test_compile_struct_field_access(self):
        """Test struct field access compilation"""
        # Define struct and create instance
        self.compiler._compile_struct(['STRUCT', 'VEC2', 'X', 'Y', 'END', 'STRUCT'], 0)
        self.compiler._compile_dim(['DIM', 'POS', 'AS', 'VEC2'], 0)
        
        # Test field access in expression
        tokens = ['POS', '.', 'X']
        lines, new_i = self.compiler._parse_primary_expression(tokens, 0)

        # Should load field value
        load_lines = [line for line in lines if 'Load POS.X' in line]
        self.assertTrue(len(load_lines) > 0)

    def test_compile_struct_field_assignment(self):
        """Test struct field assignment compilation"""
        # Define struct and create instance
        self.compiler._compile_struct(['STRUCT', 'VEC2', 'X', 'Y', 'END', 'STRUCT'], 0)
        self.compiler._compile_dim(['DIM', 'POS', 'AS', 'VEC2'], 0)
        
        # Test field assignment
        tokens = ['POS', '.', 'X', '=', '10']
        lines, new_i = self.compiler._compile_assignment(tokens, 0)

        # Should store to field
        store_lines = [line for line in lines if 'Store to POS.X' in line]
        self.assertTrue(len(store_lines) > 0)


if __name__ == '__main__':
    unittest.main()