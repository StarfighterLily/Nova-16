#!/usr/bin/env python3
"""
Nova-16 Modern Assembler
A clean, efficient, and modern assembler for the Nova-16 CPU architecture.
"""

import re
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple, Optional, Union
from opcodes import opcodes


# Mnemonics present in opcodes.py (so the CPU allocated an opcode byte for
# them and the assembler would otherwise happily encode them) but marked
# "# unimplemented" there — core/exec.py's HANDLER_INSTRUCTIONS has no
# handler for these, so the CPU raises a raw "Unknown opcode" exception at
# execution time. Rejecting them here turns a cryptic runtime crash into a
# clear assembly-time error. Keep in sync with the "# unimplemented" tags in
# opcodes.py if that ever changes.
UNIMPLEMENTED_INSTRUCTIONS = {"SMIX", "SECHO", "SREVERB", "SFILTER"}


@dataclass
class AssemblyLine:
    """Represents a parsed line of assembly code"""
    line_num: int
    label: Optional[str] = None
    instruction: Optional[str] = None
    operands: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    directive: Optional[str] = None
    directive_args: List[str] = field(default_factory=list)


@dataclass
class OperandType:
    """Enumeration of operand types"""
    REGISTER = "register"
    IMMEDIATE8 = "imm8"
    IMMEDIATE16 = "imm16"
    REGISTER_INDIRECT = "reg_indirect"
    REGISTER_INDEXED = "reg_indexed"
    DIRECT = "direct"


class InstructionSet:
    """Manages the instruction set and register mappings from opcodes.py"""

    def __init__(self):
        self.instructions: Dict[str, Tuple[str, int]] = {}
        self.registers: Dict[str, str] = {}
        self.indirect_registers: Dict[str, str] = {}
        self.indexed_registers: Dict[str, str] = {}
        self.high_byte_registers: Dict[str, str] = {}
        self.low_byte_registers: Dict[str, str] = {}
        self._load_opcodes()

    # Mnemonics that are simultaneously a register code (usable as an
    # operand, e.g. "MOV SA, 5") AND a genuine standalone one-operand
    # instruction with a real CPU handler (core/exec_handlers.py's
    # _sa/_sf/_sv/_sw/_vm/_vl/_tt/_tm/_tc/_ts/_vx/_vy, all registered in
    # core/exec.py's HANDLER_INSTRUCTIONS). The rest of reg_names below
    # (BANK, C0, C1, MX, MY, MB, SP, FP, VC, and the R/P registers) have no
    # standalone-opcode handler on the CPU, so they stay register-only.
    DUAL_PURPOSE_INSTRUCTIONS = {
        "SA", "SF", "SV", "SW", "VM", "VL", "TT", "TM", "TC", "TS", "VX", "VY"
    }

    def _load_opcodes(self):
        """Load and organize opcodes from opcodes.py"""
        reg_names = {f"R{i}" for i in range(10)} | {f"P{i}" for i in range(10)} | {
            "VX", "VY", "VM", "VC", "VL", "TT", "TM", "TC", "TS",
            "C0", "C1",
            "MX", "MY", "MB",
            "SP", "FP", "SA", "SF", "SV", "SW",
            "BANK"
        }

        for mnemonic, opcode_str, size in opcodes:
            opcode_val = int(opcode_str, 16)

            if mnemonic in reg_names:
                self.registers[mnemonic] = opcode_str
                if mnemonic in self.DUAL_PURPOSE_INSTRUCTIONS:
                    self.instructions[mnemonic] = (opcode_str, size)
            elif mnemonic.endswith(':'):  # High byte
                self.high_byte_registers[mnemonic] = opcode_str
            elif mnemonic.startswith(':'):  # Low byte
                self.low_byte_registers[mnemonic] = opcode_str
            else:
                self.instructions[mnemonic] = (opcode_str, size)

    def get_instruction_info(self, mnemonic: str) -> Optional[Tuple[str, int]]:
        """Get instruction opcode and operand count"""
        return self.instructions.get(mnemonic.upper())

    def get_register_opcode(self, register: str) -> Optional[str]:
        """Get register opcode"""
        return self.registers.get(register.upper())

    def is_register(self, token: str) -> bool:
        """Check if token is a register"""
        return token.upper() in self.registers

    def is_high_byte_register(self, token: str) -> bool:
        """Check if token is a high byte register"""
        return token in self.high_byte_registers

    def is_low_byte_register(self, token: str) -> bool:
        """Check if token is a low byte register"""
        return token in self.low_byte_registers



class Parser:
    """Parses assembly source code into structured data, with macro support"""

    def __init__(self, instruction_set: InstructionSet):
        self.instruction_set = instruction_set
        self.patterns = {
            'comment': re.compile(r';.*$'),
            'label': re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*):'),
            'directive': re.compile(r'^\s*(ORG|EQU|DB|DW|DEFSTR|DS|MACRO|ENDM|INCLUDE|IF|IFDEF|IFNDEF|ELSE|ENDIF)\s+', re.IGNORECASE),
            'macro_def': re.compile(r'^\s*MACRO\s+(\w+)(.*)$', re.IGNORECASE),
            'macro_end': re.compile(r'^\s*ENDM\b', re.IGNORECASE),
            'hex16': re.compile(r'^0x[0-9A-Fa-f]{1,4}$'),
            'hex8': re.compile(r'^0x[0-9A-Fa-f]{1,2}$'),
            'decimal': re.compile(r'^-?\d+$'),
            'char_literal': re.compile(r"^'([^'\\]|\\.)'$"),
            'indirect': re.compile(r'^\[([A-Za-z0-9:]+)\]$'),
            'indexed': re.compile(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$'),
            'direct': re.compile(r'^\[0x([0-9A-Fa-f]{1,4})\]$'),
            'string': re.compile(r'^"([^"\\]|\\.)*"$'),
        }
        self.macros = {}  # name -> (param_list, body_lines)
        self.instructions = {mnemonic.upper() for mnemonic, _, _ in opcodes}

    def _parse_operands_with_strings(self, operand_str: str) -> List[str]:
        """Parse operands while respecting quoted strings"""
        operands = []
        current_operand = ""
        in_string = False
        i = 0

        while i < len(operand_str):
            char = operand_str[i]

            if char == '"':
                in_string = not in_string
                current_operand += char
            elif char == ',' and not in_string:
                if current_operand.strip():
                    operands.append(current_operand.strip())
                current_operand = ""
            else:
                current_operand += char

            i += 1

        if current_operand.strip():
            operands.append(current_operand.strip())

        return operands

    def parse_line(self, line: str, line_num: int) -> Optional[AssemblyLine]:
        """Parse a single line of assembly code"""
        if not line.strip():
            return None

        asm_line = AssemblyLine(line_num)

        # Remove comments
        comment_match = self.patterns['comment'].search(line)
        if comment_match:
            asm_line.comment = comment_match.group().strip()
            line = line[:comment_match.start()].strip()

        if not line:
            return asm_line

        def split_head(text: str) -> Tuple[Optional[str], str]:
            stripped = text.lstrip()
            if not stripped:
                return None, ""
            parts = stripped.split(None, 1)
            if len(parts) == 1:
                return parts[0], ""
            return parts[0], parts[1]

        first_token, remainder = split_head(line)
        if not first_token:
            return asm_line

        first = first_token.upper()

        directives = {'ORG', 'EQU', 'DB', 'DW', 'DEFSTR', 'DS', 'MACRO', 'ENDM', 'INCLUDE', 'IF', 'IFDEF', 'IFNDEF', 'ELSE', 'ENDIF'}

        if first in self.instructions or first in directives:
            # no label, directive or instruction
            if first in directives:
                asm_line.directive = first
                if remainder:
                    arg_str = remainder
                    if asm_line.directive in {'DB', 'DW', 'DEFSTR', 'DS'}:
                        asm_line.directive_args = self._parse_operands_with_strings(arg_str)
                    else:
                        asm_line.directive_args = [arg_str]
            else:
                asm_line.instruction = first
                if remainder:
                    operand_str = remainder
                    asm_line.operands = [op.strip() for op in operand_str.split(',')]
        else:
            # label
            if first_token.endswith(':'):
                asm_line.label = first_token[:-1]
            else:
                asm_line.label = first_token

            current_token, current_remainder = split_head(remainder)
            if not current_token:
                return asm_line

            # now parse the rest as directive or instruction
            current = current_token.upper()
            if current in directives:
                asm_line.directive = current
                if current_remainder:
                    arg_str = current_remainder
                    if asm_line.directive in {'DB', 'DW', 'DEFSTR', 'DS'}:
                        asm_line.directive_args = self._parse_operands_with_strings(arg_str)
                    else:
                        asm_line.directive_args = [arg_str]
            else:
                asm_line.instruction = current
                if current_remainder:
                    operand_str = current_remainder
                    asm_line.operands = [op.strip() for op in operand_str.split(',')]

        return asm_line


    def parse_file(self, filename: str) -> List[AssemblyLine]:
        """Parse an entire assembly file, with include and macro support"""
        lines = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                raw_lines = list(f)
        except IOError as e:
            raise Exception(f"Could not read file {filename}: {e}")

        # Include expansion pass
        expanded_lines = self._expand_includes(raw_lines, filename)

        # Pre-scan for symbols defined by EQU
        defined_symbols = self._pre_scan_symbols(expanded_lines)

        # Conditional expansion pass
        expanded_lines = self._expand_conditionals(expanded_lines, defined_symbols)

        # Macro preprocessing pass
        expanded_lines = self._expand_macros(expanded_lines)
        for line_num, line in enumerate(expanded_lines, 1):
            parsed_line = self.parse_line(line.rstrip(), line_num)
            if parsed_line:
                lines.append(parsed_line)
        return lines

    def _expand_includes(self, raw_lines: List[str], base_filename: str) -> List[str]:
        """Expand INCLUDE directives recursively"""
        included_files = set()
        return self._expand_includes_recursive(raw_lines, base_filename, included_files)

    def _expand_includes_recursive(self, raw_lines: List[str], base_filename: str, included_files: set) -> List[str]:
        """Recursively expand includes"""
        output_lines = []
        base_dir = os.path.dirname(os.path.abspath(base_filename))

        for line in raw_lines:
            stripped = line.strip()
            if stripped.upper().startswith('INCLUDE'):
                # Parse include directive
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    raise ValueError(f"Invalid INCLUDE directive: {line}")
                include_file = parts[1].strip().strip('"').strip("'")
                include_path = os.path.join(base_dir, include_file)
                abs_include_path = os.path.abspath(include_path)

                if abs_include_path in included_files:
                    raise ValueError(f"Circular include detected: {include_file}")

                included_files.add(abs_include_path)

                try:
                    with open(include_path, 'r', encoding='utf-8') as f:
                        include_lines = f.readlines()
                    # Recursively expand includes in the included file
                    expanded_include = self._expand_includes_recursive(include_lines, include_path, included_files)
                    output_lines.extend(expanded_include)
                except IOError as e:
                    raise ValueError(f"Could not include file {include_file}: {e}")
            else:
                output_lines.append(line)

        return output_lines

    def _pre_scan_symbols(self, raw_lines: List[str]) -> set:
        """Pre-scan for symbols defined by EQU"""
        defined = set()
        for line in raw_lines:
            stripped = line.strip()
            if ' EQU ' in stripped.upper():
                parts = stripped.split(None, 2)
                if len(parts) >= 3 and parts[1].upper() == 'EQU':
                    defined.add(parts[0])
        return defined

    def _expand_conditionals(self, raw_lines: List[str], defined_symbols: set) -> List[str]:
        """Expand conditional directives"""
        output_lines = []
        i = 0
        n = len(raw_lines)
        condition_stack = []

        while i < n:
            line = raw_lines[i]
            stripped = line.strip().upper()

            if stripped.startswith('IF '):
                # Parse IF condition
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    raise ValueError(f"Invalid IF directive: {line}")
                condition = parts[1].strip()
                # Simple evaluation: if condition is '1' or 'TRUE', include, else skip
                include = condition in ['1', 'TRUE']
                condition_stack.append(include)
                i += 1
                continue

            elif stripped.startswith('IFDEF '):
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    raise ValueError(f"Invalid IFDEF directive: {line}")
                symbol = parts[1].strip()
                include = symbol in defined_symbols
                condition_stack.append(include)
                i += 1
                continue

            elif stripped.startswith('IFNDEF '):
                parts = stripped.split(None, 1)
                if len(parts) < 2:
                    raise ValueError(f"Invalid IFNDEF directive: {line}")
                symbol = parts[1].strip()
                include = symbol not in defined_symbols
                condition_stack.append(include)
                i += 1
                continue

            elif stripped == 'ELSE':
                if not condition_stack:
                    raise ValueError(f"ELSE without IF: {line}")
                # Toggle the condition
                condition_stack[-1] = not condition_stack[-1]
                i += 1
                continue

            elif stripped == 'ENDIF':
                if not condition_stack:
                    raise ValueError(f"ENDIF without IF: {line}")
                condition_stack.pop()
                i += 1
                continue

            else:
                # If in a false condition block, skip
                if condition_stack and not all(condition_stack):
                    i += 1
                    continue
                else:
                    output_lines.append(line)
                    i += 1

        if condition_stack:
            raise ValueError("Unclosed conditional directives")

        return output_lines

    def _expand_macros(self, raw_lines: List[str]) -> List[str]:
        """Preprocess macros: collect definitions, expand invocations"""
        macros = {}
        output_lines = []
        i = 0
        n = len(raw_lines)
        # First pass: collect macro definitions
        while i < n:
            line = raw_lines[i]
            macro_def = self.patterns['macro_def'].match(line)
            if macro_def:
                macro_name = macro_def.group(1)
                if macro_name in macros:
                    raise ValueError(f"Macro '{macro_name}' redefined")
                param_str = macro_def.group(2).strip()
                params = [p.strip() for p in param_str.split(',')] if param_str else []
                body = []
                i += 1
                while i < n and not self.patterns['macro_end'].match(raw_lines[i]):
                    body.append(raw_lines[i].rstrip('\n'))
                    i += 1
                if i >= n:
                    raise ValueError(f"Macro '{macro_name}' definition incomplete - missing ENDM")
                macros[macro_name] = (params, body)
                # Skip ENDM
                if i < n and self.patterns['macro_end'].match(raw_lines[i]):
                    i += 1  # skip ENDM
                continue
            else:
                output_lines.append(line.rstrip('\n'))
                i += 1
        self.macros = macros
        # Second pass: expand macro invocations recursively
        expanded = []
        for line in output_lines:
            expanded.extend(self._expand_line(line, macros))
        return expanded

    def _expand_line(self, line: str, macros: dict) -> List[str]:
        """Recursively expand a single line if it contains macro invocations"""
        tokens = line.strip().split()
        if tokens and tokens[0] in macros:
            macro_name = tokens[0]
            args = ' '.join(tokens[1:]).split(',') if len(tokens) > 1 else []
            args = [a.strip() for a in args]
            params, body = macros[macro_name]
            arg_map = {p: (args[i] if i < len(args) else '') for i, p in enumerate(params)}
            result = []
            for body_line in body:
                # Replace parameters in body
                expanded_line = body_line
                for p, v in arg_map.items():
                    expanded_line = re.sub(rf'\b{re.escape(p)}\b', v, expanded_line)
                # Recursively expand the expanded line
                result.extend(self._expand_line(expanded_line, macros))
            return result
        else:
            return [line]


class OperandClassifier:
    """Classifies operands into types"""

    def __init__(self, instruction_set: InstructionSet):
        self.instruction_set = instruction_set
        self.patterns = {
            'hex16': re.compile(r'^0x[0-9A-Fa-f]{3,4}$'),
            'hex8': re.compile(r'^0x[0-9A-Fa-f]{1,2}$'),
            'decimal': re.compile(r'^-?\d+$'),
            'char_literal': re.compile(r"^'([^'\\]|\\.)'$"),
            'indirect': re.compile(r'^\[([A-Za-z0-9:]+)\]$'),
            'indexed': re.compile(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$'),
            'fp_offset': re.compile(r'^\[(FP|fp)\s*[-+]\s*(\d+)\]$'),
            'sp_offset': re.compile(r'^\[(SP|sp)\s*[-+]\s*(\d+)\]$'),
            'reg_offset': re.compile(r'^\[([PR]\d+)\s*[-+]\s*(\d+)\]$'),
            'direct': re.compile(r'^\[0x([0-9A-Fa-f]{1,4})\]$'),
            'string': re.compile(r'^"([^"\\]|\\.)*"$'),
        }

    def parse_string_literal(self, string_operand: str) -> List[int]:
        """Parse a string literal and return list of byte values"""
        if not (string_operand.startswith('"') and string_operand.endswith('"')):
            raise ValueError(f"Invalid string literal: {string_operand}")

        content = string_operand[1:-1]
        result = []
        i = 0

        while i < len(content):
            if content[i] == '\\' and i + 1 < len(content):
                next_char = content[i + 1]
                if next_char == 'n':
                    result.append(ord('\n'))
                elif next_char == 't':
                    result.append(ord('\t'))
                elif next_char == 'r':
                    result.append(ord('\r'))
                elif next_char == '\\':
                    result.append(ord('\\'))
                elif next_char == '"':
                    result.append(ord('"'))
                elif next_char == '0':
                    result.append(0)
                else:
                    result.append(ord(next_char))
                i += 2
            else:
                result.append(ord(content[i]))
                i += 1

        return result

    def classify_operand(self, operand: str, symbol_table: Optional[Dict[str, str]] = None) -> str:
        """Classify an operand and return its type"""
        operand = operand.strip()

        # Check for register
        valid_registers = {
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
            'P0:', 'P1:', 'P2:', 'P3:', 'P4:', 'P5:', 'P6:', 'P7:', 'P8:', 'P9:',
            ':P0', ':P1', ':P2', ':P3', ':P4', ':P5', ':P6', ':P7', ':P8', ':P9',
            'VX', 'VY', 'VM', 'VC', 'VL', 'TT', 'TM', 'TC', 'TS', 'C0', 'C1',
            'MX', 'MY', 'MB',
            'SP', 'FP', 'SA', 'SF', 'SV', 'SW',
            'BANK'
        }

        if operand in valid_registers:
            return OperandType.REGISTER

        # Check for direct memory addressing
        if self.patterns['direct'].match(operand):
            return OperandType.DIRECT

        # Check for frame/stack pointer offset
        if self.patterns['fp_offset'].match(operand) or self.patterns['sp_offset'].match(operand):
            return OperandType.REGISTER_INDEXED

        # Check for register offset
        if self.patterns['reg_offset'].match(operand):
            return OperandType.REGISTER_INDEXED

        # Check for indirect addressing
        if self.patterns['indirect'].match(operand):
            return OperandType.REGISTER_INDIRECT

        # Check for indexed addressing
        if self.patterns['indexed'].match(operand):
            return OperandType.REGISTER_INDEXED

        # Check for high/low byte symbols
        if operand.endswith(':') and len(operand) > 1:
            symbol_name = operand[:-1]
            if symbol_table and symbol_name in symbol_table:
                return OperandType.IMMEDIATE8

        if operand.startswith(':') and len(operand) > 1:
            symbol_name = operand[1:]
            if symbol_table and symbol_name in symbol_table:
                return OperandType.IMMEDIATE8

        # Check symbol table for labels
        if symbol_table and operand in symbol_table:
            return OperandType.IMMEDIATE16

        # Check for immediates
        if self.patterns['hex16'].match(operand):
            val = int(operand, 16)
            return OperandType.IMMEDIATE16 if val > 127 else OperandType.IMMEDIATE8
        elif self.patterns['hex8'].match(operand):
            return OperandType.IMMEDIATE8
        elif self.patterns['decimal'].match(operand):
            val = int(operand)
            # Negative values must always be encoded as a full 16-bit two's
            # complement immediate. IMMEDIATE8 encodes a single raw byte with
            # no sign-extension step at decode time, so e.g. -2 stored as a
            # lone 0xFE loses its sign bit entirely when moved into a 16-bit
            # P register (becomes 254, not 65534/0xFFFE). Register writes
            # already mask down to the destination's actual width, so using
            # IMMEDIATE16 here is also safe for 8-bit R-register destinations.
            if val < 0:
                return OperandType.IMMEDIATE16
            return OperandType.IMMEDIATE16 if val > 127 else OperandType.IMMEDIATE8
        elif self.patterns['char_literal'].match(operand):
            return OperandType.IMMEDIATE8

        # Default to 16-bit immediate
        return OperandType.IMMEDIATE16


class DataGenerator:
    """Generates data bytes from assembler directives"""

    def __init__(self, parser: Parser):
        self.parser = parser
        self.classifier = OperandClassifier(parser.instruction_set)

    def generate_db_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate data bytes for DB directive"""
        result = []

        for arg in args:
            arg = arg.strip()

            if self.parser.patterns['string'].match(arg):
                # Parse string literal
                string_bytes = self.classifier.parse_string_literal(arg)
                result.extend(string_bytes)
            else:
                val = self._parse_numeric_value(arg, symbol_table)
                if val > 255:
                    raise ValueError(f"Value {val} too large for DB (max 255)")
                result.append(val)

        return result

    def generate_dw_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate data bytes for DW directive"""
        result = []

        for arg in args:
            val = self._parse_numeric_value(arg, symbol_table)
            if val > 65535:
                raise ValueError(f"Value {val} too large for DW (max 65535)")
            # Big-endian: high byte first, low byte second (Nova-16 specification)
            result.append((val >> 8) & 0xFF)    # High byte
            result.append(val & 0xFF)           # Low byte

        return result

    def generate_defstr_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate null-terminated string data for DEFSTR directive"""
        if len(args) != 1:
            raise ValueError("DEFSTR requires exactly one string argument")

        arg = args[0].strip()

        if not self.parser.patterns['string'].match(arg):
            raise ValueError(f"DEFSTR requires a string literal, got: {arg}")

        string_bytes = self.classifier.parse_string_literal(arg)

        # Null-terminated
        result = list(string_bytes)
        result.append(0)  # Null terminator

        if len(result) > 255:
            raise ValueError(f"String too long for DEFSTR (max 254 chars + null)")

        return result

    def _parse_numeric_value(self, value: str, symbol_table: Dict[str, str]) -> int:
        """Parse a numeric value, handling symbols"""
        value = value.strip()

        if value.startswith('0x'):
            return int(value, 16)
        elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        elif symbol_table and value in symbol_table:
            symbol_val = symbol_table[value].strip()
            if symbol_val.startswith('0x'):
                return int(symbol_val, 16)
            else:
                return int(symbol_val)
        else:
            raise ValueError(f"Unknown value: {value}")


class CodeGenerator:
    """Generates machine code from parsed assembly"""

    def __init__(self, instruction_set: InstructionSet):
        self.instruction_set = instruction_set
        self.classifier = OperandClassifier(instruction_set)

    def calculate_mode_byte(self, operand_types: List[str]) -> int:
        """Calculate mode byte for prefixed operand encoding"""
        mode_byte = 0

        # Mode encoding: bits 0-1: op1, bits 2-3: op2, bits 4-5: op3
        # 00: register, 01: imm8, 10: imm16, 11: memory

        for i, op_type in enumerate(operand_types[:3]):
            shift = i * 2
            if op_type == OperandType.REGISTER:
                mode_val = 0
            elif op_type == OperandType.IMMEDIATE8:
                mode_val = 1
            elif op_type == OperandType.IMMEDIATE16:
                mode_val = 2
            elif op_type in [OperandType.REGISTER_INDIRECT, OperandType.REGISTER_INDEXED, OperandType.DIRECT]:
                mode_val = 3
            else:
                mode_val = 0

            mode_byte |= (mode_val << shift)

        # Bit 6: Indexed flag
        if OperandType.REGISTER_INDEXED in operand_types:
            mode_byte |= (1 << 6)

        # Bit 7: Direct flag
        if OperandType.DIRECT in operand_types:
            mode_byte |= (1 << 7)

        return mode_byte

    def encode_operand(self, operand: str, operand_type: str, symbol_table: Dict[str, str], location_counter: int, instruction_name: str = "") -> List[int]:
        """Encode operand for prefixed system.

        Args:
            operand: The operand string to encode.
            operand_type: The classified operand type.
            symbol_table: Symbol table for label resolution.
            location_counter: Current assembly location for relative offset calc.
            instruction_name: The instruction mnemonic, used to determine
                              whether symbol references should be absolute
                              (CALL, JMP, etc.) or relative (BR, BRZ, BRNZ).
        """
        operand = operand.strip()

        if operand_type == OperandType.REGISTER:
            if operand in self.instruction_set.registers:
                return [int(self.instruction_set.registers[operand], 16)]
            elif operand in self.instruction_set.high_byte_registers:
                return [int(self.instruction_set.high_byte_registers[operand], 16)]
            elif operand in self.instruction_set.low_byte_registers:
                return [int(self.instruction_set.low_byte_registers[operand], 16)]
            else:
                raise ValueError(f"Unknown register: {operand}")

        elif operand_type == OperandType.IMMEDIATE8:
            val = self._parse_immediate_value(operand, symbol_table, 8, location_counter, instruction_name)
            return [val & 0xFF]

        elif operand_type == OperandType.IMMEDIATE16:
            val = self._parse_immediate_value(operand, symbol_table, 16, location_counter, instruction_name)
            return [(val >> 8) & 0xFF, val & 0xFF]

        elif operand_type == OperandType.REGISTER_INDIRECT:
            indirect_match = re.match(r'^\[([A-Za-z0-9:]+)\]$', operand)
            if indirect_match:
                reg_name = indirect_match.group(1)
                if reg_name in self.instruction_set.registers:
                    reg_num = int(self.instruction_set.registers[reg_name], 16)
                    return [reg_num]
                elif reg_name in self.instruction_set.high_byte_registers:
                    reg_num = int(self.instruction_set.high_byte_registers[reg_name], 16)
                    return [reg_num]
                elif reg_name in self.instruction_set.low_byte_registers:
                    reg_num = int(self.instruction_set.low_byte_registers[reg_name], 16)
                    return [reg_num]
                else:
                    raise ValueError(f"Unknown register for indirect: {reg_name}")
            else:
                raise ValueError(f"Invalid indirect operand: {operand}")

        elif operand_type == OperandType.REGISTER_INDEXED:
            # Handle various indexed forms
            if re.match(r'^\[(FP|fp)\s*[-+]\s*\d+\]$', operand):
                # Frame pointer offset
                match = re.match(r'^\[(FP|fp)\s*([+-])\s*(\d+)\]$', operand)
                sign, offset_str = match.groups()[1], match.groups()[2]
                offset_val = int(offset_str)
                if sign == '-':
                    offset_val = (-offset_val) & 0xFF
                return [0xFC, offset_val]  # FP indexed opcode

            elif re.match(r'^\[(SP|sp)\s*[-+]\s*\d+\]$', operand):
                # Stack pointer offset
                match = re.match(r'^\[(SP|sp)\s*([+-])\s*(\d+)\]$', operand)
                sign, offset_str = match.groups()[1], match.groups()[2]
                offset_val = int(offset_str)
                if sign == '-':
                    offset_val = (-offset_val) & 0xFF
                return [0xFB, offset_val]  # SP indexed opcode

            elif re.match(r'^\[([PR]\d+)\s*[-+]\s*\d+\]$', operand):
                # General register offset
                match = re.match(r'^\[([PR])(\d+)\s*([+-])\s*(\d+)\]$', operand)
                reg_type, reg_num_str, sign, offset_str = match.groups()
                reg_num = int(reg_num_str)
                offset_val = int(offset_str)
                if sign == '-':
                    offset_val = (-offset_val) & 0xFF

                if reg_type == 'P' and 0 <= reg_num <= 9:
                    reg_opcode = 0xF1 + reg_num
                elif reg_type == 'R' and 0 <= reg_num <= 9:
                    reg_opcode = 0xE7 + reg_num
                else:
                    raise ValueError(f"Invalid register in offset: {reg_type}{reg_num}")

                return [reg_opcode, offset_val]

            else:
                # General indexed [reg + index]
                indexed_match = re.match(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$', operand)
                if indexed_match:
                    reg_name, index_name = indexed_match.groups()

                    # Base register
                    if reg_name in self.instruction_set.registers:
                        reg_num = int(self.instruction_set.registers[reg_name], 16)
                    elif reg_name in self.instruction_set.high_byte_registers:
                        reg_num = int(self.instruction_set.high_byte_registers[reg_name], 16)
                    elif reg_name in self.instruction_set.low_byte_registers:
                        reg_num = int(self.instruction_set.low_byte_registers[reg_name], 16)
                    else:
                        raise ValueError(f"Unknown base register: {reg_name}")

                    # Index value
                    if index_name.isdigit():
                        index_val = int(index_name)
                    elif index_name.startswith('0x'):
                        index_val = int(index_name, 16)
                    else:
                        index_val = 0  # Default

                    return [reg_num, index_val & 0xFF]
                else:
                    raise ValueError(f"Invalid indexed operand: {operand}")

        elif operand_type == OperandType.DIRECT:
            direct_match = re.match(r'^\[0x([0-9A-Fa-f]{1,4})\]$', operand)
            if direct_match:
                addr = int(direct_match.group(1), 16)
                return [(addr >> 8) & 0xFF, addr & 0xFF]
            else:
                raise ValueError(f"Invalid direct operand: {operand}")

        else:
            raise ValueError(f"Unsupported operand type: {operand_type}")

    # Instructions that use relative offsets instead of absolute addresses.
    # BR/BRZ/BRNZ add the offset to the current PC, so the encoded value is
    # (target - (pc_after_instruction)). All other instructions (CALL, JMP,
    # etc.) take an absolute address as their operand.
    _RELATIVE_BRANCH_INSTRUCTIONS = {'BR', 'BRZ', 'BRNZ'}

    def _parse_immediate_value(self, operand: str, symbol_table: Dict[str, str], bit_width: int,
                               location_counter: int = 0, instruction_name: str = "") -> int:
        """Parse an immediate value.

        For BR/BRZ/BRNZ, symbol references are encoded as relative offsets
        (target - (location_counter + instruction_size)). For all other
        instructions (CALL, JMP, etc.) symbol references are absolute addresses.
        """
        if operand.startswith('0x'):
            return int(operand, 16)
        elif self.classifier.patterns['char_literal'].match(operand):
            char_content = operand[1:-1]
            if char_content.startswith('\\'):
                if char_content == '\\n':
                    return ord('\n')
                elif char_content == '\\t':
                    return ord('\t')
                elif char_content == '\\r':
                    return ord('\r')
                elif char_content == '\\\\':
                    return ord('\\')
                elif char_content == "\\'":
                    return ord("'")
                else:
                    return ord(char_content[1])
            else:
                return ord(char_content)
        elif operand.isdigit() or (operand.startswith('-') and operand[1:].isdigit()):
            return int(operand)
        elif symbol_table and operand in symbol_table:
            symbol_val = symbol_table[operand].strip()
            if symbol_val.startswith('0x'):
                val = int(symbol_val, 16)
            else:
                val = int(symbol_val)

            # BR/BRZ/BRNZ use relative offsets; other instructions use absolute addresses.
            if instruction_name.upper() in self._RELATIVE_BRANCH_INSTRUCTIONS:
                # Calculate offset as: target - (current_location + instruction_size)
                # instruction_size = opcode(1) + mode_byte(1) + imm16(2) = 4 bytes
                instruction_size = 4
                offset = val - (location_counter + instruction_size)
                # Convert to signed 16-bit value
                if offset < 0:
                    offset = offset & 0xFFFF
                return offset

            # Non-branch instructions use the absolute symbol address directly.
            return val
        else:
            raise ValueError(f"Undefined symbol: {operand}")

    def generate_instruction(self, asm_line: AssemblyLine, symbol_table: Dict[str, str], location_counter: int) -> List[int]:
        """Generate machine code for an instruction"""
        if not asm_line.instruction:
            return []

        if asm_line.instruction.upper() in UNIMPLEMENTED_INSTRUCTIONS:
            raise ValueError(
                f"{asm_line.instruction} is not implemented on this CPU "
                f"(line {asm_line.line_num})"
            )

        instr_info = self.instruction_set.get_instruction_info(asm_line.instruction)
        if not instr_info:
            raise ValueError(f"Unknown instruction: {asm_line.instruction} (line {asm_line.line_num})")

        opcode_str, operand_count = instr_info
        result = [int(opcode_str, 16)]

        if operand_count == 0:
            return result

        # Classify operands
        operand_types = []
        for operand in asm_line.operands:
            op_type = self.classifier.classify_operand(operand, symbol_table)
            operand_types.append(op_type)

        # Calculate mode byte
        mode_byte = self.calculate_mode_byte(operand_types)
        result.append(mode_byte)

        # Encode operands
        for i, operand in enumerate(asm_line.operands):
            if i < len(operand_types):
                operand_bytes = self.encode_operand(operand, operand_types[i], symbol_table, location_counter, asm_line.instruction)
                result.extend(operand_bytes)

        return result


class Assembler:
    """Main assembler class"""

    def __init__(self, log: Optional[Callable[[str], None]] = print, trace: bool = False):
        self.instruction_set = InstructionSet()
        self.parser = Parser(self.instruction_set)
        self.code_generator = CodeGenerator(self.instruction_set)
        self.data_generator = DataGenerator(self.parser)
        self.classifier = OperandClassifier(self.instruction_set)
        self.errors = []
        self.log = log
        self.trace = trace

    def _emit(self, message: str) -> None:
        if self.log is not None:
            self.log(message)

    def _trace(self, message: str) -> None:
        if self.trace:
            self._emit(message)

    def first_pass(self, lines: List[AssemblyLine]) -> Dict[str, str]:
        """First pass: build symbol table"""
        symbol_table = {}
        location_counter = 0

        for line in lines:
            # Handle labels
            if line.label:
                symbol_table[line.label] = f"0x{location_counter:04X}"

            # Handle ORG
            if line.directive == 'ORG':
                if line.directive_args:
                    location_counter = int(line.directive_args[0], 16)
                continue

            # Handle EQU
            if line.directive == 'EQU':
                if line.label and line.directive_args:
                    symbol_table[line.label] = line.directive_args[0].strip()
                continue

            # Handle data directives
            if line.directive in ['DB', 'DW', 'DEFSTR', 'DS']:
                data_size = self._calculate_data_size(line)
                location_counter += data_size
                continue

            # Calculate instruction size
            if line.instruction:
                if (line.instruction in self.instruction_set.registers
                        and line.instruction not in self.instruction_set.instructions):
                    continue  # Skip register-only mnemonics (no standalone opcode form)

                instr_info = self.instruction_set.get_instruction_info(line.instruction)
                if instr_info and instr_info[1] == 0:
                    size = 1  # No operands
                else:
                    size = 2  # opcode + mode
                    for operand in line.operands:
                        op_type = self.code_generator.classifier.classify_operand(operand, symbol_table)
                        if op_type == OperandType.REGISTER:
                            size += 1
                        elif op_type == OperandType.IMMEDIATE8:
                            size += 1
                        elif op_type == OperandType.IMMEDIATE16:
                            size += 2
                        elif op_type == OperandType.REGISTER_INDIRECT:
                            size += 1
                        elif op_type == OperandType.REGISTER_INDEXED:
                            size += 2
                        elif op_type == OperandType.DIRECT:
                            size += 2

                location_counter += size

        return symbol_table

    def _calculate_data_size(self, line: AssemblyLine) -> int:
        """Calculate size of data directive"""
        if line.directive == 'DB':
            size = 0
            for arg in line.directive_args:
                arg = arg.strip()
                if self.parser.patterns['string'].match(arg):
                    string_bytes = self.classifier.parse_string_literal(arg)
                    size += len(string_bytes)
                else:
                    size += 1
            return size
        elif line.directive == 'DW':
            return len(line.directive_args) * 2
        elif line.directive == 'DEFSTR':
            if line.directive_args:
                arg = line.directive_args[0].strip()
                if self.parser.patterns['string'].match(arg):
                    string_bytes = self.classifier.parse_string_literal(arg)
                    return len(string_bytes) + 1  # + null terminator
            return 1
        elif line.directive == 'DS':
            if line.directive_args:
                arg = line.directive_args[0].strip()
                try:
                    size = int(arg)
                    return size
                except ValueError:
                    raise ValueError(f"DS requires a numeric argument: {arg}")
            return 0
        return 0

    def second_pass(self, lines: List[AssemblyLine], symbol_table: Dict[str, str]) -> Tuple[bytearray, List[Tuple[int, int, int]]]:
        """Second pass: generate machine code"""
        code = bytearray()
        segments = []
        location_counter = 0
        current_segment_start = 0
        current_segment_binary_offset = 0

        for line in lines:
            # Handle ORG
            if line.directive == 'ORG':
                if line.directive_args:
                    if len(code) > current_segment_binary_offset:
                        segment_size = len(code) - current_segment_binary_offset
                        segments.append((current_segment_start, segment_size, current_segment_binary_offset))

                    location_counter = int(line.directive_args[0], 16)
                    current_segment_start = location_counter
                    current_segment_binary_offset = len(code)
                continue

            # Handle data directives
            if line.directive in ['DB', 'DW', 'DEFSTR', 'DS']:
                try:
                    if line.directive == 'DB':
                        data_bytes = self.data_generator.generate_db_data(line.directive_args, symbol_table)
                    elif line.directive == 'DW':
                        data_bytes = self.data_generator.generate_dw_data(line.directive_args, symbol_table)
                    elif line.directive == 'DEFSTR':
                        data_bytes = self.data_generator.generate_defstr_data(line.directive_args, symbol_table)
                    elif line.directive == 'DS':
                        size = int(line.directive_args[0].strip()) if line.directive_args else 0
                        data_bytes = [0] * size

                    code.extend(data_bytes)
                    location_counter += len(data_bytes)
                    self._trace(f"Line {line.line_num} ({line.directive}): {[f'0x{b:02X}' for b in data_bytes]}")
                except Exception as e:
                    self.errors.append(f"Line {line.line_num}: {e}")
                continue

            # Skip register-only mnemonics (no standalone opcode form)
            if (line.instruction in self.instruction_set.registers
                    and line.instruction not in self.instruction_set.instructions):
                continue

            try:
                instruction_bytes = self.code_generator.generate_instruction(line, symbol_table, location_counter)
                code.extend(instruction_bytes)
                location_counter += len(instruction_bytes)
                self._trace(f"Line {line.line_num}: {[f'0x{b:02X}' for b in instruction_bytes]}")
            except Exception as e:
                self.errors.append(f"Line {line.line_num}: {e}")
                continue

        # Final segment
        if len(code) > current_segment_binary_offset:
            segment_size = len(code) - current_segment_binary_offset
            segments.append((current_segment_start, segment_size, current_segment_binary_offset))

        return code, segments

    def assemble(self, filename: str) -> bool:
        """Assemble a file"""
        try:
            # Parse
            lines = self.parser.parse_file(filename)

            # First pass
            self._emit("First pass...")
            symbol_table = self.first_pass(lines)
            self._emit(f"Symbol table: {symbol_table}")

            # Second pass
            self._emit("Second pass...")
            machine_code, segments = self.second_pass(lines, symbol_table)

            if self.errors:
                self._emit("Assembly failed due to errors:")
                for error in self.errors:
                    self._emit(f"  {error}")
                return False

            # Write output files
            base_name = os.path.splitext(filename)[0]
            output_file = f"{base_name}.bin"

            with open(output_file, 'wb') as f:
                f.write(machine_code)

            if segments:
                org_file = f"{base_name}.org"
                with open(org_file, 'w') as f:
                    f.write("# ORG segment information\n")
                    f.write("# Format: <start_address> <length> <binary_offset>\n")
                    for start_addr, length, bin_offset in segments:
                        f.write(f"0x{start_addr:04X} {length} {bin_offset}\n")
                self._emit(f"ORG information written to {org_file}")

            sym_file = f"{base_name}.sym"
            with open(sym_file, 'w') as f:
                f.write("# Symbol table\n")
                f.write("# Format: <symbol> <value>\n")
                for symbol, value in symbol_table.items():
                    f.write(f"{symbol} {value}\n")
            self._emit(f"Symbol table written to {sym_file}")

            self._emit(f"Assembly complete: {len(machine_code)} bytes written to {output_file}")
            return True

        except Exception as e:
            self._emit(f"Assembly failed: {e}")
            import traceback
            if self.log is not None:
                self._emit(traceback.format_exc())
            return False


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <file.asm>")
        return 1

    filename = sys.argv[1]
    assembler = Assembler(log=print, trace=True)

    if assembler.assemble(filename):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
