#!/usr/bin/env python3
"""
NoBASIC Compiler for Nova-16

Compiles NoBASIC source code to Nova-16 assembly language.

This compiler translates NoBASIC programs (inspired by TI-83/84 calculators)
into optimized Nova-16 assembly code for native execution.
"""

import sys
import os
import re
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound


class NoBasicCompiler:
    """
    Compiles NoBASIC source code to Nova-16 assembly.
    """

    def __init__(self):
        # Initialize Nova-16 components for reference
        self.memory = Memory(0x10000)
        self.gfx = GFX()
        self.keyboard = NovaKeyboard()
        self.sound = NovaSound()
        self.sound.set_memory_reference(self.memory)
        self.cpu = CPU(self.memory, self.gfx, self.keyboard, self.sound)

        # Memory layout for compiled NoBASIC
        self.PROGRAM_START = 0x1000
        self.VARIABLE_START = 0x2000  # Variables A-Z
        self.LIST_START = 0x3000     # Lists L1-L6 (each 100 elements × 2 bytes)
        self.STRING_START = 0x4000   # Strings Str1-Str9
        self.MATRIX_START = 0x5000   # Matrices [A]-[J]
        self.TEMP_START = 0x6000     # Temporary storage
        self.STACK_START = 0xF000    # Parameter stack (grows downward)

        # List management
        self.lists: Dict[str, int] = {}  # List name -> memory address
        self.list_sizes: Dict[str, int] = {}  # List name -> size

        # Compilation state
        self.assembly_lines: List[str] = []
        self.variables: Dict[str, int] = {}  # Variable name -> memory address
        self.labels: Dict[str, str] = {}     # Label name -> assembly label
        self.label_counter = 0
        self.string_counter = 0
        self.strings: Dict[str, int] = {}    # String content -> memory address

        # Loop tracking for For/Next
        self.loop_start_labels: Dict[str, str] = {}  # Variable name -> loop start label
        self.loop_end_values: Dict[str, int] = {}    # Variable name -> end value
        
        # Register allocation for expression evaluation - improved system
        self.available_registers = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
        self.register_usage: Dict[str, int] = {}  # Track when registers were last used
        self.register_stack: List[str] = []
        self.next_usage_id = 0
        
        # Text cursor position for display statements
        self.cursor_x = 0
        self.cursor_y = 0

        # Color constants mapping - Nova-16 has 16 ramps × 16 shades = 256 colors
        # Each ramp has 16 shades from darkest (0) to brightest (15)
        self.color_constants = {
            # Grayscale ramp (0x00-0x0F)
            'BLACK': 0x00,      # Darkest gray
            'DARKGRAY': 0x04,
            'GRAY': 0x08,
            'LIGHTGRAY': 0x0C,
            'WHITE': 0x0F,      # Brightest gray
            
            # Red ramp (0x10-0x1F)
            'DARKRED': 0x10,
            'RED': 0x14,
            'BRIGHTRED': 0x18,
            'LIGHTRED': 0x1C,
            
            # Green ramp (0x20-0x2F)
            'DARKGREEN': 0x20,
            'GREEN': 0x24,
            'BRIGHTGREEN': 0x28,
            'LIGHTGREEN': 0x2C,
            
            # Blue ramp (0x30-0x3F)
            'DARKBLUE': 0x30,
            'BLUE': 0x34,
            'BRIGHTBLUE': 0x38,
            'LIGHTBLUE': 0x3C,
            
            # Yellow ramp (0x40-0x4F)
            'DARKYELLOW': 0x40,
            'YELLOW': 0x44,
            'BRIGHTYELLOW': 0x48,
            'LIGHTYELLOW': 0x4C,
            
            # Magenta ramp (0x50-0x5F)
            'DARKMAGENTA': 0x50,
            'MAGENTA': 0x54,
            'BRIGHTMAGENTA': 0x58,
            'LIGHTMAGENTA': 0x5C,
            
            # Cyan ramp (0x60-0x6F)
            'DARKCYAN': 0x60,
            'CYAN': 0x64,
            'BRIGHTCYAN': 0x68,
            'LIGHTCYAN': 0x6C,
            
            # Orange ramp (0x70-0x7F)
            'DARKORANGE': 0x70,
            'ORANGE': 0x74,
            'BRIGHTORANGE': 0x78,
            'LIGHTORANGE': 0x7C,
            
            # Purple ramp (0x80-0x8F)
            'DARKPURPLE': 0x80,
            'PURPLE': 0x84,
            'BRIGHTPURPLE': 0x88,
            'LIGHTPURPLE': 0x8C,
            
            # Lime ramp (0x90-0x9F)
            'DARKLIME': 0x90,
            'LIME': 0x94,
            'BRIGHTLIME': 0x98,
            'LIGHTLIME': 0x9C,
            
            # Pink ramp (0xA0-0xAF)
            'DARKPINK': 0xA0,
            'PINK': 0xA4,
            'BRIGHTPINK': 0xA8,
            'LIGHTPINK': 0xAC,
            
            # Teal ramp (0xB0-0xBF)
            'DARKTEAL': 0xB0,
            'TEAL': 0xB4,
            'BRIGHTTEAL': 0xB8,
            'LIGHTTEAL': 0xBC,
            
            # Brown ramp (0xC0-0xCF)
            'DARKBROWN': 0xC0,
            'BROWN': 0xC4,
            'BRIGHTBROWN': 0xC8,
            'LIGHTBROWN': 0xCC,
            
            # Light blue ramp (0xD0-0xDF)
            'DARKLIGHTBLUE': 0xD0,
            'LIGHTBLUE': 0xD4,
            'BRIGHTLIGHTBLUE': 0xD8,
            'VERYLIGHTBLUE': 0xDC,
            
            # Light green ramp (0xE0-0xEF)
            'DARKLIGHTGREEN': 0xE0,
            'LIGHTGREEN': 0xE4,
            'BRIGHTLIGHTGREEN': 0xE8,
            'VERYLIGHTGREEN': 0xEC,
            
            # Light red ramp (0xF0-0xFF)
            'DARKLIGHTRED': 0xF0,
            'LIGHTRED': 0xF4,
            'BRIGHTLIGHTRED': 0xF8,
            'VERYLIGHTRED': 0xFC,
        }

        # Initialize standard header
        self._init_assembly()

    def _init_assembly(self):
        """Initialize the assembly output with standard header"""
        self.assembly_lines = [
            "; NoBASIC Program - Generated by nobasic_compiler.py",
            "; Generated automatically - do not edit",
            "",
            "ORG 0x1000",
            "",
            "; Initialize stack pointer",
            "MOV P8,0xF000",
            "",
            "; Initialize text cursor position",
            "MOV VX,0",      # X position
            "MOV VY,0",      # Y position
            "MOV VL,0",      # Layer 0
            "",
            "; Program start",
            "start:",
        ]

    def _parse_tokens_for_expression(self, tokens: List[str]) -> Tuple[List[str], int]:
        """Parse a subset of tokens as an expression (helper for list indexing)"""
        # Simple implementation - just parse additive expression
        return self._parse_additive_expression(tokens, 0)

    def _allocate_register(self) -> str:
        """Allocate a register for expression evaluation using LRU strategy"""
        if self.available_registers:
            # Use first available register
            reg = self.available_registers.pop(0)
            self.register_stack.append(reg)
            self.register_usage[reg] = self.next_usage_id
            self.next_usage_id += 1
            return reg
        
        # No free registers, find least recently used
        if self.register_stack:
            # Find register with oldest usage
            lru_reg = min(self.register_stack, key=lambda r: self.register_usage.get(r, 0))
            return lru_reg
        
        # Ultimate fallback
        return "P0"

    def _free_register(self, reg: str):
        """Free a register back to the pool"""
        if reg in self.register_stack:
            self.register_stack.remove(reg)
            if reg not in self.available_registers:
                self.available_registers.insert(0, reg)
            # Keep usage info for LRU decisions

    def _get_current_register(self) -> str:
        """Get the current result register"""
        return self.register_stack[-1] if self.register_stack else "P0"

    def _generate_label(self, prefix: str = "label") -> str:
        """Generate a unique label"""
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _tokenize(self, source: str) -> List[str]:
        """Tokenize NoBASIC source code"""
        # Split on whitespace and special characters, preserving newlines
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|:=|<=|>=|<>|[0-9]+(?:\.[0-9]+)?|"[^"]*"|\n|\S', source)

        # Filter out empty tokens
        filtered_tokens = []
        for token in tokens:
            if token:  # Keep all non-empty tokens including \n
                filtered_tokens.append(token)

        return filtered_tokens

    def _parse_tokens(self, tokens: List[str]):
        """Parse tokens and generate assembly"""
        i = 0
        while i < len(tokens):
            token = tokens[i].upper()

            # Only check for keywords at the start of statements (after newline or at beginning)
            is_statement_start = (i == 0 or tokens[i-1] == '\n')

            if is_statement_start:
                if token == "CLRHOME":
                    lines = self._compile_clrhome()
                    self.assembly_lines.extend(lines)
                    i += 1

                elif token == "DISP":
                    lines, new_i = self._compile_disp(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "FOR":
                    lines, new_i = self._compile_for(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "IF":
                    lines, new_i = self._compile_if(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "INPUT":
                    lines, new_i = self._compile_input(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PROMPT":
                    lines, new_i = self._compile_prompt(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "WHILE":
                    lines, new_i = self._compile_while(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "WEND":
                    lines = self._compile_wend()
                    self.assembly_lines.extend(lines)
                    i += 1

                elif token == "PAUSE":
                    lines = self._compile_pause()
                    self.assembly_lines.extend(lines)
                    i += 1

                elif token == "END":
                    lines = self._compile_end()
                    self.assembly_lines.extend(lines)
                    i += 1

                elif token == "GOTO":
                    lines, new_i = self._compile_goto(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "LBL":
                    lines, new_i = self._compile_lbl(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "DEFINE":
                    lines, new_i = self._compile_define(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "LINE":
                    lines, new_i = self._compile_line(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "FILL":
                    lines, new_i = self._compile_fill(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PXLON":
                    lines, new_i = self._compile_pxlon(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PXLOFF":
                    lines, new_i = self._compile_pxloff(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PXLCHANGE":
                    lines, new_i = self._compile_pxlchange(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PTON":
                    lines, new_i = self._compile_pton(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PTOFF":
                    lines, new_i = self._compile_ptoff(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PTCHANGE":
                    lines, new_i = self._compile_ptchange(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "PLAY":
                    lines, new_i = self._compile_play(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "STOP":
                    lines, new_i = self._compile_stop(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "SOUND":
                    lines, new_i = self._compile_sound(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "DIM":
                    lines, new_i = self._compile_dim(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "MATRIX":
                    lines, new_i = self._compile_matrix(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "CALL":
                    lines, new_i = self._compile_call(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "RETURN":
                    lines = self._compile_return()
                    self.assembly_lines.extend(lines)
                    i += 1

                elif token == "NEXT":
                    lines, new_i = self._compile_next(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif ((re.match(r'[A-Za-z_][A-Za-z0-9_]*', token) or (token.upper().startswith('L') and len(token) == 2 and token[1].isdigit())) and i + 1 < len(tokens) and 
                      tokens[i + 1] == "="):
                    # Variable or list assignment
                    lines, new_i = self._compile_assignment(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == '\n':
                    i += 1
                    continue

                else:
                    # Skip unknown tokens at statement start
                    i += 1
            else:
                # Not at statement start, skip this token
                i += 1

        # Add program end with infinite loop to keep display visible
        self.assembly_lines.extend([
            "",
            "; Program end - infinite loop to keep display visible",
            "halt:",
            "JMP halt",
        ])

        # Add variable declarations
        for var_name, addr in self.variables.items():
            self.assembly_lines.extend([
                f"ORG 0x{addr:04X}",
                f"DW 0  ; Variable {var_name}",
            ])

        # Add string declarations
        for string_content, addr in self.strings.items():
            self.assembly_lines.extend([
                f"ORG 0x{addr:04X}",
            ])
            # Add string bytes
            for char in string_content:
                self.assembly_lines.append(f"DB {ord(char)}")
            self.assembly_lines.append("DB 0  ; Null terminator")

        # Add final ORG back to program area
        self.assembly_lines.extend([
            "",
            "ORG 0x1000",
            "",
            "; String concatenation subroutine",
            "str_concat:",
            "    ; P1 = left string address",
            "    ; Top of stack = right string address",
            "    ; Returns result address in P0",
            "    POP P2",              # P2 = return address
            "    POP P3",              # P3 = right string
            "    PUSH P2",             # Restore return address
            "    ",
            "    ; Allocate space for result string",
            "    MOV P0,0x6000",       # Temporary result buffer",
            "    MOV P4,P0",           # P4 = result pointer",
            "    ",
            "    ; Copy left string",
            "str_cat_copy_left:",
            "    MOV P5,[P1]",
            "    CMP P5,0",
            "    JZ str_cat_copy_right",
            "    MOV [P4],P5",
            "    INC P1",
            "    INC P4",
            "    JMP str_cat_copy_left",
            "    ",
            "str_cat_copy_right:",
            "    MOV P5,[P3]",
            "    CMP P5,0",
            "    JZ str_cat_done",
            "    MOV [P4],P5",
            "    INC P3",
            "    INC P4",
            "    JMP str_cat_copy_right",
            "    ",
            "str_cat_done:",
            "    MOV [P4],0",          # Null terminate",
            "    RET",
        ])

    def _compile_clrhome(self) -> List[str]:
        """Compile ClrHome statement"""
        return [
            "    ; ClrHome",
            "    MOV P0,0",
            "    MOV VM,P0",  # VM = 0 (coordinate mode)
            "    MOV VL,P0",  # VL = 0 (layer 0)
            "    MOV VX,P0",  # VX = 0
            "    MOV VY,P0",  # VY = 0
            "    SFILL P0",   # Fill screen with black
        ]

    def _compile_disp(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Disp statement"""
        lines = ["    ; Disp"]
        i += 1  # Skip DISP

        # Set cursor to current position
        lines.extend([
            f"    MOV P0,{self.cursor_x}",
            "    MOV VX,P0",  # VX
            f"    MOV P0,{self.cursor_y}",
            "    MOV VY,P0",  # VY
            "    MOV P0,0",
            "    MOV VL,P0",  # VL
        ])

        # Parse display arguments
        while i < len(tokens):
            token = tokens[i]

            if token == '\n':
                i += 1
                break

            if token.startswith('"'):
                # String literal
                string_content = token.strip('"')
                lines.extend(self._compile_display_string(string_content))
            elif token.isdigit() or token.isalpha():
                # Variable or number
                if token.isalpha():
                    # Variable
                    lines.extend(self._load_variable(token))
                else:
                    # Number
                    value = int(token)
                    lines.extend([
                        f"    MOV P0,{value}",
                    ])
                lines.extend(self._compile_display_value())
            elif token == ',':
                # New line
                lines.extend([
                    "    MOV P0,VY",  # Get current VY
                    "    ADD P0,8",
                    "    MOV VY,P0",  # Set new VY
                    "    MOV P0,0",
                    "    MOV VX,P0",  # Reset VX
                ])
                self.cursor_y += 8  # Update cursor position for next item in same Disp

            i += 1

        # Advance cursor to next line for next Disp statement
        self.cursor_y += 8
        if self.cursor_y >= 256:  # Wrap around if we reach bottom
            self.cursor_y = 0
        self.cursor_x = 0  # Reset X for next line

        return lines, i

    def _compile_for(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile For loop"""
        lines = []
        i += 1  # Skip FOR

        # Parse: FOR variable = start TO end
        if i < len(tokens):
            var_name = tokens[i]
            i += 2  # Skip variable and =

            start_value = tokens[i]
            i += 2  # Skip start and TO

            end_value = tokens[i]
            i += 1  # Skip end

            # Generate labels
            loop_label = self._generate_label("for_loop")
            end_label = self._generate_label("for_end")

            # Store loop info for NEXT
            self.labels[f"end_{var_name}"] = end_label
            self.loop_start_labels[var_name] = loop_label
            self.loop_end_values[var_name] = end_value

            # Initialize loop variable
            var_addr = self._get_variable_address(var_name)
            lines.extend([
                f"    ; For {var_name} = {start_value} To {end_value}",
                f"    MOV P0,{start_value}",
                f"    MOV [0x{var_addr:04X}],P0",
                f"{loop_label}:",
            ])

        return lines, i

    def _compile_if(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile If statement - simplified version for now"""
        lines = []
        i += 1  # Skip IF

        # Parse condition
        condition_lines, i = self._parse_condition(tokens, i)

        # Generate labels
        end_label = self._generate_label("if_end")

        lines.extend(condition_lines)
        lines.append(f"    JZ {end_label}")

        # For now, just skip to END IF without parsing the body
        # This is a temporary fix
        while i < len(tokens):
            token = tokens[i].upper()
            if token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "IF":
                i += 2  # Skip END IF
                break
            i += 1

        lines.append(f"{end_label}:")

        return lines, i

    def _compile_input(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Input statement"""
        lines = ["    ; Input"]
        i += 1  # Skip INPUT

        if i < len(tokens):
            var_name = tokens[i]
            var_addr = self._get_variable_address(var_name)

            lines.extend([
                f"    ; Input {var_name}",
                "    CALL read_number",
            ])
            lines.extend(self._store_variable(var_name))
            i += 1

        return lines, i

    def _compile_prompt(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Prompt statement"""
        lines = ["    ; Prompt"]
        i += 1  # Skip PROMPT

        if i < len(tokens):
            var_name = tokens[i]
            var_addr = self._get_variable_address(var_name)

            lines.extend([
                f"    ; Prompt {var_name}",
                "    CALL read_number",
            ])
            lines.extend(self._store_variable(var_name))
            i += 1

        return lines, i

    def _compile_while(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile While loop"""
        lines = []
        i += 1  # Skip WHILE

        # Generate labels
        loop_label = self._generate_label("while_loop")
        end_label = self._generate_label("while_end")

        lines.extend([
            f"    ; While loop",
            f"{loop_label}:",
        ])

        # Parse condition
        condition_lines, i = self._parse_condition(tokens, i)
        lines.extend(condition_lines)
        lines.extend([
            f"    JZ {end_label}",
        ])

        # Store end label for WEND
        self.labels["current_while_end"] = end_label
        self.labels["current_while_loop"] = loop_label

        return lines, i

    def _compile_wend(self) -> List[str]:
        """Compile WEnd statement"""
        end_label = self.labels.get("current_while_end", "while_end")
        loop_label = self.labels.get("current_while_loop", "while_loop")

        return [
            f"    JMP {loop_label}",
            f"{end_label}:",
        ]

    def _compile_assignment(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile variable or list assignment with optimizations"""
        target_name = tokens[i]
        i += 1  # Skip target name
        
        # Check if this is a list assignment (L1(index) = ...)
        is_list_assignment = False
        list_name = ""
        index_tokens = []
        
        if tokens[i] == '(':
            # This is a list assignment
            is_list_assignment = True
            list_name = target_name.upper()
            i += 1  # Skip '('
            
            # Collect index tokens until ')'
            paren_count = 1
            while i < len(tokens) and paren_count > 0:
                if tokens[i] == '(':
                    paren_count += 1
                elif tokens[i] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        break
                index_tokens.append(tokens[i])
                i += 1
            i += 1  # Skip ')'
        
        if tokens[i] != '=':
            raise ValueError("Expected '=' in assignment")
        i += 1  # Skip '='

        lines = [f"    ; {target_name} = "]
        
        # Parse the value expression
        expr_lines, i = self._parse_expression(tokens, i)
        lines.extend(expr_lines)
        
        if is_list_assignment:
            # For now, simple list assignment: assume index is a constant
            # TODO: Handle complex index expressions
            if len(index_tokens) == 1 and index_tokens[0].isdigit():
                index = int(index_tokens[0])
                list_addr = self._get_list_address(list_name)
                
                value_reg = self._get_current_register()
                
                lines.extend([
                    f"    ; Store to {list_name}({index})",
                    f"    MOV [0x{list_addr + index * 2:04X}],{value_reg}",  # Direct address calculation
                ])
            else:
                raise ValueError(f"Complex list indices not yet supported: {index_tokens}")
        else:
            # Regular variable assignment
            var_addr = self._get_variable_address(target_name)
            result_reg = self._get_current_register()
            lines.extend(self._store_variable_from_reg(target_name, result_reg))
        
        # Free the result register
        result_reg = self._get_current_register()
        self._free_register(result_reg)
        
        return lines, i

    def _parse_condition(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse a condition for IF/WHILE"""
        lines = []

        # Simple comparison for now: var op value
        left = tokens[i]
        i += 1
        op = tokens[i]
        i += 1
        right = tokens[i]
        i += 1

        # Load left side
        if left.isalpha():
            left_reg = self._allocate_register()
            lines.extend(self._load_variable_to_reg(left, left_reg))
        else:
            left_reg = self._allocate_register()
            lines.append(f"    MOV {left_reg},{left}")

        # Compare with right side
        if right.isalpha():
            right_reg = self._allocate_register()
            lines.extend(self._load_variable_to_reg(right, right_reg))
            lines.append(f"    CMP {left_reg},{right_reg}")
            self._free_register(right_reg)
        else:
            lines.append(f"    CMP {left_reg},{right}")

        self._free_register(left_reg)

        return lines, i

    def _parse_expression(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse an arithmetic expression with proper precedence"""
        return self._parse_additive_expression(tokens, i)

    def _parse_additive_expression(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse additive expressions (+, -) - lowest precedence"""
        lines, i = self._parse_multiplicative_expression(tokens, i)

        while i < len(tokens) and tokens[i] in ['+', '-']:
            op = tokens[i]
            i += 1

            # Save current result register
            left_reg = self._get_current_register()
            
            # Parse right operand
            right_lines, i = self._parse_multiplicative_expression(tokens, i)
            lines.extend(right_lines)
            right_reg = self._get_current_register()

            # Perform operation
            if op == '+':
                # Check if this might be string concatenation (using &)
                # For now, assume numeric addition - string concatenation needs more complex logic
                # TODO: Implement proper string concatenation detection
                lines.append(f"    ADD {left_reg},{right_reg}")
            elif op == '&':
                # String concatenation
                lines.extend([
                    f"    ; String concatenation {left_reg} & {right_reg}",
                    f"    PUSH {left_reg}",       # Save left string address
                    f"    PUSH {right_reg}",      # Save right string address
                    f"    MOV P1,{left_reg}",     # P1 = left string
                    f"    CALL str_concat",       # Call concatenation routine
                    f"    POP {right_reg}",       # Restore right string
                    f"    POP {left_reg}",        # Restore left string
                    f"    MOV {left_reg},P0",     # Result in left register
                ])
            else:  # op == '-'
                lines.append(f"    SUB {left_reg},{right_reg}")

            # Free the right register
            self._free_register(right_reg)

        return lines, i

    def _parse_multiplicative_expression(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse multiplicative expressions (*, /, MOD)"""
        lines, i = self._parse_primary_expression(tokens, i)

        while i < len(tokens) and tokens[i] in ['*', '/', 'MOD']:
            op = tokens[i]
            i += 1

            # Save current result register
            left_reg = self._get_current_register()
            
            # Parse right operand
            right_lines, i = self._parse_primary_expression(tokens, i)
            lines.extend(right_lines)
            right_reg = self._get_current_register()

            # Perform operation
            if op == '*':
                lines.append(f"    MUL {left_reg},{right_reg}")
            elif op == '/':
                lines.append(f"    DIV {left_reg},{right_reg}")
            else:  # op == 'MOD'
                lines.append(f"    MOD {left_reg},{right_reg}")

            # Free the right register
            self._free_register(right_reg)

        return lines, i

    def _parse_primary_expression(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse primary expressions (numbers, variables, parentheses, strings, functions)"""
        lines = []
        token = tokens[i]

        if token == '(':
            # Parenthesized expression
            i += 1
            lines, i = self._parse_additive_expression(tokens, i)
            if i < len(tokens) and tokens[i] == ')':
                i += 1
            else:
                raise ValueError("Missing closing parenthesis")
        elif token == '-':
            # Negative number literal
            i += 1
            if i < len(tokens) and tokens[i].isdigit():
                # Parse the number and make it negative
                num_value = -int(tokens[i])
                result_reg = self._allocate_register()
                lines.append(f"    MOV {result_reg},{num_value}")
                i += 1
            else:
                raise ValueError("Expected number after unary minus")
        elif token == '[':
            # Array literal like [BLACK, RED, GREEN, BLUE]
            i += 1  # Skip '['
            array_elements = []
            
            # Parse array elements until ']'
            while i < len(tokens) and tokens[i] != ']':
                # Parse each element expression
                elem_lines, i = self._parse_additive_expression(tokens, i)
                lines.extend(elem_lines)
                
                # Store the element value (assume it's in current register)
                elem_reg = self._get_current_register()
                array_elements.append(elem_reg)
                
                # Skip comma if present
                if i < len(tokens) and tokens[i] == ',':
                    i += 1
            
            if i < len(tokens) and tokens[i] == ']':
                i += 1
            else:
                raise ValueError("Missing closing bracket in array literal")
            
            # For now, return the address of the first element as the array base
            # TODO: Implement proper array storage and return array base address
            if array_elements:
                result_reg = self._allocate_register()
                # Store array elements in consecutive memory locations starting at a temp address
                array_base = 0x7000  # Temporary array storage area
                for idx, elem_reg in enumerate(array_elements):
                    lines.extend([
                        f"    ; Store array element {idx}",
                        f"    MOV [0x{array_base + idx * 2:04X}],{elem_reg}",
                    ])
                    if idx > 0:  # Free all but the last register
                        self._free_register(elem_reg)
                
                # Return array base address
                lines.append(f"    MOV {result_reg},{array_base}")
            else:
                # Empty array
                result_reg = self._allocate_register()
                lines.append(f"    MOV {result_reg},0")  # Null array
        elif token.startswith('"') and token.endswith('"'):
            # String literal - store in memory and return address
            string_content = token.strip('"')
            string_addr = self._store_string_in_memory(string_content)
            result_reg = self._allocate_register()
            lines.append(f"    MOV {result_reg},{string_addr}")
            i += 1
        elif token.isdigit():
            # Number literal - check for constant folding
            folded_val, new_i = self._fold_constants(tokens, i)
            if folded_val is not None:
                result_reg = self._allocate_register()
                lines.append(f"    MOV {result_reg},{folded_val}")
                i = new_i
            else:
                result_reg = self._allocate_register()
                lines.append(f"    MOV {result_reg},{token}")
                i += 1
        elif token.upper() in self.color_constants:
            # Color constant
            color_value = self.color_constants[token.upper()]
            result_reg = self._allocate_register()
            lines.append(f"    MOV {result_reg},{color_value}")
            i += 1
        elif token.isalpha() or '_' in token or '$' in token or (token.upper().startswith('L') and len(token) == 2 and token[1].isdigit()):
            # Check if this is a list access (L1(index))
            if token.upper().startswith('L') and len(token) == 2 and token[1].isdigit():
                # List access like L1, L2, etc.
                list_name = token.upper()
                i += 1
                if i < len(tokens) and tokens[i] == '(':
                    i += 1
                    # Parse index expression
                    index_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(index_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in list access")
                    
                    # Generate code to load from list
                    list_addr = self._get_list_address(list_name)
                    index_reg = self._get_current_register()  # Save index register
                    result_reg = self._allocate_register()    # Allocate result register
                    
                    lines.extend([
                        f"    ; Load {list_name}({index_reg}) into {result_reg}",
                        f"    MOV P2,{list_addr}",        # Base address of list
                        f"    ADD P2,{index_reg}",        # Add index (×2 for 16-bit)
                        f"    ADD P2,{index_reg}",
                        f"    MOV {result_reg},[P2]",     # Load value
                    ])
                else:
                    # Regular variable
                    result_reg = self._allocate_register()
                    lines.extend(self._load_variable_to_reg(token, result_reg))
                    i += 1
            # Check if this is an array access (array[index])
            elif i + 1 < len(tokens) and tokens[i + 1] == '[':
                # Array access like TEST_COLORS[I]
                array_name = token
                i += 2  # Skip array name and '['
                
                # Parse index expression
                index_lines, i = self._parse_additive_expression(tokens, i)
                lines.extend(index_lines)
                
                if i < len(tokens) and tokens[i] == ']':
                    i += 1
                else:
                    raise ValueError("Missing closing bracket in array access")
                
                # Generate code to load from array
                # For now, assume arrays are stored as consecutive 16-bit values starting at variable address
                array_addr = self._get_variable_address(array_name)
                index_reg = self._get_current_register()  # Save index register
                result_reg = self._allocate_register()    # Allocate result register
                
                lines.extend([
                    f"    ; Load {array_name}[{index_reg}] into {result_reg}",
                    f"    MOV P3,{array_addr}",        # Base address of array
                    f"    ADD P3,{index_reg}",        # Add index (×2 for 16-bit)
                    f"    ADD P3,{index_reg}",
                    f"    MOV {result_reg},[P3]",     # Load value
                ])
                
                # Free the index register
                self._free_register(index_reg)
            # Check if this is a function call
            elif i + 1 < len(tokens) and tokens[i + 1] == '(':
                # Function call
                func_name = token.upper()
                i += 2  # Skip function name and '('
                
                if func_name == 'INT':
                    # INT(string) - convert string to number
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in INT()")
                    # Assume current register contains string address, convert with STOI
                    current_reg = self._get_current_register()
                    lines.append(f"    STOI {current_reg},{current_reg}")  # Convert string at reg to integer in reg
                elif func_name == 'STR':
                    # STR(number) - convert number to string address
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse number argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in STR()")
                    # Convert number in current register to string at temporary buffer
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    PUSH {current_reg}",
                        "    MOV P1,0x6000",  # Temporary string buffer
                        f"    ITOS P1,{current_reg}",     # Convert reg to string at 0x6000
                        f"    MOV {current_reg},P1",      # Return string address
                        f"    POP {current_reg}",
                    ])
                elif func_name in ['SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN', 'SQRT', 'LOG', 'EXP', 'ABS', 'FLOOR', 'CEIL', 'ROUND']:
                    # Math functions
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError(f"Missing closing parenthesis in {func_name}()")
                    
                    current_reg = self._get_current_register()
                    opcode = func_name.lower()
                    lines.append(f"    {opcode.upper()} {current_reg},{current_reg}")  # Apply function to register
                elif func_name == 'COLOR':
                    # COLOR(ramp, shade) - create color from ramp (0-15) and shade (0-15)
                    # Parse ramp argument
                    ramp_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(ramp_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in COLOR(ramp, shade)")
                    
                    # Parse shade argument
                    shade_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(shade_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in COLOR()")
                    
                    # Combine ramp and shade: color = (ramp << 4) | shade
                    shade_reg = self._get_current_register()
                    ramp_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; COLOR({ramp_reg}, {shade_reg})",
                        f"    SHL {ramp_reg},4",        # ramp << 4
                        f"    OR {ramp_reg},{shade_reg}", # (ramp << 4) | shade
                    ])
                    
                    # Free shade register, keep ramp register as result
                    self._free_register(shade_reg)
                elif func_name == 'RAMP':
                    # RAMP(color) - extract ramp from color (color >> 4)
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse color argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in RAMP()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; RAMP({current_reg})",
                        f"    SHR {current_reg},4",  # color >> 4
                    ])
                elif func_name == 'SHADE':
                    # SHADE(color) - extract shade from color (color & 0x0F)
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse color argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in SHADE()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; SHADE({current_reg})",
                        f"    AND {current_reg},15",  # color & 0x0F (15 = 0b1111)
                    ])
                elif func_name == 'LEN':
                    # LEN(string) - get string length
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in LEN()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; LEN({current_reg})",
                        f"    MOV P1,{current_reg}",  # String address
                        f"    MOV {current_reg},0",   # Initialize length counter
                        f"len_loop_{self.label_counter}:",
                        f"    MOV P2,[P1]",           # Load character
                        f"    CMP P2,0",              # Check for null terminator
                        f"    JZ len_done_{self.label_counter}",
                        f"    INC {current_reg}",     # Increment length
                        f"    INC P1",                # Next character
                        f"    JMP len_loop_{self.label_counter}",
                        f"len_done_{self.label_counter}:",
                    ])
                    self.label_counter += 1
                else:
                    raise ValueError(f"Unknown function: {func_name}")
            else:
                # Variable
                result_reg = self._allocate_register()
                lines.extend(self._load_variable_to_reg(token, result_reg))
                i += 1
        else:
            raise ValueError(f"Unexpected token in expression: {token}")

        return lines, i

    def _fold_constants(self, tokens: List[str], i: int) -> Tuple[int, int]:
        """Try to fold constants in an expression. Returns (folded_value, new_i) or (None, original_i)"""
        # Enhanced constant folding for arithmetic expressions
        if not tokens[i].isdigit():
            return None, i
        
        original_i = i
        result = int(tokens[i])
        i += 1
        
        # Process a chain of operations
        while i < len(tokens) and tokens[i] in ['+', '-', '*', '/']:
            op = tokens[i]
            i += 1
            
            if i >= len(tokens) or not tokens[i].isdigit():
                return None, original_i
            
            right_val = int(tokens[i])
            i += 1
            
            try:
                if op == '+':
                    result += right_val
                elif op == '-':
                    result -= right_val
                elif op == '*':
                    result *= right_val
                elif op == '/' and right_val != 0:
                    result = result // right_val  # Integer division
                else:
                    return None, original_i
            except:
                return None, original_i
        
        return result, i

    def _store_string_in_memory(self, string: str) -> int:
        """Store a string in memory and return its address"""
        if string in self.strings:
            return self.strings[string]

        # Allocate new string (add null terminator)
        addr = 0x8000 + self.string_counter * 100  # Simple allocation
        self.strings[string] = addr
        self.string_counter += 1
        return addr

    def compile_program(self, nobasic_source: str, output_file: str):
        """Compile NoBASIC source code to assembly"""
        tokens = self._tokenize(nobasic_source)
        self._parse_tokens(tokens)

        # Optimize the generated assembly
        self._optimize_assembly()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.assembly_lines))

        print(f"Compiled NoBASIC program to {output_file}")

    def compile_to_lines(self, nobasic_source: str) -> list:
        """Compile NoBASIC source code to assembly lines without writing file"""
        tokens = self._tokenize(nobasic_source)
        self._parse_tokens(tokens)
        return self.assembly_lines

    def _compile_display_string(self, string: str) -> List[str]:
        """Generate code to display a string by inlining character display"""
        lines = []
        for char in string:
            if char == '\n':
                # Newline
                lines.extend([
                    f"    ; Newline",
                    "    MOV P0,VY",  # Get current VY
                    "    ADD P0,8",
                    "    MOV VY,P0",  # Set new VY
                    "    MOV P0,0",
                    "    MOV VX,P0",  # Reset VX
                ])
            else:
                ascii_val = ord(char)
                lines.extend([
                    f"    ; Display '{char}'",
                    f"    MOV P0,{ascii_val}",  # Character code
                    "    MOV P1,15",            # White color
                    "    CHAR P0,P1",          # Display character
                ])
        return lines

    def _compile_display_value(self) -> List[str]:
        """Generate code to display a value from P0 (either number or string address)"""
        # Check if P0 contains a string address (0x4000-0x7FFF range)
        return [
            "    ; Display value (number or string)",
            f"    MOV P1,P0",              # Save original value
            f"    CMP P0,0x4000",          # Check if >= string start
            f"    JC display_as_number",   # If < 0x4000, treat as number
            f"    CMP P0,0x8000",          # Check if < string end
            f"    JNC display_as_number",  # If >= 0x8000, treat as number
            f"    ; Display as string",
            f"    MOV P2,P0",              # P2 = string pointer
            f"display_str_loop:",
            f"    MOV P0,[P2]",            # Load character
            f"    CMP P0,0",               # Check for null terminator
            f"    JZ display_value_done",
            f"    CMP P0,10",              # Check for newline
            f"    JZ display_str_newline",
            f"    MOV P3,15",               # White color
            f"    CHAR P0,P3",             # Display character
            f"    INC P2",                 # Next character
            f"    JMP display_str_loop",
            f"display_str_newline:",
            f"    MOV P0,VY",        # Get current VY
            f"    ADD P0,8",
            f"    MOV VY,P0",        # Set new VY
            f"    MOV P0,0",
            f"    MOV VX,P0",        # Reset VX
            f"    INC P2",                 # Next character
            f"    JMP display_str_loop",
            f"display_as_number:",
            f"    MOV P0,P1",              # Restore original value
            f"    ; Display as number",
            f"    MOV P1,0x6000",          # Temporary buffer for string
            f"    ITOS P1,P0",             # Convert P0 to string at buffer
            f"    MOV P2,P1",              # P2 = string pointer
            f"display_num_loop:",
            f"    MOV P0,[P2]",            # Load character
            f"    CMP P0,0",               # Check for null terminator
            f"    JZ display_value_done",
            f"    MOV P3,15",               # White color
            f"    CHAR P0,P3",             # Display character
            f"    INC P2",                 # Next character
            f"    JMP display_num_loop",
            f"display_value_done:",
        ]

    def _compile_pause(self) -> List[str]:
        """Compile Pause statement - wait for key press"""
        return [
            "    ; Pause - wait for key press",
            "pause_loop:",
            "    KEYSTAT P0",     # Check if key available
            "    CMP P0,0",
            "    JZ pause_loop",  # Wait for key
            "    KEYIN P0",       # Read and discard the key
        ]

    def _compile_end(self) -> List[str]:
        """Compile End statement - terminate program"""
        return [
            "    ; End - terminate program",
            "    JMP halt",  # Jump to the halt loop
        ]

    def _compile_goto(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Goto statement"""
        i += 1  # Skip GOTO
        if i < len(tokens):
            label_name = tokens[i]
            i += 1
            return [
                f"    ; Goto {label_name}",
                f"    JMP {label_name}",
            ], i
        return [], i

    def _compile_lbl(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Lbl statement"""
        i += 1  # Skip LBL
        if i < len(tokens):
            label_name = tokens[i]
            i += 1
            return [
                f"    ; Lbl {label_name}",
                f"{label_name}:",
            ], i
        return [], i

    def _load_variable(self, var_name: str, dest_register: str = "P0") -> List[str]:
        """Generate code to load a variable into a register"""
        var_addr = self._get_variable_address(var_name)
        return [
            f"    ; Load {var_name} into {dest_register}",
            f"    MOV {dest_register},[0x{var_addr:04X}]",  # Direct memory access
        ]

    def _load_variable_to_reg(self, var_name: str, dest_register: str) -> List[str]:
        """Generate code to load a variable into a specific register"""
        var_addr = self._get_variable_address(var_name)
        return [
            f"    ; Load {var_name} into {dest_register}",
            f"    MOV {dest_register},[0x{var_addr:04X}]",  # Direct memory access
        ]

    def _store_variable(self, var_name: str, source_register: str = "P0") -> List[str]:
        """Generate code to store a register value into a variable"""
        var_addr = self._get_variable_address(var_name)
        return [
            f"    ; Store {source_register} into {var_name}",
            f"    MOV [0x{var_addr:04X}],{source_register}",  # Direct memory access
        ]

    def _store_variable_from_reg(self, var_name: str, source_register: str) -> List[str]:
        """Generate code to store a register value into a variable"""
        var_addr = self._get_variable_address(var_name)
        return [
            f"    ; Store {source_register} into {var_name}",
            f"    MOV [0x{var_addr:04X}],{source_register}",  # Direct memory access
        ]

    def _get_variable_address(self, var_name: str) -> int:
        """Get or allocate memory address for a variable"""
        var_name = var_name.upper()
        if var_name not in self.variables:
            # Allocate new variable address (2 bytes per variable)
            addr = self.VARIABLE_START + len(self.variables) * 2
            self.variables[var_name] = addr
        return self.variables[var_name]

    def _get_list_address(self, list_name: str) -> int:
        """Get or allocate memory address for a list"""
        list_name = list_name.upper()
        if list_name not in self.lists:
            # Allocate new list address (100 elements × 2 bytes = 200 bytes per list)
            addr = self.LIST_START + len(self.lists) * 200
            self.lists[list_name] = addr
            self.list_sizes[list_name] = 100  # Default size
        return self.lists[list_name]

    def _compile_line(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Line(X1,Y1,X2,Y2[,Color]) statement"""
        lines = ["    ; Line"]
        i += 1  # Skip LINE

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after LINE")
        i += 1  # Skip '('

        # Parse X1
        x1_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x1_lines)
        x1_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X1 in LINE")
        i += 1  # Skip ','

        # Parse Y1
        y1_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y1_lines)
        y1_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after Y1 in LINE")
        i += 1  # Skip ','

        # Parse X2
        x2_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x2_lines)
        x2_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X2 in LINE")
        i += 1  # Skip ','

        # Parse Y2
        y2_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y2_lines)
        y2_reg = self._get_current_register()

        # Optional color parameter
        color = 15  # Default white
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            color_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(color_lines)
            color_reg = self._get_current_register()
            color = color_reg  # Use register
        else:
            color_reg = None

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after LINE parameters")
        i += 1  # Skip ')'

        # Generate SLINE instruction
        lines.extend([
            f"    ; Draw line from ({x1_reg},{y1_reg}) to ({x2_reg},{y2_reg})",
            f"    SLINE {x1_reg},{y1_reg},{x2_reg},{y2_reg},{color}",
        ])

        # Free registers
        for reg in [x1_reg, y1_reg, x2_reg, y2_reg]:
            self._free_register(reg)
        if color_reg:
            self._free_register(color_reg)

        return lines, i

    def _compile_circle(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Circle(X,Y,Radius[,Color,Filled]) statement"""
        lines = ["    ; Circle"]
        i += 1  # Skip CIRCLE

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after CIRCLE")
        i += 1  # Skip '('

        # Parse X
        x_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x_lines)
        x_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X in CIRCLE")
        i += 1  # Skip ','

        # Parse Y
        y_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y_lines)
        y_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after Y in CIRCLE")
        i += 1  # Skip ','

        # Parse Radius
        radius_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(radius_lines)
        radius_reg = self._get_current_register()

        # Optional color parameter (default white)
        color = 15
        color_reg = None
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            color_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(color_lines)
            color_reg = self._get_current_register()
            color = color_reg

        # Optional filled parameter (default 1 = filled)
        filled = 1
        filled_reg = None
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            filled_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(filled_lines)
            filled_reg = self._get_current_register()
            filled = filled_reg

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after CIRCLE parameters")
        i += 1  # Skip ')'

        # Generate SCIRC instruction
        lines.extend([
            f"    ; Draw circle at ({x_reg},{y_reg}) radius {radius_reg}",
            f"    SCIRC {x_reg},{y_reg},{radius_reg},{color},{filled}",
        ])

        # Free registers
        for reg in [x_reg, y_reg, radius_reg]:
            self._free_register(reg)
        if color_reg:
            self._free_register(color_reg)
        if filled_reg:
            self._free_register(filled_reg)

        return lines, i

    def _compile_fill(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile FILL(X1,Y1,X2,Y2,Color) statement - fill rectangle"""
        lines = ["    ; Fill"]
        i += 1  # Skip FILL

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after FILL")
        i += 1  # Skip '('

        # Parse X1
        x1_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x1_lines)
        x1_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X1 in FILL")
        i += 1  # Skip ','

        # Parse Y1
        y1_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y1_lines)
        y1_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after Y1 in FILL")
        i += 1  # Skip ','

        # Parse X2
        x2_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x2_lines)
        x2_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X2 in FILL")
        i += 1  # Skip ','

        # Parse Y2
        y2_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y2_lines)
        y2_reg = self._get_current_register()

        # Optional color parameter
        color = 15  # Default white
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            color_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(color_lines)
            color_reg = self._get_current_register()
            color = color_reg

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after FILL parameters")
        i += 1  # Skip ')'

        # Generate SFILLR instruction (fill rectangle)
        lines.extend([
            f"    ; Fill rectangle from ({x1_reg},{y1_reg}) to ({x2_reg},{y2_reg})",
            f"    SFILLR {x1_reg},{y1_reg},{x2_reg},{y2_reg},{color}",
        ])

        # Free registers
        for reg in [x1_reg, y1_reg, x2_reg, y2_reg]:
            self._free_register(reg)
        if isinstance(color, str):  # If color was a register
            self._free_register(color)

        return lines, i

    def _compile_pxlon(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pxl-On(X,Y[,Color]) statement"""
        return self._compile_pixel_op(tokens, i, "Pxl-On", "SWRITE")

    def _compile_pxloff(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pxl-Off(X,Y) statement"""
        lines = ["    ; Pxl-Off"]
        i += 1  # Skip PXLOFF

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after PXLOFF")
        i += 1  # Skip '('

        # Parse X
        x_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x_lines)
        x_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X in PXLOFF")
        i += 1  # Skip ','

        # Parse Y
        y_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y_lines)
        y_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after PXLOFF parameters")
        i += 1  # Skip ')'

        # Set coordinates and write black pixel (0)
        lines.extend([
            f"    ; Turn off pixel at ({x_reg},{y_reg})",
            f"    MOV [0xF100],{x_reg}",  # VX = X
            f"    MOV [0xF101],{y_reg}",  # VY = Y
            f"    MOV P0,0",              # Black color
            f"    SWRITE P0",             # Write pixel
        ])

        # Free registers
        self._free_register(x_reg)
        self._free_register(y_reg)

        return lines, i

    def _compile_pxlchange(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pxl-Change(X,Y) statement"""
        lines = ["    ; Pxl-Change"]
        i += 1  # Skip PXLCHANGE

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after PXLCHANGE")
        i += 1  # Skip '('

        # Parse X
        x_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x_lines)
        x_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X in PXLCHANGE")
        i += 1  # Skip ','

        # Parse Y
        y_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y_lines)
        y_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after PXLCHANGE parameters")
        i += 1  # Skip ')'

        # Read current pixel, invert it, write back
        lines.extend([
            f"    ; Toggle pixel at ({x_reg},{y_reg})",
            f"    MOV VX,{x_reg}",  # VX = X
            f"    MOV VY,{y_reg}",  # VY = Y
            f"    SREAD P0",        # Read current pixel color
            f"    XOR P0,15",        # Invert color (assuming 4-bit color: 0-15)
            f"    SWRITE P0",       # Write inverted pixel
        ])

        # Free registers
        self._free_register(x_reg)
        self._free_register(y_reg)

        return lines, i

    def _compile_pixel_op(self, tokens: List[str], i: int, command_name: str, operation: str) -> Tuple[List[str], int]:
        """Helper for pixel operations that set coordinates and write"""
        lines = [f"    ; {command_name}"]
        i += 1  # Skip command

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError(f"Expected '(' after {command_name}")
        i += 1  # Skip '('

        # Parse X
        x_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x_lines)
        x_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError(f"Expected ',' after X in {command_name}")
        i += 1  # Skip ','

        # Parse Y
        y_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y_lines)
        y_reg = self._get_current_register()

        # Optional color parameter
        color = 15  # Default white
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            color_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(color_lines)
            color_reg = self._get_current_register()
            color = color_reg

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError(f"Expected ')' after {command_name} parameters")
        i += 1  # Skip ')'

        # Set coordinates and perform operation
        lines.extend([
            f"    ; {command_name} at ({x_reg},{y_reg})",
            f"    MOV VX,{x_reg}",  # VX = X
            f"    MOV VY,{y_reg}",  # VY = Y
        ])

        if operation == "SWRITE":
            lines.append(f"    MOV P0,{color}")
            lines.append(f"    {operation} P0")
        else:
            lines.append(f"    {operation}")

        # Free registers
        self._free_register(x_reg)
        self._free_register(y_reg)
        if isinstance(color, str):  # If color was a register
            self._free_register(color)

        return lines, i

    def _compile_pton(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pt-On(X,Y[,Color]) statement - same as Pxl-On but for points"""
        return self._compile_pixel_op(tokens, i, "Pt-On", "SWRITE")

    def _compile_ptoff(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pt-Off(X,Y) statement - same as Pxl-Off but for points"""
        return self._compile_pxloff(tokens, i)  # Reuse Pxl-Off implementation

    def _compile_ptchange(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Pt-Change(X,Y) statement - same as Pxl-Change but for points"""
        return self._compile_pxlchange(tokens, i)  # Reuse Pxl-Change implementation

    def _compile_play(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Play statement - start sound playback"""
        lines = ["    ; Play - start sound playback"]
        i += 1  # Skip PLAY

        lines.append("    SPLAY")
        return lines, i

    def _compile_stop(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Stop statement - stop sound playback"""
        lines = ["    ; Stop - stop sound playback"]
        i += 1  # Skip STOP

        lines.append("    SSTOP")
        return lines, i

    def _compile_sound(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Sound(Frequency, Duration[, Volume, Waveform]) statement"""
        lines = ["    ; Sound"]
        i += 1  # Skip SOUND

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after SOUND")
        i += 1  # Skip '('

        # Parse Frequency
        freq_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(freq_lines)
        freq_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after frequency in SOUND")
        i += 1  # Skip ','

        # Parse Duration (in cycles)
        duration_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(duration_lines)
        duration_reg = self._get_current_register()

        # Optional Volume (default 128)
        volume = 128
        volume_reg = None
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            volume_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(volume_lines)
            volume_reg = self._get_current_register()
            volume = volume_reg

        # Optional Waveform (default 0 = sine)
        waveform = 0
        waveform_reg = None
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            waveform_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(waveform_lines)
            waveform_reg = self._get_current_register()
            waveform = waveform_reg

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after SOUND parameters")
        i += 1  # Skip ')'

        # Set up sound registers and play
        lines.extend([
            f"    ; Sound freq={freq_reg}, duration={duration_reg}, vol={volume}, wave={waveform}",
            f"    MOV SA,0x2000",        # Sound buffer address
            f"    MOV SF,{freq_reg}",    # Frequency
            f"    MOV SV,{volume}",      # Volume
            f"    MOV SW,{waveform}",    # Waveform
            f"    SPLAY",                # Start playback
        ])

        # Simple duration wait (not accurate timing, but functional)
        lines.extend([
            f"    ; Wait for duration",
            f"    MOV P2,{duration_reg}",
            f"sound_wait_loop:",
            f"    DEC P2",
            f"    JNZ sound_wait_loop",
            f"    SSTOP",                # Stop after duration
        ])

        # Free registers
        self._free_register(freq_reg)
        self._free_register(duration_reg)
        if volume_reg:
            self._free_register(volume_reg)
        if waveform_reg:
            self._free_register(waveform_reg)

        return lines, i

    def _compile_define(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Define SubName statement - start subroutine definition"""
        lines = []
        i += 1  # Skip DEFINE

        if i >= len(tokens):
            raise ValueError("Expected subroutine name after DEFINE")

        sub_name = tokens[i]
        i += 1

        # Generate label for subroutine (store uppercase key for case-insensitive lookup)
        sub_label = f"sub_{sub_name}"
        self.labels[sub_name.upper()] = sub_label

        lines.extend([
            f"    ; Define subroutine {sub_name}",
            f"{sub_label}:",
        ])

        return lines, i

    def _compile_dim(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile DIM statement for array declaration"""
        lines = ["    ; DIM - array declaration"]
        i += 1  # Skip DIM

        if i >= len(tokens):
            raise ValueError("Expected array name after DIM")

        array_name = tokens[i]
        i += 1

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after array name in DIM")

        i += 1  # Skip '('

        # Parse array size
        size_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(size_lines)

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after array size in DIM")

        i += 1  # Skip ')'

        # Get the size from the current register
        size_reg = self._get_current_register()

        # Allocate memory for the array (size * 2 bytes per element)
        # For now, store array info for later use
        if not hasattr(self, 'arrays'):
            self.arrays = {}

        self.arrays[array_name] = {
            'size_reg': size_reg,
            'allocated': False
        }

        lines.extend([
            f"    ; Array {array_name} declared with size in {size_reg}",
            f"    ; Memory will be allocated at runtime"
        ])

        return lines, i

    def _compile_matrix(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile MATRIX statement for matrix declaration"""
        lines = ["    ; MATRIX - matrix declaration"]
        i += 1  # Skip MATRIX

        if i >= len(tokens):
            raise ValueError("Expected matrix name after MATRIX")

        matrix_name = tokens[i]
        i += 1

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after matrix name in MATRIX")

        i += 1  # Skip '('

        # Parse rows
        rows_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(rows_lines)

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after rows in MATRIX")

        i += 1  # Skip ','

        # Parse columns
        cols_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(cols_lines)

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after columns in MATRIX")

        i += 1  # Skip ')'

        # Get rows and cols from registers
        cols_reg = self._get_current_register()
        rows_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()

        # Store matrix info
        if not hasattr(self, 'matrices'):
            self.matrices = {}

        self.matrices[matrix_name] = {
            'rows_reg': rows_reg,
            'cols_reg': cols_reg,
            'allocated': False
        }

        lines.extend([
            f"    ; Matrix {matrix_name} declared with {rows_reg} rows, {cols_reg} cols",
            f"    ; Memory will be allocated at runtime"
        ])

        return lines, i

    def _compile_call(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Call SubName statement"""
        lines = ["    ; Call subroutine"]
        i += 1  # Skip CALL

        if i >= len(tokens):
            raise ValueError("Expected subroutine name after CALL")

        sub_name = tokens[i]
        i += 1

        # Look up subroutine label (case-insensitive)
        sub_label = self.labels.get(sub_name.upper())
        if sub_label is None:
            raise ValueError(f"Undefined subroutine: {sub_name}")

        lines.append(f"    CALL {sub_label}")

        return lines, i

    def _compile_return(self) -> List[str]:
        """Compile Return statement"""
        return [
            "    ; Return",
            "    RET",
        ]

    def _compile_next(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Next statement"""
        lines = []
        i += 1  # Skip NEXT

        if i < len(tokens):
            var_name = tokens[i]
            i += 1

            # Get the end label for this loop variable
            end_label = self.labels.get(f"end_{var_name}")
            if end_label:
                var_addr = self._get_variable_address(var_name)
                lines.extend([
                    f"    ; Next {var_name}",
                    f"    MOV P0,[0x{var_addr:04X}]",  # Load current value
                    f"    INC P0",                     # Increment
                    f"    MOV [0x{var_addr:04X}],P0",  # Store back
                    f"    CMP P0,{self.loop_end_values.get(var_name, 255)}",  # Compare with end value
                    f"    JLE {self.loop_start_labels.get(var_name, 'start')}",  # Jump back if <= end
                    f"{end_label}:",  # End label
                ])
            else:
                lines.append(f"    ; Warning: No loop found for variable {var_name}")

        return lines, i

    def _optimize_assembly(self):
        """Optimize the generated assembly code with advanced techniques"""
        optimized_lines = []
        i = 0
        
        # First pass: constant folding and algebraic simplifications
        while i < len(self.assembly_lines):
            line = self.assembly_lines[i]
            
            # Remove redundant MOV operations
            if i + 1 < len(self.assembly_lines):
                next_line = self.assembly_lines[i + 1]
                if (line.startswith("    MOV ") and next_line.startswith("    MOV ") and
                    line.split(",")[0] == next_line.split(",")[0]):
                    # Skip the first MOV if the second overwrites the same register
                    i += 1
                    continue
            
            # Optimize immediate loads followed by operations (ADD, SUB, MUL, DIV)
            if (line.startswith("    MOV ") and i + 1 < len(self.assembly_lines) and
                self.assembly_lines[i + 1].startswith(("    ADD ", "    SUB ", "    MUL ", "    DIV ")) and
                line.split()[1] == self.assembly_lines[i + 1].split()[1]):
                parts = line.split()
                op_parts = self.assembly_lines[i + 1].split()
                if (len(parts) >= 3 and parts[2].isdigit() and 
                    len(op_parts) >= 3 and op_parts[2].isdigit()):
                    try:
                        imm_val = int(parts[2])
                        op_val = int(op_parts[2])
                        if op_parts[0].endswith("ADD"):
                            new_val = imm_val + op_val
                        elif op_parts[0].endswith("SUB"):
                            new_val = imm_val - op_val
                        elif op_parts[0].endswith("MUL"):
                            new_val = imm_val * op_val
                        elif op_parts[0].endswith("DIV") and op_val != 0:
                            new_val = imm_val // op_val
                        else:
                            raise ValueError("Invalid operation")
                        optimized_lines.append(f"    MOV {parts[1]},{new_val}")
                        i += 2
                        continue
                    except (ValueError, ZeroDivisionError):
                        pass
            
            # Optimize MOV reg,0 followed by operations that can be simplified
            parts = line.split()
            if (line.startswith("    MOV ") and len(parts) >= 3 and parts[2] == "0" and 
                i + 1 < len(self.assembly_lines)):
                reg = parts[1]
                next_line = self.assembly_lines[i + 1]
                if next_line.startswith("    ADD "):
                    # MOV reg,0; ADD reg,val -> MOV reg,val
                    add_parts = next_line.split()
                    if len(add_parts) >= 3 and add_parts[1] == reg:
                        optimized_lines.append(f"    MOV {reg},{add_parts[2]}")
                        i += 2
                        continue
                elif next_line.startswith("    MUL "):
                    # MOV reg,0; MUL reg,val -> MOV reg,0 (multiplication by zero)
                    mul_parts = next_line.split()
                    if len(mul_parts) >= 3 and mul_parts[1] == reg:
                        optimized_lines.append(line)  # Keep MOV reg,0
                        i += 2
                        continue
            
            # Remove comments that are just semicolons
            if line.strip() == ";":
                i += 1
                continue
            
            # Optimize consecutive MOV operations to the same destination
            if (line.startswith("    MOV ") and i > 0 and 
                optimized_lines[-1].startswith("    MOV ") and
                line.split()[1] == optimized_lines[-1].split()[1]):
                # Replace the previous MOV with this one
                optimized_lines[-1] = line
                i += 1
                continue
            
            optimized_lines.append(line)
            i += 1
        
        # Second pass: remove unreachable code after JMP
        final_lines = []
        i = 0
        while i < len(optimized_lines):
            line = optimized_lines[i]
            final_lines.append(line)
            
            # If this is an unconditional jump, skip until next label
            if line.strip().startswith("JMP "):
                i += 1
                # Skip lines until we find a label or end
                while i < len(optimized_lines):
                    next_line = optimized_lines[i]
                    if next_line.strip().endswith(":") or not next_line.strip():
                        break
                    i += 1
                continue
            
            i += 1
        
        self.assembly_lines = final_lines
        
        self.assembly_lines = optimized_lines

def main():
    if len(sys.argv) != 3:
        print("Usage: python nobasic_compiler.py <input.nob> <output.asm>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, 'r', encoding='utf-8') as f:
        nobasic_source = f.read()

    compiler = NoBasicCompiler()
    compiler.compile_program(nobasic_source, output_file)


if __name__ == "__main__":
    main()
