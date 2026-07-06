"""
Nova-16 Assembler Intermediate Representation

Simple dataclasses representing the structured output of the parser and the
input to the symbol-resolution / code-generation passes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Label:
    """A label definition (e.g. ``START:``)."""
    name: str
    line_num: int = 0


@dataclass
class Instruction:
    """An assembly instruction with its operands."""
    mnemonic: str
    operands: List[str] = field(default_factory=list)
    line_num: int = 0


@dataclass
class Directive:
    """An assembler directive (ORG, EQU, DB, DW, DS, IF, IFDEF, etc.)."""
    name: str
    args: List[str] = field(default_factory=list)
    line_num: int = 0


@dataclass
class Data:
    """A data directive that emits bytes (DB, DW, DEFSTR, DS)."""
    directive: str          # 'DB' | 'DW' | 'DEFSTR' | 'DS'
    args: List[str] = field(default_factory=list)
    line_num: int = 0


IRNode = Label | Instruction | Directive | Data
