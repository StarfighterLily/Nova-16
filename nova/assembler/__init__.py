"""
Nova-16 Assembler Package

Public facade for the new token-based, multi-pass assembler.  Maintains the
same ``Assembler`` API as the old ``nova_assembler.py`` so existing callers
and tests continue to work.

Usage:
    from nova.assembler import Assembler
    asm = Assembler()
    asm.assemble("program.asm")
"""

import os
from typing import Callable, Dict, List, Optional, Tuple

from . import parser
from . import symbols as sym
from . import codegen as cg
from .macro import expand_macros

# Patch forward declarations in symbols.py so first_pass can use the real
# implementations defined in codegen.py.
sym.data_size = cg.data_size
sym.operand_size = cg.operand_size


class Assembler:
    """Main assembler class — compatible API with the legacy assembler."""

    def __init__(self, log: Optional[Callable[[str], None]] = print, trace: bool = False):
        self.log = log
        self.trace = trace
        self.errors: List[str] = []
        self.symbol_table: Dict[str, str] = {}
        self.segments: List[Tuple[int, int, int]] = []

    def _emit(self, message: str) -> None:
        if self.log is not None:
            self.log(message)

    def _trace(self, message: str) -> None:
        if self.trace:
            self._emit(message)

    def assemble(self, filename: str) -> bool:
        """Assemble a file and write .bin, .sym, and .org outputs."""
        try:
            self.errors = []
            base_dir = os.path.dirname(os.path.abspath(filename))

            with open(filename, "r", encoding="utf-8") as f:
                source = f.read()

            # Macro expansion pass
            expanded_source = expand_macros(source)

            # Parse into IR
            nodes = parser.parse(expanded_source, base_dir)

            # Pass 1: symbol table + segments
            self._emit("First pass...")
            symbol_table, segments = sym.first_pass(nodes)
            self.symbol_table = {
                name: f"0x{value:04X}" for name, value in symbol_table.items()
            }
            self.segments = segments
            self._emit(f"Symbol table: {self.symbol_table}")

            # Pass 2: code generation
            self._emit("Second pass...")
            machine_code, out_segments = cg.second_pass(nodes, symbol_table, segments)
            self.segments = out_segments

            if self.errors:
                self._emit("Assembly failed due to errors:")
                for error in self.errors:
                    self._emit(f"  {error}")
                return False

            base_name = os.path.splitext(filename)[0]
            output_file = f"{base_name}.bin"
            with open(output_file, "wb") as f:
                f.write(machine_code)

            if out_segments:
                org_file = f"{base_name}.org"
                with open(org_file, "w") as f:
                    f.write("# ORG segment information\n")
                    f.write("# Format: <start_address> <length> <binary_offset>\n")
                    for start_addr, length, bin_offset in out_segments:
                        f.write(f"0x{start_addr:04X} {length} {bin_offset}\n")
                self._emit(f"ORG information written to {org_file}")

            sym_file = f"{base_name}.sym"
            with open(sym_file, "w") as f:
                f.write("# Symbol table\n")
                f.write("# Format: <symbol> <value>\n")
                for symbol, value in self.symbol_table.items():
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


# Convenience alias for direct imports
__all__ = ["Assembler"]
