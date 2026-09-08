# NovaDOS Phase 3 — Shell & Utilities

**Goal:** a graphical program launcher, a small text editor, a file manager,
persistent settings, and a network console — mostly in Astrid (C-like) built on
the Phase 1/2 assembly kernel + `/dev` drivers.

**Exit criteria**
1. Click an icon with the mouse → the program runs (and returns to the shell).
2. `EDIT "FILE"` opens/creates an NDF data file, edits text, saves.
3. Settings (default layer colors, boot bank, bell on/off) persist across a
   `SAVE SETTINGS` + reboot in the same session.

## 1. Graphical launcher

Layer budget (9 layers, verified in `nova/graphics/compositor.py`):

| Layer | Use                                  |
|-------|--------------------------------------|
| 0     | console / text mode (kernel)         |
| 1     | window chrome, title bar             |
| 2     | icon grid (Phase 3 default)          |
| 3     | selection highlight / focus ring     |
| 4     | dialog / message box                 |
| 5     | sprite layer (animated selector)     |
| 6     | sprite layer (status sprites)        |
| 7-8   | user / effects                       |

Icon grid math (256×256, 32×32 tiles → 8×8 grid):

```
tile_x = col * 32, tile_y = row * 32
icon index = row * 8 + col
hit test: MX in [tile_x, tile_x+31] AND MY in [tile_y, tile_y+31]
```

Flow (poll-driven, no threading):

```asm
LAUNCHER_MAIN:
    CALL DRAW_CHROME          ; layer 1
    CALL DRAW_ICON_GRID       ; layer 2 (icons from NDF `type=0` entries)
    CALL DRAW_STATUS_BAR      ; layer 3/4 "BANK:n  MEM:xKB"
LAUNCHER_LOOP:
    CALL REPL_IDLE            ; consume a timer tick (keeps clock alive)
    MOV R0, [MOUSE_FLAG]      ; 0x0033
    CMP R0, 0
    JZ LAUNCHER_LOOP
    MOV R0, 0
    MOV [MOUSE_FLAG], R0
    MOV MX, [REG_MX]
    MOV MY, [REG_MY]
    MOV R2, [REG_MB]
    CALL HILITE_UNDER_CURSOR  ; layer 3 move + redraw
    AND R2, 0x01              ; left button
    CMP R2, 0
    JZ LAUNCHER_LOOP
    CALL HIT_TEST_ICON        ; -> index in R0, Z if none
    JZ LAUNCHER_LOOP
    CALL LAUNCH_INDEXED_ICON  ; BANK+LOAD+RUN (Phase 1 loader), returns here
    JMP LAUNCHER_LOOP
```

Keyboard fallback: arrows move the selection ring (sprite on layer 5), Enter
launches — required because pytest/headless uses keys, not the mouse.

## 2. Text editor

- Data model: an NDF `type=1` file staged into SCRATCH (max 2 KB in Phase 3),
  a line table (up to 64 × 2-byte offsets), and a cursor (row/col).
- Rendering: 32 cols × 32 rows; redraw window from the line table using the
  console driver on layer 0.
- Commands (key-only in Phase 3): typing inserts; Backspace deletes; arrows
  move; Ctrl-S saves (`/spr`-style windowed copy back to the bank); Esc exits.
- SYS/REPL bridge: `EDIT "NAME"` from the shell; on exit returns to launcher.

## 3. File manager

- `FILES` page: list NDF entries across banks (loop banks 1-15, read directory
  offset from each volume header). `COPY src dst`, `DELETE`, `RENAME` operate on
  directory entries — byte surgery on the 16-byte entry.

## 4. Settings

- A fixed NDF file on bank 0 (`type=1`, name `"SETTINGS"`), loaded at boot into
  `K_SETTINGS` (0xF100-0xF1FF). Fields: boot bank, console color, layer layout,
  bell flag, launcher grid dims.
- `SAVE SETTINGS` writes it back; `RESET SETTINGS` restores defaults.

## 5. Network console

- REPL command `NET` swaps the input focus to the UART bridge: every `/net` RX
  byte is echoed to the console; every key typed goes out `/net`.
- Uses vector-1 UART_FLAG (0x0031) to know when to drain.
- Requires the emulator to run with `--uart-bridge tcp` or `terminal`.

## 6. Phase 4 roadmap (design, not yet spec)

- **Cooperative multitasking:** the timer heartbeat in `implementation-phase2.md`
  §4 becomes a run queue. Each task = saved PUSHA/POPA frame + its own stack
  region carved from the user area; the REPL stays the scheduler. Tasks yield
  on `SYS_YIELD` (INT 4 opcode) or on blocking `/dev` ops.
- **FAT-like filesystem:** upgrade NDF to a proper FAT — directory entries gain
  next-cluster links; allocation bitmap in each volume header; fragment-aware
  `LOAD` (multi-`MEMCPY`). Backwards-compatible read of Phase 1 NDF.
- **TCP/IP over `/net`:** framing protocol on the UART bridge (start/len/checksum
  is already in `nova_uart.py` — `build_frame`) with a small socket API on top.
- **On-device IDE:** Astrid/NoBASIC compiler runs *on* the Nova-16? Unlikely in
  64 KB — instead a remote-compile bridge over `/net` (host compiles, OS loads
  the `.bin` into a bank). Flag as stretch goal.
- **Astrid porting notes:** Astrid already emits Nova-16 assembly (verified:
  `astrid/codegen/` emits `ORG 0x0100` IVT, DEFSTR, etc.). Phase 3 apps should
  be written in Astrid and *linked against the kernel* via the SYS mailbox
  (`INT 4`) rather than calling kernel internals, keeping the ABI surface tiny.

## 7. Acceptance tests

| # | Test | Assert |
|---|------|--------|
| 1 | launcher key-nav: arrows + Enter | launched program sets marker; shell returns |
| 2 | `EDIT "HELLO"` + type + Ctrl-S | NDF file `HELLO` length == typed bytes |
| 3 | `SAVE SETTINGS`; reboot | layer colors restored from bank 0 settings |
| 4 | `NET` with uart bridge seeded | echoed RX bytes appear on layer 0 |

---
*Up: [`implementation-phase2.md`](implementation-phase2.md).
Next: [`build-and-test.md`](build-and-test.md).*
