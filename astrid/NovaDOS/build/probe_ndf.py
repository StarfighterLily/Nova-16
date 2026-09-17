"""Diagnostic: run the NDF probe and dump bank page + globals."""

import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "astrid"))

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator
from nova_assembler import Assembler
from nova_main import initialize_system


SOURCE = """
include "ndf.ast";
int count;
int first_name_byte;

void main() {
    ndf_format(1);
    ndf_add(1, 66, 83, 89, 116, 0, 12);  // "BCYt" type=0 size=12
    count = ndf_entry_count(1);
    first_name_byte = ndf_name_byte(1, 0, 0);
}
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "p.ast"
        asm = Path(tmp) / "p.asm"
        src.write_text(SOURCE, encoding="utf-8")

        # Compile with bank-safe layout, staged alongside ndf.ast
        fs_dir = ROOT / "astrid" / "NovaDOS" / "src" / "fs"
        src = fs_dir / "diag_probe.ast"
        asm = src.with_suffix(".asm")
        src.write_text(SOURCE, encoding="utf-8")

        tokens = Lexer(SOURCE).tokenize()
        ast = Parser(tokens, source_path=str(src)).parse()
        gen = CodeGenerator(memory_layout="bank-safe")
        asm_lines = gen.generate(ast)
        asm.write_text("\n".join(asm_lines))

        ok = Assembler(log=None, trace=False).assemble(str(asm))
        assert ok, "assemble failed"
        binp = asm.with_suffix(".bin")

        cpu, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        cpu.pc = mem.load(binp)

        n = 0
        while not cpu.halted and n < 200000:
            cpu.step()
            n += 1

        print(f"halt={cpu.halted} PC=0x{cpu.pc:04X} cycles={n}")
        print(f"SP=0x{cpu.sp:04X} FP=0x{cpu.fp:04X}")

        # Dump globals
        for name, info in gen.global_vars.items():
            addr = info["address"]
            if info.get("is_array"):
                print(f"  gvar_{name} @ 0x{addr:04X} (array)")
            else:
                val = mem.read_word(addr)
                print(f"  gvar_{name} @ 0x{addr:04X} = {val} (0x{val:04X})")

        # Dump bank page 1
        page = mem._bank_pages[1]
        print("\nBank page 1 (first 128 bytes):")
        for off in range(0, 128, 16):
            hexbytes = " ".join(f"{page[off + i]:02X}" for i in range(16))
            ascii_str = "".join(chr(page[off + i]) if 32 <= page[off + i] < 127 else "."
                                for i in range(16))
            print(f"  +0x{off:04X}: {hexbytes}  |{ascii_str}|")

        print(f"\nFound 'NDF1' at offset 0: {bytes(page[0:4])}")
        print(f"Entry count at offset 4: {(page[4] << 8) | page[5]}")
        print(f"Entry 0 name byte 0 at offset 0x0010: {page[0x0010]} (expected 66='B')")
        print(f"Entry 0 name byte 1 at offset 0x0011: {page[0x0011]} (expected 83='C')")


if __name__ == "__main__":
    main()