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
| 0 Scaffold | done | src/ + build/ populated; kernel boots headless |
| 1 Kernel   | done | 11/11 pytest green; all 5 exit criteria verified |
| 2 Devices  | not started | implementation-phase2.md |
| 3 Shell    | not started | implementation-phase3.md |
| 4 Advanced | not started | roadmap only |

## 2026-09-10 — Phase 1 kernel implemented and green

- Built the full Phase 1 kernel per `implementation-phase1.md`, restructured
  into the documented one-file-per-part layout with INCLUDE splicing
  (`kernel.asm` -> ndefs/boot/console/parse/vars/sys/loader/commands/repl).
- Commands working from the REPL: HELP, PEEK, BANK, DIR, LOAD, RUN, NEW,
  PRINT, `A = 5` assignment, BYE (HLT). SYS mailbox (INT 4) implements
  opcodes 1-6 with PUSHA/POPA isolation.
- Sample NDF program (`src/sample.asm`, ORG 0x1000) loads from bank 3 via
  LOAD and returns to the REPL through indirect CALL P0 / RET, setting
  marker bytes 0x42/0x2A at 0x00E0/0x00E1.
- Test harness in `NovaDOS/tests/` (conftest + 3 files, 11 tests): boots the
  kernel through the real Memory/CPU/Keyboard/InterruptController stack,
  seeds the keyboard FIFO, seeds bank 3 via `write_bytes_direct`, and asserts
  registers, memory, and compositor layer pixels. REPL_MAIN is resolved from
  `build/kernel.sym` at import time so tests track kernel relayouts.

Exact commands:

```powershell
py -3.13 nova_assembler.py NovaDOS/src/kernel.asm   # 3538 bytes -> build/
py -3.13 nova_assembler.py NovaDOS/src/sample.asm   # 19 bytes -> build/
py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin --cycles 6000
python -m pytest NovaDOS/tests -q                   # 11 passed
```

Evidence: headless boot prints 222 non-black pixels on layer 0 (banner) and
rests in GETLINE_LOOP; `pytest NovaDOS/tests` green; emulator core
unaffected (`tests/unit/test_memory.py` + `tests/unit/test_bank_register.py`
67 passed).

## 2026-09-10 — Pitfalls log resolutions

- **`MOV BANK, 3` operand mnemonic**: works — assembler maps BANK (0xC2) as
  a register mnemonic (`nova/assembler/codegen.py` REGISTER_CODES; verified
  by `tests/unit/test_bank_register.py::test_mov_bank_immediate`).
- **MEMCPY operand order**: `(dest, src, len)` confirmed via IVT wiring test
  (`test_boot_wires_ivt_vectors` reads handler words back from 0x0100+).
- **STRCMP operand order / POP flag preservation**: avoided entirely —
  string compares in the loader are hand-rolled byte loops, no POP-across-
  flags dependency exists in the shipped code.
- **Indirect CALL P0**: supported. `get_operand_value` on a register operand
  returns register contents as the branch target (`nova_cpu.py`), used by
  NDF_RUN; verified by the LOAD/RUN round-trip test.
- **PUSHA/POPA isolation for RUN**: not needed in Phase 1 — user programs
  return via RET and the REPL re-initializes its own registers; the SYS
  mailbox (the ABI surface for user programs) does PUSHA/POPA.

## 2026-09-10 — New pitfalls discovered (append-only)

- **Assembler ignores EQU symbols in memory references**: `MOV R0, [SYM]`
  fails with "Undefined symbol" (legacy 2-pass assembler's operand
  classifier only matches register/immediate/hex patterns inside
  brackets). Workaround: literal hex addresses in memory refs with the
  symbolic name as a trailing comment; EQUs remain valid for immediates.
  Documented in `src/ndefs.asm`. Revisit if/when the token-based
  assembler (`nova/assembler/`) becomes the default path.
- **IVT slot stride is 4 bytes, not 2**: the CPU reads the handler word at
  `0x0100 + v*4`. A vector table of packed 2-byte words silently wires
  only vectors 0-3 (later slots read garbage/code bytes). VECTOR_TABLE
  uses one 4-byte slot per vector (handler word + reserved word).
- **Interrupt handlers must preserve registers**: INT frames save only
  flags+PC; IRET restores nothing else. V0-V3 now PUSH/POP R0 around their
  flag-byte stores, otherwise pre-seeded keyboard input corrupts REPL R0.
- **Duplicate labels assemble silently**: the 2-pass assembler resolves
  repeated label definitions to one address without error — the loader and
  REPL dispatcher both defining `CMD_LOAD:` made `RUN`/`LOAD` branch into
  the dispatcher. Loader routines renamed NDF_LOAD/NDF_RUN/NDF_DIR/NDF_NEW.
- **Byte order is big-endian everywhere**: memory words, the .bin, and NDF
  directory fields. INIT_VARS originally wrote VARS_BASE little-endian,
  which read back as 0x00D0; LOAD_FOUND word math likewise rebuilt.
- **CLRSCREEN per-pixel loop costs ~400k cycles**: replaced with a single
  SFILL 0x00 (fill_layer targets the active VL layer); boot reaches the
  REPL in <5k cycles.
- **Test predicates can fire mid-instruction**: `run_until` checks between
  steps, so a predicate like "bank byte == 3" passes one instruction before
  `MOV BANK, R0` runs. Composite predicates (state AND in_repl) avoid it.
## 2026-09-10 — Console key-code fix (interactive GUI path)

- **Bug:** booting `kernel.bin` in the interactive GUI showed the prompt but
  no command ever executed; Enter produced only a cursor-dropping newline
  and Backspace drew a garbage glyph instead of editing the line.
- **Root cause:** GETLINE only recognized the design docs' Enter=0x93 /
  Backspace=0x92. But the real chain — `nova_gui.py::map_event_to_nova_key`
  (Return→'enter', Backspace→'backspace') → `NovaKeyboard.press_key` →
  `_create_key_mapping()` — produces **0x0A / 0x08**. The unrecognized 0x0A
  was stored into the line buffer and echoed as a newline by PUTCHAR, so
  lines never terminated; 0x08 was stored and echoed as glyph 0x08.
- **Fix:** GETLINE now accepts Enter = {0x0A, 0x0D, 0x93} and Backspace =
  {0x08, 0x92}, and swallows any other byte outside printable ASCII
  (0x20-0x7E) so arrows/F-keys/Tab can never echo as glyph garbage.
  Constants canonicalized in `src/ndefs.asm` (K_ENTER=0x0A, K_BACKSP=0x08,
  K_ENTER_ALT=0x93, K_BACKSP_ALT=0x92). Raw per-key codes remain available
  to programs via SYS GETKEY (opcode 1); the line editor only filters.
- **Coverage gap closed:** the old tests injected raw 0x93, exactly
  mirroring the doc error. New tests type via `kbd.press_key` (the same
  call the GUI makes): `test_gui_path_typing_executes_commands` runs HELP
  through scan codes, and
  `test_gui_control_codes_swallowed_and_backspace_edits` proves Tab/BS are
  swallowed and BS edits the buffer (types "A = 6", backspaces, types "5",
  asserts A==5).
- **Test-bug note:** the first draft of the backspace test called
  `type_cmd_gui("A = 6")` (which appends its own Enter) before the extra
  backspace — the kernel correctly executed "A = 6" and sat in the NEXT
  unterminated line. The passes-13 run uses one terminator per line.

Commands:

```powershell
py -3.13 nova_assembler.py NovaDOS/src/kernel.asm   # 3597 bytes -> build/
python -m pytest NovaDOS/tests -q                   # 13 passed
```

- **pytest.ini section header is `[tool:pytest]`**: only honored in
  setup.cfg; pytest.ini requires `[pytest]`. Net effect repo-wide: ini
  markers/addopts silently ignored (hence PytestUnknownMarkWarnings and no
  --strict-markers enforcement). Left as-is (repo-wide behavior change out
  of scope); flagged here for whoever owns the test config.

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
- Keyboard BUFFER_MAX = 64 (`nova_keyboard.py`); the GUI path
  (`nova_gui.py::map_event_to_nova_key` + `press_key`) produces **Enter=0x0A,
  Backspace=0x08** (plain ASCII controls); 0x80-0x9E block holds
  arrows/F-keys/insert/delete/home for the special-key names. The 0x93/0x92
  values are NOT produced by the emulator keyboard path (see 2026-09-10
  console fix entry). Letters arrive as their ASCII codes.
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