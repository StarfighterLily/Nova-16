"""Size-focused peephole patterns and statement-level codegen shortcuts.

Added 2026-10-15 to bring the NovaDOS kernel back under its 12.5 KB code
budget. Each pattern is checked for its effect on the emitted assembly and,
by running the program, for unchanged results.
"""
import os
import re
import tempfile

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system
from astrid.codegen.peephole import PeepholeOptimizer


def _opt(lines):
    return PeepholeOptimizer().optimize("\n".join(lines)).splitlines()


def _run(source):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_peep_')
    src = os.path.join(tmpdir, 'prog.ast')
    asm = os.path.join(tmpdir, 'prog.asm')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    compile_astrid(src, asm, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm[:-4] + '.bin')
    n = 0
    while not proc.halted and n < 200000:
        proc.step()
        n += 1
    assert proc.halted
    syms = {}
    with open(asm[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    with open(asm, encoding='utf-8') as f:
        text = f.read()
    return mem, syms, text


def test_redundant_save_around_leaf_operand():
    out = _opt(["MOV P4, [0x8000]", "PUSH P4", "MOV P5, 1", "POP P4",
                "ADD P4, P5", "MOV [0x8000], P4", "MOV P5, 0"])
    assert "PUSH P4" not in out and "POP P4" not in out


def test_redundant_save_kept_when_middle_writes_the_saved_register():
    out = _opt(["PUSH P4", "MOV P4, 1", "POP P4", "MOV [0x8000], P4"])
    assert out[:3] == ["PUSH P4", "MOV P4, 1", "POP P4"]


def test_redundant_save_kept_for_sp_relative_operand():
    out = _opt(["PUSH P4", "MOV P5, [SP+2]", "POP P4", "ADD P4, P5",
                "MOV [0x8000], P4", "MOV P5, 0"])
    assert "PUSH P4" in out


def test_push_from_memory():
    out = _opt(["MOV P1, [0x42D6]", "PUSH P1", "CALL f", "MOV P1, 0"])
    assert out[0] == "PUSH [0x42D6]"
    # A live register keeps its load.
    out = _opt(["MOV P1, [0x42D6]", "PUSH P1", "CALL f", "MOV [0x9000], P1"])
    assert out[:2] == ["MOV P1, [0x42D6]", "PUSH P1"]
    # R registers push one byte: never folded.
    out = _opt(["MOV R1, [0x42D6]", "PUSH R1", "MOV R1, 0"])
    assert out[:2] == ["MOV R1, [0x42D6]", "PUSH R1"]


def test_immediate_operand():
    out = _opt(["MOV P5, 32", "OR P4, P5", "MOV [0x9000], P4", "MOV P5, 0"])
    assert out[0] == "OR P4, 32"
    # Negative literals and R destinations are left alone.
    out = _opt(["MOV P5, -1", "AND P4, P5", "MOV P5, 0"])
    assert out[0] == "MOV P5, -1"
    out = _opt(["MOV P5, 3", "ADD R4, P5", "MOV P5, 0"])
    assert out[0] == "MOV P5, 3"


def test_patterns_keep_program_results():
    mem, syms, text = _run("""
int r[6];
int g = 0x1234;
int add3(int a, int b, int c) { return a + b - c; }
void main() {
    int i;
    int s = 0;
    for (i = 0; i < 10; i++) { s += i; }
    r[0] = s;                       // 45
    r[1] = (g | 0x80) & 0xF0F0;     // 0x10B0
    r[2] = add3(g, r[0], 5);        // 0x1234 + 45 - 5
    i = 3;
    i--;
    r[3] = i;                       // 2
    r[4] = g ^ 0xFF;                // 0x12CB
    r[5] = (g > 0x1000) + (g < 0x80);
}
""")
    got = [mem.read_word(syms['gvar_r'] + 2 * k) for k in range(6)]
    assert got == [45, 0x10B0, 0x1234 + 40, 2, 0x12CB, 1]
    body = text[text.index('func_main:'):]
    assert 'PUSH [' in body                       # argument pushed from memory
    assert re.search(r'^\s*(OR|AND|XOR) P\d, (0x)?[0-9A-Fa-f]+\s*$', body, re.M)
