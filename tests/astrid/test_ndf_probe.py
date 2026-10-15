"""Probe the isolated NovaDOS NDF layer under the bank-safe layout.

WHY: ndf.ast is compiled in isolation from the kernel so the bank-page path
(set_bank + window access) is proven before kernel.ast relies on it. Each
test compiles a tiny program that drives bank 1 through the NDF API, runs
it, and inspects the emulator's bank pages directly.

Probe sources are staged in pytest's tmp_path and include ndf.ast by
absolute path. (They used to be written next to ndf.ast in
astrid/NovaDOS/src/fs/ and the .ast/.nex files were never removed.)
"""
from pathlib import Path

import pytest

# Fixtures + sys.path injected by tests/astrid/conftest.py at collection time.
from nova_main import initialize_system  # noqa: E402
from astrid.compiler_api import compile_astrid  # noqa: E402

_NDF = (Path(__file__).resolve().parent.parent.parent
        / "astrid" / "NovaDOS" / "src" / "fs" / "ndf.ast")
assert _NDF.is_file(), f"ndf.ast missing: {_NDF}"


def _run(source: str, tmp_path: Path, max_cycles=300000):
    from nova_assembler import Assembler
    src = tmp_path / "probe.ast"
    asm = tmp_path / "probe.asm"
    src.write_text(f'include "{_NDF.as_posix()}";\n' + source, encoding="utf-8")
    compile_astrid(str(src), str(asm), memory_layout="bank-safe", log=None)
    assert Assembler(log=None, trace=False).assemble(str(asm))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(str(asm.with_suffix(".bin")))
    n = 0
    while not proc.halted and n < max_cycles:
        proc.step()
        n += 1
    assert proc.halted, f"did not halt (PC=0x{proc.pc:04X})"
    assert mem.current_bank == 0, "an NDF call left a disk bank mapped"
    syms = {}
    for line in asm.with_suffix(".sym").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            syms[parts[0].lower()] = int(parts[1], 16)
    return mem, syms


def _signed(v):
    return v - 0x10000 if v & 0x8000 else v


def _words(mem, syms, name, n):
    return [_signed(mem.read_word(syms[f"gvar_{name}"] + 2 * i)) for i in range(n)]


def test_format_writes_header_and_mounts(tmp_path):
    mem, syms = _run("""
int r[3];
void main() {
    r[0] = ndf_mounted(1);
    ndf_format(1);
    r[1] = ndf_mounted(1);
    r[2] = ndf_count(1);
}
""", tmp_path)
    assert _words(mem, syms, "r", 3) == [0, 1, 0]
    page = mem._bank_pages[1]
    assert bytes(page[0:8]) == b"NDF1\x00\x00\x04\x00"   # magic, count 0, free 0x400


def test_create_find_and_read_back(tmp_path):
    mem, syms = _run("""
int r[8];
char buf[16];
char name[9];
void main() {
    ndf_format(1);
    r[0] = ndf_create(1, "BOOT", NDF_TEXT, "HELLO", 5);
    r[1] = ndf_create(1, "PROG", NDF_PROG, "ABCDEFG", 7);
    r[2] = ndf_find(1, "PROG");
    r[3] = ndf_size(1, 1);
    r[4] = ndf_type(1, 1);
    r[5] = ndf_read(1, 1, 0, buf, 16);
    r[6] = ndf_read(1, 1, 5, buf + 8, 16);   // tail from offset 5
    r[7] = ndf_free(1);
    ndf_name(1, 0, name);
}
""", tmp_path)
    assert _words(mem, syms, "r", 8) == [0, 1, 1, 7, 1, 7, 2, 0x4000 - 0x400 - 12]
    buf = syms["gvar_buf"]
    assert bytes(mem._mem[buf:buf + 7]) == b"ABCDEFG"
    assert bytes(mem._mem[buf + 8:buf + 10]) == b"FG"
    name = syms["gvar_name"]
    assert bytes(mem._mem[name:name + 9]) == b"BOOT\x00\x00\x00\x00\x00"
    page = mem._bank_pages[1]
    # Header: count 2, next free 0x040C; data packed in creation order.
    assert bytes(page[4:8]) == b"\x00\x02\x04\x0C"
    assert bytes(page[0x10:0x20]) == b"BOOT\x00\x00\x00\x00\x00\x00\x00\x05\x04\x00\x00\x00"
    assert bytes(page[0x20:0x30]) == b"PROG\x00\x00\x00\x00\x01\x00\x00\x07\x04\x05\x00\x00"
    assert bytes(page[0x400:0x40C]) == b"HELLOABCDEFG"


def test_name_matching_is_exact(tmp_path):
    mem, syms = _run("""
int r[5];
void main() {
    ndf_format(1);
    ndf_create(1, "ABCDEFGH", NDF_TEXT, "x", 1);
    ndf_create(1, "AB", NDF_TEXT, "y", 1);
    r[0] = ndf_find(1, "ABCDEFGH");
    r[1] = ndf_find(1, "ABCDEFG");     // prefix of an 8-byte name
    r[2] = ndf_find(1, "ABCDEFGHI");   // longer than any stored name
    r[3] = ndf_find(1, "AB");
    r[4] = ndf_find(1, "A");
}
""", tmp_path)
    assert _words(mem, syms, "r", 5) == [0, -1, -1, 1, -1]


def test_create_errors(tmp_path):
    lines = ["int r[5];", "void main() {", "    ndf_format(1);",
             '    ndf_create(1, "DUP", NDF_TEXT, "x", 1);',
             '    r[0] = ndf_create(1, "DUP", NDF_TEXT, "x", 1);',
             '    r[1] = ndf_create(1, "", NDF_TEXT, "x", 1);',
             '    r[2] = ndf_create(1, "NINECHARS", NDF_TEXT, "x", 1);',
             '    r[3] = ndf_create(1, "BIG", NDF_TEXT, 0x1000, 0x3C00);']
    for i in range(15):
        lines.append(f'    ndf_create(1, "F{i}", NDF_TEXT, "x", 1);')
    lines += ['    r[4] = ndf_create(1, "ONEMORE", NDF_TEXT, "x", 1);', "}"]
    mem, syms = _run("\n".join(lines), tmp_path)
    # exists, bad name, bad name, no space, directory full
    assert _words(mem, syms, "r", 5) == [-4, -5, -5, -3, -2]
    page = mem._bank_pages[1]
    assert (page[4] << 8) | page[5] == 16


def test_unformatted_bank_is_not_mounted(tmp_path):
    mem, syms = _run("""
int r[2];
void main() {
    ndf_format(1);
    r[0] = ndf_mounted(2);
    r[1] = ndf_mounted(1);
}
""", tmp_path)
    assert _words(mem, syms, "r", 2) == [0, 1]
