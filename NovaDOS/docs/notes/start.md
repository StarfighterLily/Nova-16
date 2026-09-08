# NovaDOS — Developer Notes (start)

Living notes for NovaDOS work. Per project protocols: *detailed notes for other
developers to read and add to*. Append dated entries; keep the pitfalls log
append-only. When this file exceeds ~400 lines, split it and add a pointer to
the continuation at the bottom.

## How to log

```markdown
## 2026-09-08 — <topic>
- what was decided / discovered
- exact commands run (copy/paste)
- links to code/doc evidence (file + line or function)
```

## Status board

| Phase | State | Notes |
|-------|-------|-------|
| 0 Scaffold | not started | docs drafted; src/ empty |
| 1 Kernel   | not started | implementation-phase1.md is the guide |
| 2 Devices  | not started | implementation-phase2.md |
| 3 Shell    | not started | implementation-phase3.md |
| 4 Advanced | not started | roadmap only |

## Verified emulator facts (Dec 2026 analysis)

- First `ORG` in a `.bin` = PC entry point (`nova/memory/memory.py::load`).
- `SWRITE` writes to the `VL` layer buffer; `SREAD` reads the **composite**
  screen (`nova/graphics/gfx.py:set_screen_val/get_screen_val`).
- `INT` pushes flags(2)+PC(2), clears I; `IRET` pops PC then flags
  (`core/exec_handlers.py:_int`, `core/exec.py:_iret`).
- IVT handler word read at `0x0100 + v*4`; only the word matters to the CPU.
- InterruptController auto-fires only vectors 0-3 (timer/serial/kbd/mouse);
  4-7 are software-only (`nova/bus/interrupt.py`).
- Bank window 0x8000-0xBFFF (16 KB); `BANK` 0-15; bank 0 = base RAM
  (`nova/memory/memory.py`, `core/regfile.py:0xC2`).
- Keyboard BUFFER_MAX = 64 (`nova_keyboard.py`); Enter=0x93, BS=0x92, Home=0x98.
- Timer TS = (divisor cycles −1); fires at TT ≥ TM with TC bit1
  (`nova/peripherals/timer.py`).
- SW bits 0-2 waveform / 3-5 channel / 6 loop / 7 enable (`nova_sound.py`).
- RTC epoch 2018-07-17 UTC; C0 low word, C1 high word (`nova_cpu.py`).
- Memory has no memory-mapped VRAM (checked against `nova/graphics/blitter.py`).

## Pitfalls log (append-only)

- [ ] Confirm assembler accepts `BANK` as an operand mnemonic (`MOV BANK, 3`);
      fallback is raw byte 0xC2 — document resolution here.
- [ ] Confirm `MEMCPY` operand order (`(dest, src, len)`) with a probe before
      writing the loader.
- [ ] Confirm `STRCMP` operand order and whether `POP` preserves the Z flag
      (used by `STRCMPEQ` in repl.asm).
- [ ] Confirm indirect `CALL P0` support; otherwise build a trampoline stub.
- [ ] Decide PUSHA/POPA isolation for `RUN` (see design.md open questions).

## First bring-up checklist (Phase 1)

1. `kernel.asm` with `ORG 0x0120` first → boot banner prints.
2. `HELP` command echoes help text.
3. `PEEK 0x0000` prints `4E 44` (signature "ND").
4. `A = 5` + `PRINT A` prints `5`.
5. Seed bank 3 (NDF) + `LOAD`/`RUN` sample that `RET`s to the REPL.

---
*Root: [`design.md`](../plans/design.md) · [`memory-map.md`](../plans/memory-map.md)
· [`phase1`](../plans/implementation-phase1.md) · [`phase2`](../plans/implementation-phase2.md)
· [`phase3`](../plans/implementation-phase3.md) · [`build-and-test`](../plans/build-and-test.md)*