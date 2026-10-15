"""`include` must carry unions, bit-field layouts and typedefs.

The strict include merge copied only enums, structs and impl methods
(`inherits` already merged everything). Found 2026-10-15 while moving the
NovaDOS NDF directory record to a bit-field struct: through `include`, a
4-byte struct with two 8-bit fields grew to 6 bytes and its fields stopped
packing, so the shared on-disk layout silently changed. Included typedef
names were not even recognized as types.
"""
import os
import tempfile

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system


def _run(files, main_name='main.ast'):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_incmerge_')
    for name, text in files.items():
        with open(os.path.join(tmpdir, name), 'w', encoding='utf-8') as f:
            f.write(text)
    src = os.path.join(tmpdir, main_name)
    asm = src[:-4] + '.asm'
    compile_astrid(src, asm, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm[:-4] + '.bin')
    cycles = 0
    while not proc.halted and cycles < 100000:
        proc.step()
        cycles += 1
    assert proc.halted
    syms = {}
    with open(asm[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return mem, syms


LIB = """
struct BF { unsigned int lo : 8; unsigned int hi : 8; int w; };
union U { int w; char b; };
typedef signed int sint;
"""


def test_bitfields_unions_and_typedefs_survive_include():
    mem, syms = _run({'lib.ast': LIB, 'main.ast': """
include "lib.ast";
int r[5];
void main() {
    struct BF *p;
    union U u;
    sint s;
    p = 0x9000;
    p->hi = 0x12;
    p->lo = 0x34;
    r[0] = sizeof(struct BF);
    r[1] = peek2(0x9000);
    r[2] = sizeof(u);
    s = -1;
    r[3] = (s < 0);
    u.w = 0x0102;
    r[4] = u.w;
}
"""})
    got = [mem.read_word(syms['gvar_r'] + 2 * i) for i in range(5)]
    assert got == [4, 0x1234, 2, 1, 0x0102]


def test_conflicting_typedef_via_include_is_an_error():
    from astrid.compiler_api import compile_astrid
    from astrid.errors import ParserError
    tmpdir = tempfile.mkdtemp(prefix='astrid_incmerge_')
    with open(os.path.join(tmpdir, 'a.ast'), 'w') as f:
        f.write('typedef signed int num;\n')
    with open(os.path.join(tmpdir, 'main.ast'), 'w') as f:
        f.write('typedef unsigned int num;\ninclude "a.ast";\nvoid main() { }\n')
    with pytest.raises(ParserError, match="Typedef 'num' redefined"):
        compile_astrid(os.path.join(tmpdir, 'main.ast'),
                       os.path.join(tmpdir, 'main.asm'), log=lambda m: None)
