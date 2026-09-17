"""Regression tests for selectable Astrid memory layouts.

WHAT: verifies the ``bank-safe`` layout moves every runtime object out of the
0x8000-0xBFFF hardware bank window (globals, the string-scratch cells and the
per-function spill windows), and that the legacy ``default`` layout is
byte-for-byte unchanged.

WHY: the emulator's BANK register swaps 0x8000-0xBFFF for a private 16 KB page
(``nova/memory/memory.py``). While Astrid globals lived at 0x8000, a program
could not touch a bank page without swapping out its own globals -- so an OS
filesystem built on bank pages (NovaDOS NDF disks) was impossible. The
bank-safe layout exists to fix that. These tests pin the addresses, pin the
absence of the hardware ITOS instruction (whose scratch cell is HARDCODED to
0xA000, inside the window -- ``core/exec_handlers.py::_itos``), and prove at
runtime that banked window writes cannot corrupt program state.
"""
import os
import re

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.compiler_api import compile_astrid
from astrid.codegen.codegen import CodeGenerator

# The hardware bank window: addressing here follows the BANK register.
BANK_WINDOW_START = 0x8000
BANK_WINDOW_END = 0xC000

# A program that exercises every layout-sensitive feature: initialised and BSS
# globals, a global string, signed decimal conversion (ITOS by default,
# software conversion under bank-safe), an array, and banked window access
# through set_bank + poke/peek.
CANONICAL_SOURCE = """
int counter = 7;
int buffer[4];
string msg = "NDF";
int first_char;
int neg_first;

void main() {
    string s;
    string s2;
    counter = counter + 1;
    buffer[0] = 0x1234;
    s = (string)4660;
    first_char = s[0];
    s2 = (string)(-60);
    neg_first = s2[0];
    set_bank(5);
    poke(0x8000, 0xAB);
    poke(0x8001, 0xCD);
    buffer[1] = peek(0x8000);
    buffer[2] = peek(0x8001);
    set_bank(0);
    poke(0x8000, 0x11);
    buffer[3] = peek(0x8000);
    counter = counter + 100;
}
"""


def _compile(source, layout, tmpdir):
    """Compile + assemble ``source`` under ``layout``; return (asm, bin) paths."""
    src = os.path.join(tmpdir, "prog.ast")
    asm = os.path.join(tmpdir, "prog.asm")
    with open(src, "w", encoding="utf-8") as f:
        f.write(source)
    compile_astrid(src, asm, verbose=False, memory_layout=layout, log=None)
    from nova_assembler import Assembler
    assert Assembler(log=None, trace=False).assemble(asm), "assemble failed"
    return asm, asm.replace(".asm", ".bin")


def _load_syms(bin_path):
    syms = {}
    with open(bin_path.replace(".bin", ".sym")) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


def _run(bin_path, max_cycles=200000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        proc.step()
        cycles += 1
    return proc, mem, cycles


def _direct_addresses(text):
    """Every absolute memory operand (``[0xXXXX]``) in generated assembly."""
    return {int(m, 16) for m in re.findall(r"\[0x([0-9A-Fa-f]{4})\]", text)}


# ---------------------------------------------------------------------------
# Layout table invariants
# ---------------------------------------------------------------------------

def test_default_layout_regions_unchanged():
    """The legacy numbers must not drift: existing programs depend on them."""
    gen = CodeGenerator(memory_layout="default")
    assert gen.global_region_start == 0x8000
    assert gen.itos_buffer == 0xA000
    assert gen.itob_buffer == 0xA100
    assert gen.string_concat_buffers == (0xA200, 0xA300, 0xA400,
                                         0xA500, 0xA600, 0xA700)
    assert (gen.spill_region_start, gen.spill_region_end) == (0xC000, 0xF000)
    assert gen.stack_floor == 0x8000
    assert gen.code_org == 0x1100


def test_bank_safe_layout_clears_the_bank_window():
    """Every runtime object must sit outside 0x8000-0xBFFF under bank-safe."""
    gen = CodeGenerator(memory_layout="bank-safe")

    def outside(addr, size=1):
        return not (BANK_WINDOW_START <= addr < BANK_WINDOW_END) and \
               not (BANK_WINDOW_START < addr + size <= BANK_WINDOW_END)

    assert outside(gen.global_region_start), "globals inside bank window"
    assert outside(gen.itos_buffer, 64), "ITOS cell inside bank window"
    assert outside(gen.itob_buffer, 64), "ITOB cell inside bank window"
    for buf in gen.string_concat_buffers:
        assert outside(buf, gen.string_concat_buf_size), \
            f"concat buffer 0x{buf:04X} inside bank window"
    assert outside(gen.spill_region_start,
                   gen.spill_region_end - gen.spill_region_start), \
        "spill region overlaps bank window"
    # Code must stay below the relocated global region.
    assert gen.code_org < gen.global_region_start
    assert gen.memory_layout["code_limit"] == gen.global_region_start
    # The scratch cells and spills must not overlap one another.
    assert gen.itos_buffer + 64 <= gen.itob_buffer
    assert gen.itob_buffer + 64 <= gen.string_concat_buffers[0]
    assert gen.string_concat_buffers[-1] + gen.string_concat_buf_size \
        <= gen.spill_region_start


def test_unknown_layout_name_is_rejected():
    """A typo'd layout must fail loudly instead of silently using defaults."""
    try:
        CodeGenerator(memory_layout="bank-safe-ish")
    except ValueError as exc:
        assert "bank-safe-ish" in str(exc)
    else:
        raise AssertionError("unknown memory layout did not raise")


def test_memory_layouts_expose_only_known_names():
    assert set(CodeGenerator.MEMORY_LAYOUTS) == {"default", "bank-safe"}
    for name, layout in CodeGenerator.MEMORY_LAYOUTS.items():
        for key in ("code_org", "globals_start", "static_locals_start",
                    "static_locals_end", "itos_buffer", "itob_buffer",
                    "concat_buffers", "spill_start", "spill_end",
                    "stack_floor"):
            assert key in layout, f"layout '{name}' is missing '{key}'"


# ---------------------------------------------------------------------------
# Generated code: where objects land, and no ITOS inside the window
# ---------------------------------------------------------------------------

def test_default_code_places_objects_in_the_bank_window(tmp_path):
    """The legacy layout still emits globals at 0x8000 and uses hardware ITOS."""
    asm, _bin = _compile(CANONICAL_SOURCE, "default", str(tmp_path))
    text = tmp_path.joinpath("prog.asm").read_text(encoding="utf-8")
    assert "ORG 0x8000" in text
    assert "ITOS" in text, "default layout should still use the ITOS instruction"
    assert "ORG 0x5000" not in text


def test_bank_safe_code_avoids_the_bank_window(tmp_path):
    """Bank-safe code must neither place objects nor touch memory in the window."""
    asm, _bin = _compile(CANONICAL_SOURCE, "bank-safe", str(tmp_path))
    text = tmp_path.joinpath("prog.asm").read_text(encoding="utf-8")

    assert "ORG 0x4200" in text, "globals should move to 0x4200"
    assert "ORG 0x8000" not in text, "no runtime object may be placed in the window"
    assert "ORG 0x5000" not in text, "the old 0x5000 split must be gone"
    # ITOS hardcodes its scratch cell at 0xA000 (inside the window), so the
    # bank-safe layout must convert in software instead.
    assert "ITOS" not in text, (
        "bank-safe code must not use the hardware ITOS instruction:\n" + text)
    # And no direct memory operand may address the window.
    bad = sorted(a for a in _direct_addresses(text)
                 if BANK_WINDOW_START <= a < BANK_WINDOW_END)
    assert not bad, f"direct operands inside the bank window: {[hex(a) for a in bad]}"
    # The conversions must use the relocated scratch cells instead.
    assert "0xC000" in text and "0xC100" in text


# ---------------------------------------------------------------------------
# Runtime: banked window writes cannot corrupt the program
# ---------------------------------------------------------------------------

def test_bank_safe_bank_switch_preserves_program_state(tmp_path):
    """End-to-end: globals survive a bank switch, and the window stays free.

    WHY: this is the property the layout exists for. If globals still lived in
    the window, set_bank(5) would hide them and the values below would be
    garbage (or the writes would land in the program's own variables).
    """
    _asm, bin_path = _compile(CANONICAL_SOURCE, "bank-safe", str(tmp_path))
    syms = _load_syms(bin_path)
    proc, mem, cycles = _run(bin_path)

    assert proc.halted, f"program never halted (PC=0x{proc.pc:04X})"
    assert proc.pc in (0x100E, 0x100F), f"halted at 0x{proc.pc:04X}"
    assert proc.sp == 0xFFFF and proc.fp == 0xFFFF

    base = syms["gvar_buffer"]
    # Globals were relocated and survived the bank switch.
    assert mem.read_word(syms["gvar_counter"]) == 108
    assert mem.read_word(base + 0) == 0x1234          # buffer[0]
    assert mem.read_word(base + 2) == 0x00AB          # buffer[1]: bank-5 read
    assert mem.read_word(base + 4) == 0x00CD          # buffer[2]: bank-5 read
    assert mem.read_word(base + 6) == 0x0011          # buffer[3]: base-RAM read
    assert mem.read_word(syms["gvar_first_char"]) == ord('4')
    assert mem.read_word(syms["gvar_neg_first"]) == ord('-')

    # The signed conversion wrote "-60" into the layout's own scratch cell...
    assert bytes(mem._mem[0xC000:0xC004]) == b"-60\x00"
    # ...and the hardware ITOS cell inside the window was never touched.
    assert bytes(mem._mem[0xA000:0xA004]) == b"\x00\x00\x00\x00"
    # The window holds only what the program itself poked while bank 0 was
    # selected -- not any runtime object.
    assert mem.read_byte(0x8000) == 0x11
    assert mem.read_byte(0x8001) == 0x00
    assert cycles < 5000, f"bank-safe program took {cycles} cycles"


if __name__ == "__main__":
    test_default_layout_regions_unchanged()
    test_bank_safe_layout_clears_the_bank_window()
    test_unknown_layout_name_is_rejected()
    test_memory_layouts_expose_only_known_names()
    print("Astrid memory-layout regression tests (layout table) passed!")