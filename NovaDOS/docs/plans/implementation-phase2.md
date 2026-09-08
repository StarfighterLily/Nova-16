# NovaDOS Phase 2 — Device Drivers (`/dev`)

**Goal:** a working device abstraction over the Nova-16 peripherals, exposed to
REPL commands and to user programs through the `INT 4` SYS mailbox. Also: the
timer heartbeat for later cooperative multitasking, and a batch-script runner.

**Exit criteria**
1. `STAT /con`, `PUT /con "hello"`, `GET /con` (one key), `SEEK /gfx2 0x0040`
   work from the REPL and render expected pixels.
2. A sample program opens `/tim`, writes `TT`, waits, and reads it back via the
   SYS mailbox — returns `SYS_RET = 0`.
3. Every device has a pytest driver test.

## 1. Device table (16 slots × 8 B at `K_DEV_TBL = 0x0F00`)

| Off | Size | Meaning                                        |
|-----|------|------------------------------------------------|
| +0  | 1    | device type id (0-15, matches table below)     |
| +1  | 1    | flags: bit0 readable, bit1 writable, bit2 seekable, bit3 int-driven |
| +2  | word | driver entry address (R0-op style, `RET`)      |
| +4  | word | data base pointer (e.g. SCB base, or 0)        |
| +6  | 1    | sub-count (e.g. `/gfx` -> 9)                   |
| +7  | 1    | reserved                                       |

| ID | Name        | Class | Flags | Sub-count |
|----|-------------|-------|-------|-----------|
| 0  | `/con`      | con   | R/W   | 1 |
| 1  | `/gfxN`     | gfx   | R/W/S | 9 (layers 0-8) |
| 2  | `/spr`      | spr   | R/W/S | 1 |
| 3  | `/snd`      | snd   | W     | 1 |
| 4  | `/tim`      | tim   | R/W   | 1 |
| 5  | `/net`      | net   | R/W   | 1 |
| 6  | `/kbd`      | kbd   | R     | 1 |
| 7  | `/mouse`    | mouse | R     | 1 |
| 8  | `/rtc`      | rtc   | R     | 1 |
| 9-15 | free     | —     | —     | — |

## 2. Driver call convention

A driver is a normal subroutine called with registers pre-loaded. It performs
the op and `RET`s. **Contract:** the driver may clobber R0-R3 and P0-P1 only.

| Reg | In (per op)                 | Out                      |
|-----|------------------------------|--------------------------|
| R0  | op: 0=STAT, 1=GET, 2=PUT, 3=SEEK, 4=FLUSH, 5=INFO | op echo |
| R1  | sub-id (device instance)     | —                        |
| P0  | cursor/offset (GET/PUT/SEEK) | updated cursor           |
| R2  | PUT: data byte out; GET: data byte in | data byte |
| R3  | —                            | status (0 = ok)          |

Dispatcher (`devtable.asm`) resolves SYS `OPEN`+op into a `CALL driver_entry`.
REPL side:

```
> /dev list
> STAT /con
> PUT /con "hello"          ; string form accepted at REPL only
> GET /con  -> R               ; echoes key scan code as char
> SEEK /gfx2 0x0040
```

## 3. Per-device behavior

### 3.1 `/con` — console (real & write stream)

- **STAT:** return bytes available (KEYSTAT) and cursor address.
- **GET:** if `KEYSTAT` bit0, `KEYIN` → `R2`; else `R2 = 0` (non-blocking!).
  Blocking GET is a REPL-side loop, not a driver concern.
- **PUT:** `CHAR R2` at `VID_CURSOR`, then advance X by 8 (wrap to next row at
  column 32; scroll by clearing rows — keep it simple in Phase 2).
- SYS opcode: `SYS_CON_PUTCHAR = 2`, `SYS_CON_GETKEY = 1`.

### 3.2 `/gfxN` — graphics layers (the tricky one)

Layer buffers are **not** CPU memory and there is **no layer readback
instruction** (verified: `SWRITE` → `_set_pixel_to_layer(VL)` writes layer
buffers; `SREAD` → `get_screen_val()` reads the *composited screen*).

Consequently:

- **PUT** (layer-accurate): set `VL = sub-id`, `VM = 0`; derive
  `y = P0 >> 8`, `x = P0 & 0xFF`; set `VX/VY`; `SWRITE R2`. Advance `P0 += 1`.
- **GET** (composite-accurate): same addressing but use `SREAD` → `R2`.
  Documented limitation: the byte returned is what is *visible* on screen at
  that pixel, i.e. the top visible layer, not necessarily layer N.
- **SEEK:** `P0 += R2` (relative) — implement with simple add.
- **STAT:** return layer count (9) and current layer from `VL`.
- **SYS interface:** `SYS_GFX_PUT = 0x20` (arg0 = layer, arg1 = offset,
  arg2 = color), `SYS_GFX_GET = 0x21`.

Why this is acceptable: Phase 1/2 targets *drawing* (text, borders, icons).
Pixel-perfect readback is only available through VRAM (`VWRITE`/`VREAD`), which
is a **separate off-screen buffer** — useful for sprite staging in Phase 3.

### 3.3 `/spr` — sprite control blocks

SCB region is real CPU memory (0xF000-0xF0FF), so the driver is a windowed
copy:

- **GET/PUT/SEEK:** relative to `data base = 0xF000`; `P0` selects the byte.
  `GET`: `R2 = [0xF000 + P0]`; `PUT`: `[0xF000 + P0] = R2`.
- Writing an SCB byte auto-publishes `memory.scb_written` (handled by the
  emulator) so sprites re-blit. Remember the SCB layout from `docs/SPRITE_SYSTEM.md`
  and `nova/graphics/sprites.py`: `data_addr(2) x(1) y(1) w(1) h(1) flags(1)
  trans(1) reserved(8)`.

### 3.4 `/snd` — sound (write-only)

- **PUT** toggles a sub-command by cursor offset:
  - `P0 = 0` → set `SF = R2` (frequency)
  - `P0 = 1` → set `SV = R2` (volume)
  - `P0 = 2` → set `SW & 0x07 = R2` (waveform)
  - `P0 = 3` → `SA = P1` (16-bit sample address)
  - `P0 = 0x80` → `SPLAY`, `P0 = 0x81` → `SSTOP`
- SW bit layout (verified): bits 0-2 waveform, 3-5 channel, 6 loop, 7 enable.

### 3.5 `/tim` — timer (R/W mirror of TT/TM/TC/TS)

- **GET/PUT** `P0 = 0..3` maps to TT/TM/TC/TS.
- `TC` writes go through the timer's control semantics (bit0 enable, bit1
  interrupt-enable, TS = (divisor − 1)) — see `nova/peripherals/timer.py`.
- The vector-0 handler mirrors the four bytes into zero page `TIMER_MIRROR`
  (0x0028-0x002B) so programs can poll without touching registers.

### 3.6 `/net` — UART bridge

- **STAT:** `SERSTAT` → bytes available (RX) in `R2`.
- **GET:** `SERIN R2` (returns 0 on no data — non-blocking).
- **PUT:** `SEROUT R2` (blocking send is fine for the emulator).
- The vector-1 handler sets UART_FLAG (0x0031) on RX so the REPL can prompt
  "INCOMING" or (Phase 3) run a network console. Bridge config (TCP/terminal)
  happens at emulator start (`--uart-bridge`), not from the OS.

### 3.7 `/kbd` — keyboard status

- **GET** cursor 0-3 → status / data / count / control shadow bytes
  (`KEYSTAT`, `KEYCOUNT`, `KEYCTRL` mirrors). Data byte is the *last* key
  (non-destructive; use `/con` GET for consuming).

### 3.8 `/mouse` — mouse snapshot

- **GET** cursor 0-2 → MX / MY / MB. Optionally `P0` = button mask check:
  `STAT` reports whether any button bit is set. `MOUSECTRL` can enable the
  emulator's hardware cursor. Vector 3 sets MOUSE_FLAG (0x0033);
  the launcher (Phase 3) polls then clears it.

### 3.9 `/rtc` — real-time clock

- **GET** cursor 0-1 → `C0` (low word), `C1` (high word) of the 32-bit epoch
  seconds since 2018-07-17 UTC. Provide `/rtc` "HH:MM:SS" formatting in Phase 3
  (divide-and-modulo through the decimal printer).

## 4. Timer heartbeat & the multitask hook (Phase 2 groundwork)

```asm
; REPL idle loop — poll the tick flag instead of busy-waiting everywhere
REPL_IDLE:
    MOV R0, [0x0030]        ; TICK_FLAG
    CMP R0, 0
    JZ REPL_IDLE
    MOV R0, 0
    MOV [0x0030], R0        ; consume tick
    ; Phase 4: run a cooperative scheduler queue here
    CALL REPL_TICK  ; (update clock line, idle tasks, etc.)
    JMP REPL_IDLE
```

This replaces naked `KEYSTAT` busy-loops in the REPL: read keys while idle,
service the timer once per tick. It is the seam where cooperative multitasking
drops in later.

## 5. Batch script runner

- `RUN "SCRIPT"` where `type == 2`: load the script into SCRATCH, then feed each
  line (`0x0A`-delimited) through `EXEC_LINE` — the same routine the REPL uses.
- Guard: max 64 lines, max 128 chars/line; never allow recursive `RUN` of a
  script in Phase 2.

## 6. Acceptance tests (harness in build-and-test.md)

| # | Test | Assert |
|---|------|--------|
| 1 | `STAT /con` + `PUT /con "A"` | "A" glyph pixels at VID_CURSOR |
| 2 | `PUT /gfx2 0x0040 0x0F` with offset | layer 2 buffer[pixel] == 0x0F |
| 3 | `/spr` write byte 7 (transparency) | memory[0xF007] == value; no crash |
| 4 | `/tim` set TT=3, TM=5, TC=0x03; step 8 | TT mirrored via TIMER_MIRROR changes |
| 5 | `/net` put "HI"; program `SYS 1=GETKEY`, 2=PUTCHAR` | SYS_RET == 0 on both |
| 6 | batch script sets 3 variables | all three values set after `RUN "SCRIPT"` |

## 7. Known device quirks (verified)

- `SREAD` composite-only readback — see §3.2.
- Keyboard `BUFFER_MAX` is 64 (not 16 as older docs said) — status bit1 = full.
- Timer `TT` increments only while enabled (`TC bit0`) and caps at 255 before
  the modulo reset (`nova/peripherals/timer.py`).
- UART RX FIFO is small; the OS should drain `/net` on UART_FLAG, not poll.
- Mouse positions are 16-bit but the screen is 256×256 — mask `& 0xFF`.

---
*Up: [`implementation-phase1.md`](implementation-phase1.md).
Next: [`implementation-phase3.md`](implementation-phase3.md).
Log decisions in [`notes/start.md`](../notes/start.md).*