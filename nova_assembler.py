#!/usr/bin/env python3
"""
Nova-16 Assembler
A clean, well-structured assembler for the Nova-16 CPU architecture.
"""

import re
import os
import sys
from typing import Dict, List, Tuple, Optional, Union
from opcodes import opcodes


class InstructionSet:
    """Manages the instruction set and register mappings from opcodes.py"""
    
    def __init__(self):
        self.instructions: Dict[str, Tuple[str, int]] = {}  # mnemonic -> (opcode, size)
        self.registers: Dict[str, str] = {}                 # register -> direct opcode
        self.indirect_registers: Dict[str, str] = {}        # register -> indirect opcode
        self.indexed_registers: Dict[str, str] = {}         # register -> indexed opcode
        self.high_byte_registers: Dict[str, str] = {}       # register -> high byte opcode
        self.low_byte_registers: Dict[str, str] = {}        # register -> low byte opcode
        
        self._build_lookup_tables()
    
    def _build_lookup_tables(self):
        """Build lookup tables from opcodes.py"""
        reg_names = {f"R{i}" for i in range(10)} | {f"P{i}" for i in range(10)} | {"VX", "VY", "VM"} | {"TT", "TM", "TC", "TS"} | {"VL"} | {"SP", "FP"} | {"SA", "SF", "SV", "SW"}
        
        for mnemonic, opcode_str, size in opcodes:
            opcode_val = int(opcode_str, 16)
            
            # Handle register opcodes
            if mnemonic in reg_names:
                if (0x9D <= opcode_val <= 0xA2) or (0xA3 <= opcode_val <= 0xA4) or (0xA5 <= opcode_val <= 0xBE):  # Direct registers (sound + VM + VL + timer + standard)
                    self.registers[mnemonic] = opcode_str
                elif 0xBF <= opcode_val <= 0xD4:  # Indirect registers
                    self.indirect_registers[mnemonic] = opcode_str
                elif 0xE9 <= opcode_val <= 0xFE:  # Indexed registers
                    self.indexed_registers[mnemonic] = opcode_str
            
            # Handle high/low byte register accessors
            elif mnemonic.endswith(':'):  # High byte (P0:, P1:, etc.)
                self.high_byte_registers[mnemonic] = opcode_str
            elif mnemonic.startswith(':'):  # Low byte (:P0, :P1, etc.)
                self.low_byte_registers[mnemonic] = opcode_str
            
            # Handle instruction opcodes
            else:
                self.instructions[mnemonic] = (opcode_str, size)
    
    def get_instruction_info(self, mnemonic: str) -> Optional[Tuple[str, int]]:
        """Get instruction opcode and size"""
        return self.instructions.get(mnemonic)
    
    def get_register_opcode(self, register: str) -> Optional[str]:
        """Get direct register opcode"""
        return self.registers.get(register)
    
    def is_register(self, token: str) -> bool:
        """Check if token is a register name"""
        return token in self.registers
    
    def is_high_byte_register(self, token: str) -> bool:
        """Check if token is a high byte register"""
        return token in self.high_byte_registers
    
    def is_low_byte_register(self, token: str) -> bool:
        """Check if token is a low byte register"""
        return token in self.low_byte_registers


class Token:
    """Represents a parsed token in assembly code"""
    
    def __init__(self, value: str, token_type: str, line_num: int = 0):
        self.value = value
        self.type = token_type  # 'instruction', 'register', 'immediate', 'label', etc.
        self.line_num = line_num


class AssemblyLine:
    """Represents a parsed line of assembly code"""
    
    def __init__(self, line_num: int):
        self.line_num = line_num
        self.label: Optional[str] = None
        self.instruction: Optional[str] = None
        self.operands: List[str] = []
        self.comment: Optional[str] = None
        self.directive: Optional[str] = None
        self.directive_args: List[str] = []


class Parser:
    """Parses assembly source code into structured data"""
    
    def __init__(self, instruction_set: InstructionSet):
        self.instruction_set = instruction_set
        
        # Regex patterns
        self.patterns = {
            'comment': re.compile(r';.*$'),
            'label': re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*):'),
            'directive': re.compile(r'^\s*(ORG|EQU|DB|DW|DEFSTR)\s+', re.IGNORECASE),
            'hex16': re.compile(r'^0x[0-9A-Fa-f]{1,4}$'),
            'hex8': re.compile(r'^0x[0-9A-Fa-f]{1,2}$'),
            'decimal': re.compile(r'^\d+$'),
            'indirect': re.compile(r'^\[([A-Za-z0-9:]+)\]$'),
            'indexed': re.compile(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$'),
            'direct': re.compile(r'^\[0x([0-9A-Fa-f]{1,4})\]$'),
            'string': re.compile(r'^"([^"\\]|\\.)*"$'),
        }
    
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
        
        # Add the last operand
        if current_operand.strip():
            operands.append(current_operand.strip())
        
        return operands
    
    def parse_line(self, line: str, line_num: int) -> Optional[AssemblyLine]:
        """Parse a sinVLe line of assembly code"""
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
        
        # Check for label
        label_match = self.patterns['label'].match(line)
        if label_match:
            asm_line.label = label_match.group(1)
            line = line[label_match.end():].strip()
        
        if not line:
            return asm_line
        
        # Check for directive (including EQU without label)
        directive_match = self.patterns['directive'].match(line)
        if directive_match:
            parts = line.split(None, 1)
            asm_line.directive = parts[0].upper()
            if len(parts) > 1:
                # For data directives, parse operands carefully to preserve strings
                if asm_line.directive in ['DB', 'DW', 'DEFSTR']:
                    operand_str = parts[1]
                    # Parse operands while respecting quoted strings
                    asm_line.directive_args = self._parse_operands_with_strings(operand_str)
                else:
                    asm_line.directive_args = [parts[1].strip()]
            return asm_line
        
        # Check for EQU directive (label EQU value format)
        if 'EQU' in line.upper():
            parts = line.split(None, 2)
            if len(parts) >= 3 and parts[1].upper() == 'EQU':
                if not asm_line.label:  # If we didn't find a label with colon, use first part
                    asm_line.label = parts[0]
                asm_line.directive = 'EQU'
                asm_line.directive_args = [parts[2].strip()]
                return asm_line
        
        # Parse instruction and operands
        parts = line.split(None, 1)
        if parts:
            asm_line.instruction = parts[0].upper()
            if len(parts) > 1:
                # Split operands by comma
                operand_str = parts[1]
                asm_line.operands = [op.strip() for op in operand_str.split(',')]
        
        return asm_line
    
    def parse_file(self, filename: str) -> List[AssemblyLine]:
        """Parse an entire assembly file"""
        lines = []
        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    parsed_line = self.parse_line(line, line_num)
                    if parsed_line:
                        lines.append(parsed_line)
        except IOError as e:
            raise Exception(f"Could not read file {filename}: {e}")
        
        return lines


class OperandType:
    """Enumeration of operand types"""
    REGISTER = "reg"
    IMMEDIATE8 = "imm8"
    IMMEDIATE16 = "imm16"
    REGISTER_INDIRECT = "regIndir"
    REGISTER_INDEXED = "regIndex"
    DIRECT = "direct"


class OperandClassifier:
    """Classifies operands into types"""
    
    def __init__(self, instruction_set: InstructionSet):
        self.instruction_set = instruction_set
        self.patterns = {
            'hex16': re.compile(r'^0x[0-9A-Fa-f]{3,4}$'),
            'hex8': re.compile(r'^0x[0-9A-Fa-f]{1,2}$'),
            'decimal': re.compile(r'^\d+$'),
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
            raise Exception(f"Invalid string literal: {string_operand}")
        
        # Remove quotes
        content = string_operand[1:-1]
        result = []
        i = 0
        
        while i < len(content):
            if content[i] == '\\' and i + 1 < len(content):
                # Handle escape sequences
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
                    # Unknown escape, treat literally
                    result.append(ord(next_char))
                i += 2
            else:
                result.append(ord(content[i]))
                i += 1
        
        return result
    
    def classify_operand(self, operand: str, symbol_table: Dict[str, str] = None) -> str:
        """Classify an operand and return its type"""
        operand = operand.strip()
        
        # Check for register (hardcoded list for new prefixed format)
        valid_registers = {
            # 8-bit registers
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
            # 16-bit registers  
            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
            # Special registers
            'VX', 'VY', 'VM', 'VL', 'TT', 'TM', 'TC', 'TS', 'SP', 'FP'
        }
        
        if operand in valid_registers:
            return OperandType.REGISTER
        
        # Check for direct memory addressing
        direct_match = self.patterns['direct'].match(operand)
        if direct_match:
            return OperandType.DIRECT
        
        # Check for direct indexed addressing (not supported yet)
        direct_indexed_match = re.match(r'^\[0x([0-9A-Fa-f]{1,4})\s*\+\s*([A-Za-z0-9]+)\]$', operand)
        if direct_indexed_match:
            raise Exception(f"Direct indexed memory access {operand} is not supported. Use register indirect with offset instead: load address into a register first, then use [register+offset].")
        
        # Check for frame pointer offset addressing
        fp_offset_match = self.patterns['fp_offset'].match(operand)
        if fp_offset_match:
            return OperandType.REGISTER_INDEXED
        
        # Check for stack pointer offset addressing
        sp_offset_match = self.patterns['sp_offset'].match(operand)
        if sp_offset_match:
            return OperandType.REGISTER_INDEXED
        
        # Check for general register offset addressing
        reg_offset_match = self.patterns['reg_offset'].match(operand)
        if reg_offset_match:
            return OperandType.REGISTER_INDEXED
        
        # Check for indirect addressing
        indirect_match = self.patterns['indirect'].match(operand)
        if indirect_match:
            return OperandType.REGISTER_INDIRECT
        
        # Check for indexed addressing
        indexed_match = self.patterns['indexed'].match(operand)
        if indexed_match:
            return OperandType.REGISTER_INDEXED
        
        # Check for high byte symbol (SYMBOL:)
        if operand.endswith(':') and len(operand) > 1:
            symbol_name = operand[:-1]
            if symbol_table and symbol_name in symbol_table:
                return OperandType.IMMEDIATE8  # High byte is always 8-bit
        
        # Check for low byte symbol (:SYMBOL)
        if operand.startswith(':') and len(operand) > 1:
            symbol_name = operand[1:]
            if symbol_table and symbol_name in symbol_table:
                return OperandType.IMMEDIATE8  # Low byte is always 8-bit
        
        # Check symbol table first for labels
        if symbol_table and operand in symbol_table:
            return OperandType.IMMEDIATE16
        
        # Check for immediate values
        if self.patterns['hex16'].match(operand):
            val = int(operand, 16)
            return OperandType.IMMEDIATE16 if val > 127 else OperandType.IMMEDIATE8
        elif self.patterns['hex8'].match(operand):
            val = int(operand, 16)
            return OperandType.IMMEDIATE16 if val > 127 else OperandType.IMMEDIATE8
        elif self.patterns['decimal'].match(operand):
            val = int(operand)
            return OperandType.IMMEDIATE16 if val > 127 else OperandType.IMMEDIATE8
        
        # Default to 16-bit immediate for unknown symbols
        return OperandType.IMMEDIATE16


class DataGenerator:
    """Generates data bytes from assembler directives"""
    
    def __init__(self, parser: Parser):
        self.parser = parser
    
    def parse_string_literal(self, string_operand: str) -> List[int]:
        """Parse a string literal and return list of byte values"""
        if not (string_operand.startswith('"') and string_operand.endswith('"')):
            raise Exception(f"Invalid string literal: {string_operand}")
        
        # Remove quotes
        content = string_operand[1:-1]
        result = []
        i = 0
        
        while i < len(content):
            if content[i] == '\\' and i + 1 < len(content):
                # Handle escape sequences
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
                    # Unknown escape, treat literally
                    result.append(ord(next_char))
                i += 2
            else:
                result.append(ord(content[i]))
                i += 1
        
        return result
    
    def generate_db_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate data bytes for DB directive"""
        result = []
        
        for arg in args:
            arg = arg.strip()
            
            # Check if it's a string literal
            if self.parser.patterns['string'].match(arg):
                string_bytes = self.parse_string_literal(arg)
                result.extend(string_bytes)
            else:
                # Parse as numeric value
                if arg.startswith('0x'):
                    val = int(arg, 16)
                elif arg.isdigit():
                    val = int(arg)
                elif symbol_table and arg in symbol_table:
                    symbol_val = symbol_table[arg].strip()
                    if symbol_val.startswith('0x'):
                        val = int(symbol_val, 16)
                    else:
                        val = int(symbol_val)
                else:
                    raise Exception(f"Unknown value in DB: {arg}")
                
                # DB stores sinVLe bytes
                if val > 255:
                    raise Exception(f"Value {val} too large for DB (max 255)")
                result.append(val)
        
        return result
    
    def generate_dw_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate data bytes for DW directive (16-bit words)"""
        result = []
        
        for arg in args:
            arg = arg.strip()
            
            # Parse as numeric value (DW doesn't support strings)
            if arg.startswith('0x'):
                val = int(arg, 16)
            elif arg.isdigit():
                val = int(arg)
            elif symbol_table and arg in symbol_table:
                symbol_val = symbol_table[arg].strip()
                if symbol_val.startswith('0x'):
                    val = int(symbol_val, 16)
                else:
                    val = int(symbol_val)
            else:
                raise Exception(f"Unknown value in DW: {arg}")
            
            # DW stores 16-bit words (high byte first, then low byte)
            if val > 65535:
                raise Exception(f"Value {val} too large for DW (max 65535)")
            result.append((val >> 8) & 0xFF)  # High byte
            result.append(val & 0xFF)         # Low byte
        
        return result
    
    def generate_defstr_data(self, args: List[str], symbol_table: Dict[str, str]) -> List[int]:
        """Generate null-terminated string data for DEFSTR directive"""
        if len(args) != 1:
            raise Exception("DEFSTR requires exactly one string argument")
        
        arg = args[0].strip()
        
        if not self.parser.patterns['string'].match(arg):
            raise Exception(f"DEFSTR requires a string literal, got: {arg}")
        
        string_bytes = self.parse_string_literal(arg)
        
        # Null-terminated format: [string_bytes...][0x00]
        if len(string_bytes) > 254:  # Reserve 1 byte for null terminator
            raise Exception(f"String too long for DEFSTR (max 254 chars + null terminator), got {len(string_bytes)}")
        
        result = list(string_bytes)  # String content
        result.append(0)             # Null terminator
        
        return result


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
        
        for i, op_type in enumerate(operand_types[:3]):  # Max 3 operands
            shift = i * 2
            if op_type == OperandType.REGISTER:
                mode_val = 0  # 00
            elif op_type == OperandType.IMMEDIATE8:
                mode_val = 1  # 01
            elif op_type == OperandType.IMMEDIATE16:
                mode_val = 2  # 10
            elif op_type in [OperandType.REGISTER_INDIRECT, OperandType.REGISTER_INDEXED, OperandType.DIRECT]:
                mode_val = 3  # 11
            else:
                mode_val = 0  # Default to register
            
            mode_byte |= (mode_val << shift)
        
        # Bit 6: Indexed flag (set if any operand is REGISTER_INDEXED)
        if OperandType.REGISTER_INDEXED in operand_types:
            mode_byte |= (1 << 6)
        
        # Bit 7: Direct flag (set if any operand is DIRECT)
        if OperandType.DIRECT in operand_types:
            mode_byte |= (1 << 7)
        
        return mode_byte
    
    def build_instruction_mnemonic(self, instruction: str, operands: List[str], symbol_table: Dict[str, str]) -> str:
        """Build core instruction mnemonic (no variants for new prefixed system)"""
        return instruction
    
    def encode_operand_new(self, operand: str, operand_type: str, symbol_table: Dict[str, str]) -> List[int]:
        """Encode operand for new prefixed system"""
        operand = operand.strip()
        
        if operand_type == OperandType.REGISTER:
            # Registers encoded using CPU lookup table codes
            if operand.startswith('R') and len(operand) <= 3:
                reg_num = int(operand[1:])
                return [0xA9 + reg_num]  # R0-R9 = 0xA9-0xB2
            elif operand.startswith('P') and len(operand) <= 3:
                reg_num = int(operand[1:])
                return [0xB3 + reg_num]  # P0-P9 = 0xB3-0xBC
            elif operand == 'VX':
                return [0xBD]  # VX
            elif operand == 'VY':
                return [0xBE]  # VY
            elif operand == 'VM':
                return [0x5F]  # VM
            elif operand == 'VL':
                return [0x60]  # VL
            elif operand == 'TT':
                return [0x61]  # TT
            elif operand == 'TM':
                return [0x62]  # TM
            elif operand == 'TC':
                return [0x63]  # TC
            elif operand == 'TS':
                return [0x64]  # TS
            elif operand == 'SP':
                return [18]  # SP = P8
            elif operand == 'FP':
                return [19]  # FP = P9
            else:
                raise Exception(f"Unknown register: {operand}")
        
        elif operand_type == OperandType.IMMEDIATE8:
            if operand.startswith('0x'):
                val = int(operand, 16)
            elif operand.isdigit():
                val = int(operand)
            elif symbol_table and operand in symbol_table:
                symbol_val = symbol_table[operand].strip()
                val = int(symbol_val, 16) if symbol_val.startswith('0x') else int(symbol_val)
            else:
                val = 0  # Unknown symbol defaults to 0
            return [val & 0xFF]
        
        elif operand_type == OperandType.IMMEDIATE16:
            if operand.startswith('0x'):
                val = int(operand, 16)
            elif operand.isdigit():
                val = int(operand)
            elif symbol_table and operand in symbol_table:
                symbol_val = symbol_table[operand].strip()
                val = int(symbol_val, 16) if symbol_val.startswith('0x') else int(symbol_val)
            else:
                val = 0  # Unknown symbol defaults to 0
            return [(val >> 8) & 0xFF, val & 0xFF]
        
        elif operand_type == OperandType.REGISTER_INDIRECT:
            indirect_match = re.match(r'^\[([A-Za-z0-9]+)\]$', operand)
            if indirect_match:
                reg_name = indirect_match.group(1)
                if reg_name.startswith('R'):
                    reg_num = 0xA9 + int(reg_name[1:])  # R0-R9 = 0xA9-0xB2
                elif reg_name.startswith('P'):
                    reg_num = 0xB3 + int(reg_name[1:])  # P0-P9 = 0xB3-0xBC
                elif reg_name == 'SP':
                    reg_num = 0xB3 + 8  # SP = P8 = 0xBB
                elif reg_name == 'FP':
                    reg_num = 0xB3 + 9  # FP = P9 = 0xBC
                else:
                    raise Exception(f"Unknown register for indirect: {reg_name}")
                return [reg_num]
            else:
                raise Exception(f"Invalid indirect operand: {operand}")
        
        elif operand_type == OperandType.REGISTER_INDEXED:
            indexed_match = re.match(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$', operand)
            if indexed_match:
                reg_name = indexed_match.group(1)
                index_name = indexed_match.group(2)
                
                # Base register
                if reg_name.startswith('R'):
                    reg_num = 0xA9 + int(reg_name[1:])  # R0-R9 = 0xA9-0xB2
                elif reg_name.startswith('P'):
                    reg_num = 0xB3 + int(reg_name[1:])  # P0-P9 = 0xB3-0xBC
                elif reg_name == 'SP':
                    reg_num = 0xB3 + 8  # SP = P8 = 0xBB
                elif reg_name == 'FP':
                    reg_num = 0xB3 + 9  # FP = P9 = 0xBC
                else:
                    raise Exception(f"Unknown base register for indexed: {reg_name}")
                
                # Index register/value
                if index_name.startswith('R'):
                    index_num = int(index_name[1:])
                elif index_name.startswith('P'):
                    index_num = int(index_name[1:]) + 10
                elif index_name.isdigit():
                    index_num = int(index_name)
                elif index_name.startswith('0x'):
                    index_num = int(index_name, 16)
                else:
                    index_num = 0  # Default
                
                return [reg_num, index_num & 0xFF]
            else:
                raise Exception(f"Invalid indexed operand: {operand}")
        
        elif operand_type == OperandType.DIRECT:
            direct_match = re.match(r'^\[0x([0-9A-Fa-f]{1,4})\]$', operand)
            if direct_match:
                addr = int(direct_match.group(1), 16)
                return [(addr >> 8) & 0xFF, addr & 0xFF]
            else:
                raise Exception(f"Invalid direct operand: {operand}")
        
        else:
            raise Exception(f"Unsupported operand type: {operand_type}")
    
    def generate_instruction(self, asm_line: AssemblyLine, symbol_table: Dict[str, str]) -> List[int]:
        """Generate machine code for new prefixed operand instruction"""
        if not asm_line.instruction:
            return []
        
        # Get core instruction opcode
        instr_info = self.instruction_set.get_instruction_info(asm_line.instruction)
        if not instr_info:
            raise Exception(f"Unknown instruction: {asm_line.instruction} (line {asm_line.line_num})")
        
        opcode_str, operand_count = instr_info
        result = [int(opcode_str, 16)]
        
        # For no-operand instructions, don't add mode byte
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
                operand_bytes = self.encode_operand_new(operand, operand_types[i], symbol_table)
                result.extend(operand_bytes)
        
        return result
    
    def encode_operand(self, operand: str, symbol_table: Dict[str, str], expected_type: str = None) -> List[int]:
        """Encode a sinVLe operand into bytes"""
        operand = operand.strip()
        
        # Direct register
        if operand in self.instruction_set.registers:
            opcode = self.instruction_set.registers[operand]
            return [int(opcode, 16)]
        
        # High byte register
        if operand in self.instruction_set.high_byte_registers:
            opcode = self.instruction_set.high_byte_registers[operand]
            return [int(opcode, 16)]
        
        # Low byte register
        if operand in self.instruction_set.low_byte_registers:
            opcode = self.instruction_set.low_byte_registers[operand]
            return [int(opcode, 16)]
        
        # Indirect register
        indirect_match = re.match(r'^\[([A-Za-z0-9:]+)\]$', operand)
        if indirect_match:
            reg_name = indirect_match.group(1)
            if reg_name in self.instruction_set.indirect_registers:
                opcode = self.instruction_set.indirect_registers[reg_name]
                return [int(opcode, 16)]
        
        # Direct memory address
        direct_match = re.match(r'^\[0x([0-9A-Fa-f]{1,4})\]$', operand)
        if direct_match:
            addr_str = direct_match.group(1)
            addr = int(addr_str, 16)
            return [(addr >> 8) & 0xFF, addr & 0xFF]  # Return 16-bit address
        
        # Indexed register
        indexed_match = re.match(r'^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$', operand)
        if indexed_match:
            reg_name = indexed_match.group(1)
            offset = indexed_match.group(2)
            if reg_name in self.instruction_set.indexed_registers:
                reg_opcode = int(self.instruction_set.indexed_registers[reg_name], 16)
                if offset.isdigit():
                    offset_val = int(offset)
                elif offset.startswith('0x'):
                    offset_val = int(offset, 16)
                else:
                    offset_val = int(symbol_table.get(offset, '0'), 16) if symbol_table else 0
                return [reg_opcode, offset_val & 0xFF]
        
        # Frame pointer offset addressing
        fp_offset_match = re.match(r'^\[(FP|fp)\s*([+-])\s*(\d+)\]$', operand)
        if fp_offset_match:
            sign = fp_offset_match.group(2)
            offset_str = fp_offset_match.group(3)
            offset_val = int(offset_str)
            if sign == '-':
                offset_val = (-offset_val) & 0xFF  # Convert to 8-bit two's complement
            
            # Use FP indexed opcode (0xFC) with the offset
            return [0xFC, offset_val]
        
        # Stack pointer offset addressing
        sp_offset_match = re.match(r'^\[(SP|sp)\s*([+-])\s*(\d+)\]$', operand)
        if sp_offset_match:
            sign = sp_offset_match.group(2)
            offset_str = sp_offset_match.group(3)
            offset_val = int(offset_str)
            if sign == '-':
                offset_val = (-offset_val) & 0xFF  # Convert to 8-bit two's complement
            
            # Use SP indexed opcode (0xFB) with the offset
            return [0xFB, offset_val]
        
        # General register offset addressing (P0-P9, R0-R9)
        reg_offset_match = re.match(r'^\[([PR])(\d+)\s*([+-])\s*(\d+)\]$', operand)
        if reg_offset_match:
            reg_type = reg_offset_match.group(1)
            reg_num = int(reg_offset_match.group(2))
            sign = reg_offset_match.group(3)
            offset_str = reg_offset_match.group(4)
            offset_val = int(offset_str)
            if sign == '-':
                offset_val = (-offset_val) & 0xFF  # Convert to 8-bit two's complement
            
            # Calculate indexed register opcode
            if reg_type == 'P' and 0 <= reg_num <= 9:
                reg_opcode = 0xF3 + reg_num  # P0-P9 indexed: 0xF3-0xFC
            elif reg_type == 'R' and 0 <= reg_num <= 9:
                reg_opcode = 0xE9 + reg_num  # R0-R9 indexed: 0xE9-0xF2
            else:
                raise Exception(f"Invalid register in offset addressing: {reg_type}{reg_num}")
            
            return [reg_opcode, offset_val]
        
        # High byte of symbol (SYMBOL:)
        if operand.endswith(':') and len(operand) > 1:
            symbol_name = operand[:-1]
            if symbol_table and symbol_name in symbol_table:
                symbol_val = symbol_table[symbol_name].strip()
                if symbol_val.startswith('0x'):
                    val = int(symbol_val, 16)
                else:
                    val = int(symbol_val)
                return [(val >> 8) & 0xFF]  # High byte only
            else:
                raise Exception(f"Unknown symbol for high byte: {symbol_name}")
        
        # Low byte of symbol (:SYMBOL)
        if operand.startswith(':') and len(operand) > 1:
            symbol_name = operand[1:]
            if symbol_table and symbol_name in symbol_table:
                symbol_val = symbol_table[symbol_name].strip()
                if symbol_val.startswith('0x'):
                    val = int(symbol_val, 16)
                else:
                    val = int(symbol_val)
                return [val & 0xFF]  # Low byte only
            else:
                raise Exception(f"Unknown symbol for low byte: {symbol_name}")
        
        # Immediate value
        if operand.startswith('0x'):
            val = int(operand, 16)
        elif operand.isdigit():
            val = int(operand)
        elif symbol_table and operand in symbol_table:
            symbol_val = symbol_table[operand].strip()
            if symbol_val.startswith('0x'):
                val = int(symbol_val, 16)
            else:
                val = int(symbol_val)
        else:
            raise Exception(f"Unknown operand: {operand}")
        
        # Return as 8-bit or 16-bit value based on expected type
        if expected_type == OperandType.IMMEDIATE16:
            return [(val >> 8) & 0xFF, val & 0xFF]  # Always 2 bytes for imm16
        elif expected_type == OperandType.IMMEDIATE8:
            return [val & 0xFF]  # Always 1 byte for imm8
        else:
            # Fallback: auto-detect based on value size
            if val <= 0xFF:
                return [val]
            else:
                return [(val >> 8) & 0xFF, val & 0xFF]
    
    def generate_instruction(self, asm_line: AssemblyLine, symbol_table: Dict[str, str]) -> List[int]:
        """Generate machine code for new prefixed operand instruction"""
        if not asm_line.instruction:
            return []
        
        # Get core instruction opcode
        instr_info = self.instruction_set.get_instruction_info(asm_line.instruction)
        if not instr_info:
            raise Exception(f"Unknown instruction: {asm_line.instruction} (line {asm_line.line_num})")
        
        opcode_str, operand_count = instr_info
        result = [int(opcode_str, 16)]
        
        # For no-operand instructions, don't add mode byte
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
                operand_bytes = self.encode_operand_new(operand, operand_types[i], symbol_table)
                result.extend(operand_bytes)
        
        return result


class Assembler:
    """Main assembler class"""
    
    def __init__(self):
        self.instruction_set = InstructionSet()
        self.parser = Parser(self.instruction_set)
        self.code_generator = CodeGenerator(self.instruction_set)
        self.data_generator = DataGenerator(self.parser)
        self.symbol_table: Dict[str, str] = {}
        self.location_counter = 0
    
    def first_pass(self, lines: List[AssemblyLine]) -> Dict[str, str]:
        """First pass: build symbol table and calculate addresses"""
        symbol_table = {}
        location_counter = 0
        
        for line in lines:
            # Handle labels first (they can appear with directives or instructions)
            if line.label:
                symbol_table[line.label] = f"0x{location_counter:04X}"
            
            # Handle ORG directive
            if line.directive == 'ORG':
                if line.directive_args:
                    location_counter = int(line.directive_args[0], 16)
                continue
            
            # Handle EQU directive
            if line.directive == 'EQU':
                if line.label and line.directive_args:
                    symbol_table[line.label] = line.directive_args[0].strip()
                continue
            
            # Handle data directives
            if line.directive in ['DB', 'DW', 'DEFSTR']:
                # Calculate size of data directive
                if line.directive == 'DB':
                    # Each DB argument can be a byte or string
                    data_size = 0
                    for arg in line.directive_args:
                        arg = arg.strip()
                        if self.parser.patterns['string'].match(arg):
                            # String literal - count characters (excluding quotes)
                            string_bytes = self.data_generator.parse_string_literal(arg)
                            data_size += len(string_bytes)
                        else:
                            # SinVLe byte
                            data_size += 1
                elif line.directive == 'DW':
                    # Each DW argument is 2 bytes
                    data_size = len(line.directive_args) * 2
                elif line.directive == 'DEFSTR':
                    # Length-prefixed string: 1 byte for length + string length
                    if line.directive_args:
                        arg = line.directive_args[0].strip()
                        if self.parser.patterns['string'].match(arg):
                            string_bytes = self.data_generator.parse_string_literal(arg)
                            data_size = 1 + len(string_bytes)  # Length prefix + content
                        else:
                            data_size = 1  # Just length byte if invalid
                    else:
                        data_size = 1
                
                location_counter += data_size
                continue
            
            # Calculate instruction size
            if line.instruction:
                # Don't process standalone register names as instructions
                if line.instruction in self.instruction_set.registers:
                    print(f"Warning: Standalone register '{line.instruction}' on line {line.line_num}, skipping")
                    continue
                
                # For new prefixed operand system, calculate size dynamically
                # Size = 1 (opcode) + 1 (mode) + operand bytes
                size = 2  # opcode + mode byte
                
                # Add operand sizes
                for operand in line.operands:
                    op_type = self.code_generator.classifier.classify_operand(operand, symbol_table)
                    if op_type == OperandType.REGISTER:
                        size += 1  # 1 byte for register number
                    elif op_type == OperandType.IMMEDIATE8:
                        size += 1  # 1 byte
                    elif op_type == OperandType.IMMEDIATE16:
                        size += 2  # 2 bytes
                    elif op_type == OperandType.REGISTER_INDIRECT:
                        size += 1  # 1 byte for register number
                    elif op_type == OperandType.REGISTER_INDEXED:
                        size += 2  # base register + index (1 byte each)
                    elif op_type == OperandType.DIRECT:
                        size += 2  # 16-bit address
                
                location_counter += size
        
        return symbol_table
    
    def second_pass(self, lines: List[AssemblyLine], symbol_table: Dict[str, str]) -> bytearray:
        """Second pass: generate machine code"""
        code = bytearray()
        segments = []  # Track segments for ORG-aware loading
        location_counter = 0
        current_segment_start = 0
        current_segment_binary_offset = 0
        
        for line in lines:
            # Handle ORG directive
            if line.directive == 'ORG':
                if line.directive_args:
                    # Save current segment if we have code
                    if len(code) > current_segment_binary_offset:
                        segment_size = len(code) - current_segment_binary_offset
                        segments.append((current_segment_start, segment_size, current_segment_binary_offset))
                    
                    # Start new segment
                    location_counter = int(line.directive_args[0], 16)
                    current_segment_start = location_counter
                    current_segment_binary_offset = len(code)
                continue
            
            # Handle data directives
            if line.directive in ['DB', 'DW', 'DEFSTR']:
                try:
                    if line.directive == 'DB':
                        data_bytes = self.data_generator.generate_db_data(line.directive_args, symbol_table)
                    elif line.directive == 'DW':
                        data_bytes = self.data_generator.generate_dw_data(line.directive_args, symbol_table)
                    elif line.directive == 'DEFSTR':
                        data_bytes = self.data_generator.generate_defstr_data(line.directive_args, symbol_table)
                    
                    code.extend(data_bytes)
                    location_counter += len(data_bytes)
                    print(f"Line {line.line_num} ({line.directive}): {[f'0x{b:02X}' for b in data_bytes]}")
                except Exception as e:
                    print(f"Error on line {line.line_num}: {e}")
                continue
            
            # Skip EQU directives and labels
            if line.directive == 'EQU' or not line.instruction:
                continue
            
            # Skip standalone register names
            if line.instruction in self.instruction_set.registers:
                continue
            
            try:
                instruction_bytes = self.code_generator.generate_instruction(line, symbol_table)
                code.extend(instruction_bytes)
                location_counter += len(instruction_bytes)
                print(f"Line {line.line_num}: {[f'0x{b:02X}' for b in instruction_bytes]}")
            except Exception as e:
                print(f"Error on line {line.line_num}: {e}")
        
        # Save final segment
        if len(code) > current_segment_binary_offset:
            segment_size = len(code) - current_segment_binary_offset
            segments.append((current_segment_start, segment_size, current_segment_binary_offset))
        
        # Store segments for use in assemble method
        self.segments = segments
        
        return code
    
    def assemble(self, filename: str) -> bool:
        """Assemble a file"""
        try:
            # Parse the file
            lines = self.parser.parse_file(filename)
            
            # First pass
            print("First pass...")
            symbol_table = self.first_pass(lines)
            print(f"Symbol table: {symbol_table}")
            
            # Second pass
            print("Second pass...")
            machine_code = self.second_pass(lines, symbol_table)
            
            # Write binary output
            base_name = os.path.splitext(filename)[0]
            output_file = f"{base_name}.bin"
            
            with open(output_file, 'wb') as f:
                f.write(machine_code)
            
            # Write ORG segment information if we have segments
            if hasattr(self, 'segments') and self.segments:
                org_file = f"{base_name}.org"
                with open(org_file, 'w') as f:
                    f.write("# ORG segment information\n")
                    f.write("# Format: <start_address> <length> <binary_offset>\n")
                    for start_addr, length, bin_offset in self.segments:
                        f.write(f"0x{start_addr:04X} {length} {bin_offset}\n")
                print(f"ORG information written to {org_file}")
            
            print(f"Assembly complete: {len(machine_code)} bytes written to {output_file}")
            return True
            
        except Exception as e:
            print(f"Assembly failed: {e}")
            return False


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python nova_assembler.py <file.asm>")
        return 1
    
    filename = sys.argv[1]
    assembler = Assembler()
    
    if assembler.assemble(filename):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
