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
from .. import nomf


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

# Mnemonics present in opcodes.py (so the CPU allocated an opcode byte for
# them) but marked "# unimplemented" there — core/exec.py's
# HANDLER_INSTRUCTIONS has no handler for these, so the CPU raises a raw
# "Unknown opcode" exception at execution time. Rejecting them here turns a
# cryptic runtime crash into a clear assembly-time error. Keep in sync with
# nova_assembler.py's UNIMPLEMENTED_INSTRUCTIONS and the "# unimplemented"
# tags in opcodes.py if that ever changes.
UNIMPLEMENTED_INSTRUCTIONS = {"SMIX", "SECHO", "SREVERB", "SFILTER"}

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
    # Symbol-relative absolute memory: ``[label]`` / ``[label+N]``.  In
    # object mode the address field is a relocation (the linker patches it
    # once the symbol's section is placed); in executable mode the symbol
    # value (plus optional offset) encodes immediately, like a numeric
    # DIRECT address.  This is what lets separately-compiled units address
    # each other's globals through the linker.
    SYMBOL_DIRECT = "symbol_direct"
    SYMBOL_INDEXED = "symbol_indexed"


def _symbol_ref(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Split operand text that may reference a symbol.

    Returns ``(name, form)`` where form is one of ``"full"``, ``"hi"``
    (``NAME:``), ``"lo"`` (``:NAME``).  Returns ``(None, None)`` for
    non-symbol text (numbers, hex literals, registers, bracket forms).
    """
    t = text.strip()
    if not t:
        return None, None
    if t.startswith(":") and len(t) > 1:
        return t[1:].upper(), "lo"
    if t.endswith(":") and len(t) > 1:
        return t[:-1].upper(), "hi"
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return t.upper(), "full"
    return None, None


class ObjectEmitContext:
    """Live context passed through codegen while assembling a *relocatable
    object* (.nobj).

    Tracks the current byte position within the section being emitted so
    every absolute-address operand site can be recorded as a relocation
    instead of baking in a final address.

    ``symbol_index`` and ``relocatable`` are held by reference so labels
    added mid-walker (and pre-registered EXTERN symbols) are visible to
    relocations emitted for forward references.
    """

    def __init__(self, section_id: int, symbol_index, relocatable, relocs):
        self.section = section_id
        self.symbol_index = symbol_index   # live dict: symbol name -> SYMT idx
        self.relocatable = relocatable     # live set of relocatable names
        self.relocs = relocs               # growing List[nomf.Reloc]
        self.offset = 0                    # byte offset within this section

    def is_relocatable(self, name: str) -> bool:
        return name in self.relocatable

    def emit(self, rtype: int, width: int, anchor: int, symbol: str,
             addend: int = 0) -> None:
        self.relocs.append(nomf.Reloc(
            section=self.section, offset=anchor, width=width,
            rtype=rtype, symbol_index=self.symbol_index[symbol],
            addend=addend))

    def advance(self, n: int) -> None:
        self.offset += n


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

    # Symbol-relative absolute memory: ``[label]`` / ``[label+N]``.  This
    # must run after the bracket REGISTER forms above (so ``[P0]`` still
    # classifies as REGISTER_INDIRECT even if a label happened to share the
    # name) and before the plain-symbol immediate16 fall-through.
    symm = re.match(
        r"^\[([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s*([+-])\s*(0x[0-9A-Fa-f]+|\d+))?\]$", text)
    if symm and symm.group(1).upper() in symbols:
        return (OperandType.SYMBOL_DIRECT if symm.group(2) is None
                else OperandType.SYMBOL_INDEXED)

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
        # Negative values must always be encoded as a full 16-bit two's
        # complement immediate, matching nova_assembler.py. IMMEDIATE8 stores
        # a single raw byte with no sign-extension at decode time, so e.g.
        # -2 stored as a lone 0xFE loses its sign bit entirely when moved
        # into a 16-bit P register (becomes 254, not 65534/0xFFFE). Register
        # writes already mask down to the destination's actual width, so
        # using IMMEDIATE16 here is also safe for 8-bit R-register
        # destinations.
        if val < 0:
            return OperandType.IMMEDIATE16
        if val <= 127:
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
        elif op_type == OperandType.SYMBOL_DIRECT:
            size += 2
        elif op_type == OperandType.SYMBOL_INDEXED:
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


def _encode_data_arg(arg: str, symbols: SymbolTable, width: int,
                     obj_ctx: Optional[ObjectEmitContext] = None,
                     anchor: int = 0) -> List[int]:
    """Encode one data-directive value into bytes (1 byte for DB, 2 for DW).

    In object mode, symbol references become relocations (ABS16/HI8/LO8)
    encoded as zero placeholders.
    """
    arg = arg.strip()
    name, form = _symbol_ref(arg)
    if obj_ctx is not None and name is not None \
            and obj_ctx.is_relocatable(name):
        if form == "hi" or form == "lo":
            rtype = nomf.RELOC_HI8 if form == "hi" else nomf.RELOC_LO8
            obj_ctx.emit(rtype, width=8, anchor=anchor, symbol=name)
            return [0]
        if width == 16:
            obj_ctx.emit(nomf.RELOC_ABS16, width=16, anchor=anchor,
                         symbol=name)
            return [0, 0]
        raise CodeGenError(
            f"Relocatable symbol '{name}' cannot be an 8-bit data value "
            f"(use '{name}:' or ':{name}')")
    val = _parse_immediate(arg, symbols, width)
    if width == 16:
        return [(val >> 8) & 0xFF, val & 0xFF]
    return [val & 0xFF]


def generate_data(node: Data, symbols: SymbolTable,
                  obj_ctx: Optional[ObjectEmitContext] = None) -> List[int]:
    """Generate the byte list for a data directive."""
    directive = node.directive.upper()
    result: List[int] = []

    if directive == "DB":
        for arg in node.args:
            arg = arg.strip()
            if arg.startswith('"') and arg.endswith('"'):
                string_bytes = _parse_string_literal(arg)
                result.extend(string_bytes)
                if obj_ctx is not None:
                    obj_ctx.advance(len(string_bytes))
            else:
                anchor = obj_ctx.offset if obj_ctx is not None else 0
                encoded = _encode_data_arg(arg, symbols, 8, obj_ctx, anchor)
                result.extend(encoded)
                if obj_ctx is not None:
                    obj_ctx.advance(len(encoded))
        return result

    if directive in {"DW", "DEFWORD"}:
        for arg in node.args:
            anchor = obj_ctx.offset if obj_ctx is not None else 0
            encoded = _encode_data_arg(arg, symbols, 16, obj_ctx, anchor)
            result.extend(encoded)
            if obj_ctx is not None:
                obj_ctx.advance(len(encoded))
        return result

    if directive == "DEFSTR":
        if not node.args:
            if obj_ctx is not None:
                obj_ctx.advance(1)
            return [0]
        arg = node.args[0].strip()
        result.extend(_parse_string_literal(arg))
        result.append(0)
        if obj_ctx is not None:
            obj_ctx.advance(len(result))
        return result

    if directive in {"DS", "DEFBYTE"}:
        count = int(node.args[0].strip()) if node.args else 0
        if obj_ctx is not None:
            obj_ctx.advance(count)
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
    if (OperandType.DIRECT in operand_types
            or OperandType.SYMBOL_DIRECT in operand_types
            or OperandType.SYMBOL_INDEXED in operand_types):
        mode_byte |= (1 << 7)
    return mode_byte


def _encode_register(text: str) -> int:
    return REGISTER_CODES[text.strip().upper()]


def _encode_operand(text: str, op_type: str, symbols: SymbolTable,
                    obj_ctx: Optional[ObjectEmitContext] = None,
                    anchor: int = 0) -> List[int]:
    """Encode a single operand into bytes.

    When ``obj_ctx`` is provided (relocatable-object mode), references to
    relocatable symbols are recorded as relocations and encoded as zero
    placeholders instead of final addresses.
    """
    text = text.strip()

    if op_type == OperandType.REGISTER:
        return [_encode_register(text)]

    if op_type == OperandType.IMMEDIATE8:
        name, form = _symbol_ref(text)
        if obj_ctx is not None and name is not None \
                and obj_ctx.is_relocatable(name):
            if form == "hi" or form == "lo":
                rtype = nomf.RELOC_HI8 if form == "hi" else nomf.RELOC_LO8
                obj_ctx.emit(rtype, width=8, anchor=anchor, symbol=name)
                return [0]
            raise CodeGenError(
                f"Relocatable symbol '{name}' cannot be encoded as an 8-bit "
                f"immediate (use '{name}:' for the high byte or ':{name}' "
                f"for the low byte)")
        val = _parse_immediate(text, symbols, 8)
        return [val & 0xFF]

    if op_type == OperandType.IMMEDIATE16:
        name, form = _symbol_ref(text)
        if obj_ctx is not None and name is not None \
                and obj_ctx.is_relocatable(name):
            obj_ctx.emit(nomf.RELOC_ABS16, width=16, anchor=anchor,
                         symbol=name)
            return [0, 0]
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

    if op_type in (OperandType.SYMBOL_DIRECT, OperandType.SYMBOL_INDEXED):
        m = re.match(
            r"^\[([A-Za-z_][A-Za-z0-9_]*)"
            r"(?:\s*([+-])\s*(0x[0-9A-Fa-f]+|\d+))?\]$", text)
        name = m.group(1).upper()
        offset = 0
        if m.group(2) is not None:
            offset = int(m.group(3), 0)
            if m.group(2) == "-":
                offset = -offset
        if obj_ctx is not None and obj_ctx.is_relocatable(name):
            # Linker patches the address; the addend rides along.
            obj_ctx.emit(nomf.RELOC_ABS16, width=16, anchor=anchor,
                         symbol=name, addend=offset)
            return [0, 0]
        val = (symbols.resolve(name) + offset) & 0xFFFF
        return [(val >> 8) & 0xFF, val & 0xFF]

    raise CodeGenError(f"Unsupported operand type: {op_type}")


def generate_instruction(inst: Instruction, symbols: SymbolTable,
                         location: int,
                         obj_ctx: Optional[ObjectEmitContext] = None) -> List[int]:
    """Encode an instruction into machine-code bytes.

    When ``obj_ctx`` is provided (relocatable-object mode), each operand
    is recorded as a relocation if it references a relocatable symbol.
    """
    mnemonic = inst.mnemonic.upper()
    if mnemonic in UNIMPLEMENTED_INSTRUCTIONS:
        raise CodeGenError(f"{mnemonic} is not implemented on this CPU")
    if mnemonic not in INSTRUCTION_INFO:
        raise CodeGenError(f"Unknown instruction: {mnemonic}")

    opcode, operand_count = INSTRUCTION_INFO[mnemonic]
    result = [opcode]
    if obj_ctx is not None:
        obj_ctx.advance(1)

    # Old assembler is lenient about operand counts; match that behavior.
    if operand_count == 0:
        # Zero-operand instructions (NOP, HLT, SPBLITALL, etc.)
        return result

    # For instructions expecting operands but getting none, emit mode byte with default
    # This handles cases like SWRITE with no operand (uses VC implicitly as operand 0).
    if len(inst.operands) == 0:
        result.append(0)  # mode byte with register=0 for implicit VC operand
        if obj_ctx is not None:
            obj_ctx.advance(1)
        return result

    if len(inst.operands) != operand_count:
        # Length mismatch: be lenient like old assembler — try to encode what we have
        pass

    operand_types = [classify_operand(op, symbols) for op in inst.operands]
    mode_byte = _calculate_mode_byte(operand_types)
    result.append(mode_byte)
    if obj_ctx is not None:
        obj_ctx.advance(1)

    for op, op_type in zip(inst.operands, operand_types):
        anchor = obj_ctx.offset if obj_ctx is not None else 0
        encoded = _encode_operand(op, op_type, symbols, obj_ctx, anchor)
        result.extend(encoded)
        if obj_ctx is not None:
            obj_ctx.advance(len(encoded))

    return result


# ---------------------------------------------------------------------------
# Pass 2 driver
# ---------------------------------------------------------------------------
def second_pass(nodes: List[IRNode], symbols: SymbolTable,
                segments: List[Tuple[int, int, int]],
                segment_types: Optional[List[str]] = None
                ) -> Tuple[bytearray, List[Tuple[int, int, int]]]:
    """Generate machine code from IR nodes and symbol table.

    If ``segment_types`` is a list, it is filled with one of
    ``"CODE"``/``"DATA"`` per emitted ORG segment (parallel to the
    returned segment tuples): ``"DATA"`` when the segment contains only
    data directives, ``"CODE"`` otherwise.  This lets the NOMF emitter
    type sections without changing the legacy tuple shape.
    """
    code = bytearray()
    location = 0
    current_segment_start = 0
    current_segment_bin_offset = 0
    emitted_since_org = False
    out_segments: List[Tuple[int, int, int]] = []
    errors: List[str] = []
    seg_is_data_only = False

    def _close_segment():
        # Flush the segment that just ended: record its extent and
        # whether it held only data directives (for NOMF section typing).
        if emitted_since_org:
            seg_len = location - current_segment_start
            out_segments.append((current_segment_start, seg_len,
                                 current_segment_bin_offset))
            if segment_types is not None:
                segment_types.append("DATA" if seg_is_data_only else "CODE")

    for node in nodes:
        try:
            if isinstance(node, Directive):
                if node.name == "ORG":
                    _close_segment()
                    location = _parse_value(node.args[0], symbols) if node.args else 0
                    current_segment_start = location
                    current_segment_bin_offset = len(code)
                    emitted_since_org = False
                    seg_is_data_only = True
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
                seg_is_data_only = False

        except Exception as e:
            errors.append(f"Line {node.line_num}: {e}")

    _close_segment()

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
