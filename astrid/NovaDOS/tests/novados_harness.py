"""Shared helpers for the NovaDOS kernel tests.

WHAT: build the kernel (bank-safe layout, optional -D settings), boot it
headlessly on the Python emulator with typed input, and read the console
back as text.

WHY text: the console draws 8x8 glyphs on layer 0, so every cell can be
matched against the emulator's own font. Tests then assert on what a user
would read ("2 files, 15319 free") instead of counting non-zero pixels.
"""
import functools
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from nova_main import initialize_system  # noqa: E402

REPO_ROOT = _REPO_ROOT
KERNEL_SRC = os.path.join(REPO_ROOT, "astrid", "NovaDOS", "src", "kernel", "kernel.ast")
HI_ASM = os.path.join(REPO_ROOT, "astrid", "NovaDOS", "src", "progs", "hi.asm")

ENTER = 0x0A
BACKSPACE = 0x08
ESC = 0x1B

# The entry stub's HLT is at 0x100E; PC is one past it once halted.
STUB_HALT_PCS = (0x100E, 0x100F)


def build_kernel(out_dir, name="kernel", defines=None):
    """Compile + assemble the kernel into out_dir; return the .bin path."""
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    asm = os.path.join(str(out_dir), f"{name}.asm")
    ok = compile_astrid(KERNEL_SRC, asm, memory_layout="bank-safe", log=None,
                        defines=defines or {})
    assert ok, "Astrid compile failed"
    assert Assembler(log=None, trace=False).assemble(asm), "assembler failed"
    return asm[:-4] + ".bin"


def load_syms(bin_path):
    syms = {}
    with open(bin_path[:-4] + ".sym") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


def load_segments(bin_path):
    """[(start, end)] for every segment in the .org sidecar."""
    segments = []
    with open(bin_path[:-4] + ".org") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                start, length, _ = line.split()
                start = int(start, 16)
                segments.append((start, start + int(length)))
    return segments


@functools.lru_cache(maxsize=1)
def _glyph_table():
    from nova.graphics.gfx import GFX
    ref = GFX()
    layer = ref._compositor.layers[0]
    table = {}
    for code in range(32, 127):
        layer[:] = 0
        ref.draw_string_to_screen(chr(code), 0, 0, color=0x0F)
        # First wins, so an empty cell reads as a space.
        table.setdefault((layer[0:8, 0:8] != 0).tobytes(), chr(code))
    return table


def screen_rows(gfx):
    """The 32 console rows as strings ('?' for a cell that is no glyph)."""
    table = _glyph_table()
    lit = gfx._compositor.layers[0] != 0
    rows = []
    for row in range(32):
        text = ""
        for col in range(32):
            cell = lit[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            text += table.get(cell.tobytes(), "?" if cell.any() else " ")
        rows.append(text.rstrip())
    return rows


class Run:
    """Result of one boot: emulator objects plus convenient readers."""

    def __init__(self, bin_path, proc, mem, gfx, kbd, cycles):
        self.bin_path = bin_path
        self.proc = proc
        self.mem = mem
        self.gfx = gfx
        self.kbd = kbd
        self.cycles = cycles
        self.syms = load_syms(bin_path)

    def word(self, name):
        """A global's 16-bit value by source name (gvar_ prefix optional)."""
        key = name if name.startswith(("gvar_", "func_")) else f"gvar_{name}"
        return self.mem.read_word(self.syms[key])

    def signed(self, name):
        v = self.word(name)
        return v - 0x10000 if v & 0x8000 else v

    @property
    def screen(self):
        return screen_rows(self.gfx)

    @property
    def text(self):
        """Every non-blank console row, stripped of the 2-column margin."""
        return [row.strip() for row in self.screen if row.strip()]

    def assert_clean_halt(self):
        p = self.proc
        assert p.halted, f"kernel never halted (PC=0x{p.pc:04X})"
        assert p.pc in STUB_HALT_PCS, (
            f"kernel halted at 0x{p.pc:04X}, expected the entry stub HLT")
        assert p.sp == 0xFFFF and p.fp == 0xFFFF, (
            f"frames not unwound: SP=0x{p.sp:04X} FP=0x{p.fp:04X}")


def boot(bin_path, keys="", max_cycles=2_000_000):
    """Boot the kernel and type `keys` ("\\n" is Enter; ints are raw codes).

    Keys are fed as the shell drains them: the keyboard FIFO silently drops
    input past its capacity, so a long script cannot be preloaded.
    """
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    if isinstance(keys, str):
        pending = [ENTER if ch == "\n" else ord(ch) for ch in keys]
    else:
        pending = list(keys)
    pending.reverse()
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        if pending and len(kbd._buffer) < 4:
            kbd.add_key(pending.pop())
        proc.step()
        cycles += 1
    return Run(bin_path, proc, mem, gfx, kbd, cycles)
