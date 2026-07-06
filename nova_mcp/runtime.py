#!/usr/bin/env python3
"""Shared runtime state and imports for the Nova-16 MCP server."""

from __future__ import annotations

import gc
import logging
import os
import sys
from pathlib import Path

# Suppress pygame output before importing Nova modules.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
logging.getLogger("pygame").setLevel(logging.ERROR)

ROOT_DIR = Path(__file__).resolve().parent.parent
NOBASIC_DIR = ROOT_DIR / "NoBASIC"

for path in (ROOT_DIR, NOBASIC_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

try:
    import nova_assembler
    import nova_cpu as cpu_module
    import nova_debugger
    import nova_disassembler
    import nova_gfx as gfx_module
    import nova_keyboard as keyboard_module
    from nova.memory import Memory as memory_module
    import nova_sound as sound_module
except ImportError as exc:
    print(f"Error importing Nova modules: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

try:
    from nobasic_compiler import compile_nobasic

    _HAS_NOBASIC = True
except ImportError:
    compile_nobasic = None
    _HAS_NOBASIC = False

try:
    from PIL import Image

    _HAS_PIL = True
except Exception:
    Image = None
    _HAS_PIL = False


_emulator_state = {
    "cpu": None,
    "memory": None,
    "gfx": None,
    "kbd": None,
    "sound": None,
    "program_path": None,
    "running": False,
    "cycle_count": 0,
    "debugger": None,
}


def cleanup_emulator() -> None:
    """Explicitly release emulator resources before reinitialization."""
    if _emulator_state["sound"] is not None:
        try:
            _emulator_state["sound"].cleanup()
        except Exception as exc:
            print(f"[MCP] Error cleaning up sound: {exc}", file=sys.stderr)

    _emulator_state.update(
        {
            "cpu": None,
            "memory": None,
            "gfx": None,
            "kbd": None,
            "sound": None,
            "program_path": None,
            "running": False,
            "cycle_count": 0,
            "debugger": None,
        }
    )
    gc.collect()
    print("[MCP] Emulator resources cleaned up", file=sys.stderr)


def initialize_emulator(force_clean: bool = True):
    """Initialize the Nova-16 emulator components with event-bus architecture."""
    if force_clean and _emulator_state["cpu"] is not None:
        cleanup_emulator()

    # Create shared event bus first (per Phase 3 architecture)
    from nova.bus import EventBus, InterruptController
    bus = EventBus()

    mem = memory_module(bus=bus)
    gfx = gfx_module.GFX()
    kbd = keyboard_module.NovaKeyboard(bus=bus)
    snd = sound_module.NovaSound()

    intr_ctrl = InterruptController(bus=bus, cpu=None, memory=mem)

    proc = cpu_module.CPU(mem, gfx, kbd, snd,
                         bus=bus, interrupt_controller=intr_ctrl)
    intr_ctrl.cpu = proc

    _emulator_state.update(
        {
            "cpu": proc,
            "memory": mem,
            "gfx": gfx,
            "kbd": kbd,
            "sound": snd,
            "program_path": None,
            "running": False,
            "cycle_count": 0,
            "debugger": None,
        }
    )

    print("[MCP] Emulator initialized", file=sys.stderr)
    return proc, mem, gfx, kbd, snd


def ensure_emulator() -> None:
    """Ensure the emulator has been initialized."""
    if _emulator_state["cpu"] is None:
        initialize_emulator()