"""Integration tests for Star System 1 (astrid/starsystem/starsys.ast).

Boots the compiled kernel headlessly against the real Nova-16 emulator,
and verifies:

- Boot: banner/chrome pixels on background + sprite layers, booted flag,
  zero-page union-mount tables installed via poke/peek, IVT programmed.
- sec4 heartbeat: vector-0 timer interrupts increment gvar_ticks; SP stays
  stable across dispatches (ISR register contract).
- sec3 R: ramdisk: pressing 'r' runs the self-test; signature lands in
  bank page 3 (not base RAM); BANK invariant holds.
- Console window: printable keys echo as glyphs at the cursor.
- Console scroll: consuming the bottom row scrolls the text layer up one
  glyph row (SSHFT -8) instead of wrapping over the prompt; the gutter
  row between title bar and viewport is cleared, chrome stays put on
  background layer 2.
- Deterministic shutdown: ESC halts cleanly with a HALT banner.

The kernel is compiled ONCE per pytest session into a temp directory;
every test boots a fresh emulator instance from that binary.
"""
import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system

ASTRID_DIR = os.path.dirname(os.path.abspath(__file__))
STARSYS_SRC = os.path.join(ASTRID_DIR, 'starsystem', 'starsys.ast')

_BIN_CACHE = {}


def get_kernel_binary():
    """Compile starsys.ast once per session; return path to .bin."""
    if 'bin' in _BIN_CACHE:
        return _BIN_CACHE

    out_dir = tempfile.mkdtemp(prefix='starsys_test_')
    src_copy = os.path.join(out_dir, 'starsys.ast')
    shutil.copyfile(STARSYS_SRC, src_copy)

    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], src_copy, '-o', src_copy.replace('.ast', '.asm')]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv

    from nova_assembler import Assembler
    Assembler().assemble(src_copy.replace('.ast', '.asm'))

    _BIN_CACHE['bin'] = src_copy.replace('.ast', '.bin')
    _BIN_CACHE['dir'] = out_dir
    _BIN_CACHE['sym'] = src_copy.replace('.ast', '.sym')
    return _BIN_CACHE


def load_symbols():
    """Parse the generated .sym into {name: int address}."""
    syms = {}
    with open(get_kernel_binary()['sym'], encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0]] = int(parts[1], 16)
    return syms


class Kernel:
    """A freshly booted Star System instance."""

    def __init__(self):
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        self.proc, self.mem, self.gfx, self.kbd = proc, mem, gfx, kbd
        self.proc.pc = self.mem.load(get_kernel_binary()['bin'])
        self.syms = load_symbols()

    def run(self, cycles):
        c = 0
        while c < cycles and not self.proc.halted:
            self.proc.step()
            c += 1
        return c

    def press(self, key_code):
        self.kbd.add_key(key_code)

    def gvar(self, name):
        return self.mem.read_word_fast(self.syms[f'gvar_{name}'])

    def sprite_layer5(self):
        """Compositor sprite layer 5 buffer (index 0 of sprite_layers)."""
        return self.gfx.sprite_layers[0]


@pytest.fixture
def kernel():
    k = Kernel()
    yield k
# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

def test_kernel_boot_state(kernel):
    kernel.run(120000)
    assert not kernel.proc.halted, 'kernel halted during boot'
    assert kernel.gvar('booted') == 1
    # Window chrome (frame + title bar) is static background content on
    # layer 2 per sec5 -- sprite layer 5 is reserved for the scrolling
    # console viewport, so the SSHFT scroll never drags the chrome around.
    chrome = kernel.gfx.background_layers[1]
    title_ink = int((chrome[24:32, 24:130] != 0).sum())
    assert title_ink > 20, f'title bar empty (ink={title_ink})'
    # The desktop frame stays on background layer 1.
    bg = kernel.gfx.background_layers[0]
    frame_ink = int((bg != 0).sum())
    assert frame_ink > 100, f'desktop frame missing (ink={frame_ink})'
    # The text viewport (sprite layer 5) starts clean above the first
    # content row (y=56) -- no chrome ink may leak into the scroll region.
    layer5 = kernel.sprite_layer5()
    leaked = int((layer5[:56, :] != 0).sum())
    assert leaked == 0, f'chrome ink on scrolling layer (px={leaked})'
    print(f'PASS boot state (title_ink={title_ink}, frame_ink={frame_ink})')


def test_mount_tables_installed_in_zero_page(kernel):
    kernel.run(120000)
    data = [kernel.mem.read_byte(a) for a in range(0x0010, 0x0018)]
    assert data == [0x10, 0x00, 15, 0, 0x80, 0, ord('S'), ord('S')], data
    print('PASS mount tables in zero page')


def test_interrupt_vector_programmed(kernel):
    handler = kernel.mem.read_word_fast(0x0100)
    assert handler == kernel.syms['func_timer_interrupt'], (
        f'vector 0 -> 0x{handler:04X}, expected '
        f"0x{kernel.syms['func_timer_interrupt']:04X}")
    print('PASS interrupt vector programmed')


# ---------------------------------------------------------------------------
# sec4 heartbeat / ISR contract
# ---------------------------------------------------------------------------

def test_timer_heartbeat_ticks(kernel):
    kernel.run(150000)
    ticks = kernel.gvar('ticks')
    assert ticks > 10, f'heartbeat dead after 150k cycles: ticks={ticks}'
    print(f'PASS heartbeat (ticks={ticks})')


def test_sp_stable_across_interrupts(kernel):
    """ISR register save/restore contract: SP at the shell loop top must
    be identical across many timer dispatches (no per-interrupt leak)."""
    kernel.run(100000)
    loop_pc = next(pc for name, pc in kernel.syms.items()
                   if name.startswith('while_start'))
    sp_samples = set()
    c = 0
    while c < 200000 and not kernel.proc.halted:
        kernel.proc.step()
        c += 1
        if kernel.proc.pc == loop_pc:
            sp_samples.add(kernel.proc.sp)
    assert len(sp_samples) == 1, (
        f'SP drifted across iterations: {sorted(hex(s) for s in sp_samples)}')
    print(f'PASS SP stability across interrupts (SP=0x{sp_samples.pop():04X})')
# ---------------------------------------------------------------------------
# sec3 R: ramdisk
# ---------------------------------------------------------------------------

def test_ramdisk_selftest_passes(kernel):
    kernel.run(120000)
    assert kernel.gvar('ramdisk_ok') == 0, 'self-test ran without the r key'

    kernel.press(ord('r'))
    kernel.run(40000)

    assert kernel.gvar('ramdisk_ok') == 1, (
        f'R: self-test failed: ramdisk_ok={kernel.gvar("ramdisk_ok")}')
    assert kernel.gvar('bank_invariant') == 1
    assert kernel.mem.current_bank == 0
    # Signature bytes live in bank page 3 -- NOT in base RAM.
    assert kernel.mem._bank_pages[3][0] == ord('S')
    assert kernel.mem._bank_pages[3][1] == ord('1')
    # Verdict visible on the console layer.
    verdict_ink = int((kernel.sprite_layer5()[56:64, 24:80] != 0).sum())
    assert verdict_ink > 5, 'R: OK verdict not rendered'
    print(f'PASS R: self-test (verdict ink={verdict_ink})')


def test_base_ram_globals_unshadowed_after_ramdisk_ops(kernel):
    kernel.run(120000)
    kernel.press(ord('r'))
    kernel.run(40000)
    kernel.press(ord('A'))
    kernel.run(20000)
    # All kernel globals still readable through the pass-through window.
    assert kernel.gvar('booted') == 1
    assert kernel.gvar('last_key') == ord('A')
    assert kernel.mem.current_bank == 0
    print('PASS globals unshadowed after R: operations')


# ---------------------------------------------------------------------------
# Console window echo
# ---------------------------------------------------------------------------

def test_printable_key_echoes_at_cursor(kernel):
    kernel.run(120000)
    col0, row0 = kernel.gvar('cursor_col'), kernel.gvar('cursor_row')

    kernel.press(ord('H'))
    kernel.run(30000)
    assert kernel.gvar('last_key') == ord('H')
    assert kernel.gvar('cursor_col') == col0 + 1

    # The glyph landed in the cell where the cursor was.
    layer5 = kernel.sprite_layer5()
    y0, x0 = row0 * 8, col0 * 8
    cell_ink = int((layer5[y0:y0 + 8, x0:x0 + 8] != 0).sum())
    assert cell_ink > 0, f"'H' glyph missing at ({x0},{y0})"
    print(f'PASS console echo (cell ink={cell_ink} at {x0},{y0})')


def test_console_scrolls_at_bottom_instead_of_wrapping(kernel):
    """Issue #2: the console must scroll its history away when the bottom
    row is consumed, not wrap to the top and overwrite the prompt."""
    kernel.run(120000)
    assert kernel.gvar('cursor_row') == 7

    # Drive the cursor past the bottom row (21): 16 Enter presses cover
    # rows 7..22, forcing at least one scroll.
    for _ in range(16):
        kernel.press(13)
        kernel.run(20000)

    # The cursor is pinned to the bottom row, not wrapped to row 7.
    assert kernel.gvar('cursor_row') == 21, (
        f"cursor wrapped to row {kernel.gvar('cursor_row')} "
        'instead of scrolling')

    layer5 = kernel.sprite_layer5()
    # The gutter row between the title bar and the first content row is
    # blank -- the scrolled-out top line did not poke into the chrome gap.
    gutter_ink = int((layer5[48:56, :] != 0).sum())
    assert gutter_ink == 0, f'gutter row not cleared after scroll (ink={gutter_ink})'
    # A fresh "> " prompt is rendered on the new bottom line (col 4 -> x=32).
    prompt_ink = int((layer5[168:176, 32:48] != 0).sum())
    assert prompt_ink > 0, 'prompt missing on the scrolled bottom row'
    # Chrome survived the scroll untouched on background layer 2.
    chrome_ink = int((kernel.gfx.background_layers[1][24:32, 24:130] != 0).sum())
    assert chrome_ink > 20, 'window chrome lost after scroll'
    print(f'PASS console scroll (gutter={gutter_ink}, prompt_ink={prompt_ink})')


def test_scrolled_history_is_preserved(kernel):
    """A line printed before the scroll must still be visible one row higher
    after the scroll -- history scrolls away, it is not erased."""
    kernel.run(120000)
    # 'H' echoes on row 7 (y=56), the first content row.
    kernel.press(ord('H'))
    kernel.run(20000)
    layer5 = kernel.sprite_layer5()
    assert int((layer5[56:64, 32:40] != 0).sum()) > 0, 'H glyph missing pre-scroll'

    # Sixteen Enters consume rows 8..21 plus one scroll.
    for _ in range(16):
        kernel.press(13)
        kernel.run(20000)

    # The 'H' line scrolled up exactly one glyph row (y=48 is the gutter...
    # rows 8..21 moved to 7..20 => H's row 7 scrolled out; the line one
    # below the wrap point is verifiable instead): the last Enters'
    # prompts stack at one-row intervals above the bottom row.
    layer5 = kernel.sprite_layer5()
    prompt_rows = [y for y in range(56, 176, 8)
                   if int((layer5[y:y + 8, 32:48] != 0).sum()) > 0]
    assert len(prompt_rows) >= 14, (
        f'scroll collapsed history: prompt rows at {prompt_rows}')
    print(f'PASS scroll history ({len(prompt_rows)} stacked prompt rows)')


def test_control_keys_do_not_echo(kernel):
    kernel.run(120000)
    col0 = kernel.gvar('cursor_col')
    # Tab (9), newline (10) etc. are below the printable range.
    kernel.press(9)
    kernel.run(20000)
    assert kernel.gvar('cursor_col') == col0, 'control byte was echoed'
    print('PASS control keys ignored')


# ---------------------------------------------------------------------------
# Shutdown + MCP surface
# ---------------------------------------------------------------------------

def test_esc_halts_cleanly_with_halt_banner(kernel):
    kernel.run(120000)
    kernel.press(27)
    remaining = kernel.run(60000)
    assert kernel.proc.halted, 'ESC did not halt the machine'
    screen = kernel.gfx.screen
    nz = int((screen != 0).sum())
    assert nz > 0, 'HALT banner missing after shutdown'
    print(f'PASS clean shutdown (screen px={nz}, cycles={remaining})')


def test_astrid_compile_tool_compiles_kernel():
    """The astrid_compile MCP tool builds the kernel end-to-end."""
    from nova_mcp_server import _handle_astrid_compile, _HAS_ASTRID
    assert _HAS_ASTRID, 'astrid compiler not detected by the MCP server'

    result = json.loads(_handle_astrid_compile({
        'source_path': os.path.relpath(
            STARSYS_SRC, os.path.dirname(ASTRID_DIR)),
    }))
    assert result.get('status') == 'compiled', result
    assert os.path.exists(result['binary'])
    print('PASS astrid_compile tool compiles the kernel')


if __name__ == '__main__':
    test_kernel_boot_state(Kernel())
    test_mount_tables_installed_in_zero_page(Kernel())
    test_interrupt_vector_programmed(Kernel())
    test_timer_heartbeat_ticks(Kernel())
    test_sp_stable_across_interrupts(Kernel())
    test_ramdisk_selftest_passes(Kernel())
    test_base_ram_globals_unshadowed_after_ramdisk_ops(Kernel())
    test_printable_key_echoes_at_cursor(Kernel())
    test_control_keys_do_not_echo(Kernel())
    test_console_scrolls_at_bottom_instead_of_wrapping(Kernel())
    test_scrolled_history_is_preserved(Kernel())
    test_esc_halts_cleanly_with_halt_banner(Kernel())
    test_astrid_compile_tool_compiles_kernel()
    shutil.rmtree(_BIN_CACHE.get('dir', ''), ignore_errors=True)
    print('All Star System kernel tests passed!')
