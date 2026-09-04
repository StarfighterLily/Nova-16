"""Regression tests for the MCP debugger breakpoint integration.

The original bug: breakpoint_set/breakpoint_clear/breakpoint_list stored
breakpoints on cpu.breakpoints, but handle_debugger_run_until_breakpoint only
consulted the NovaDebugger instance's own (always-empty) breakpoint set, so
breakpoints set through the MCP tools never fired. It also checked for a hit
BEFORE stepping, which meant that once stopped at a breakpoint it could never
resume past it.

The fix honors the union of both registries and steps first, then checks
(matching the CLI debugger's documented behavior).
"""
import json
import os
import shutil
import sys
import tempfile

import pytest

from nova_main import initialize_system


PROGRAM = """ORG 0x1000
start:
    MOV P0, 3
loop:
    SUB P0, 1
    JNZ loop
    HLT
"""


def _assemble_program():
    """Assemble PROGRAM into a temp dir; return (bin_path, sym, tmpdir)."""
    tmpdir = tempfile.mkdtemp(prefix="nova_dbg_bp_")
    asm_path = os.path.join(tmpdir, "bptest.asm")
    with open(asm_path, "w") as f:
        f.write(PROGRAM)
    Assembler = pytest.importorskip("nova_assembler").Assembler
    Assembler().assemble(asm_path)
    bin_path = asm_path.replace(".asm", ".bin")
    sym = {}
    with open(asm_path.replace(".asm", ".sym")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) == 2 and parts[1].startswith("0x"):
                    sym[parts[0]] = int(parts[1], 16)
    return bin_path, sym, tmpdir


@pytest.fixture()
def emulator_state():
    from nova_mcp.handlers_system import handle_breakpoint_set

    bin_path, sym, tmpdir = _assemble_program()
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)

    state = {
        "cpu": proc,
        "memory": mem,
        "gfx": gfx,
        "sound": snd,
        "keyboard": kbd,
        "program_path": bin_path,
        "cycle_count": 0,
    }
    yield state, handle_breakpoint_set, sym
    shutil.rmtree(tmpdir, ignore_errors=True)


def _run_until_breakpoint(state):
    import nova_debugger
    from nova_mcp.handlers_debugger import handle_debugger_run_until_breakpoint

    return json.loads(handle_debugger_run_until_breakpoint(
        {"max_cycles": 100000},
        ensure_emulator=lambda: None,
        state=state,
        debugger_module=nova_debugger,
    ))


def test_breakpoint_set_fires_in_debugger_run(emulator_state):
    """A breakpoint registered via breakpoint_set must stop the run."""
    state, handle_breakpoint_set, sym = emulator_state
    loop_addr = sym["loop"]
    handle_breakpoint_set({"address": loop_addr},
                          ensure_emulator=lambda: None, state=state)

    result = _run_until_breakpoint(state)
    assert result["breakpoint_hit"] == f"0x{loop_addr:04X}", result
    # The MOV at start executed; PC parked at loop with P0 still 3
    assert state["cpu"].Pregisters[0] == 3


def test_breakpoint_resumes_past_itself(emulator_state):
    """Re-running from a breakpoint must step past it, not re-hit instantly."""
    state, handle_breakpoint_set, sym = emulator_state
    loop_addr = sym["loop"]
    handle_breakpoint_set({"address": loop_addr},
                          ensure_emulator=lambda: None, state=state)

    first = _run_until_breakpoint(state)
    assert first["breakpoint_hit"] == f"0x{loop_addr:04X}"
    assert state["cpu"].Pregisters[0] == 3

    second = _run_until_breakpoint(state)
    assert second["breakpoint_hit"] == f"0x{loop_addr:04X}"
    assert second["cycles"] > 0, "run must make progress past the breakpoint"
    # SUB executed once, then JNZ jumped back to loop: P0 is now 2
    assert state["cpu"].Pregisters[0] == 2


def test_run_completes_when_no_breakpoint_left(emulator_state):
    """After the loop exits, the run continues to HLT without a false hit."""
    state, handle_breakpoint_set, sym = emulator_state
    loop_addr = sym["loop"]
    handle_breakpoint_set({"address": loop_addr},
                          ensure_emulator=lambda: None, state=state)

    _run_until_breakpoint(state)   # MOV: P0 = 3, PC parked at loop
    _run_until_breakpoint(state)   # SUB, JNZ back: P0 = 2
    _run_until_breakpoint(state)   # SUB, JNZ back: P0 = 1
    final = _run_until_breakpoint(state)  # SUB -> 0, JNZ falls through, HLT
    assert final["halted"] is True
    assert final["breakpoint_hit"] is None
    assert state["cpu"].Pregisters[0] == 0


def test_debugger_init_adopts_cpu_breakpoints(emulator_state):
    """debugger_init must sync cpu-level breakpoints into the debugger view."""
    state, handle_breakpoint_set, sym = emulator_state
    loop_addr = sym["loop"]
    handle_breakpoint_set({"address": loop_addr},
                          ensure_emulator=lambda: None, state=state)

    import nova_debugger
    from nova_mcp.handlers_debugger import handle_debugger_init

    handle_debugger_init(ensure_emulator=lambda: None, state=state,
                         debugger_module=nova_debugger)
    assert loop_addr in state["debugger"].breakpoints


if __name__ == "__main__":
    print("Run with pytest")
