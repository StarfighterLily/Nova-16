"""
Nova-16 Assembler Code Generator

Pass 2: encode IR nodes into machine code using the symbol table.  This module
also contains the operand classifier and encoder, replacing the regex-heavy
implementation in the old assembler.
"""

import re
from typing import Dict, List, Optional, Tuple

from .ir import IRNode, Instruction, Data, Directive
from .symbols import SymbolTable, SymbolError


class CodeGenError(Exception):
    """Error during code generation."""
    pass


# ---------------------------------------------------------------------------
# Instruction set metadata
# ---------------------------------------------------------------------------

def _load_opcodes() -> Dict[str, Tuple[int, int]]:
    """Load instruction metadata from opcodes.py."""
    from opcodes import opcodes
    info: Dict[str, Tuple[int, int]] = {}
    for mnemonic, opcode_str, size in opcodes:
        opcode = int(opcode_str, 16)
        info[mnemonic.upper()] = (opcode, size)
    return info


INSTRUCTION_INFO = _load_opcodes()

# Register codes from opcodes.py
REGISTER_CODES: Dict[str, int] = {}
for mnemonic, opcode_str, _ in __import__("opcodes").opcodes:
    if mnemonic.upper() in {
        f"R{i}" for i in range(10)
    } | {
        f"P{i}" for i in range(10)
    } | {
        f"P{i}:" for i in range(10)
    } | {
        f":P{i}" for i in range(10)
    } | {
        "VX", "VY", "VM", "VC", "VL",
        "TT", "TM", "TC", "TS", "C0", "C1",
        "MX", "MY", "MB",
        "SP", "FP", "SA", "SF", "SV", "SW",
        "PA", "PB", "PC", "PD",
        "BANK",
    }:
        REGISTER_CODES[mnemonic.upper()] = int(opcode_str, 16)


# ---------------------------------------------------------------------------
# Operand classification
# ---------------------------------------------------------------------------

class OperandType:
    REGISTER = "register"
    IMMEDIATE8 = "imm8"
    IMMEDIATE16 = "imm16"
    REGISTER_INDIRECT = "reg_indirect"
    REGISTER_INDEXED = "reg_indexed"
    DIRECT = "direct"


def _parse_immediate(text: str, symbols: SymbolTable, bit_width: int = 16) -> int:
    """Resolve an immediate value from text."""
    text = text.strip()
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16)
    if text.startswith("'") and text.endswith("'"):
        content = text[1:-1]
        if content.startswith("\\") and len(content) == 2:
            mapping = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'", '"': '"'}
            return ord(mapping.get(content[1], content[1]))
        return ord(content)
    if text.lstrip("-").isdigit():
        return int(text)
    if text in symbols:
        return symbols.resolve(text)
    # High/low byte of symbol:  SYMBOL:  or  :SYMBOL
    if text.endswith(":") and text[:-1] in symbols:
        val = symbols.resolve(text[:-1])
        return (val >> 8) & 0xFF
    if text.startswith(":") and text[1:] in symbols:
        val = symbols.resolve(text[1:])
        return val & 0xFF
    raise CodeGenError(f"Undefined symbol: {text}")


def classify_operand(text: str, symbols: SymbolTable) -> str:
    """Classify an operand string into an OperandType."""
    text = text.strip()
    upper = text.upper()

    if upper in REGISTER_CODES:
        return OperandType.REGISTER

    # Direct memory [0xaddr]
    if re.match(r"^\[0x[0-9A-Fa-f]{1,4}\]$", text):
        return OperandType.DIRECT

    # Stack/frame pointer offset [SP+4] [FP-8]
    if re.match(r"^\[(SP|FP)\s*[+-]\s*\d+\]$", text, re.IGNORECASE):
        return OperandType.REGISTER_INDEXED

    # General register offset [P0+4] [R3-8]
    if re.match(r"^\[[PR]\d+\s*[+-]\s*\d+\]$", text, re.IGNORECASE):
        return OperandType.REGISTER_INDEXED

    # Register indirect [reg]
    if re.match(r"^\[[A-Za-z0-9:]+\]$", text):
        return OperandType.REGISTER_INDIRECT

    # Register indexed [reg + index]
    if re.match(r"^\[[A-Za-z0-9]+\s*\+\s*[A-Za-z0-9]+\]$", text):
        return OperandType.REGISTER_INDEXED

    # High/low byte symbol forms
    if text.endswith(":") and text[:-1] in symbols:
        return OperandType.IMMEDIATE8
    if text.startswith(":") and text[1:] in symbols:
        return OperandType.IMMEDIATE8

    # If the text is a known symbol, it's always imm16 (matches old assembler).
    if text in symbols:
        return OperandType.IMMEDIATE16

    # Try to resolve as immediate
    try:
        val = _parse_immediate(text, symbols)
        # Match old assembler behavior:
        # - Hex literals (0x00-0xFF) are imm8
        # - Decimal literals: -128 to 127 are imm8, rest are imm16
        if text.startswith("0x") or text.startswith("0X"):
            if 0 <= val <= 0xFF:
                return OperandType.IMMEDIATE8
            return OperandType.IMMEDIATE16
        if -128 <= val <= 127:
            return OperandType.IMMEDIATE8
        return OperandType.IMMEDIATE16
    except CodeGenError:
        # Default to 16-bit immediate; codegen will fail with a clear error
        return OperandType.IMMEDIATE16


def operand_size(inst: Instruction, symbols: SymbolTable) -> int:
    """Return the number of bytes consumed by operands (mode byte + data)."""
    if not inst.operands:
        return 0
    size = 1  # mode byte
    for op in inst.operands:
        op_type = classify_operand(op, symbols)
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
    return size


# ---------------------------------------------------------------------------
# Data directive sizes
# ---------------------------------------------------------------------------

def _parse_string_literal(text: str) -> List[int]:
    """Parse a double-quoted string into a list of byte values."""
    if not (text.startswith('"') and text.endswith('"')):
        raise CodeGenError(f"Invalid string literal: {text}")
    content = text[1:-1]
    result: List[int] = []
    i = 0
    while i < len(content):
        if content[i] == "\\" and i + 1 < len(content):
            nxt = content[i + 1]
            mapping = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"'}
            result.append(ord(mapping.get(nxt, nxt)))
            i += 2
        else:
            result.append(ord(content[i]))
            i += 1
    return result


def data_size(node: Data, symbols: SymbolTable) -> int:
    """Return the number of bytes emitted by a data directive."""
    directive = node.directive.upper()
    if directive == "DB":
        size = 0
        for arg in node.args:
            arg = arg.strip()
            if arg.startswith('"') and arg.endswith('"'):
                size += len(_parse_string_literal(arg))
            else:
                size += 1
        return size
    if directive in {"DW", "DEFWORD"}:
        return len(node.args) * 2
    if directive == "DEFSTR":
        if not node.args:
            return 1
        arg = node.args[0].strip()
        return len(_parse_string_literal(arg)) + 1
    if directive in {"DS", "DEFBYTE"}:
        if not node.args:
            return 0
        return int(node.args[0].strip())
    return 0


def generate_data(node: Data, symbols: SymbolTable) -> List[int]:
    """Generate the byte list for a data directive."""
    directive = node.directive.upper()
    result: List[int] = []

    if directive == "DB":
        for arg in node.args:
            arg = arg.strip()
            if arg.startswith('"') and arg.endswith('"'):
                result.extend(_parse_string_literal(arg))
            else:
                result.append(_parse_immediate(arg, symbols, 8) & 0xFF)
        return result

    if directive in {"DW", "DEFWORD"}:
        for arg in node.args:
            val = _parse_immediate(arg, symbols, 16) & 0xFFFF
            result.append((val >> 8) & 0xFF)
            result.append(val & 0xFF)
        return result

    if directive == "DEFSTR":
        if not node.args:
            return [0]
        arg = node.args[0].strip()
        result.extend(_parse_string_literal(arg))
        result.append(0)
        return result

    if directive in {"DS", "DEFBYTE"}:
        count = int(node.args[0].strip()) if node.args else 0
        return [0] * count

    return []


# ---------------------------------------------------------------------------
# Instruction encoding
# ---------------------------------------------------------------------------

def _calculate_mode_byte(operand_types: List[str]) -> int:
    """Compute the mode byte for prefixed operand encoding."""
    mode_byte = 0
    for i, op_type in enumerate(operand_types[:3]):
        shift = i * 2
        if op_type == OperandType.REGISTER:
            mode_val = 0
        elif op_type == OperandType.IMMEDIATE8:
            mode_val = 1
        elif op_type == OperandType.IMMEDIATE16:
            mode_val = 2
        else:
            mode_val = 3
        mode_byte |= (mode_val << shift)

    if OperandType.REGISTER_INDEXED in operand_types:
        mode_byte |= (1 << 6)
    if OperandType.DIRECT in operand_types:
        mode_byte |= (1 << 7)
    return mode_byte


def _encode_register(text: str) -> int:
    return REGISTER_CODES[text.strip().upper()]


def _encode_operand(text: str, op_type: str, symbols: SymbolTable) -> List[int]:
    """Encode a single operand into bytes."""
    text = text.strip()

    if op_type == OperandType.REGISTER:
        return [_encode_register(text)]

    if op_type == OperandType.IMMEDIATE8:
        val = _parse_immediate(text, symbols, 8)
        return [val & 0xFF]

    if op_type == OperandType.IMMEDIATE16:
        val = _parse_immediate(text, symbols, 16) & 0xFFFF
        return [(val >> 8) & 0xFF, val & 0xFF]

    if op_type == OperandType.REGISTER_INDIRECT:
        m = re.match(r"^\[([A-Za-z0-9:]+)\]$", text)
        reg = m.group(1).upper()
        return [_encode_register(reg)]

    if op_type == OperandType.REGISTER_INDEXED:
        # Stack/frame pointer offset
        m = re.match(r"^\[(SP|FP)\s*([+-])\s*(\d+)\]$", text, re.IGNORECASE)
        if m:
            offset = int(m.group(3))
            if m.group(2) == "-":
                offset = (-offset) & 0xFF
            reg = "SP" if m.group(1).upper() == "SP" else "FP"
            return [_encode_register(reg), offset]

        # General register offset [P0+4] [R3-8]
        m = re.match(r"^\[([PR])(\d+)\s*([+-])\s*(\d+)\]$", text, re.IGNORECASE)
        if m:
            reg_type, num, sign, offset_str = m.groups()
            reg = f"{reg_type.upper()}{num}"
            offset = int(offset_str)
            if sign == "-":
                offset = (-offset) & 0xFF
            return [_encode_register(reg), offset]

        # General indexed [reg + index]
        m = re.match(r"^\[([A-Za-z0-9]+)\s*\+\s*([A-Za-z0-9]+)\]$", text)
        if m:
            reg = m.group(1).upper()
            index_text = m.group(2)
            if index_text.isdigit():
                index = int(index_text)
            elif index_text.startswith("0x"):
                index = int(index_text, 16)
            else:
                index = 0
            return [_encode_register(reg), index & 0xFF]

        raise CodeGenError(f"Cannot encode indexed operand: {text}")

    if op_type == OperandType.DIRECT:
        m = re.match(r"^\[0x([0-9A-Fa-f]{1,4})\]$", text)
        addr = int(m.group(1), 16)
        return [(addr >> 8) & 0xFF, addr & 0xFF]

    raise CodeGenError(f"Unsupported operand type: {op_type}")


def generate_instruction(inst: Instruction, symbols: SymbolTable,
                         location: int) -> List[int]:
    """Encode an instruction into machine-code bytes."""
    mnemonic = inst.mnemonic.upper()
    if mnemonic not in INSTRUCTION_INFO:
        raise CodeGenError(f"Unknown instruction: {mnemonic}")

    opcode, operand_count = INSTRUCTION_INFO[mnemonic]
    result = [opcode]

    # Old assembler is lenient about operand counts; match that behavior.
    if operand_count == 0:
        # Zero-operand instructions (NOP, HLT, SPBLITALL, etc.)
        return result

    # For instructions expecting operands but getting none, emit mode byte with default
    # This handles cases like SWRITE with no operand (uses VC implicitly as operand 0).
    if len(inst.operands) == 0:
        result.append(0)  # mode byte with register=0 for implicit VC operand
        return result

    if len(inst.operands) != operand_count:
        # Length mismatch: be lenient like old assembler — try to encode what we have
        pass

    operand_types = [classify_operand(op, symbols) for op in inst.operands]
    mode_byte = _calculate_mode_byte(operand_types)
    result.append(mode_byte)

    for op, op_type in zip(inst.operands, operand_types):
        result.extend(_encode_operand(op, op_type, symbols))

    return result


# ---------------------------------------------------------------------------
# Pass 2 driver
# ---------------------------------------------------------------------------

def second_pass(nodes: List[IRNode], symbols: SymbolTable,
                segments: List[Tuple[int, int, int]]) -> Tuple[bytearray, List[Tuple[int, int, int]]]:
    """Generate machine code from IR nodes and symbol table."""
    code = bytearray()
    location = 0
    current_segment_start = 0
    current_segment_bin_offset = 0
    emitted_since_org = False
    out_segments: List[Tuple[int, int, int]] = []
    errors: List[str] = []

    for node in nodes:
        try:
            if isinstance(node, Directive):
                if node.name == "ORG":
                    if emitted_since_org:
                        seg_len = location - current_segment_start
                        out_segments.append((current_segment_start, seg_len,
                                             current_segment_bin_offset))
                    location = _parse_value(node.args[0], symbols) if node.args else 0
                    current_segment_start = location
                    current_segment_bin_offset = len(code)
                    emitted_since_org = False
                    continue
                if node.name == "EQU":
                    continue

            if isinstance(node, Data):
                data_bytes = generate_data(node, symbols)
                code.extend(data_bytes)
                location += len(data_bytes)
                emitted_since_org = True
                continue

            if isinstance(node, Instruction):
                inst_bytes = generate_instruction(node, symbols, location)
                code.extend(inst_bytes)
                location += len(inst_bytes)
                emitted_since_org = True

        except Exception as e:
            errors.append(f"Line {node.line_num}: {e}")

    if emitted_since_org:
        seg_len = location - current_segment_start
        out_segments.append((current_segment_start, seg_len, current_segment_bin_offset))

    if errors:
        raise CodeGenError("\n".join(errors))

    return code, out_segments or segments


def _parse_value(text: str, symbols: SymbolTable) -> int:
    """Parse a numeric or symbol value (local helper)."""
    text = text.strip()
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16)
    if text.lstrip("-").isdigit():
        return int(text)
    if text in symbols:
        return symbols.resolve(text)
    raise CodeGenError(f"Cannot resolve value: {text}")
