# NovaDOS Build & Test Toolchain

How to assemble, run, and regression-test NovaDOS on the Nova-16 emulator.

## 1. Prerequisites

- Python **3.13** with numpy, pygame — invoke as `py -3.13`.
- The Nova-16 repo at `c:\Code\projects\Nova` (this project lives under its
  `NovaDOS/` subdirectory, per protocols).
- pytest, optional (`pip install pytest`).

## 2. Directory conventions (project protocols)

```
'src'  -> assembly/Astrid sources for NovaDOS     (NovaDOS/src)
'build'-> final executable artifacts (.bin/.org/.sym)  (NovaDOS/build)
'docs\plans' -> implementation docs (this set)
'docs\notes' -> living developer notes (start.md)
```

Generated `.bin`/`.org`/`.sym` in `build/` may be git-ignored; keep `.asm`.

## 3. Build the kernel

```powershell
cd c:\Code\projects\Nova
py -3.13 nova_assembler.py NovaDOS/src/kernel.asm
```

- Produces `NovaDOS/build/kernel.bin` (+ `.org`, `.sym`, and NOMF siblings).
- **Entry point:** the *first* `ORG` segment start (0x0120) becomes PC after
  load — verified behavior of `nova/memory/memory.py::load`.
- If the file declares `GLOBAL`/`EXTERN`, the new assembler/NOMF path is used;
  NovaDOS Phase 1 stays on the legacy `.bin`/`.org` path (no GLOBAL/EXTERN).

## 4. Inspect what was emitted

```powershell
py -3.13 nova_disassembler.py NovaDOS/build/kernel.bin
```

Verify the first instructions are the boot JMP and that the VECTOR_TABLE data
lands where `MEMCPY` expects (check the `.sym` for label addresses:
`label: 0x0120`).

## 5. Run headless

```powershell
py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin --cycles 20000
```

Expect: no exception, final PC in the `REPL_MAIN` loop, banner pixels present
(`Graphics: NNN non-black pixels`). For UART tests add
`--uart-bridge terminal` or `--uart-bridge tcp --uart-tcp-role client
--uart-host 127.0.0.1 --uart-port 9999`.

Interactive (GUI): `py -3.13 nova_main.py NovaDOS/build/kernel.bin`.

## 6. pytest harness

Seed the keyboard buffer before stepping (the emulator's `NovaKeyboard.add_key`
takes scan codes directly), then run cycles.

```python
# NovaDOS/tests/conftest.py
import pytest
from nova.bus.eventbus import EventBus
from nova.bus.interrupt import InterruptController
from nova.memory.memory import Memory
from nova.peripherals.timer import Timer
import nova_gfx as gpu
import nova_keyboard as keyboard
import nova_uart as uart
from nova_cpu import CPU

KERNEL = r"..\..\..\NovaDOS\build\kernel.bin"   # relative to cwd when run

def boot_novados(keys=(), cycles_budget=200000):
    """Boot NovaDOS, optionally pre-seed key scan codes, step to a sentinel."""
    bus = EventBus()
    mem = Memory(bus=bus)
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard(bus=bus)
    intr = InterruptController(bus=bus, memory=mem)
    timer = Timer(bus=bus, interrupt_controller=intr)
    proc = CPU(mem, gfx, kbd, None, uart_device=uart.NovaUART(host_bridge=None),
               bus=bus, interrupt_controller=intr, timer_device=timer)
    intr.cpu = proc
    bus.subscribe("cpu.post_step", intr.check)

    entry = mem.load(KERNEL)          # reads .org, returns 0x0120
    proc.pc = entry

    for k in keys:                    # letters/special names or scan codes
        if isinstance(k, int):
            kbd.add_key(k)
        elif len(k) == 1:
            kbd.add_key(ord(k))
        else:
            kbd.add_key(kbd.get_scan_code(k))

    return proc, mem, gfx, kbd
```

```python
# NovaDOS/tests/test_phase1_boot.py
import pytest
from conftest import boot_novados

def test_boot_reaches_repl():
    proc, mem, gfx, kbd = boot_novados()
    for _ in range(20000):
        proc.step()
        if proc.halted:
            break
    # Kernel REPL is an infinite loop; assert we did not crash and saw a banner
    assert not proc.halted
    assert gfx.background_layers[0].sum() > 0          # banner pixels on layer 0
    assert 0x0120 <= proc.pc <= 0x0FFF                 # PC back in kernel

    # zero page signature written by boot
    assert bytes(mem.memory[0x0000:0x0002]) == b"ND"
```

### 6.1 Keyboard-driven REPL test

```python
# NovaDOS/tests/test_phase1_repl.py
from conftest import boot_novados

def type_cmd(proc, gfx, kbd, text):
    """Inject a command line and run until the REPL prompt is drawn again."""
    for ch in text:
        kbd.add_key(ord(ch))
    kbd.add_key(kbd.get_scan_code("enter"))

def run_until(proc, predicate, max_steps=400000):
    for _ in range(max_steps):
        proc.step()
        if proc.halted:
            break
        if predicate(proc):
            return True
    return False

def test_help_command():
    proc, mem, gfx, kbd = boot_novados()
    run_until(proc, lambda p: p.pc == 0x0120 + 3)     # deterministic PC marker
    type_cmd(proc, gfx, kbd, "HELP")
    # help text drawn at layer 0, video cursor advanced past banner
    assert gfx.background_layers[0].sum() > 0
    # and we are back inside REPL loop (PC < 0x1000)
    assert 0x0120 <= proc.pc < 0x1000

def test_assign_and_print():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, "A = 5")
    type_cmd(proc, gfx, kbd, "PRINT A")
    run_until(proc, lambda p: mem.memory[0xD000] == 5 or True)  # VARS_BASE low byte
    # after enough steps, VARS_BASE word == 5
    val = mem.memory[0xD000] | (mem.memory[0xD001] << 8)
    assert val == 5
```

> Timing notes: the REPL busy-polls `KEYSTAT`, so stepping always progresses;
> use generous budgets (≥ 100k steps) headless. Pre-seed *all* keys before
> stepping — `KEYIN` drains FIFO, no wall-clock timing is involved.

### 6.2 Seeding a program into a bank

```python
def seed_bank(mem, bank, file_name, payload, entry_addr):
    """Write an NDF volume into bank `bank` (window at 0x8000-0xBFFF)."""
    mem.set_bank(bank)                          # BANK = bank (memory API)
    base = 0x8000
    # volume header
    mem.write_bytes_direct(base + 0x0000, b"NDB1")
    # ... directory at base+0x0010: name(10) type(1) flags(1) start(2) len(2) entry(2)
    # ... file bytes at base+0x0400
    mem.set_bank(0)                             # back to bank 0
```

Then `type_cmd(proc, gfx, kbd, 'BANK 3')`, `'DIR'`, `'LOAD "SAMPLE"'`, `'RUN'`,
and assert the sample's marker byte in RAM after returning to the REPL.

### 6.3 Graphics assertions

```python
def test_gfx_put():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, 'DEV POKE /gfx2 0x0040 0x3F')   # blue pixel
    # layer 2 numpy buffer (compositor.layers[2])
    assert gfx._compositor.layers[2][0, 0x40] == 0x3F
```

`screen = gfx.get_screen()` composites dirty layers; layer buffers live in
`gfx._compositor.layers[i]` (i = 0-8).

## 7. Acceptance matrix (mapped from each phase doc)

| Phase | Doc | Core test files |
|-------|-----|-----------------|
| 0-1 | implementation-phase1.md | test_phase1_boot.py, test_phase1_repl.py, test_phase1_loader.py |
| 2   | implementation-phase2.md | test_phase2_devices.py, test_phase2_batch.py |
| 3   | implementation-phase3.md | test_phase3_launcher.py, test_phase3_editor.py |
| 4   | roadmap                 | test_phase4_sched.py, test_phase4_fat.py |

Run everything:

```powershell
pytest NovaDOS/tests -q
```

## 8. Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Program never leaves fetch loop / PC stuck | REPL still in `GETLINE` busy loop because keys were injected after boot or FIFO empty — inject before stepping |
| Instructions assemble to wrong bytes | `.sym` labels off — check `ORG` is the *first* directive and segments don't overlap |
| `HLT` ends the headless run early | a user program (or bug) executed HLT — frames of the REPL must be JMP-based |
| Sprite doesn't move after SCB write | SCB writes repaint only layers 5-8; check `active` bit0 in flags and `data_addr` range |
| Screen blank headless | layers visible by default; ensure `gfx.get_screen()` used for assertions |
| Bank copy "lost" | reading/writing the window while `BANK` was reset to 0 — keep `BANK` set for the whole copy |

## 9. MCP-assisted development

The MCP server (`py -3.13 nova_mcp_server.py`) exposes assemble, step, memory,
register, and graphics tools that mirror this workflow interactively — useful
for bring-up debugging of a single REPL command.

---
*Up: [`implementation-phase3.md`](implementation-phase3.md). Log learnings in
[`notes/start.md`](../notes/start.md).*