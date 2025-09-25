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
        
        # Array management
        self.arrays: Dict[str, Dict] = {}  # Array name -> {'address': addr, 'size': size, 'allocated': bool}
        self.array_allocation_ptr = self.TEMP_START  # Start allocating arrays from temp area

        # Struct management
        self.structs: Dict[str, Dict] = {}  # Struct name -> {'fields': {'field_name': offset}, 'size': total_size}
        self.struct_instances: Dict[str, Dict] = {}  # Instance name -> {'struct_name': name, 'address': addr}

        # Compilation state
        self.assembly_lines: List[str] = []
        self.variables: Dict[str, int] = {}  # Variable name -> memory address
        self.labels: Dict[str, str] = {}     # Label name -> assembly label
        self.label_counter = 0
        self.string_counter = 0
        self.strings: Dict[str, int] = {}    # String content -> memory address

        # Pre-allocate variables A-Z
        for i in range(26):
            var_name = chr(65 + i)  # A-Z
            self.variables[var_name] = self.VARIABLE_START + i * 2

        # Loop tracking for For/Next
        self.loop_start_labels: Dict[str, str] = {}  # Variable name -> loop start label
        self.loop_end_values: Dict[str, int] = {}    # Variable name -> end value
        
        # Loop stack for BREAK/CONTINUE support
        self.loop_stack: List[Dict[str, str]] = []  # Stack of {'start': label, 'end': label, 'type': 'for'|'while'}
        
        # Register allocation for expression evaluation - improved system
        self.available_registers = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
        self.register_usage: Dict[str, int] = {}  # Track when registers were last used
        self.register_stack: List[str] = []
        self.next_usage_id = 0
        
        # Text cursor position for display statements
        self.cursor_x = 0
        self.cursor_y = 0

        # SELECT CASE state
        self.select_stack = []

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

        # Boolean constants
        self.boolean_constants = {
            'TRUE': 1,
            'FALSE': 0,
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
        # Include $ in variable names for string variables
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_$]*|:=|<=|>=|<>|[0-9]+(?:\.[0-9]+)?|"[^"]*"|\n|\S', source)

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

                elif token == "TRY":
                    lines, new_i = self._compile_try(tokens, i)
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
                    # Check if we need to add jump after SELECT CASE statement
                    self._add_select_jump_if_needed(tokens, i)

                elif token == "END":
                    lines = self._compile_end()
                    self.assembly_lines.extend(lines)
                    i += 1
                    # Check if we need to add jump after SELECT CASE statement
                    self._add_select_jump_if_needed(tokens, i)

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

                elif token == "STRUCT":
                    lines, new_i = self._compile_struct(tokens, i)
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

                elif token == "RECT":
                    lines, new_i = self._compile_rect(tokens, i)
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

                elif token == "SPLAY":
                    lines, new_i = self._compile_splay(tokens, i)
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

                elif token == "SELECT":
                    lines, new_i = self._compile_select(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif token == "CASE":
                    # If we were in a case body, add jump to end before starting new case
                    if self.select_stack and self.select_stack[-1]['in_case_body']:
                        select_info = self.select_stack[-1]
                        end_label = select_info['end_label']
                        self.assembly_lines.append(f"    JMP {end_label}")
                        self.select_stack[-1]['in_case_body'] = False
                    
                    lines, new_i = self._compile_case(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i
                    # Mark that we're now in a case body
                    if self.select_stack:
                        self.select_stack[-1]['in_case_body'] = True

                elif token == "CASEELSE":
                    # If we were in a case body, add jump to end before starting case else
                    if self.select_stack and self.select_stack[-1]['in_case_body']:
                        select_info = self.select_stack[-1]
                        end_label = select_info['end_label']
                        self.assembly_lines.append(f"    JMP {end_label}")
                        self.select_stack[-1]['in_case_body'] = False
                    
                    lines, new_i = self._compile_case_else(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i
                    # Mark that we're now in a case body
                    if self.select_stack:
                        self.select_stack[-1]['in_case_body'] = True

                elif token.upper() == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "SELECT":
                    # If we were in a case body, add jump to end before ending select
                    if self.select_stack and self.select_stack[-1]['in_case_body']:
                        select_info = self.select_stack[-1]
                        end_label = select_info['end_label']
                        self.assembly_lines.append(f"    JMP {end_label}")
                        self.select_stack[-1]['in_case_body'] = False
                    
                    lines = self._compile_end_select()
                    self.assembly_lines.extend(lines)
                    i += 2  # Skip END SELECT

                elif ((re.match(r'[A-Za-z_][A-Za-z0-9_]*', token) or (token.upper().startswith('L') and len(token) == 2 and token[1].isdigit())) and i + 1 < len(tokens) and 
                      tokens[i + 1] == "="):
                    # Variable assignment: VAR = expression
                    lines, new_i = self._compile_assignment(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif (token.upper().startswith('L') and len(token) == 2 and token[1].isdigit()) and i + 1 < len(tokens) and tokens[i + 1] == "(":
                    # List assignment: L1(index) = expression
                    lines, new_i = self._compile_assignment(tokens, i)
                    self.assembly_lines.extend(lines)
                    i = new_i

                elif re.match(r'[A-Za-z_][A-Za-z0-9_]*', token) and i + 1 < len(tokens) and tokens[i + 1] == "[":
                    # Array assignment: ARRAY[index] = expression
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
            "ORG 0x8000",
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
            "    STRCPY P0,P1",        # Copy left string to result buffer
            "    STRCAT P0,P3",        # Append right string to result buffer
            "    RET",
            "",
            "; LEFT(string, count) - extract left count characters",
            "left_substr:",
            "    ; P0 = result buffer, P1 = source string, P2 = count",
            "    MOV P3,P0",           # P3 = result pointer",
            "    MOV P4,0",            # P4 = character counter",
            "left_loop:",
            "    CMP P4,P2",           # Check if we've copied enough",
            "    JZ left_done",
            "    MOV P5,[P1]",         # Load character from source",
            "    CMP P5,0",            # Check for null terminator",
            "    JZ left_done",
            "    MOV [P3],P5",         # Store character in result",
            "    INC P1",              # Next source character",
            "    INC P3",              # Next result position",
            "    INC P4",              # Increment counter",
            "    JMP left_loop",
            "left_done:",
            "    MOV [P3],0",          # Null terminate result",
            "    RET",
            "",
            "; RIGHT(string, count) - extract right count characters",
            "right_substr:",
            "    ; P0 = result buffer, P1 = source string, P2 = count",
            "    MOV P3,P1",           # P3 = string pointer for length calculation",
            "    MOV P4,0",            # P4 = string length counter",
            "right_len_loop:",
            "    MOV P5,[P3]",         # Load character",
            "    CMP P5,0",            # Check for null terminator",
            "    JZ right_len_done",
            "    INC P3",              # Next character",
            "    INC P4",              # Increment length",
            "    JMP right_len_loop",
            "right_len_done:",
            "    ; P4 now contains string length",
            "    ; Calculate start position: max(0, length - count)",
            "    CMP P4,P2",           # Compare length with count",
            "    JC right_use_all",   # If length < count, use all characters",
            "    MOV P3,P4",           # P3 = length",
            "    SUB P3,P2",           # P3 = length - count (start position)",
            "    JMP right_copy",
            "right_use_all:",
            "    MOV P3,0",            # Start from beginning",
            "right_copy:",
            "    ADD P1,P3",           # P1 = source + start position",
            "    MOV P3,P0",           # P3 = result pointer",
            "right_copy_loop:",
            "    MOV P5,[P1]",         # Load character from source",
            "    CMP P5,0",            # Check for null terminator",
            "    JZ right_copy_done",
            "    MOV [P3],P5",         # Store character in result",
            "    INC P1",              # Next source character",
            "    INC P3",              # Next result position",
            "    JMP right_copy_loop",
            "right_copy_done:",
            "    MOV [P3],0",          # Null terminate result",
            "    RET",
            "",
            "; MID(string, start, count) - extract substring",
            "mid_substr:",
            "    ; P0 = result buffer, P1 = source string, P2 = start position, P3 = count",
            "    ADD P1,P2",           # P1 = source + start position",
            "    MOV P4,P0",           # P4 = result pointer",
            "    MOV P5,0",            # P5 = character counter",
            "mid_loop:",
            "    CMP P5,P3",           # Check if we've copied enough",
            "    JZ mid_done",
            "    MOV P6,[P1]",         # Load character from source",
            "    CMP P6,0",            # Check for null terminator",
            "    JZ mid_done",
            "    MOV [P4],P6",         # Store character in result",
            "    INC P1",              # Next source character",
            "    INC P4",              # Next result position",
            "    INC P5",              # Increment counter",
            "    JMP mid_loop",
            "mid_done:",
            "    MOV [P4],0",          # Null terminate result",
            "    RET",
            "",
            "; TRIM(string) - remove leading and trailing whitespace (space and tab only for simplicity)",
            "trim_string:",
            "    ; P0 = result buffer, P1 = source string",
            "    ; Find start of non-whitespace characters",
            "    MOV P2,P1",           # P2 = source pointer for finding start",
            "trim_find_start:",
            "    MOV P3,[P2]",         # Load character",
            "    CMP P3,0",            # End of string?",
            "    JZ trim_empty",       # If empty string, return empty result",
            "    CMP P3,32",           # Space character?",
            "    JZ trim_skip_space_start",
            "    CMP P3,9",            # Tab character?",
            "    JZ trim_skip_space_start",
            "    JMP trim_found_start", # Found non-whitespace, start copying",
            "trim_skip_space_start:",
            "    INC P2",              # Skip whitespace character",
            "    JMP trim_find_start",
            "trim_found_start:",
            "    ; P2 now points to first non-whitespace character",
            "    ; Find end of non-whitespace characters (scan backwards from end)",
            "    MOV P3,P1",           # P3 = pointer to find string end",
            "trim_find_end:",
            "    MOV P4,[P3]",         # Load character to find end of string",
            "    CMP P4,0",            # End of string?",
            "    JZ trim_end_found",   # Found end, now scan backwards for non-whitespace",
            "    INC P3",              # Next character to find end of string",
            "    JMP trim_find_end",
            "trim_end_found:",
            "    DEC P3",              # P3 now points to last character (before null terminator)",
            "trim_scan_back:",
            "    CMP P3,P2",           # Reached start position? (all whitespace case handled above by trim_empty check above, but this is safe guard)", 
            "    JC trim_empty",       # If start > end, empty result (shouldn't happen with our earlier check, but safe guard)", 
            "    MOV P4,[P3]",         # Load character from end", 
            "    CMP P4,32",           # Space?",
            "    JZ trim_skip_space_end", 
            "    CMP P4,9",            # Tab?",
            "    JZ trim_skip_space_end", 
            "    JMP trim_copy",       # Found last non-whitespace, start copying", 
            "trim_skip_space_end:",
            "    DEC P3",              # Move back one character", 
            "    JMP trim_scan_back", 
            "trim_copy:",
            "    ; Copy from P2 to P3 (inclusive) to result buffer P0", 
            "    MOV P4,P0",           # P4 = result pointer", 
            "trim_copy_loop:",
            "    CMP P2,P3",           # Past end position?", 
            "    JNC trim_copy_done",   # Yes, done copying", 
            "    MOV P5,[P2]",         # Load character from source", 
            "    MOV [P4],P5",         # Store in result", 
            "    INC P2",              # Next source character", 
            "    INC P4",              # Next result position", 
            "    JMP trim_copy_loop", 
            "trim_copy_done:",
            "    MOV [P4],0",          # Null terminate result", 
            "    RET", 
            "trim_empty:",
            "    MOV [P0],0",          # Return empty string", 
            "    RET", 
            "", 
            "; REPLACE(string, old_substr, new_substr) - replace all occurrences of old_substr with new_substr", 
            "replace_string:",
            "    ; P0 = result buffer, P1 = source string, P2 = old substring, P3 = new substring", 
            "    MOV P4,P0",           # P4 = result pointer", 
            "    MOV P5,P1",           # P5 = source pointer", 
            "    MOV P6,P2",           # P6 = old substring pointer", 
            "    MOV P7,P3",           # P7 = new substring pointer", 
            "    ", 
            "    ; Get lengths of old and new substrings", 
            "    MOV P8,P6",           # P8 = old substring for length", 
            "    MOV P9,0",            # P9 = old substring length", 
            "replace_old_len_loop:",
            "    MOV R0,[P8]", 
            "    CMP R0,0", 
            "    JZ replace_old_len_done", 
            "    INC P8", 
            "    INC P9", 
            "    JMP replace_old_len_loop", 
            "replace_old_len_done:",
            "    ", 
            "    MOV P8,P7",           # P8 = new substring for length", 
            "    MOV R0,0",            # R0 = new substring length", 
            "replace_new_len_loop:",
            "    MOV R1,[P8]", 
            "    CMP R1,0", 
            "    JZ replace_new_len_done", 
            "    INC P8", 
            "    INC R0", 
            "    JMP replace_new_len_loop", 
            "replace_new_len_done:",
            "    MOV P8,R0",           # P8 = new substring length", 
            "    ", 
            "replace_main_loop:",
            "    MOV R0,[P5]",         # Load character from source", 
            "    CMP R0,0",            # End of string?", 
            "    JZ replace_done",     # Yes, done", 
            "    ", 
            "    ; Check if old substring matches at current position", 
            "    MOV R1,P5",           # R1 = current source position", 
            "    MOV R2,P6",           # R2 = old substring pointer", 
            "    MOV R3,0",            # R3 = match counter", 
            "replace_check_match:",
            "    MOV R4,[R1]",         # Load source char", 
            "    MOV R5,[R2]",         # Load old substring char", 
            "    CMP R4,R5",           # Do they match?", 
            "    JNZ replace_no_match", # No match", 
            "    CMP R5,0",            # End of old substring?", 
            "    JZ replace_match_found", # Match found!", 
            "    INC R1",              # Next source char", 
            "    INC R2",              # Next old substring char", 
            "    INC R3",              # Increment match counter", 
            "    CMP R3,P9",           # Checked all chars?", 
            "    JNZ replace_check_match", 
            "    JMP replace_match_found", 
            "    ", 
            "replace_no_match:",
            "    ; No match, copy current character", 
            "    MOV [P4],R0", 
            "    INC P5", 
            "    INC P4", 
            "    JMP replace_main_loop", 
            "    ", 
            "replace_match_found:",
            "    ; Match found, copy new substring", 
            "    MOV R1,P7",           # R1 = new substring pointer", 
            "replace_copy_new:",
            "    MOV R2,[R1]", 
            "    CMP R2,0", 
            "    JZ replace_skip_old", 
            "    MOV [P4],R2", 
            "    INC P4", 
            "    INC R1", 
            "    JMP replace_copy_new", 
            "    ", 
            "replace_skip_old:",
            "    ; Skip the old substring in source", 
            "    ADD P5,P9", 
            "    JMP replace_main_loop", 
            "    ", 
            "replace_done:",
            "    MOV [P4],0",          # Null terminate result", 
            "    RET", 
            "", 
            "; SPLIT(string, delimiter) - split string by delimiter, store parts in array", 
            "split_string:",
            "    ; P0 = array base address, P1 = source string, P2 = delimiter", 
            "    ; This is a simplified implementation - splits on single character delimiter only", 
            "    ; Returns array with parts, first element is count, then string addresses", 
            "    MOV P3,P0",           # P3 = array pointer (skip count slot for now)", 
            "    ADD P3,2",            # Start after count position", 
            "    MOV P4,P1",           # P4 = current position in source", 
            "    MOV P5,0",            # P5 = part counter", 
            "split_loop:",
            "    MOV P6,[P4]",         # Load character from source", 
            "    CMP P6,0",            # End of string?", 
            "    JZ split_done",       # Yes, add final part", 
            "    MOV P7,[P2]",         # Load first delimiter character", 
            "    CMP P6,P7",           # Is it the delimiter?", 
            "    JNZ split_continue",  # No, continue", 
            "    ; Found delimiter, store current part", 
            "    MOV [P3],P4",         # Store address of next part start", 
            "    ADD P3,2",            # Next array slot", 
            "    INC P5",              # Increment part count", 
            "    INC P4",              # Skip delimiter", 
            "    JMP split_loop",      # Continue", 
            "split_continue:",
            "    INC P4",              # Next character", 
            "    JMP split_loop", 
            "split_done:",
            "    ; Store final part (empty string after last delimiter)", 
            "    MOV [P3],P4",         # Store address of final part (end of string)", 
            "    ADD P3,2",            # Next array slot", 
            "    INC P5",              # Increment part count", 
            "    ; Store count at array start", 
            "    MOV [P0],P5",         # Store part count", 
            "    RET", 
            "", 
            "; JOIN(array_base, delimiter, count) - join array elements with delimiter", 
            "join_array:",
            "    ; P0 = result buffer, P1 = array base, P2 = delimiter, P3 = element count", 
            "    MOV P4,P0",           # P4 = result pointer", 
            "    MOV P5,P1",           # P5 = array pointer", 
            "    ADD P5,2",            # Skip count, start with first element", 
            "    MOV P6,0",            # P6 = current element index", 
            "join_loop:",
            "    CMP P6,P3",           # Processed all elements?", 
            "    JZ join_done",        # Yes, done", 
            "    ; Copy current element string", 
            "    MOV P7,[P5]",         # P7 = address of current element string", 
            "join_copy_element:",
            "    MOV P8,[P7]",         # Load character from element", 
            "    CMP P8,0",            # End of element string?", 
            "    JZ join_next_element", # Yes, add delimiter if not last", 
            "    MOV [P4],P8",         # Copy character to result", 
            "    INC P7",              # Next element character", 
            "    INC P4",              # Next result position", 
            "    JMP join_copy_element", 
            "join_next_element:",
            "    INC P6",              # Next element index", 
            "    CMP P6,P3",           # Was this the last element?", 
            "    JZ join_done",        # Yes, don't add delimiter", 
            "    ; Add delimiter", 
            "    MOV P7,P2",           # P7 = delimiter string", 
            "join_copy_delim:",
            "    MOV P8,[P7]",         # Load delimiter character", 
            "    CMP P8,0",            # End of delimiter?", 
            "    JZ join_delim_done",  # Yes, done with delimiter", 
            "    MOV [P4],P8",         # Copy delimiter character", 
            "    INC P7",              # Next delimiter character", 
            "    INC P4",              # Next result position", 
            "    JMP join_copy_delim", 
            "join_delim_done:",
            "    ADD P5,2",            # Next array element", 
            "    JMP join_loop", 
            "join_done:",
            "    MOV [P4],0",          # Null terminate result", 
            "    RET", 
            "", 
            "; INSTR(haystack, needle) - find position of needle in haystack (1-based, 0 if not found)", 
            "instr_substr:",
            "    ; P1 = haystack, P2 = needle, returns position in P0 (1-based, 0 if not found)", 
            "    MOV P0,0",            # P0 = position counter (1-based)", 
            "    MOV P3,P1",           # P3 = haystack pointer", 
            "instr_loop:",
            "    MOV P4,[P3]",         # Load haystack character", 
            "    CMP P4,0",            # End of haystack?", 
            "    JZ instr_not_found",  # Yes, not found", 
            "    ; Check if needle matches at current position", 
            "    MOV P5,P3",           # P5 = current haystack position", 
            "    MOV P6,P2",           # P6 = needle pointer", 
            "    MOV P7,1",            # P7 = match flag (assume match)", 
            "instr_check_match:",
            "    MOV P8,[P6]",         # Load needle character", 
            "    CMP P8,0",            # End of needle?", 
            "    JZ instr_found",      # Yes, match found!", 
            "    MOV P9,[P5]",         # Load haystack character", 
            "    CMP P8,P9",           # Do they match?", 
            "    JNZ instr_no_match",  # No match", 
            "    INC P5",              # Next haystack position", 
            "    INC P6",              # Next needle position", 
            "    JMP instr_check_match", 
            "instr_no_match:",
            "    INC P0",              # Increment position", 
            "    INC P3",              # Next haystack position", 
            "    JMP instr_loop", 
            "instr_found:",
            "    INC P0",              # Make position 1-based", 
            "    RET", 
            "instr_not_found:",
            "    MOV P0,0",            # Return 0 (not found)", 
            "    RET", 
        ])

    def _compile_clrhome(self) -> List[str]:
        """Compile ClrHome statement"""
        return [
            "    ; ClrHome - clear screen (optimized)",
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

        # If we're in a SELECT CASE case body, add jump to end after the DISP
        if self.select_stack and self.select_stack[-1]['in_case_body']:
            select_info = self.select_stack[-1]
            end_label = select_info['end_label']
            lines.append(f"    JMP {end_label}")

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
            
            # Push to loop stack for BREAK/CONTINUE
            self.loop_stack.append({
                'start': loop_label,
                'end': end_label,
                'type': 'for',
                'var': var_name
            })

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
        """Compile If statement with ELSE/ELSEIF support"""
        # Check if this IF has ELSE/ELSEIF by scanning ahead
        has_else = self._if_has_else(tokens, i)
        
        if not has_else:
            # Simple IF without ELSE - use original approach
            lines = []
            i += 1  # Skip IF

            # Parse condition
            condition_lines, i = self._parse_condition(tokens, i)

            # Skip THEN if present
            if i < len(tokens) and tokens[i].upper() == "THEN":
                i += 1

            # Generate labels
            end_label = self._generate_label("if_end")

            lines.extend(condition_lines)
            lines.append(f"    JZ {end_label}")

            # Skip to END IF without parsing body
            while i < len(tokens):
                token = tokens[i].upper()
                if token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "IF":
                    i += 2  # Skip END IF
                    break
                i += 1

            lines.append(f"{end_label}:")

            return lines, i
        else:
            # IF with ELSE/ELSEIF - use new parsing
            return self._compile_if_with_else(tokens, i)

    def _if_has_else(self, tokens: List[str], start_i: int) -> bool:
        """Check if IF statement has ELSE or ELSEIF"""
        i = start_i + 1  # Skip IF
        nesting = 0
        
        while i < len(tokens):
            token = tokens[i].upper()
            if token == "IF":
                nesting += 1
            elif token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "IF":
                if nesting == 0:
                    return False  # Found END IF without ELSE
                nesting -= 1
                i += 1  # Skip the IF part
            elif (token == "ELSE" or token == "ELSEIF") and nesting == 0:
                return True
            i += 1
        
        return False

    def _compile_if_with_else(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile IF statement with ELSE/ELSEIF support"""
        lines = []
        i += 1  # Skip IF

        # Parse condition
        condition_lines, i = self._parse_condition(tokens, i)

        # Skip THEN if present
        if i < len(tokens) and tokens[i].upper() == "THEN":
            i += 1

        # Generate labels
        else_label = self._generate_label("if_else")
        end_label = self._generate_label("if_end")

        lines.extend(condition_lines)
        lines.append(f"    JZ {else_label}")

        # Collect all tokens until END IF, handling nested structures
        if_body_tokens = []
        nesting_level = 0
        while i < len(tokens):
            token = tokens[i].upper()
            if token in ["IF", "FOR", "WHILE", "DEFINE", "SELECT"]:
                nesting_level += 1
                if_body_tokens.append(tokens[i])
            elif token == "END" and i + 1 < len(tokens):
                next_token = tokens[i + 1].upper()
                if next_token in ["IF", "FOR", "WHILE", "DEFINE", "SELECT"]:
                    if nesting_level == 0:
                        # Found our END IF
                        i += 2  # Skip END IF
                        break
                    else:
                        nesting_level -= 1
                        if_body_tokens.append(tokens[i])
                        if_body_tokens.append(tokens[i + 1])
                        i += 2
                        continue
                else:
                    if_body_tokens.append(tokens[i])
            elif token in ["NEXT", "WEND", "RETURN", "CASEELSE"]:
                # These close nested structures
                if_body_tokens.append(tokens[i])
                if nesting_level > 0:
                    nesting_level -= 1
            elif token == "CASE":
                # CASE doesn't start nesting but can be in SELECT
                if_body_tokens.append(tokens[i])
            else:
                if_body_tokens.append(tokens[i])
            i += 1

        # Parse the IF body tokens
        if if_body_tokens:
            body_lines = self._parse_token_block(if_body_tokens, else_label, end_label)
            lines.extend(body_lines)

        lines.append(f"{else_label}:")
        lines.append(f"{end_label}:")

        return lines, i

    def _is_function_name(self, name: str) -> bool:
        """Check if a name is a known function"""
        known_functions = {
            'INT', 'STR', 'MIN', 'MAX', 'RND', 'LOWER', 'UPPER', 'LEN', 'LEFT', 'RIGHT', 'MID', 'INSTR',
            'TRIM', 'REPLACE', 'SPLIT', 'JOIN',
            'MEMSET', 'MEMTEST', 'MEMMOVE', 'STRCMP', 'STRCPY', 'MEMSWAP', 'KEYIN', 'KEYSTAT',
            'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN', 'SQRT', 'LOG', 'EXP', 'ABS', 'FLOOR', 'CEIL', 'ROUND',
            'COLOR', 'RAMP', 'SHADE', 'POW'
        }
        return name.upper() in known_functions

    def _compile_try(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile TRY/CATCH block with error flag mechanism"""
        lines = []
        i += 1  # Skip TRY

        # Generate labels
        catch_label = self._generate_label("catch")
        end_label = self._generate_label("try_end")

        # Use a simple error flag mechanism
        # We'll use a dedicated error flag register/variable
        error_flag_addr = 0xFFF0  # Use a fixed address for error flag

        lines.extend([
            f"    ; TRY block start",
            f"    MOV [0x{error_flag_addr:04X}],0",  # Clear error flag
        ])

        # Parse TRY block until CATCH or END TRY
        try_tokens = []
        catch_found = False
        try_end_found = False

        while i < len(tokens):
            token = tokens[i].upper()
            if token == "CATCH":
                catch_found = True
                break
            elif token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "TRY":
                try_end_found = True
                i += 2  # Skip END TRY
                break
            try_tokens.append(tokens[i])
            i += 1

        # Parse TRY block
        if try_tokens:
            try_lines = self._parse_token_block(try_tokens, "", "")
            lines.extend(try_lines)

        # Check error flag after TRY block
        lines.extend([
            f"    ; Check error flag after TRY block",
            f"    MOV P0,[0x{error_flag_addr:04X}]",
            f"    CMP P0,0",
            f"    JNZ {catch_label}",  # Jump to CATCH if error occurred
            f"    JMP {end_label}",    # Skip CATCH if no error
        ])

        # Parse CATCH block if present
        if catch_found:
            lines.append(f"{catch_label}:")
            i += 1  # Skip CATCH

            # Parse optional error variable
            error_var = None
            if i < len(tokens) and tokens[i].isalpha():
                error_var = tokens[i]
                i += 1

            # Parse CATCH block until END TRY
            catch_tokens = []
            while i < len(tokens):
                token = tokens[i].upper()
                if token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "TRY":
                    i += 2  # Skip END TRY
                    break
                catch_tokens.append(tokens[i])
                i += 1

            # Parse CATCH block
            if catch_tokens:
                # If error variable specified, load error code into it
                if error_var:
                    var_addr = self._get_variable_address(error_var)
                    catch_lines = [
                        f"    ; Load error code into {error_var}",
                        f"    MOV P0,[0x{error_flag_addr:04X}]",
                        f"    MOV [0x{var_addr:04X}],P0",
                    ]
                else:
                    catch_lines = []

                # Parse the catch block
                catch_body_lines = self._parse_token_block(catch_tokens, "", "")
                catch_lines.extend(catch_body_lines)
                lines.extend(catch_lines)

        lines.extend([
            f"{end_label}:",
            f"    ; TRY/CATCH block end",
        ])

        return lines, i

    def _parse_token_block(self, tokens: List[str], else_label: str, end_label: str) -> List[str]:
        """Parse a block of tokens, handling ELSE/ELSEIF within IF"""
        lines = []
        i = 0
        while i < len(tokens):
            token = tokens[i].upper()

            # Check for ELSE/ELSEIF
            if token == "ELSEIF":
                # Jump to end after previous block
                lines.append(f"    JMP {end_label}")
                lines.append(f"{else_label}:")

                i += 1  # Skip ELSEIF
                # Parse ELSEIF condition
                condition_lines, i = self._parse_condition(tokens, i)

                # Skip THEN if present
                if i < len(tokens) and tokens[i].upper() == "THEN":
                    i += 1

                # Generate new else label
                else_label = self._generate_label("if_else")
                lines.extend(condition_lines)
                lines.append(f"    JZ {else_label}")

            elif token == "ELSE":
                # Jump to end after previous block
                lines.append(f"    JMP {end_label}")
                lines.append(f"{else_label}:")
                else_label = end_label  # No more alternatives
                i += 1

            else:
                # Parse regular statement
                if self._is_statement_start_in_block(tokens, i):
                    statement_lines, new_i = self._parse_statement_in_block(tokens, i)
                    lines.extend(statement_lines)
                    i = new_i
                else:
                    i += 1

        return lines

    def _is_statement_start_in_block(self, tokens: List[str], i: int) -> bool:
        """Check if current position is start of a statement in a block"""
        if i >= len(tokens):
            return False
        token = tokens[i].upper()
        return token in [
            "CLRHOME", "DISP", "FOR", "IF", "INPUT", "PROMPT", "WHILE", "WEND",
            "PAUSE", "END", "GOTO", "LBL", "DEFINE", "STRUCT", "LINE", "FILL", "PXLON",
            "PXLOFF", "PXLCHANGE", "PTON", "PTOFF", "PTCHANGE", "PLAY", "STOP",
            "SOUND", "DIM", "MATRIX", "CALL", "RETURN", "NEXT", "SELECT", "CASE",
            "CASEELSE"
        ]

    def _parse_statement_in_block(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse a single statement in a block"""
        token = tokens[i].upper()

        # Use the same compilation methods as the main parser
        if token == "CLRHOME":
            lines = self._compile_clrhome()
            return lines, i + 1

        elif token == "DISP":
            return self._compile_disp(tokens, i)

        elif token == "FOR":
            return self._compile_for(tokens, i)

        elif token == "IF":
            return self._compile_if(tokens, i)

        elif token == "TRY":
            return self._compile_try(tokens, i)

        elif token == "INPUT":
            return self._compile_input(tokens, i)

        elif token == "PROMPT":
            return self._compile_prompt(tokens, i)

        elif token == "WHILE":
            return self._compile_while(tokens, i)

        elif token == "WEND":
            lines = self._compile_wend()
            return lines, i + 1

        elif token == "PAUSE":
            lines = self._compile_pause()
            return lines, i + 1

        elif token == "END":
            lines = self._compile_end()
            return lines, i + 1

        elif token == "GOTO":
            return self._compile_goto(tokens, i)

        elif token == "LBL":
            return self._compile_lbl(tokens, i)

        elif token == "DEFINE":
            return self._compile_define(tokens, i)

        elif token == "STRUCT":
            return self._compile_struct(tokens, i)

        elif token == "LINE":
            return self._compile_line(tokens, i)

        elif token == "FILL":
            return self._compile_fill(tokens, i)

        elif token == "RECT":
            return self._compile_rect(tokens, i)

        elif token == "PXLON":
            return self._compile_pxlon(tokens, i)

        elif token == "PXLOFF":
            return self._compile_pxloff(tokens, i)

        elif token == "PXLCHANGE":
            return self._compile_pxlchange(tokens, i)

        elif token == "PTON":
            return self._compile_pton(tokens, i)

        elif token == "PTOFF":
            return self._compile_pttoff(tokens, i)

        elif token == "PTCHANGE":
            return self._compile_ptchange(tokens, i)

        elif token == "PLAY":
            return self._compile_play(tokens, i)

        elif token == "STOP":
            return self._compile_stop(tokens, i)

        elif token == "SPLAY":
            return self._compile_splay(tokens, i)

        elif token == "SOUND":
            return self._compile_sound(tokens, i)

        elif token == "DIM":
            return self._compile_dim(tokens, i)

        elif token == "MATRIX":
            return self._compile_matrix(tokens, i)

        elif token == "CALL":
            return self._compile_call(tokens, i)

        elif token == "RETURN":
            lines = self._compile_return()
            return lines, i + 1

        elif token == "NEXT":
            return self._compile_next(tokens, i)

        elif token == "SELECT":
            return self._compile_select(tokens, i)

        elif token == "CASE":
            return self._compile_case(tokens, i)

        elif token == "CASEELSE":
            return self._compile_case_else(tokens, i)

        elif token == "BREAK":
            lines = self._compile_break()
            return lines, i + 1

        elif token == "CONTINUE":
            lines = self._compile_continue()
            return lines, i + 1

        else:
            # Unknown statement, skip it
            return [], i + 1

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
        
        # Push to loop stack for BREAK/CONTINUE
        self.loop_stack.append({
            'start': loop_label,
            'end': end_label,
            'type': 'while'
        })

        return lines, i

    def _compile_wend(self) -> List[str]:
        """Compile WEnd statement"""
        end_label = self.labels.get("current_while_end", "while_end")
        loop_label = self.labels.get("current_while_loop", "while_loop")

        lines = [
            f"    JMP {loop_label}",
            f"{end_label}:",
        ]
        
        # Pop from loop stack if this is a WHILE loop
        if self.loop_stack and self.loop_stack[-1]['type'] == 'while':
            self.loop_stack.pop()

        return lines

    def _compile_assignment(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile variable, list, array, or struct field assignment with optimizations"""
        target_name = tokens[i]
        i += 1  # Skip target name
        
        # Check if this is a struct field assignment (instance.field = ...)
        is_struct_field_assignment = False
        instance_name = ""
        field_name = ""
        
        if tokens[i] == '.':
            # Struct field assignment like player.x = 10
            is_struct_field_assignment = True
            instance_name = target_name.upper()
            i += 1  # Skip '.'
            
            if i >= len(tokens):
                raise ValueError("Expected field name after '.'")
            
            field_name = tokens[i].upper()
            i += 1
            
        # Check if this is a list assignment (L1(index) = ...)
        is_list_assignment = False
        is_array_assignment = False
        list_name = ""
        array_name = ""
        index_tokens = []
        
        if tokens[i] == '(':
            # This could be a list assignment
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
        elif tokens[i] == '[':
            # This is an array assignment
            is_array_assignment = True
            array_name = target_name.upper()
            i += 1  # Skip '['
            
            # Collect index tokens until ']'
            bracket_count = 1
            while i < len(tokens) and bracket_count > 0:
                if tokens[i] == '[':
                    bracket_count += 1
                elif tokens[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        break
                index_tokens.append(tokens[i])
                i += 1
            i += 1  # Skip ']'
        
        if tokens[i] != '=':
            raise ValueError("Expected '=' in assignment")
        i += 1  # Skip '='

        lines = [f"    ; {target_name} = "]
        
        # Parse the value expression
        expr_lines, i = self._parse_expression(tokens, i)
        lines.extend(expr_lines)
        
        if is_list_assignment:
            # Parse complex index expressions for lists
            index_lines, remaining_tokens = self._parse_tokens_for_expression(index_tokens)
            lines.extend(index_lines)
            
            list_addr = self._get_list_address(list_name)
            index_reg = self._get_current_register()
            value_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
            
            lines.extend([
                f"    ; Store to {list_name}[{index_reg}]",
                f"    LEA P2,[{list_addr} + {index_reg}*2]",  # Calculate address with LEA
                f"    MOV [P2],{value_reg}",  # Store value
            ])
            
            # Free the index register
            self._free_register(index_reg)
        elif is_array_assignment:
            # Array assignment: parse index expression
            index_lines, remaining_tokens = self._parse_tokens_for_expression(index_tokens)
            lines.extend(index_lines)
            
            # Get array address
            if array_name in self.arrays:
                array_addr = self.arrays[array_name]['address']
                array_info = self.arrays[array_name]
            else:
                # Fallback to variable address for compatibility
                array_addr = self._get_variable_address(array_name)
                array_info = None
            
            index_reg = self._get_current_register()  # Top of stack is the index result
            value_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()  # Previous is the value result
            
            lines.append(f"    ; Store to {array_name}[{index_reg}]")
            
            # Add bounds checking if we have array info
            if array_info and 'size_addr' in array_info:
                size_addr = array_info['size_addr']
                bounds_check_label = self._generate_label("bounds_ok")
                lines.extend([
                    f"    ; Bounds check: 0 <= {index_reg} < [{size_addr}]",
                    f"    MOV P3,[0x{size_addr:04X}]",  # Load size into P3
                    f"    CMP {index_reg},P3",
                    f"    JC {bounds_check_label}",  # Jump if index < size (unsigned)
                    f"    ; Bounds check failed - index out of range",
                    f"    ; For now, continue execution (TODO: proper error handling)",
                    f"{bounds_check_label}:",
                ])
            
            lines.extend([
                f"    LEA P2,[0x{array_addr:04X} + {index_reg}*2]",  # Calculate address with LEA
                f"    MOV [P2],{value_reg}",  # Store value
            ])
            
            # Free the index register
            self._free_register(index_reg)
        elif is_struct_field_assignment:
            # Struct field assignment: instance.field = value
            # Verify instance exists
            if instance_name not in self.struct_instances:
                raise ValueError(f"Undefined struct instance '{instance_name}'")
            
            instance_info = self.struct_instances[instance_name]
            struct_name = instance_info['struct_name']
            instance_addr = instance_info['address']
            
            # Verify struct and field exist
            if struct_name not in self.structs:
                raise ValueError(f"Struct definition for '{struct_name}' not found")
            
            struct_info = self.structs[struct_name]
            if field_name not in struct_info['fields']:
                raise ValueError(f"Field '{field_name}' not found in struct '{struct_name}'")
            
            field_offset = struct_info['fields'][field_name]['offset']
            field_addr = instance_addr + field_offset
            
            # Get the value register
            value_reg = self._get_current_register()
            
            lines.extend([
                f"    ; Store to {instance_name}.{field_name}",
                f"    MOV [0x{field_addr:04X}],{value_reg}",
            ])
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
        lines, i = self._parse_bitwise_expression(tokens, i)

        while i < len(tokens) and tokens[i] in ['+', '-']:
            op = tokens[i]
            i += 1

            # Save current result register
            left_reg = self._get_current_register()
            
            # Parse right operand
            right_lines, i = self._parse_bitwise_expression(tokens, i)
            lines.extend(right_lines)
            right_reg = self._get_current_register()

            # Check if right operand is a constant for algebraic simplification
            right_is_constant = len(right_lines) == 1 and right_lines[0].startswith(f"    MOV {right_reg},")
            if right_is_constant:
                constant_val = right_lines[0].split(',')[1].strip()
                # Apply algebraic simplification
                simplified_lines = self._apply_algebraic_simplification(left_reg, op, constant_val)
                if simplified_lines:
                    lines[-1:] = simplified_lines  # Replace the MOV with simplified operations
                else:
                    # No simplification needed, but we still need to handle the operation
                    if op == '+':
                        lines.append(f"    ADD {left_reg},{right_reg}")
                    elif op == '-':
                        lines.append(f"    SUB {left_reg},{right_reg}")
            else:
                # Right operand is not a constant, perform normal operation
                if op == '+':
                    lines.append(f"    ADD {left_reg},{right_reg}")
                elif op == '-':
                    lines.append(f"    SUB {left_reg},{right_reg}")

            # Free the right register
            self._free_register(right_reg)

        return lines, i

    def _parse_bitwise_expression(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Parse bitwise expressions (AND, OR, XOR, SHL, SHR)"""
        lines, i = self._parse_multiplicative_expression(tokens, i)

        while i < len(tokens) and tokens[i] in ['AND', 'OR', 'XOR', 'SHL', 'SHR']:
            op = tokens[i]
            i += 1

            # Save current result register
            left_reg = self._get_current_register()
            
            # Parse right operand
            right_lines, i = self._parse_multiplicative_expression(tokens, i)
            lines.extend(right_lines)
            right_reg = self._get_current_register()

            # Perform bitwise operation
            if op == 'AND':
                lines.append(f"    AND {left_reg},{right_reg}")
            elif op == 'OR':
                lines.append(f"    OR {left_reg},{right_reg}")
            elif op == 'XOR':
                lines.append(f"    XOR {left_reg},{right_reg}")
            elif op == 'SHL':

                lines.append(f"    SHL {left_reg},{right_reg}")
            elif op == 'SHR':
                lines.append(f"    SHR {left_reg},{right_reg}")

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

            # Check if right operand is a constant for algebraic simplification
            right_is_constant = len(right_lines) == 1 and right_lines[0].startswith(f"    MOV {right_reg},")
            if right_is_constant:
                constant_val = right_lines[0].split(',')[1].strip()
                # Apply algebraic simplification
                simplified_lines = self._apply_algebraic_simplification(left_reg, op, constant_val)
                if simplified_lines:
                    lines[-1:] = simplified_lines  # Replace the MOV with simplified operations
                else:
                    # No simplification needed, but we still need to handle the operation
                    if op == '*':
                        lines.append(f"    MUL {left_reg},{right_reg}")
                    elif op == '/':
                        lines.append(f"    DIV {left_reg},{right_reg}")
                    else:  # op == 'MOD'
                        lines.append(f"    MOD {left_reg},{right_reg}")
            else:
                # Right operand is not a constant, perform normal operation
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
        elif token == 'NOT':
            # Bitwise NOT unary operator
            i += 1
            # Parse the operand
            operand_lines, i = self._parse_primary_expression(tokens, i)
            lines.extend(operand_lines)
            operand_reg = self._get_current_register()
            # Apply NOT operation
            lines.append(f"    NOT {operand_reg}")
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
            
            # Allocate array storage dynamically
            if array_elements:
                result_reg = self._allocate_register()
                # Calculate array size: number of elements * 2 bytes per element + 2 bytes for count
                array_size = len(array_elements) * 2 + 2
                array_base = self.array_allocation_ptr
                
                # Store array size at the beginning
                lines.extend([
                    f"    ; Allocate array of {len(array_elements)} elements",
                    f"    MOV [0x{array_base:04X}],{len(array_elements)}",  # Store element count
                ])
                
                # Store array elements starting after the count
                element_addr = array_base + 2
                for idx, elem_reg in enumerate(array_elements):
                    lines.extend([
                        f"    ; Store array element {idx}",
                        f"    MOV [0x{element_addr + idx * 2:04X}],{elem_reg}",
                    ])
                    if idx > 0:  # Free all but the last register
                        self._free_register(elem_reg)
                
                # Return array base address
                lines.append(f"    MOV {result_reg},{array_base}")
                
                # Update allocation pointer
                self.array_allocation_ptr += array_size
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
        elif token.upper() in self.boolean_constants:
            # Boolean constant
            bool_value = self.boolean_constants[token.upper()]
            result_reg = self._allocate_register()
            lines.append(f"    MOV {result_reg},{bool_value}")
            i += 1
        elif (token.isalpha() or '_' in token or '$' in token or 
              (token and token[0].isalpha() and all(c.isalnum() or c in '_$' for c in token))) or \
             (token.upper().startswith('L') and len(token) == 2 and token[1].isdigit()):
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
                        f"    LEA {result_reg},[{list_addr} + {index_reg}*2]",  # Calculate address with LEA
                        f"    MOV {result_reg},[{result_reg}]",     # Load value
                    ])
                else:
                    # Regular variable
                    result_reg = self._allocate_register()
                    lines.extend(self._load_variable_to_reg(token, result_reg))
                    i += 1
            # Check if this is a struct field access (instance.field)
            elif i + 1 < len(tokens) and tokens[i + 1] == '.':
                # Struct field access like player.x or enemy.health
                instance_name = token.upper()
                i += 2  # Skip instance name and '.'
                
                if i >= len(tokens):
                    raise ValueError("Expected field name after '.'")
                
                field_name = tokens[i].upper()
                i += 1
                
                # Verify instance exists
                if instance_name not in self.struct_instances:
                    raise ValueError(f"Undefined struct instance '{instance_name}'")
                
                instance_info = self.struct_instances[instance_name]
                struct_name = instance_info['struct_name']
                instance_addr = instance_info['address']
                
                # Verify struct and field exist
                if struct_name not in self.structs:
                    raise ValueError(f"Struct definition for '{struct_name}' not found")
                
                struct_info = self.structs[struct_name]
                if field_name not in struct_info['fields']:
                    raise ValueError(f"Field '{field_name}' not found in struct '{struct_name}'")
                
                field_offset = struct_info['fields'][field_name]['offset']
                field_addr = instance_addr + field_offset
                
                # Load the field value
                result_reg = self._allocate_register()
                lines.extend([
                    f"    ; Load {instance_name}.{field_name} into {result_reg}",
                    f"    MOV {result_reg},[0x{field_addr:04X}]",
                ])
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
                # Use allocated array address
                if array_name in self.arrays:
                    array_addr = self.arrays[array_name]['address']
                    array_info = self.arrays[array_name]
                else:
                    # Fallback to variable address for compatibility
                    array_addr = self._get_variable_address(array_name)
                    array_info = None
                
                index_reg = self._get_current_register()  # Save index register
                result_reg = self._allocate_register()    # Allocate result register
                
                lines.extend([
                    f"    ; Load {array_name}[{index_reg}] into {result_reg}",
                ])
                
                # Add bounds checking if we have array info
                if array_info and 'size_addr' in array_info:
                    size_addr = array_info['size_addr']
                    bounds_check_label = self._generate_label("bounds_ok")
                    lines.extend([
                        f"    ; Bounds check: 0 <= {index_reg} < [{size_addr}]",
                        f"    MOV P3,[0x{size_addr:04X}]",  # Load size into P3
                        f"    CMP {index_reg},P3",
                        f"    JC {bounds_check_label}",  # Jump if index < size (unsigned)
                        f"    ; Bounds check failed - index out of range",
                        f"    ; For now, continue execution (TODO: proper error handling)",
                        f"{bounds_check_label}:",
                    ])
                
                lines.extend([
                    f"    LEA {result_reg},[0x{array_addr:04X} + {index_reg}*2]",  # Calculate address with LEA
                    f"    MOV {result_reg},[{result_reg}]",     # Load value
                ])
                
                # Free the index register
                self._free_register(index_reg)
            # Check if this is a general array access (array(index)) - for compatibility
            elif i + 1 < len(tokens) and tokens[i + 1] == '(' and not self._is_function_name(token):
                # Array access like Notes(I) - treat as array access if not a known function
                array_name = token
                i += 2  # Skip array name and '('
                
                # Parse index expression
                index_lines, i = self._parse_additive_expression(tokens, i)
                lines.extend(index_lines)
                
                if i < len(tokens) and tokens[i] == ')':
                    i += 1
                else:
                    raise ValueError("Missing closing parenthesis in array access")
                
                # Generate code to load from array
                # Use allocated array address
                if array_name in self.arrays:
                    array_addr = self.arrays[array_name]['address']
                    array_info = self.arrays[array_name]
                else:
                    # Fallback to variable address for compatibility
                    array_addr = self._get_variable_address(array_name)
                    array_info = None
                
                index_reg = self._get_current_register()  # Save index register
                result_reg = self._allocate_register()    # Allocate result register
                
                lines.extend([
                    f"    ; Load {array_name}({index_reg}) into {result_reg}",
                ])
                
                # Add bounds checking if we have array info
                if array_info and 'size_addr' in array_info:
                    size_addr = array_info['size_addr']
                    bounds_check_label = self._generate_label("bounds_ok")
                    lines.extend([
                        f"    ; Bounds check: 0 <= {index_reg} < [{size_addr}]",
                        f"    MOV P3,[0x{size_addr:04X}]",  # Load size into P3
                        f"    CMP {index_reg},P3",
                        f"    JC {bounds_check_label}",  # Jump if index < size (unsigned)
                        f"    ; Bounds check failed - index out of range",
                        f"    ; For now, continue execution (TODO: proper error handling)",
                        f"{bounds_check_label}:",
                    ])
                
                lines.extend([
                    f"    LEA {result_reg},[0x{array_addr:04X} + {index_reg}*2]",  # Calculate address with LEA
                    f"    MOV {result_reg},[{result_reg}]",     # Load value
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
                elif func_name == 'POW':
                    # POW(base, exponent) - power function
                    base_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(base_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in POW(base, exponent)")
                    
                    exp_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(exp_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in POW()")
                    
                    # Get the two argument registers
                    exp_reg = self._get_current_register()
                    base_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; POW({base_reg}, {exp_reg})",
                        f"    POWR {base_reg},{exp_reg}",  # Power instruction
                    ])
                    
                    # Free exp register, keep base as result
                    self._free_register(exp_reg)
                elif func_name == 'RND':
                    # RND() or RND(max) - random number
                    if i < len(tokens) and tokens[i] == ')':
                        # RND() - random number 0-255
                        i += 1
                        current_reg = self._allocate_register()
                        lines.append(f"    RND {current_reg}")
                    else:
                        # RND(max) - random number 0 to max-1
                        max_lines, i = self._parse_additive_expression(tokens, i)
                        lines.extend(max_lines)
                        if i < len(tokens) and tokens[i] == ')':
                            i += 1
                        else:
                            raise ValueError("Missing closing parenthesis in RND()")
                        
                        max_reg = self._get_current_register()
                        lines.extend([
                            f"    ; RND(0 to {max_reg}-1)",
                            f"    RNDR {max_reg},0,{max_reg}",  # Random in range 0 to max-1
                        ])
                elif func_name == 'LOWER':
                    # LOWER(string) - convert string to lowercase
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in LOWER()")
                    # Apply STRLWR to the string
                    current_reg = self._get_current_register()
                    lines.append(f"    STRLWR {current_reg}")
                elif func_name == 'UPPER':
                    # UPPER(string) - convert string to uppercase
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in UPPER()")
                    # Apply STRUPR to the string
                    current_reg = self._get_current_register()
                    lines.append(f"    STRUPR {current_reg}")
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
                elif func_name == 'MIN':
                    # MIN(a, b) - return minimum of two values
                    # Parse first argument
                    arg1_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(arg1_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MIN(a, b)")
                    
                    # Parse second argument
                    arg2_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(arg2_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MIN()")
                    
                    # Get the two argument registers
                    arg2_reg = self._get_current_register()
                    arg1_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MIN({arg1_reg}, {arg2_reg})",
                        f"    MIN {arg1_reg},{arg2_reg}",  # MIN result,arg1,arg2
                    ])
                    
                    # Free arg2 register, keep arg1 as result
                    self._free_register(arg2_reg)
                elif func_name == 'MAX':
                    # MAX(a, b) - return maximum of two values
                    # Parse first argument
                    arg1_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(arg1_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MAX(a, b)")
                    
                    # Parse second argument
                    arg2_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(arg2_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MAX()")
                    
                    # Get the two argument registers
                    arg2_reg = self._get_current_register()
                    arg1_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MAX({arg1_reg}, {arg2_reg})",
                        f"    MAX {arg1_reg},{arg2_reg}",  # MAX result,arg1,arg2
                    ])
                    
                    # Free arg2 register, keep arg1 as result
                    self._free_register(arg2_reg)
                elif func_name == 'KEYIN':
                    # KEYIN() - read key from keyboard buffer
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in KEYIN()")
                    
                    current_reg = self._allocate_register()
                    lines.extend([
                        f"    ; KEYIN()",
                        f"    KEYIN {current_reg}",  # Read key into register
                    ])
                elif func_name == 'KEYSTAT':
                    # KEYSTAT() - check if key is available
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in KEYSTAT()")
                    
                    current_reg = self._allocate_register()
                    lines.extend([
                        f"    ; KEYSTAT()",
                        f"    KEYSTAT {current_reg}",  # Check key status into register
                    ])
                elif func_name == 'LEN':
                    # LEN(string) - get string length using STRLEN
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in LEN()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; LEN({current_reg})",
                        f"    STRLEN {current_reg},{current_reg}",  # STRLEN result,string_addr
                    ])
                elif func_name == 'UPPER':
                    # UPPER(string) - convert string to uppercase using STRUPR
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in UPPER()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; UPPER({current_reg})",
                        f"    STRUPR {current_reg}",  # STRUPR string_addr
                    ])
                    # STRUPR modifies the string in place and returns the address
                elif func_name == 'LEFT':
                    # LEFT(string, count) - extract left count characters
                    # Parse string argument
                    str_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in LEFT(string, count)")
                    
                    # Parse count argument
                    count_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(count_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in LEFT()")
                    
                    # Get registers
                    count_reg = self._get_current_register()
                    str_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    # Allocate temp buffer for result
                    lines.extend([
                        f"    ; LEFT({str_reg}, {count_reg})",
                        f"    PUSH {str_reg}",       # Save string address
                        f"    PUSH {count_reg}",     # Save count
                        f"    MOV P0,0x6000",        # Temp buffer
                        f"    POP P2",               # P2 = count
                        f"    POP P1",               # P1 = string address
                        f"    CALL left_substr",
                        f"    MOV {str_reg},P0",     # Return temp buffer address
                    ])
                    
                    # Free count register, keep str_reg as result
                    self._free_register(count_reg)
                elif func_name == 'RIGHT':
                    # RIGHT(string, count) - extract right count characters
                    # Parse string argument
                    str_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in RIGHT(string, count)")
                    
                    # Parse count argument
                    count_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(count_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in RIGHT()")
                    
                    # Get registers
                    count_reg = self._get_current_register()
                    str_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    # Allocate temp buffer for result
                    lines.extend([
                        f"    ; RIGHT({str_reg}, {count_reg})",
                        f"    PUSH {str_reg}",       # Save string address
                        f"    PUSH {count_reg}",     # Save count
                        f"    MOV P0,0x6000",        # Temp buffer
                        f"    POP P2",               # P2 = count
                        f"    POP P1",               # P1 = string address
                        f"    CALL right_substr",
                        f"    MOV {str_reg},P0",     # Return temp buffer address
                    ])
                    
                    # Free count register, keep str_reg as result
                    self._free_register(count_reg)
                elif func_name == 'MID':
                    # MID(string, start, count) - extract substring starting at position start for count characters
                    # Parse string argument
                    str_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MID(string, start, count)")
                    
                    # Parse start argument
                    start_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(start_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MID(string, start, count)")
                    
                    # Parse count argument
                    count_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(count_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MID()")
                    
                    # Get registers
                    count_reg = self._get_current_register()
                    start_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    str_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    # Allocate temp buffer for result
                    lines.extend([
                        f"    ; MID({str_reg}, {start_reg}, {count_reg})",
                        f"    PUSH {str_reg}",       # Save string address
                        f"    PUSH {start_reg}",     # Save start position
                        f"    PUSH {count_reg}",     # Save count
                        f"    DEC {start_reg}",      # Convert 1-based to 0-based indexing
                        f"    MOV P0,0x6000",        # Temp buffer
                        f"    POP P3",               # P3 = count
                        f"    POP P2",               # P2 = start position (0-based)
                        f"    POP P1",               # P1 = string address
                        f"    CALL mid_substr",
                        f"    MOV {str_reg},P0",     # Return temp buffer address
                    ])
                    
                    # Free registers, keep str_reg as result
                    self._free_register(count_reg)
                    self._free_register(start_reg)
                elif func_name == 'INSTR':
                    # INSTR(haystack, needle) - find position of needle in haystack (1-based, 0 if not found)
                    # Parse haystack argument
                    haystack_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(haystack_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in INSTR(haystack, needle)")
                    
                    # Parse needle argument
                    needle_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(needle_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in INSTR()")
                    
                    # Get registers
                    needle_reg = self._get_current_register()
                    haystack_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; INSTR({haystack_reg}, {needle_reg})",
                        f"    PUSH {haystack_reg}",  # Save haystack address
                        f"    PUSH {needle_reg}",    # Save needle address
                        f"    MOV P0,0x6000",        # Temp buffer (not used for INSTR)
                        f"    POP P2",               # P2 = needle address
                        f"    POP P1",               # P1 = haystack address
                        f"    CALL instr_substr",
                        f"    MOV {haystack_reg},P0", # Return position in haystack_reg
                    ])
                    
                    # Free needle register, keep haystack_reg as result
                    self._free_register(needle_reg)
                elif func_name == 'TRIM':
                    # TRIM(string) - remove leading and trailing whitespace
                    lines, i = self._parse_additive_expression(tokens, i)  # Parse string argument
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in TRIM()")
                    
                    current_reg = self._get_current_register()
                    lines.extend([
                        f"    ; TRIM({current_reg})",
                        f"    MOV P0,0x6000",        # Temp buffer
                        f"    MOV P1,{current_reg}", # Source string
                        f"    CALL trim_string",
                        f"    MOV {current_reg},P0", # Return trimmed string address
                    ])
                elif func_name == 'REPLACE':
                    # REPLACE(string, old_substr, new_substr) - replace all occurrences
                    # Parse string argument
                    str_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in REPLACE(string, old_substr, new_substr)")
                    
                    # Parse old_substr argument
                    old_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(old_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in REPLACE(string, old_substr, new_substr)")
                    
                    # Parse new_substr argument
                    new_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(new_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in REPLACE()")
                    
                    # Get registers
                    new_reg = self._get_current_register()
                    old_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    str_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; REPLACE({str_reg}, {old_reg}, {new_reg})",
                        f"    MOV P0,0x6000",        # Temp buffer
                        f"    MOV P1,{str_reg}",     # Source string
                        f"    MOV P2,{old_reg}",     # Old substring
                        f"    MOV P3,{new_reg}",     # New substring
                        f"    CALL replace_string",
                        f"    MOV {str_reg},P0",     # Return result string address
                    ])
                    
                    # Free registers, keep str_reg as result
                    self._free_register(new_reg)
                    self._free_register(old_reg)
                elif func_name == 'SPLIT':
                    # SPLIT(string, delimiter) - split string by delimiter, return array base address
                    # Parse string argument
                    str_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in SPLIT(string, delimiter)")
                    
                    # Parse delimiter argument
                    delim_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(delim_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in SPLIT()")
                    
                    # Get registers
                    delim_reg = self._get_current_register()
                    str_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; SPLIT({str_reg}, {delim_reg})",
                        f"    MOV P0,0x6100",        # Temp array storage area
                        f"    MOV P1,{str_reg}",     # Source string
                        f"    MOV P2,{delim_reg}",   # Delimiter
                        f"    CALL split_string",
                        f"    MOV {str_reg},P0",     # Return array base address
                    ])
                    
                    # Free delim register, keep str_reg as result
                    self._free_register(delim_reg)
                elif func_name == 'JOIN':
                    # JOIN(array_base, delimiter, count) - join array elements with delimiter
                    # Parse array_base argument
                    array_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(array_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in JOIN(array_base, delimiter, count)")
                    
                    # Parse delimiter argument
                    delim_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(delim_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in JOIN(array_base, delimiter, count)")
                    
                    # Parse count argument
                    count_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(count_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in JOIN()")
                    
                    # Get registers
                    count_reg = self._get_current_register()
                    delim_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    array_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; JOIN({array_reg}, {delim_reg}, {count_reg})",
                        f"    MOV P0,0x6000",        # Temp buffer for result
                        f"    MOV P1,{array_reg}",   # Array base
                        f"    MOV P2,{delim_reg}",   # Delimiter
                        f"    MOV P3,{count_reg}",   # Element count
                        f"    CALL join_array",
                        f"    MOV {array_reg},P0",   # Return joined string address
                    ])
                    
                    # Free registers, keep array_reg as result
                    self._free_register(count_reg)
                    self._free_register(delim_reg)
                elif func_name == 'MEMSET':
                    # MEMSET(address, value, length) - set memory block to value
                    # Parse address argument
                    addr_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(addr_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMSET(address, value, length)")
                    
                    # Parse value argument
                    value_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(value_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMSET(address, value, length)")
                    
                    # Parse length argument
                    length_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(length_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MEMSET()")
                    
                    # Get registers for the three arguments
                    length_reg = self._get_current_register()
                    value_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    addr_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MEMSET({addr_reg}, {value_reg}, {length_reg})",
                        f"    MEMSET {addr_reg},{value_reg},{length_reg}",
                        f"    MOV {addr_reg},0",  # Return 0 to indicate success
                    ])
                    
                    # Free registers we don't need
                    self._free_register(length_reg)
                    self._free_register(value_reg)
                    
                    # Keep addr_reg as result register (contains 0)
                elif func_name == 'MEMTEST':
                    # MEMTEST(addr1, addr2, length) - compare memory blocks, return 1 if equal, 0 if different
                    # Parse addr1 argument
                    addr1_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(addr1_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMTEST(addr1, addr2, length)")
                    
                    # Parse addr2 argument
                    addr2_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(addr2_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMTEST(addr1, addr2, length)")
                    
                    # Parse length argument
                    length_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(length_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MEMTEST()")
                    
                    # Get registers for the three arguments
                    length_reg = self._get_current_register()
                    addr2_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    addr1_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MEMTEST({addr1_reg}, {addr2_reg}, {length_reg})",
                        f"    MEMTEST {addr1_reg},{addr2_reg},{length_reg}",
                        f"    MOV {addr1_reg},0",      # Assume not equal
                        f"    JNZ memtest_done_{self.label_counter}",
                        f"    MOV {addr1_reg},1",      # Equal
                        f"memtest_done_{self.label_counter}:",
                    ])
                    
                    # Free registers we don't need
                    self._free_register(length_reg)
                    self._free_register(addr2_reg)
                    
                    # Keep addr1_reg as result register
                    self.label_counter += 1
                elif func_name == 'MEMMOVE':
                    # MEMMOVE(destination, source, length) - move memory block
                    # Parse destination argument
                    dest_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(dest_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMMOVE(destination, source, length)")
                    
                    # Parse source argument
                    src_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(src_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMMOVE(destination, source, length)")
                    
                    # Parse length argument
                    length_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(length_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MEMMOVE()")
                    
                    # Get registers for the three arguments
                    length_reg = self._get_current_register()
                    src_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    dest_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MEMMOVE({dest_reg}, {src_reg}, {length_reg})",
                        f"    MEMMOVE {dest_reg},{src_reg},{length_reg}",
                        f"    MOV {dest_reg},0",  # Return 0 to indicate success
                    ])
                    
                elif func_name == 'STRCMP':
                    # STRCMP(str1, str2) - compare two strings, return -1, 0, or 1
                    str1_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str1_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in STRCMP(str1, str2)")
                    
                    str2_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(str2_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in STRCMP()")
                    
                    # Get the two string registers
                    str2_reg = self._get_current_register()
                    str1_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; STRCMP({str1_reg}, {str2_reg})",
                        f"    MOV P1,{str1_reg}",        # String 1 address
                        f"    MOV P2,{str2_reg}",        # String 2 address
                        f"    MOV P3,255",               # Maximum length to compare
                        f"    MEMCMP P1,P2,P3",          # Compare strings
                        f"    MOV {str1_reg},P1",        # Result in str1_reg
                    ])
                    
                elif func_name == 'STRCPY':
                    # STRCPY(destination, source) - copy string
                    dest_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(dest_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in STRCPY(destination, source)")
                    
                    src_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(src_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in STRCPY()")
                    
                    # Get the two string registers
                    src_reg = self._get_current_register()
                    dest_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; STRCPY({dest_reg}, {src_reg})",
                        f"    MOV P1,{dest_reg}",  # Destination
                        f"    MOV P2,{src_reg}",   # Source
                        f"    MOV P3,255",         # Maximum length
                        f"    MEMCPY P1,P2,P3",    # Copy string
                        f"    MOV {dest_reg},P1",  # Return destination address
                    ])
                    
                    # Free source register, keep destination as result
                    self._free_register(src_reg)
                    
                elif func_name == 'MEMSWAP':
                    # MEMSWAP(addr1, addr2, length) - swap memory blocks
                    addr1_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(addr1_lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMSWAP(addr1, addr2, length)")
                    
                    addr2_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(addr2Lines)
                    if i < len(tokens) and tokens[i] == ',':
                        i += 1  # Skip comma
                    else:
                        raise ValueError("Expected comma in MEMSWAP(addr1, addr2, length)")
                    
                    length_lines, i = self._parse_additive_expression(tokens, i)
                    lines.extend(length_lines)
                    
                    if i < len(tokens) and tokens[i] == ')':
                        i += 1
                    else:
                        raise ValueError("Missing closing parenthesis in MEMSWAP()")
                    
                    # Get registers for the three arguments
                    length_reg = self._get_current_register()
                    addr2_reg = self.register_stack[-2] if len(self.register_stack) >= 2 else self._allocate_register()
                    addr1_reg = self.register_stack[-3] if len(self.register_stack) >= 3 else self._allocate_register()
                    
                    lines.extend([
                        f"    ; MEMSWAP({addr1_reg}, {addr2_reg}, {length_reg})",
                        f"    MEMSWAP {addr1_reg},{addr2_reg},{length_reg}",
                        f"    MOV {addr1_reg},0",  # Return 0 to indicate success
                    ])
                    
                    # Free registers we don't need
                    self._free_register(length_reg)
                    self._free_register(addr2_reg)
                    
                    # Keep addr1_reg as result register (contains 0)
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

    def _fold_constants(self, tokens: List[str], i: int) -> Tuple[Optional[int], int]:
        """Attempt to fold constants in expressions at compile time"""
        if i >= len(tokens):
            return None, i
        
        # Look for simple constant expressions: number op number
        if tokens[i].isdigit():
            left_val = int(tokens[i])
            i += 1
            
            # Check for binary operation
            if i < len(tokens) and tokens[i] in ['+', '-', '*', '/', 'MOD']:
                op = tokens[i]
                i += 1
                
                # Check for right operand
                if i < len(tokens) and tokens[i].isdigit():
                    right_val = int(tokens[i])
                    i += 1
                    
                    # Perform the operation
                    try:
                        if op == '+':
                            result = left_val + right_val
                        elif op == '-':
                            result = left_val - right_val
                        elif op == '*':
                            result = left_val * right_val
                        elif op == '/':
                            if right_val == 0:
                                return None, i - 2  # Division by zero, don't fold
                            result = left_val // right_val  # Integer division
                        elif op == 'MOD':
                            if right_val == 0:
                                return None, i - 2  # Modulo by zero, don't fold
                            result = left_val % right_val
                        else:
                            return None, i - 2
                        
                        return result, i
                    except (OverflowError, ZeroDivisionError):
                        return None, i - 2
        
        return None, i

    def _apply_algebraic_simplification(self, left_reg: str, op: str, right_reg: str) -> List[str]:
        """Apply algebraic simplifications to reduce instruction count"""
        lines = []
        
        # Multiplication by zero: x * 0 = 0
        if op == '*' and right_reg == '0':
            lines.append(f"    MOV {left_reg},0")
            return lines
        
        # Multiplication by one: x * 1 = x (no change needed)
        if op == '*' and right_reg == '1':
            return lines  # No operation needed
        
        # Addition with zero: x + 0 = x (no change needed)
        if op == '+' and right_reg == '0':
            return lines  # No operation needed
        
        # Subtraction of zero: x - 0 = x (no change needed)
        if op == '-' and right_reg == '0':
            return lines  # No operation needed
        
        # Division by one: x / 1 = x (no change needed)
        if op == '/' and right_reg == '1':
            return lines  # No operation needed
        
        # Default: perform the operation
        if op == '+':
            lines.append(f"    ADD {left_reg},{right_reg}")
        elif op == '-':
            lines.append(f"    SUB {left_reg},{right_reg}")
        elif op == '*':
            lines.append(f"    MUL {left_reg},{right_reg}")
        elif op == '/':
            lines.append(f"    DIV {left_reg},{right_reg}")
        elif op == 'MOD':
            lines.append(f"    MOD {left_reg},{right_reg}")

        return lines

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
        """Generate code to display a string - optimized for longer strings"""
        lines = []
        
        # For strings longer than 2 characters, use TEXT instruction for efficiency
        if len(string) > 2:
            # Store string in memory and use TEXT instruction
            string_addr = self._store_string_in_memory(string)
            lines.extend([
                f"    ; Display string '{string}' using TEXT",
                f"    MOV P0,0x{string_addr:04X}",  # String address
                "    MOV P1,15",                   # White color
                "    TEXT P0,P1",                  # Display entire string
            ])
            # TEXT automatically updates VX/VY, so update compiler cursor tracking
            text_width = len(string) * 8  # Assuming 8 pixels per character
            self.cursor_x = (self.cursor_x + text_width) % 256
        else:
            # For short strings, use individual CHAR instructions for efficiency
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
                    # Update compiler cursor tracking
                    self.cursor_y = (self.cursor_y + 8) % 256
                    self.cursor_x = 0
                else:
                    ascii_val = ord(char)
                    lines.extend([
                        f"    ; Display '{char}'",
                        f"    MOV P0,{ascii_val}",  # Character code
                        "    MOV P1,15",            # White color
                        "    CHAR P0,P1",          # Display character
                    ])
                    # Update compiler cursor tracking (CHAR advances VX by 8)
                    self.cursor_x = (self.cursor_x + 8) % 256
        
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
        if var_addr == -1:
            # This is a special register
            return [
                f"    ; Load {var_name} into {dest_register}",
                f"    MOV {dest_register},{var_name}",  # Direct register access
            ]
        else:
            return [
                f"    ; Load {var_name} into {dest_register}",
                f"    MOV {dest_register},[0x{var_addr:04X}]",  # Direct memory access
            ]

    def _load_variable_to_reg(self, var_name: str, dest_register: str) -> List[str]:
        """Generate code to load a variable into a specific register"""
        var_addr = self._get_variable_address(var_name)
        if var_addr == -1:
            # This is a special register
            return [
                f"    ; Load {var_name} into {dest_register}",
                f"    MOV {dest_register},{var_name}",  # Direct register access
            ]
        else:
            return [
                f"    ; Load {var_name} into {dest_register}",
                f"    MOV {dest_register},[0x{var_addr:04X}]",  # Direct memory access
            ]

    def _store_variable(self, var_name: str, source_register: str = "P0") -> List[str]:
        """Generate code to store a register value into a variable"""
        var_addr = self._get_variable_address(var_name)
        if var_addr == -1:
            # This is a special register
            return [
                f"    ; Store {source_register} into {var_name}",
                f"    MOV {var_name},{source_register}",  # Direct register access
            ]
        else:
            return [
                f"    ; Store {source_register} into {var_name}",
                f"    MOV [0x{var_addr:04X}],{source_register}",  # Direct memory access
            ]

    def _store_variable_from_reg(self, var_name: str, source_register: str) -> List[str]:
        """Generate code to store a register value into a variable"""
        var_addr = self._get_variable_address(var_name)
        if var_addr == -1:
            # This is a special register
            return [
                f"    ; Store {source_register} into {var_name}",
                f"    MOV {var_name},{source_register}",  # Direct register access
            ]
        else:
            return [
                f"    ; Store {source_register} into {var_name}",
                f"    MOV [0x{var_addr:04X}],{source_register}",  # Direct memory access
            ]

    def _get_variable_address(self, var_name: str) -> int:
        """Get or allocate memory address for a variable"""
        # Normalize variable name by removing $ suffix (make it optional)
        var_name = var_name.upper().rstrip('$')
        
        # Check if this is a special register
        special_registers = {
            # Graphics registers
            'VX': 'VX', 'VY': 'VY', 'VM': 'VM', 'VL': 'VL',
            # Sound registers  
            'SA': 'SA', 'SF': 'SF', 'SV': 'SV', 'SW': 'SW',
            # Timer registers
            'TT': 'TT', 'TM': 'TM', 'TC': 'TC', 'TS': 'TS'
        }
        
        if var_name in special_registers:
            # Return a negative value to indicate this is a special register
            return -1
        
        # Check if this is a string variable (Str1-Str9)
        # NOTE: String variables are now treated like regular variables
        # They store the address of their string data, not the data itself
        # if var_name.startswith('STR') and len(var_name) == 4 and var_name[3].isdigit() and var_name[3] in '123456789':
        #     # String variables Str1-Str9 are allocated in STRING_START area
        #     str_num = int(var_name[3])
        #     addr = self.STRING_START + (str_num - 1) * 256  # 256 bytes per string
        #     return addr
        
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
            color = color_reg
        else:
            color_reg = None

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after LINE parameters")
        i += 1  # Skip ')'

        # Generate SLINE instruction
        lines.extend([
            f"    ; Draw line from ({x1_reg},{y1_reg}) to ({x2_reg},{y2_reg})",
            f"    MOV VX,{x1_reg}",
            f"    MOV VY,{y1_reg}",
            f"    MOV VC,{color}",
            f"    SLINE {x2_reg},{y2_reg}",
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
        i += 1 # Skip ','

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
            f"    MOV VX,{x_reg}",
            f"    MOV VY,{y_reg}",
            f"    MOV VC,{color}",
            f"    SCIRC {radius_reg},{filled}",
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

    def _compile_rect(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile RECT(X,Y,Width,Height[,Color]) statement - draw rectangle outline"""
        lines = ["    ; Rect"]
        i += 1  # Skip RECT

        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after RECT")
        i += 1  # Skip '('

        # Parse X
        x_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(x_lines)
        x_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after X in RECT")
        i += 1  # Skip ','

        # Parse Y
        y_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(y_lines)
        y_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after Y in RECT")
        i += 1  # Skip ','

        # Parse Width
        width_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(width_lines)
        width_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ',':
            raise ValueError("Expected ',' after Width in RECT")
        i += 1  # Skip ','

        # Parse Height
        height_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(height_lines)
        height_reg = self._get_current_register()

        # Optional color parameter (default white = 15)
        color_reg = "P7"
        lines.append("    MOV P7,15")  # Default white color
        if i < len(tokens) and tokens[i] == ',':
            i += 1  # Skip ','
            color_lines, i = self._parse_additive_expression(tokens, i)
            lines.extend(color_lines)
            color_reg = self._get_current_register()

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after RECT parameters")
        i += 1  # Skip ')'

        # Calculate X2 = X + Width - 1, Y2 = Y + Height - 1
        lines.extend([
            f"    ; Calculate rectangle coordinates",
            f"    MOV P5,{x_reg}",        # P5 = X
            f"    ADD P5,{width_reg}",    # P5 = X + Width
            f"    DEC P5",                # P5 = X + Width - 1 (X2)
            f"    MOV P6,{y_reg}",        # P6 = Y
            f"    ADD P6,{height_reg}",   # P6 = Y + Height
            f"    DEC P6",                # P6 = Y + Height - 1 (Y2)
        ])

        # Generate SRECT instruction (unfilled rectangle)
        lines.extend([
            f"    ; Draw rectangle from ({x_reg},{y_reg}) to (P5,P6)",
            f"    MOV VX,{x_reg}",
            f"    MOV VY,{y_reg}",
            f"    MOV VC,{color_reg}",
            f"    SRECT P5,P6,0",  # 0 = unfilled
        ])

        # Free registers in reverse order to maintain allocation order
        for reg in reversed([x_reg, y_reg, width_reg, height_reg]):
            self._free_register(reg)
        if color_reg != "P7":  # Don't free P7 if we used it for default color
            self._free_register(color_reg)

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

    def _compile_splay(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Splay statement - start sound playback"""
        lines = ["    ; Splay - start sound playback"]
        i += 1  # Skip SPLAY

        lines.append("    SPLAY")
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
        """Compile DIM statement for array declaration or struct instance creation"""
        lines = ["    ; DIM - declaration"]
        i += 1  # Skip DIM

        if i >= len(tokens):
            raise ValueError("Expected variable name after DIM")

        var_name = tokens[i].upper()
        i += 1

        # Check if this is a struct instance declaration (DIM var AS struct_name)
        if i < len(tokens) and tokens[i].upper() == 'AS':
            i += 1  # Skip 'AS'
            
            if i >= len(tokens):
                raise ValueError("Expected struct name after AS")
            
            struct_name = tokens[i].upper()
            i += 1
            
            # Verify struct exists
            if struct_name not in self.structs:
                raise ValueError(f"Undefined struct '{struct_name}'")
            
            struct_info = self.structs[struct_name]
            struct_size = struct_info['size']
            
            # Allocate memory for the struct instance
            instance_addr = self.array_allocation_ptr  # Reuse array allocation pointer
            
            # Store struct instance info
            self.struct_instances[var_name] = {
                'struct_name': struct_name,
                'address': instance_addr
            }
            
            lines.extend([
                f"    ; Create struct instance {var_name} of type {struct_name}",
                f"    ; Struct size: {struct_size} bytes",
                f"    ; Instance address: 0x{instance_addr:04X}"
            ])
            
            # Update allocation pointer
            self.array_allocation_ptr += struct_size
            
            return lines, i
        
        # Original array declaration logic
        if i >= len(tokens) or tokens[i] != '(':
            raise ValueError("Expected '(' after array name in DIM or 'AS' for struct instance")

        i += 1  # Skip '('

        # Parse array size
        size_lines, i = self._parse_additive_expression(tokens, i)
        lines.extend(size_lines)

        if i >= len(tokens) or tokens[i] != ')':
            raise ValueError("Expected ')' after array size in DIM")

        i += 1  # Skip ')'

        # Get the size from the current register
        size_reg = self._get_current_register()

        # Calculate actual memory needed: size * 2 bytes per element + 2 bytes for size storage
        lines.append(f"    ; Calculate total memory needed: {size_reg} * 2 + 2")
        lines.append(f"    MOV P2,{size_reg}")  # Copy size to P2
        lines.append(f"    SHL P2,P2,1")        # Multiply by 2 (P2 = P2 * 2)
        lines.append(f"    ADD P2,2")           # Add 2 for size storage

        # Allocate memory for the array at runtime
        array_addr = self.array_allocation_ptr
        size_addr = array_addr  # Store size at the beginning of array data

        # Store array info with proper size tracking
        self.arrays[var_name] = {
            'address': array_addr + 2,  # Data starts after size
            'size_addr': size_addr,     # Address where size is stored
            'size_reg': size_reg,       # Size register (for compilation time)
            'allocated': True,
            'max_elements': None        # Will be set at runtime
        }

        # Update allocation pointer with actual size (P2 contains total bytes needed)
        lines.append(f"    ; Update allocation pointer")
        lines.append(f"    MOV P3,{self.array_allocation_ptr}")  # Current pointer
        lines.append(f"    ADD P3,P2")                           # Add allocated size
        lines.append(f"    MOV [0x{self.array_allocation_ptr - 2:04X}],P3")  # Store new pointer (using temp location)

        # Store the size at size_addr
        lines.extend([
            f"    ; Store array size at 0x{size_addr:04X}",
            f"    MOV [0x{size_addr:04X}],{size_reg}",
            f"    ; Array {var_name} data address: 0x{array_addr + 2:04X}",
            f"    ; Runtime bounds checking enabled"
        ])

        # Update the allocation pointer for next allocation
        self.array_allocation_ptr += 1024  # Reserve reasonable space, actual size tracked at runtime

        # Free the size register since we stored it
        self._free_register(size_reg)

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

    def _compile_break(self) -> List[str]:
        """Compile Break statement"""
        if not self.loop_stack:
            raise ValueError("BREAK statement must be inside a loop")
        
        end_label = self.loop_stack[-1]['end']
        return [
            f"    ; Break",
            f"    JMP {end_label}",
        ]

    def _compile_continue(self) -> List[str]:
        """Compile Continue statement"""
        if not self.loop_stack:
            raise ValueError("CONTINUE statement must be inside a loop")
        
        start_label = self.loop_stack[-1]['start']
        return [
            f"    ; Continue",
            f"    JMP {start_label}",
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

        # Pop from loop stack if this is a FOR loop
        if self.loop_stack and self.loop_stack[-1]['type'] == 'for':
            self.loop_stack.pop()

        return lines, i

    def _compile_select(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Select Case statement - simplified implementation"""
        lines = []
        i += 1  # Skip SELECT

        if i >= len(tokens) or tokens[i].upper() != "CASE":
            raise ValueError("Expected CASE after SELECT")

        i += 1  # Skip CASE

        # Parse the select expression
        expr_lines, i = self._parse_expression(tokens, i)
        lines.extend(expr_lines)

        # Store the select value register
        select_reg = self._get_current_register()
        
        # Generate end label for the select
        end_label = self._generate_label("select_end")
        
        # Store select info for nested CASE statements
        if not hasattr(self, 'select_stack'):
            self.select_stack = []
        
        self.select_stack.append({
            'reg': select_reg,
            'end_label': end_label,
            'next_case_label': None,
            'in_case_body': False
        })

        lines.extend([
            f"    ; Select Case {select_reg}",
        ])

        return lines, i

    def _compile_case(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Case value statement - simplified"""
        lines = []
        i += 1  # Skip CASE

        if not self.select_stack:
            raise ValueError("CASE without SELECT")

        select_info = self.select_stack[-1]
        select_reg = select_info['reg']
        end_label = select_info['end_label']

        # If there's a previous case, add the jump to next case
        if select_info['next_case_label']:
            lines.append(f"{select_info['next_case_label']}:")

        # Generate label for next case
        next_case_label = self._generate_label("case_next")
        select_info['next_case_label'] = next_case_label

        # Parse case value
        value_lines, i = self._parse_expression(tokens, i)
        lines.extend(value_lines)
        value_reg = self._get_current_register()
        
        lines.extend([
            f"    ; Case {value_reg}",
            f"    CMP {select_reg},{value_reg}",
            f"    JNZ {next_case_label}",
        ])
        
        self._free_register(value_reg)

        return lines, i

    def _compile_case_else(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile Case Else statement"""
        lines = []
        i += 1  # Skip CASEELSE

        if not self.select_stack:
            raise ValueError("CASE ELSE without SELECT")

        select_info = self.select_stack[-1]

        # If there's a previous case, add the jump to next case
        if select_info['next_case_label']:
            lines.append(f"{select_info['next_case_label']}:")

        lines.extend([
            f"    ; Case Else",
        ])

        return lines, i

    def _compile_end_select(self) -> List[str]:
        """Compile End Select statement"""
        if not self.select_stack:
            raise ValueError("END SELECT without SELECT")

        select_info = self.select_stack.pop()
        select_reg = select_info['reg']
        end_label = select_info['end_label']

        # Add the final next case label if it exists
        lines = []
        if select_info['next_case_label']:
            lines.append(f"{select_info['next_case_label']}:")
        
        lines.extend([
            f"{end_label}:",
        ])

        # Free the select register
        self._free_register(select_reg)

        return lines

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
                            new_val = imm_val // op_val  # Integer division
                        elif op_parts[0].endswith("MOD") and op_val != 0:
                            new_val = imm_val % op_val
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
                parts = line.strip().split()
                if len(parts) >= 2:
                    target = parts[1]
                    # Don't optimize away jumps to SELECT CASE end labels
                    if not target.startswith("select_end_"):
                        i += 1
                        # Skip lines until we find a label, empty line, or assembler directive
                        while i < len(optimized_lines):
                            next_line = optimized_lines[i]
                            stripped = next_line.strip()
                            if (stripped.endswith(":") or not stripped or 
                                (stripped and stripped[0].isalpha() and not stripped.startswith("    "))):
                                # Label, empty line, or assembler directive (ORG, DW, DB, etc.)
                                break
                            i += 1
                        continue
            
            i += 1
        
        self.assembly_lines = final_lines

    def _add_select_jump_if_needed(self, tokens: List[str], current_i: int):
        """Add jump to end of SELECT CASE if next statement doesn't start a new case"""
        if not self.select_stack:
            return

        # Find the next statement start
        i = current_i
        while i < len(tokens):
            token = tokens[i].upper()
            if token == '\n':
                i += 1
                continue
            # Check if this is a statement start
            if i == 0 or tokens[i-1] == '\n':
                # If next statement is CASE, CASEELSE, or END SELECT, don't add jump
                if token in ["CASE", "CASEELSE"] or (token == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "SELECT"):
                    return
                else:
                    # Add jump to end of SELECT CASE
                    select_info = self.select_stack[-1]
                    end_label = select_info['end_label']
                    self.assembly_lines.append(f"    JMP {end_label}")
                    return
            i += 1

    def _store_string_in_memory(self, string_content: str) -> int:
        """Store a string in memory and return its address"""
        # Check if we've already stored this string
        if string_content in self.strings:
            return self.strings[string_content]
        
        # Allocate new address for the string
        string_addr = self.STRING_START + self.string_counter * 256  # 256 bytes per string
        self.strings[string_content] = string_addr
        self.string_counter += 1
        
        return string_addr

    def _compile_struct(self, tokens: List[str], i: int) -> Tuple[List[str], int]:
        """Compile STRUCT statement - define a user-defined structure"""
        lines = ["    ; STRUCT - structure definition"]
        i += 1  # Skip STRUCT

        if i >= len(tokens):
            raise ValueError("Expected structure name after STRUCT")

        struct_name = tokens[i].upper()
        i += 1

        # Initialize struct definition
        fields = {}
        offset = 0

        # Parse fields until END STRUCT
        while i < len(tokens):
            token = tokens[i]

            if token.upper() == "END" and i + 1 < len(tokens) and tokens[i + 1].upper() == "STRUCT":
                # End of struct definition
                i += 2  # Skip END STRUCT
                break

            # Skip newlines and empty tokens
            if token == '\n' or token.strip() == '':
                i += 1
                continue

            # Expect field name
            field_name = token.upper()
            i += 1

            # For now, assume all fields are 16-bit integers (2 bytes)
            # Future: could support different types like BYTE, WORD, etc.
            field_size = 2  # 16-bit words

            # Store field info
            fields[field_name] = {
                'offset': offset,
                'size': field_size
            }

            offset += field_size

            # Check for comma (multiple fields on same line) or end of line
            if i < len(tokens) and tokens[i] == ',':
                i += 1  # Skip comma, continue parsing fields
            # If no comma, assume end of field declarations for this line

        # Store struct definition
        self.structs[struct_name] = {
            'fields': fields,
            'size': offset,  # Total size in bytes
            'field_count': len(fields)
        }

        lines.extend([
            f"    ; Struct {struct_name} defined with {len(fields)} fields, total size {offset} bytes",
        ])

        # List the fields for debugging
        for field_name, field_info in fields.items():
            lines.append(f"    ;   {field_name}: offset {field_info['offset']}, size {field_info['size']}")

        return lines, i

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python nobasic_compiler.py <input.nob> <output>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            nobasic_source = f.read()
        
        compiler = NoBasicCompiler()
        compiler.compile_program(nobasic_source, output_file)
        
    except Exception as e:
        print(f"Error compiling {input_file}: {e}")
        sys.exit(1)
    