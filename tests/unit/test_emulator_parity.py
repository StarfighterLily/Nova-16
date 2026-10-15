"""Behaviour shared with nova16.exe (the compiled Star port).

These pin the points where the Python reference and the Star emulator were
reconciled. Every expected value here was produced identically by both
emulators running the same binary (serial-port dumps), so a change that
breaks one of these breaks cross-emulator parity:

* DIVH divides the 32-bit value dest:P3, writes the quotient's low word to
  dest, then the remainder to P3, and sets flags from the quotient.
* DIV/MOD/DIVH/FDIV by zero leave dest, P3 and the flags unchanged and keep
  running (Star NOTES.md "Known simplifications"; Python used to raise).
* TT wraps mod 256 (Star used to saturate at 255) and advances at most one
  count per divisor period (Python used to catch up after TS was lowered).
* A timer IRQ is masked by TC bit 1 -- a request latched while masked waits --
  and is taken at the start of the step that raised it.
* SERFSTAT is opcode 0xB5 (0xB4 is SALPHA): bit 2 framed mode, bit 4 latched
  checksum error, cleared by the read.
* SREAD returns the composite: a layer-0 write (SWRITE or CHAR) under an
  opaque upper-layer pixel does not show through.
* Blending writes follow the reference's exact write sequence, so an outline
  rectangle's corners are blended twice.
"""
import os
import tempfile

import pytest

from nova_main import initialize_system


def run_asm(source, max_steps=200000, symbols=False):
    """Assemble source text, run it on a full system until HLT.

    Returns (proc, mem, gfx), plus the symbol table when ``symbols``."""
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='nova_parity_')
    path = os.path.join(tmpdir, 'prog.asm')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(source)
    assert Assembler().assemble(path)
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(path[:-4] + '.bin')
    steps = 0
    while not proc.halted and steps < max_steps:
        proc.step()
        steps += 1
    assert proc.halted, 'program did not halt'
    if not symbols:
        return proc, mem, gfx
    syms = {}
    with open(path[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith('#'):
                try:
                    syms[parts[0].upper()] = int(parts[1], 0)
                except ValueError:
                    pass
    return proc, mem, gfx, syms


@pytest.mark.parametrize('hi, lo, div, quot, rem', [
    (0x001B, 0x5800, 1024, 0x06D6, 0x0000),   # 0x001B5800 / 1024
    (0x00DC, 0x5640, 4000, 0x0E1A, 0x0000),
    (0x0000, 0xFFFE, 3, 0x5554, 0x0002),      # the low word alone
    (0x00FE, 0x0001, 0x00FF, 0xFEFF, 0x0000),
    (0x7735, 0x9400, 65000, 0x7831, 0x3A98),
])
def test_divh_uses_p3_as_low_word(hi, lo, div, quot, rem):
    proc, _, _ = run_asm(f"""
ORG 0x1000
MOV P3, {lo}
MOV P4, {hi}
MOV P6, {div}
DIVH P4, P6
HLT
""")
    assert proc.Pregisters[4] == quot
    assert proc.Pregisters[3] == rem


def test_divide_by_zero_leaves_everything_unchanged(capsys):
    proc, _, _ = run_asm("""
ORG 0x1000
MOV P3, 0x1234
MOV P4, 99
MOV P6, 0
DIV P4, P6
MOD P4, P6
DIVH P4, P6
FDIV P4, P6
HLT
""")
    assert proc.Pregisters[4] == 99
    assert proc.Pregisters[3] == 0x1234
    err = capsys.readouterr().err
    for name in ('DIV', 'MOD', 'DIVH', 'FDIV'):
        assert f'[nova16] {name} by zero -- ignored' in err


def test_timer_counter_wraps_instead_of_saturating():
    proc, _, _ = run_asm("""
ORG 0x1000
MOV TS, 0
MOV TM, 0
MOV TC, 1
MOV P2, 300
spin:
DEC P2
JNZ spin
MOV P0, TT
HLT
""")
    assert proc.Pregisters[0] == 0x5A       # 602 ticks -> 602 mod 256


def test_timer_catch_up_is_capped_at_one_count():
    """Lowering TS mid-period advances TT by one, not by every elapsed period."""
    proc, _, _ = run_asm("""
ORG 0x1000
MOV TC, 0
MOV TS, 200
MOV TC, 1
MOV P2, 75
sp2:
DEC P2
JNZ sp2
MOV TS, 4
MOV P2, 20
sp3:
DEC P2
JNZ sp3
MOV P0, TT
HLT
""")
    assert proc.Pregisters[0] == 9


TIMER_IRQ_PROGRAM = """
ORG 0x0000
START:
    MOV P8, 0xFF00
    MOV P1, 0x0100
    MOV P2, HANDLER
    MOV [P1], P2            ; IVT vector 0
    MOV R9, 0
    MOV P5, 0               ; handler entry count
    MOV TT, 0
    MOV TM, 2
    MOV TS, 0
    MOV TC, 0x03
    STI
WAIT:
    MOV R8, R9
    CMP R8, 0
    JZ WAIT
    CLI
    HLT
HANDLER:
    INC P5
    POP P6                  ; return address (peek)
    PUSH P6
    MOV P7, P6
    NOP
    NOP
    NOP
    NOP
    MOV R9, 1
    MOV TT, 0
    MOV TC, 0               ; disarm: a request latched meanwhile stays masked
    IRET
"""


def test_timer_irq_masked_by_tc_and_taken_before_the_step():
    proc, mem, _, syms = run_asm(TIMER_IRQ_PROGRAM, symbols=True)
    # Exactly one handler entry: TT keeps reaching TM during the handler, but
    # once TC bit 1 is clear the pending request is masked.
    assert proc.Pregisters[5] == 1
    # The request is taken before the step that raised it executes, so the
    # interrupted instruction is the first one of WAIT (not the one after).
    assert proc.Pregisters[7] == syms['WAIT']


def test_serfstat_reports_framed_mode_and_checksum_error():
    from core.exec import HANDLER_INSTRUCTIONS
    assert HANDLER_INSTRUCTIONS[0xB5].name == 'SERFSTAT'
    assert HANDLER_INSTRUCTIONS[0xB4].name == 'SALPHA'

    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.uart.write_control(0x04)                          # framed mode
    assert proc.uart.read_extended_status() == 0x04
    proc.uart.ingest_rx_stream(bytes([0x7E, 0x01, 0x99, 0x00]))  # bad checksum
    assert proc.uart.read_extended_status() == 0x14
    assert proc.uart.read_extended_status() == 0x04       # read clears it


def test_char_on_layer0_does_not_show_through_upper_layer():
    proc, mem, gfx = run_asm("""
ORG 0x1000
MOV VM, 0
MOV VL, 1
SFILL 0x10
MOV VL, 0
MOV VC, 0x0F
MOV VX, 8
MOV VY, 8
CHAR 65
MOV VX, 9
MOV VY, 9
SREAD P0
HLT
""")
    assert int((gfx.screen == 0x10).all())       # layer 1 covers everything
    assert proc.Pregisters[0] == 0x10


def test_outline_rectangle_corners_are_blended_twice():
    proc, mem, gfx = run_asm("""
ORG 0x1000
MOV VM, 0
MOV VL, 0
SBLEND 1                ; additive
SALPHA 255
MOV VC, 10
MOV VX, 20
MOV VY, 30
SRECT 40, 50, 0
HLT
""")
    layer = gfx.layer_0
    assert int(layer[30, 20]) == 20     # corner: top row, then left column
    assert int(layer[30, 30]) == 10     # top edge
    assert int(layer[40, 20]) == 10     # left edge
    assert int(layer[50, 40]) == 20


def test_reversed_rectangle_follows_slice_semantics():
    """Corners are clamped, never reordered: a reversed filled rectangle is
    empty, as the reference's numpy slices are."""
    proc, mem, gfx = run_asm("""
ORG 0x1000
MOV VM, 0
MOV VL, 0
MOV VC, 7
MOV VX, 200
MOV VY, 30
SRECT 150, 70, 1
HLT
""")
    assert int(gfx.layer_0.sum()) == 0
