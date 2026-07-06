"""
Nova-16 Assembler Symbol Table & Pass 1

Computes label addresses and resolves EQU values from the IR.  Produces a
symbol table mapping names to integer values, plus a list of segments for ORG
awareness.
"""

from typing import Dict, List, Tuple

from .ir import IRNode, Label, Instruction, Directive, Data


def data_size(node, symbols):
    """Forward declaration; real implementation is in codegen.py."""
    raise NotImplementedError("data_size must be imported from codegen")


def operand_size(inst, symbols):
    """Forward declaration; real implementation is in codegen.py."""
    raise NotImplementedError("operand_size must be imported from codegen")


class SymbolError(Exception):
    """Error during symbol resolution."""
    pass


class SymbolTable:
    """Simple symbol table with integer values."""

    def __init__(self):
        self.symbols: Dict[str, int] = {}

    def define(self, name: str, value: int):
        self.symbols[name.upper()] = value

    def resolve(self, name: str) -> int:
        try:
            return self.symbols[name.upper()]
        except KeyError:
            raise SymbolError(f"Undefined symbol: {name}")

    def __contains__(self, name: str) -> bool:
        return name.upper() in self.symbols

    def items(self):
        return self.symbols.items()


def _parse_value(text: str, symbols: SymbolTable) -> int:
    """Parse a numeric or symbol value."""
    text = text.strip()
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16)
    if text.lstrip("-").isdigit():
        return int(text)
    if text in symbols:
        return symbols.resolve(text)
    raise SymbolError(f"Cannot resolve value: {text}")


def first_pass(nodes: List[IRNode]) -> Tuple[SymbolTable, List[Tuple[int, int, int]]]:
    """Compute symbol addresses and ORG segments from IR.

    Returns:
        (symbol_table, segments) where segments is a list of
        (start_address, length, binary_offset) tuples.
    """
    symbols = SymbolTable()
    location = 0
    segments: List[Tuple[int, int, int]] = []
    current_segment_start = 0
    current_segment_bin_offset = 0
    emitted_since_org = False

    pending_equ_value = None
    for node in nodes:
        if isinstance(node, Label):
            symbols.define(node.name, location)
            # If the next node is EQU, this label's value will be overwritten
            pending_equ_value = node.name

        elif isinstance(node, Directive):
            if node.name == "EQU":
                # EQU directive follows a label (e.g., "START EQU 0x0000")
                # The label name is in pending_equ_value, and the value is in args[0]
                if pending_equ_value and node.args:
                    symbols.define(pending_equ_value, _parse_value(node.args[0], symbols))
                    pending_equ_value = None
                continue

            if node.name == "ORG":
                if emitted_since_org:
                    segment_len = location - current_segment_start
                    segments.append((current_segment_start, segment_len,
                                     current_segment_bin_offset))
                location = _parse_value(node.args[0], symbols) if node.args else 0
                current_segment_start = location
                current_segment_bin_offset = sum(seg[1] for seg in segments)
                emitted_since_org = False

        elif isinstance(node, Data):
            size = data_size(node, symbols)
            location += size
            emitted_since_org = True

        elif isinstance(node, Instruction):
            size = 1 + operand_size(node, symbols)
            location += size
            emitted_since_org = True

    if emitted_since_org:
        segment_len = location - current_segment_start
        segments.append((current_segment_start, segment_len, current_segment_bin_offset))

    return symbols, segments
