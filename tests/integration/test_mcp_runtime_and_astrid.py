"""MCP server regression tests: emulator wiring + astrid_compile tool.

Two areas:

1. Runtime wiring (regression): nova_mcp.runtime.initialize_emulator must
   build the SAME machine nova_main.initialize_system builds. It previously
   omitted the standalone Timer device, the UART device, both CPU
   constructor kwargs, and the cpu.post_step -> intr_ctrl.check
   subscription -- so timer interrupts never dispatched and serial builtins
   had no backing device in every MCP session. Star System 1's kernel was
   the first workload to notice.

2. astrid_compile handler: success path with auto_load, missing source,
   wrong extension, compile errors, and tool/dispatch registration.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'astrid'))

from nova_mcp import runtime


# ---------------------------------------------------------------------------
# 1. Emulator wiring parity with nova_main.initialize_system
# ---------------------------------------------------------------------------

@pytest.fixture()
def mcp_emulator():
    """A fresh emulator via the MCP runtime; cleaned up afterwards."""
    proc, mem, gfx, kbd, snd = runtime.initialize_emulator()
    yield runtime._emulator_state
    runtime.cleanup_emulator()


def test_cpu_has_timer_device(mcp_emulator):
    assert mcp_emulator['cpu'].timer_device is not None, (
        'MCP-initialized CPU has no timer device: TT/TM/TC/TS writes go '
        'nowhere and vector 0 never fires')
    print('PASS cpu.timer_device wired')


def test_uart_device_present(mcp_emulator):
    """ser_* builtins need a real UART behind the CPU."""
    uart_dev = getattr(mcp_emulator['cpu'], 'uart', None)
    assert uart_dev is not None, 'MCP CPU has no UART device'
    print('PASS uart device wired')


def test_timer_heartbeat_dispatches_in_mcp_session(mcp_emulator):
    """End-to-end: a program that programs vector 0 and counts ticks must
    see them increment when driven through the MCP runtime path."""
    import tempfile
    src = os.path.join(tempfile.mkdtemp(), 'ticks.ast')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(
            "int ticks;\n"
            "\n"
            "void timer_interrupt() {\n"
            "    ticks++;\n"
            "    iret();\n"
            "}\n"
            "\n"
            "int main() {\n"
            "    set_timer(0, 32, 2, 3);\n"
            "    sti();\n"
            "    while (1) { }\n"
            "}\n")
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], src]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    from nova_assembler import Assembler
    Assembler().assemble(src.replace('.ast', '.asm'))

    proc = mcp_emulator['cpu']
    mem = mcp_emulator['memory']
    entry = mem.load(src.replace('.ast', '.bin'))
    proc.pc = entry
    for _ in range(120000):
        if proc.halted:
            break
        proc.step()

    sym_path = src.replace('.ast', '.sym')
    ticks_addr = None
    with open(sym_path, encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0] == 'gvar_ticks':
                ticks_addr = int(parts[1], 16)
    assert ticks_addr is not None
    ticks = mem.read_word_fast(ticks_addr)
    assert ticks > 10, (
        f'timer heartbeat dead through MCP runtime: ticks={ticks} -- '
        'initialize_emulator lost its Timer/post_step wiring again')
    print(f'PASS heartbeat dispatches in MCP session (ticks={ticks})')

# ---------------------------------------------------------------------------
# 2. astrid_compile handler
# ---------------------------------------------------------------------------

def _write_tmp_ast(source):
    import tempfile
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    return fd.name


def _handle_state():
    from nova_mcp_server import _handle_get_cpu_state
    return _handle_get_cpu_state()


def test_astrid_compile_success_with_auto_load():
    from nova_mcp_server import _handle_astrid_compile
    src = _write_tmp_ast('int main() { return 42; }')
    try:
        result = json.loads(_handle_astrid_compile({
            'source_path': src,
            'auto_load': True,
        }))
        assert result['status'] == 'compiled'
        assert result.get('auto_loaded') is True
        assert result['entry_point'] == '0x1000'
        assert os.path.exists(result['assembly'])
        assert os.path.exists(result['binary'])
        # The program really is loaded at PC.
        state = json.loads(_handle_state())
        assert state['pc'] == '0x1000'
        print('PASS astrid_compile success + auto_load')
    finally:
        for ext in ('.ast', '.asm', '.bin', '.org', '.sym'):
            p = src.replace('.ast', ext)
            if os.path.exists(p):
                os.unlink(p)


def test_astrid_compile_missing_source():
    from nova_mcp_server import _handle_astrid_compile
    result = json.loads(_handle_astrid_compile({
        'source_path': 'does/not/exist.ast',
    }))
    assert 'error' in result and 'not found' in result['error']
    print('PASS missing-source error')


def test_astrid_compile_bad_extension(tmp_path):
    from nova_mcp_server import _handle_astrid_compile
    bad = tmp_path / 'program.nb'
    bad.write_text('int x = 1;', encoding='utf-8')
    result = json.loads(_handle_astrid_compile({
        'source_path': str(bad),
    }))
    assert 'error' in result and 'extension' in result['error']
    print('PASS bad-extension error')


def test_astrid_compile_syntax_error_reported(tmp_path):
    from nova_mcp_server import _handle_astrid_compile
    bad = tmp_path / 'broken.ast'
    bad.write_text('int main( { this is not C', encoding='utf-8')
    result = json.loads(_handle_astrid_compile({
        'source_path': str(bad),
    }))
    assert 'error' in result, f'expected compile error, got {result}'
    assert 'traceback' in result
    print('PASS syntax error surfaced as JSON')


def test_tool_registered_in_dispatch_and_definitions():
    from nova_mcp_server import TOOL_HANDLER_NAMES, build_tools
    assert TOOL_HANDLER_NAMES.get('astrid_compile') == '_handle_astrid_compile'
    tools = {t.name for t in build_tools()}
    assert 'astrid_compile' in tools
    print('PASS tool registered (dispatch + schema)')
