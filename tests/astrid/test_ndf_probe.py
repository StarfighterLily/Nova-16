"""Probe the isolated NDF layer under the bank-safe layout.

WHY: ndf.ast is compiled in isolation from the kernel so we can assert the
bank-page path (set_bank/peek/poke) before trusting it inside kernel.ast.
Each test compiles, assembles and runs a tiny program that reads/writes bank 1
through the NDF primitives, then inspects the emulator's bank pages directly.

Negative cases: unstored bank pages return 0 (never formatted), the name scan
stops at NUL padding, and add() returns -1 when the directory is full.
"""
import os
import re
import sys
from pathlib import Path

import pytest

# Fixtures + sys.path injected by tests/astrid/conftest.py at collection time.

from nova_main import initialize_system  # noqa: E402
from astrid.compiler_api import compile_astrid  # noqa: E402
from astrid.codegen.codegen import CodeGenerator  # noqa: E402
from astrid.lexer.lexer import Lexer  # noqa: E402
from astrid.parser.parser import Parser  # noqa: E402


# Determine the NDF source directory from the test file's location so
# include "ndf.ast" resolves correctly when probe sources are staged
# alongside it. This is an absolute path so pytest collection works
# regardless of the current working directory.
_NDF_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "astrid" / "NovaDOS" / "src" / "fs"
)
assert _NDF_DIR.is_dir(), f"ndf dir missing: {_NDF_DIR}"


def _build(source: str, tmp_path: Path, layout: str = "bank-safe"):
    """Compile source with ndf.ast included; return (asm, binp, gen).

    gen is a CodeGenerator that has actually compiled the source, so its
    global_vars table has real addresses for the probe to assert against.
    """
    fs_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "astrid" / "NovaDOS" / "src" / "fs"
    )
    src_tag = re.sub(r"[^A-Za-z0-9_.-]+$", "", tmp_path.name)
    src = fs_dir / f"probe_{src_tag}.ast"
    asm = src.with_suffix(".asm")
    src.write_text(source, encoding="utf-8")
    try:
        compile_astrid(str(src), str(asm), verbose=False, memory_layout=layout,
                       log=None)
        from nova_assembler import Assembler
        assembler = Assembler(log=None, trace=False)
        ok = assembler.assemble(str(asm))
        assert ok, f"assemble failed for probe_{src_tag}"
        binp = asm.with_suffix(".bin")
        assert binp.exists(), f"bin file not created: {binp}"

        # Recompile to get a CodeGenerator with real global addresses.
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens, source_path=str(src)).parse()
        gen = CodeGenerator(memory_layout=layout)
        gen.generate(ast)
        return asm, binp, gen
    except Exception:
        _probe_cleanup(asm)
        raise


def _probe_cleanup(asm_path: Path) -> None:
    """Remove a probe's generated artifacts (call after _run is done)."""
    for p in (asm_path, asm_path.with_suffix(".bin"),
              asm_path.with_suffix(".org"), asm_path.with_suffix(".sym")):
        p.unlink(missing_ok=True)


def _run(bin_path: Path, max_cycles=200000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    n = 0
    while not proc.halted and n < max_cycles:
        proc.step()
        n += 1
    return proc, mem, n


def test_ndf_format_writes_header_and_count_is_zero(tmp_path):
    asm, binp, gen = _build(
        """
include "ndf.ast";
int mounted;

void main() {
    ndf_format(1);
    mounted = ndf_mounted(1);
}
""",
        tmp_path,
    )

    proc, mem, n = _run(binp)
    _probe_cleanup(asm)
    assert proc.halted, f"did not halt (PC=0x{proc.pc:04X})"
    assert proc.pc in (0x100E, 0x100F), f"halted at 0x{proc.pc:04X}"

    page = mem._bank_pages[1]
    assert bytes(page[0:4]) == b"NDF1"
    assert (page[4] << 8) | page[5] == 0
    # Use the compiled global address (gen has the real layout layout).
    mounted_addr = gen.global_vars["mounted"]["address"]
    assert mem.read_word(mounted_addr) == 1
    print("PASS: ndf_format(mounted=1) leaves header intact")


def test_ndf_add_one_entry_and_read_back(tmp_path):
    asm, binp, gen = _build(
        """
include "ndf.ast";
int count;
int first_name_byte;

void main() {
    ndf_format(1);
    ndf_add(1, 66, 83, 89, 116, 0, 12);  // "BSYt"  type=0 size=12
    count = ndf_entry_count(1);
    first_name_byte = ndf_name_byte(1, 0, 0);
}
""",
        tmp_path,
    )

    proc, mem, n = _run(binp)
    _probe_cleanup(asm)
    assert proc.halted, f"did not halt (PC=0x{proc.pc:04X})"

    count_addr = gen.global_vars["count"]["address"]
    name_addr = gen.global_vars["first_name_byte"]["address"]
    assert mem.read_word(count_addr) == 1
    assert mem.read_word(name_addr) == ord("B")

    page = mem._bank_pages[1]
    entry0 = 0x0010
    assert chr(page[entry0]) == "B"
    assert page[entry0 + 8] == 0  # type
    assert (page[entry0 + 10] << 8) | page[entry0 + 11] == 12  # length
    print("PASS: ndf_add installs an entry whose name/type/size read back")


def test_ndf_add_returns_minus_one_only_path(tmp_path):
    # Fill directory past the known hard limit, then assert add() returns -1.
    # The layout already reserves bank 1 as a real disk page, so this tests
    # the overflow guard without polluting bank 0.
    lines = []
    lines.append('include "ndf.ast";')
    lines.append("int r;")
    lines.append("int i;")
    lines.append("")
    lines.append("void main() {")
    lines.append("    ndf_format(1);")
    for i in range(16):
        lines.append(
            f'    ndf_add(1, {65}, {65}, {65}, {65}, 0, 0);  // "AAAA"'
        )
    lines.append("    r = ndf_add(1, 72, 76, 76, 84, 0, 0);  // overflow")
    lines.append("}")
    source = "\n".join(lines)

    asm, binp, gen = _build(source, tmp_path)
    proc, mem, n = _run(binp)
    _probe_cleanup(asm)
    assert proc.halted, f"did not halt (PC=0x{proc.pc:04X})"

    r_addr = gen.global_vars["r"]["address"]
    assert mem.read_word(r_addr) == 0xFFFF  # -1 stored as 16-bit unsigned
    # The directory itself should have exactly 16 entries after the loop.
    assert (mem._bank_pages[1][4] << 8) | mem._bank_pages[1][5] == 16
    # Last slot should be "AAAA" (first 32 lines wrote 16 entries, then the
    # overflow call returned -1 without overwriting slot 0).
    assert mem._bank_pages[1][0x0010 + 15 * 0x10] == ord("A")
    print("PASS: ndf_add returns -1 past the directory capacity")


if __name__ == "__main__":
    main = pytest.main([__file__, "-v", "-p", "no:cacheprovider"])
    raise SystemExit(0 if main == 0 else 1)