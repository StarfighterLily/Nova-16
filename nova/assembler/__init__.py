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
from . import object_mode as objmod
from .ir import Directive
from .. import nomf

# Patch forward declarations in symbols.py so first_pass can use the real
# implementations defined in codegen.py.
sym.data_size = cg.data_size
sym.operand_size = cg.operand_size


class Assembler:
    """Main assembler class — compatible API with the legacy assembler.

    Output artifacts (all written by default):
      - ``.nex``  NOMF executable  (primary artifact; ORG'd programs)
      - ``.nobj`` NOMF object      (primary artifact; ORG-less units)
      - ``.bin`` / ``.org`` / ``.sym``  legacy sidecars (compatibility)

    ``emit_nomf=False`` suppresses the NOMF artifact;
    ``emit_legacy=False`` suppresses the sidecar trio once the
    ecosystem has fully migrated.
    """

    def __init__(self, log: Optional[Callable[[str], None]] = print,
                 trace: bool = False,
                 emit_nomf: bool = True,
                 emit_legacy: bool = True):
        self.log = log
        self.trace = trace
        self.emit_nomf = emit_nomf
        self.emit_legacy = emit_legacy
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
        """Assemble a file.

        If the source declares ``GLOBAL``/``EXTERN`` directives it is
        assembled as a relocatable object (``.nobj``); otherwise it follows
        the executable path (``.nex`` + legacy sidecars).
        """
        try:
            self.errors = []
            base_dir = os.path.dirname(os.path.abspath(filename))

            with open(filename, "r", encoding="utf-8") as f:
                source = f.read()

            # Macro expansion pass
            expanded_source = expand_macros(source)

            # Parse into IR
            nodes = parser.parse(expanded_source, base_dir)

            if self._is_object_source(nodes):
                return self._assemble_object(filename, base_dir, nodes)

            return self._assemble_executable(filename, base_dir, nodes)

        except Exception as e:
            self._emit(f"Assembly failed: {e}")
            import traceback
            if self.log is not None:
                self._emit(traceback.format_exc())
            return False

    def _is_object_source(self, nodes) -> bool:
        """True when the source declares GLOBAL or EXTERN directives."""
        for node in nodes:
            if isinstance(node, Directive) and node.name in ("GLOBAL", "EXTERN"):
                return True
        return False

    def _assemble_object(self, filename: str, base_dir: str, nodes) -> bool:
        """Assemble a relocatable .nobj (GLOBAL/EXTERN sources)."""
        try:
            self._emit("Object mode (GLOBAL/EXTERN detected)...")
            module_name = os.path.splitext(os.path.basename(filename))[0]
            doc = objmod.assemble_object(nodes, module_name, filename)
            out_path = os.path.splitext(filename)[0] + nomf.OBJECT_EXT
            doc.write(out_path)
            self._emit(f"NOMF object written to {out_path}")
            self._emit(f"Sections: {len(doc.sections)}, "
                       f"symbols: {len(doc.symbols)}, "
                       f"relocations: {len(doc.relocs)}")
            return True
        except objmod.ObjectAsmError as e:
            self._emit(f"Object assembly failed: {e}")
            return False
        except Exception as e:
            self._emit(f"Object assembly failed: {e}")
            import traceback
            if self.log is not None:
                self._emit(traceback.format_exc())
            return False

    def _assemble_executable(self, filename: str, base_dir: str, nodes) -> bool:
        """Assemble an executable (.nex + legacy sidecars)."""
        try:
            self.errors = []

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
            segment_types: List[str] = []
            machine_code, out_segments = cg.second_pass(
                nodes, symbol_table, segments, segment_types)
            self.segments = out_segments

            if self.errors:
                self._emit("Assembly failed due to errors:")
                for error in self.errors:
                    self._emit(f"  {error}")
                return False

            base_name = os.path.splitext(filename)[0]

            if self.emit_nomf:
                # NOMF is the primary artifact since the format became
                # the default: a self-contained file carrying segments,
                # explicit entry point, symbols, and integrity data.
                self._write_nomf(base_name, filename, machine_code,
                                 out_segments, segment_types)

            if self.emit_legacy:
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

            self._emit(f"Assembly complete: {len(machine_code)} bytes written to {base_name}")
            return True

        except Exception as e:
            self._emit(f"Assembly failed: {e}")
            import traceback
            if self.log is not None:
                self._emit(traceback.format_exc())
            return False

    def _write_nomf(self, base_name: str, source_filename: str,
                    machine_code: bytearray,
                    out_segments: List[Tuple[int, int, int]],
                    segment_types: List[str]) -> None:
        """Emit the NOMF artifact for this assembly unit.

        ORG'd programs become a ``.nex`` executable (absolute segments +
        explicit entry point = first ORG segment, matching legacy loader
        semantics); ORG-less units become a ``.nobj`` relocatable object
        with section-relative symbols, ready for the future linker.
        """
        module_name = os.path.basename(base_name)
        type_map = {"CODE": nomf.SECTION_CODE, "DATA": nomf.SECTION_DATA}

        if out_segments:
            segments_data = [
                (start, bytes(machine_code[offset:offset + length]))
                for start, length, offset in out_segments
            ]
            sec_types = [
                type_map.get(segment_types[i] if i < len(segment_types)
                             else "CODE", nomf.SECTION_CODE)
                for i in range(len(segments_data))
            ]
            symbols = {
                name: int(value, 16)
                for name, value in self.symbol_table.items()
                if value.startswith("0x")
            }
            doc = nomf.build_executable(
                module_name, segments_data, symbols,
                entry_addr=out_segments[0][0],
                source=source_filename, section_types=sec_types)
            nomf_path = f"{base_name}{nomf.EXECUTABLE_EXT}"
        else:
            # No ORG: the unit is position-independent in spirit — emit
            # a relocatable object with a single code section and
            # section-relative symbol values.
            section = nomf.Section(id=0, type=nomf.SECTION_CODE,
                                   org_hint=0, data=bytes(machine_code))
            symbols = [
                nomf.Symbol(name=name, kind=nomf.SYM_LABEL,
                            binding=nomf.BIND_GLOBAL, section=0,
                            value=int(value, 16))
                for name, value in self.symbol_table.items()
                if value.startswith("0x")
            ]
            doc = nomf.build_object(module_name, [section], symbols,
                                    source=source_filename)
            nomf_path = f"{base_name}{nomf.OBJECT_EXT}"

        doc.write(nomf_path)
        self._emit(f"NOMF artifact written to {nomf_path}")


# Convenience alias for direct imports
__all__ = ["Assembler"]
