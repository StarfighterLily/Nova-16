# NovaDOS — A TI-OS / DOS / Plan-9 Hybrid for the Nova-16

> **Status:** Living design document, ground-truth checked against the Nova-16
> implementation (commit `1ae12ab`). Items marked **[fix]** correct earlier
> drafts that contradicted the emulator.

NovaDOS is an operating system that runs *inside* the Nova-16 emulator. It blends
three lineages:

| Lineage        | Contribution |
|----------------|--------------|
| TI-OS (NoBASIC heritage) | Immediate-mode command line; typed variables (real, string, list, matrix); graphical shell with layer management; icon-based program launcher |
| DOS            | REPL with commands & batch scripts; program load/run; PEEK/POKE memory tools; filesystem abstraction over banked memory |
| Plan 9         | "Everything is a file": `/con`, `/gfx0`-`/gfx8`, `/spr`, `/snd`, `/tim`, `/net`, `/kbd`, `/mouse`, `/rtc` |

---

## 1. Ground Truth — what the Nova-16 actually provides

Every line below was verified in the codebase. It is the contract NovaDOS is built on.

### 1.1 CPU & registers

- 16-bit big-endian CPU, 64 KB unified RAM, single-threaded fetch-execute.
- **R0-R9** (8-bit; register codes 0xE7-0xF0), **P0-P9** (16-bit; 0xF1-0xFA);
  **SP = P8** (0xFB, initial value 0xFFFF), **FP = P9** (0xFC).
- Byte access to P-registers: `P0:` high byte (0xC9-0xD2), `:P0` low byte (0xD3-0xDC).
- 12 flags: **T S O B D I C Z P H A E** (one 12-bit field; `I`=5 is the master
  interrupt switch — `STI`/`CLI`).
- Hardware stack in RAM, grows down from 0xFFFF. Each `INT` frame = 2 B flags + 2 B PC (4 B);
  each `CALL` frame = 2 B return address.

### 1.2 Memory

- Hot region 0x0000-0x011F (zero page + IVT) is the fastest-accessed region —
  OS globals and scratch belong there.
- **Bank window 0x8000-0xBFFF (16 KB):** the `BANK` register (code 0xC2, 0-15)
  selects the visible page. Bank 0 = base-RAM pass-through; banks 1-15 are private
  16 KB pages → **240 KB usable extra storage**. **[fix]** The earlier draft wrote
  "256 KB storage" — bank 0 aliases base memory, so 15 pages are genuine additional.
- **SCB region 0xF000-0xF0FF** (16 sprites × 16 B); writes publish `memory.scb_written`.
- No hardware paging or protection — NovaDOS is a **cooperative** OS.

### 1.3 Graphics — there is NO memory-mapped VRAM

- 256×256 screen, 8-bit color/byte per pixel, **9 layers** (0 base, 1-4 background,
  5-8 sprite). `VL` selects the active layer.
- **`SWRITE`/`SREAD` act on the current `VL` layer** (verified: `set_screen_val`
  routes through `_set_pixel_to_layer(VL)`).
- `VX`/`VY` = coordinates (VM=0) or linear screen address (VM=1).
- VRAM is a **separate emulator-side 64 KB buffer** reached by `VREAD`/`VWRITE`
  and blit ops — it is *not* CPU-RAM. **[fix]** The region 0xC000-0xEFFF is ordinary
  RAM; label it "data region" (sprite bitmaps, sound samples, variable heap) by
  **software convention only**.
- `CHAR`/`TEXT` render 8×8 glyphs; **the emulator keeps no text cursor — NovaDOS
  must maintain its own** (zero page `VID_CURSOR`).
- **Read-back caveat:** `SREAD` returns the *composited* screen pixel, not the `VL`
  layer buffer. There is no instruction that reads an arbitrary layer's raw byte.
  So `/gfxN` PUT is layer-accurate but `/gfxN` GET returns what is *visible* at that
  pixel. Programs that need pixel-perfect readback should use VRAM (VWRITE → VREAD).
- Mouse: `MOUSECTRL` (0xB3), `MX`/`MY`/`MB` (0xC5-0xC7); buttons bit 0 = left,
  bit 1 = right.

### 1.4 Interrupts

| V | Addr  | Source            | Role in NovaDOS |
|---|-------|-------------------|-----------------|
| 0 | 0x0100| Timer (TC bit 1)  | OS tick / cooperative scheduler heartbeat |
| 1 | 0x0104| UART RX           | `/net` async input |
| 2 | 0x0108| Keyboard          | key events |
| 3 | 0x010C| Mouse             | button/position events |
| 4 | 0x0110| software `INT 4`  | **kernel SYS-call dispatch** |
| 5 | 0x0114| software          | user interrupt 2 |
| 6 | 0x0118| software          | user interrupt 3 |
| 7 | 0x011C| debug/breakpoint  | trap handler |

- `INT v` requires the I flag; the handler runs with I cleared and resumes via `IRET`.
- The emulator's InterruptController only auto-fires vectors 0-3 (timer, serial,
  keyboard, mouse). **[fix]** "Hook all 8 vectors" means: write handler addresses for
  0-3 (peripheral-driven) *and* 4-7 (software `INT` instruction).

### 1.5 Peripherals (verified)

- **Keyboard:** `KEYIN` (0x43), `KEYSTAT` (0x44), `KEYCOUNT` (0x45), `KEYCTRL` (0x47).
  Scan codes: `0x80`-`0x83` arrows, `0x91` Delete, `0x92` Backspace, `0x93` Enter,
  `0x98`/`0x99` Home/End, `0x9A` Esc, `0x9B` Space, `0x84`-`0x8F` F1-F12.
- **Timer:** `TT`/`TM`/`TC`/`TS` (0xE3-0xE6). TS = divisor cycles − 1; fires when
  TT ≥ TM (and TC bit 1 set).
- **Sound:** `SA`/`SF`/`SV`/`SW` (0xDD-0xE0) + `SPLAY`/`SSTOP`/`STRIG`. SW bits
  0-2 waveform, 3-5 channel, 6 loop, 7 enable.
- **UART:** `SERIN`/`SEROUT`/`SERSTAT`/`SERCTRL` (0xA2-0xA5) with optional TCP /
  terminal host bridge.
- **RTC:** `C0`/`C1` (0xC3-0xC4) = seconds since 2018-07-17 UTC (32-bit, C0 low).
- **Memory/string helpers:** `MEMCPY`/`MEMSET`/`MEMMOVE`, `STRCPY`/`STRCAT`/
  `STRCMP`/`STRLEN`, `ITOS`/`STOI` — key building blocks for the loader and console.

---

## 2. Canonical Memory Layout

The complete byte-granular tables (zero page, IVT, kernel data constants) live in
[`memory-map.md`](memory-map.md) — *normative*. Summary:

| Range        | Size   | Owner             | Notes |
|--------------|--------|-------------------|-------|
| 0x0000-0x00FF | 256 B  | OS globals        | zero page, hot view |
| 0x0100-0x011F | 32 B   | IVT               | 8 vectors × 4 B |
| 0x0120-0x0FFF | 3,808 B| Kernel code       | boot + REPL + loader + vars + /dev dispatch |
| 0x1000-0x17FF | 2 KB   | Kernel extent     | overflow zone if kernel > 3.8 KB |
| 0x1800-0x7FFF | 26 KB  | User program area | `LOAD`/`RUN` target (else 0x1000) |
| 0x8000-0xBFFF | 16 KB  | Bank window       | `BANK` 0-15 selects page |
| 0xC000-0xCFFF | 4 KB   | Asset store       | sprite bitmaps, sound samples |
| 0xD000-0xE7FF | 6 KB   | Variable heap     | TI-OS variables (VARS_BASE) |
| 0xE800-0xEFFF | 2 KB   | Kernel scratch    | line buffer, cursors, syscall mirrors |
| 0xF000-0xF0FF | 256 B  | SCB               | hardware sprite controls |
| 0xF100-0xFBFF | 1,280 B| OS settings/FAT   | persisted settings + bank directory cache |
| 0xFC00-0xFFFF | 1 KB   | Hardware stack    | grows down from 0xFFFF |

Budget warnings (verified sizes):

- Kernel = **3,808 B**. Phase 1 must fit inside it; if it grows, use the 0x1000-0x17FF
  extent and bump `PROG_BASE` to 0x1800.
- Stack = 1 KB = 256 nested `INT` frames (or 512 `CALL` frames). `PUSH`/`CALL`
  below 0xFC00 silently corrupts the FAT area — guard recursion depth.

## 3. Boot Sequence

Detailed in [`implementation-phase1.md`](implementation-phase1.md). Summary:

1. `MOV SP, 0xFFFF`; clear screen; select console layer/color.
2. Write vector handler addresses into 0x0100-0x011F (bytes 0-1 of each slot).
3. Store `VARS_BASE`, `PROG_BASE`, device-table base into the zero page.
4. Initialize keyboard/mouse/timer control registers; `STI`.
5. Print banner; enter REPL.

## 4. Kernel Components (0x0120-0x0FFF)

- **Boot / reset** — vector wiring, stack init, zero-page self-test.
- **Interrupt dispatcher** — vector 4 SYS-call mailbox handler (kernel's main vectored
  code); vectors 0-3 are short peripheral handlers that set a flag byte and `IRET`.
- **Console I/O** — `GETLINE` (line editor: Backspace, cursor keys, Home/End, Enter),
  `PRINT`, `PRINTHEX`, `NEWLINE`. Text cursor in zero page.
- **Command parser / REPL** — dispatch on tokenized first word (see §5).
- **Bank manager** — `BANK` register helpers + `MEMCPY` window⇄RAM copies.
- **Program loader** — NDF directory scan in the active bank page; `LOAD`→RAM, `RUN`.
- **Variable store** — A-Z reals + Str0-9 strings (lists/matrices in Phase 3).
- **Device table** — 16 slots × 8 B dispatch table (§6).
- **Batch runner** (Phase 2) — executes a script file line-by-line through the REPL.

## 5. REPL Command Set

```
NovaDOS v1.0
> HELP                      ; command list
> DIR                       ; list programs in active bank
> LOAD "GAME"               ; copy program from bank to PROG_BASE
> RUN                       ; CALL entry of loaded program (ends with RET)
> BANK 3                    ; switch bank window
> PEEK 0x1000               ; print byte at address
> POKE 0x1000, 0xFF         ; write byte at address
> CALL 0x1000               ; call a subroutine address directly
> LIST                      ; list variable names + values
> A = 5                     ; set real variable
> Str0 = "hello"            ; set string variable
> PRINT A                   ; print variable value
> NEW                       ; clear program area
> CLS                       ; clear screen
> SAVE "GAME", 0x1000       ; copy program area into bank (Phase 1)
> BYE                       ; halt
```

Parsing: commands case-insensitive; arguments space-separated; strings double-quoted;
numbers decimal or `0x`-hex. **Programs must end with `RET`, never `HLT`** (`HLT`
halts the entire emulator). **[fix]** added — program return protocol was unspecified.

## 6. Device Files (Plan 9) & SYS-call interface

**[fix]** All /dev access funnels through the kernel via the `INT 4` SYS mailbox,
so kernel state stays consistent between programs:

| Zero page | Purpose |
|-----------|---------|
| 0x0012    | `SYS_NUM` (word) — operation id |
| 0x0014    | `SYS_RET` (word) — 0 = ok, else error |
| 0x0016/0x0018/0x001A | `SYS_ARG0..2` (words) |

Device ids — 16-slot table **[fix]** (earlier draft said 8 slots but lists more):

| ID | Name      | Access | Backed by |
|----|-----------|--------|-----------|
| 0  | `/con`    | R/W    | KEYIN stream (R); CHAR/TEXT cursor writer (W) |
| 1  | `/gfx0`-`/gfx8` | R/W | layer byte stream; offset = y*256+x; sub-id 0-8 |
| 2  | `/spr`    | R/W    | SCB region (0xF000-0xF0FF) |
| 3  | `/snd`    | W      | SA/SF/SV/SW + SPLAY/SSTOP/STRIG |
| 4  | `/tim`    | R/W    | TT/TM/TC/TS |
| 5  | `/net`    | R/W    | SERIN/SEROUT stream |
| 6  | `/kbd`    | R      | keyboard status bytes |
| 7  | `/mouse`  | R      | MX/MY/MB snapshot |
| 8  | `/rtc`    | R      | C0/C1 32-bit seconds |

Driver convention: `R0` = op (0 STAT, 1 GET, 2 PUT, 3 SEEK, 4 FLUSH), `R1` = sub-id,
`P0` = cursor/offset, `R2` = data byte, `R3` = status. See
[`implementation-phase2.md`](implementation-phase2.md).

## 7. Variable System (TI-OS heritage)

| Type   | Name                       | Phase |
|--------|----------------------------|-------|
| Real   | A-Z (26 × signed word)     | 1     |
| String | Str0-Str9 (10 × 1+255 B)   | 1     |
| List   | L0-L5 (6 × ≤255 elts)      | 3     |
| Matrix | Mat0-Mat9 (≤ 99×99)        | 3     |
| Pic    | Pic0-Pic9 (VRAM snapshots) | 3     |
| GDB    | GDB0-GDB9 (graph buffers)  | 4     |

Minimum footprint = 26×2 + 10×256 = **2,612 B — too big for the 256-byte zero page**.
**[fix]** Variables live in the 0xD000-0xE7FF variable heap; the zero page holds only
pointers/indices (`VARS_BASE`, `VARS_END`).

## 8. Program Storage (NDF) & Launcher

- Each bank page is an **NovaDisk (NDF)** volume: 16-byte directory entries at window
  offset 0x0010; file bytes from 0x0400. Entry = name(10) + type + flags + start(2) +
  length(2) + entry-point(2).
- `LOAD "GAME"` → set `BANK n`; `MEMCPY` window[start .. start+len] → `PROG_BASE`;
  `BANK 0`; remember entry point. `RUN` → `CALL entry` (program returns via `RET`).
- Launcher UI (Phase 3): icon grid on BG layers 1-4, selection ring on sprite layers,
  mouse `MB` click-hit test, page navigation through bank `DIR`.

## 9. Build & Test Toolchain

See [`build-and-test.md`](build-and-test.md): assemble with
`py -3.13 nova_assembler.py NovaDOS/src/kernel.asm` (the **first `ORG 0x0120`
directive becomes the PC entry point** — verified in `nova/memory/memory.py`),
run headless with `py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin`,
regression-test with pytest (`NovaDOS/tests/` seeds the keyboard buffer, steps the
CPU to a sentinel, asserts registers/memory).

## 10. Implementation Phases

| Phase | Scope | Exit criteria |
|-------|-------|---------------|
| 0 | Scaffold repo, banner, boot stub, SP/vector init | boots, prints banner, answers `HELP` |
| 1 | Kernel: console I/O, REPL, NDF loader, A-Z + Str vars, SYS mailbox | `LOAD`/`RUN` sample that `RET`s; pytest green |
| 2 | Device drivers (§6), `/dev` REPL, timer heartbeat, batch runner | every device passes a driver test |
| 3 | GUI launcher, editor, settings, network console | click-to-run works with mouse |
| 4 | Cooperative multitasking, FAT upgrade, TCP/IP over `/net`, on-device IDE | two concurrent demos |

## 11. Open Questions

- Should `RUN` snapshot/restore the full register set (PUSHA/POPA) for isolation?
- Should batch scripts live at a reserved NDF file on bank 0?
- Do we need `.org`-aware loading for multi-segment programs (kernel extent)?

---
*Next: [`memory-map.md`](memory-map.md) → [`implementation-phase1.md`](implementation-phase1.md)
→ [`implementation-phase2.md`](implementation-phase2.md) → [`implementation-phase3.md`](implementation-phase3.md)
→ [`build-and-test.md`](build-and-test.md). Life-log in [`notes/start.md`](../notes/start.md).*