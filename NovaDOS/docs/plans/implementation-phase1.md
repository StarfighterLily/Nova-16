# NovaDOS Phase 1 — Kernel Foundation

**Goal:** a bootable Nova-16 assembly kernel that clears the screen, wires all 8
interrupt vectors, prints a banner, and hosts a working REPL with console I/O,
hex PEEK/POKE, bank switching, NDF `LOAD`/`RUN`, and A-Z / Str0-9 variables.

**Exit criteria**
1. `py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin --cycles 20000`
   boots without exceptions and reaches the REPL prompt.
2. Seeded keyboard sequence `HELP <Enter>` then `A = 5 <Enter>` then
   `PRINT A <Enter>` then `PEEK 0x0000 <Enter>` produces the expected screen
   pixels (verified in pytest).
3. A sample program stored in bank 3 is `LOAD`ed and `RUN`, then returns via
   `RET` to the prompt.

## 1. Repo layout (per project protocols)

```
NovaDOS/
  src/                  ; assembly sources
    kernel.asm          ; entry point, boot, includes all parts
    boot.asm            ; reset, vector wiring, banner
    console.asm         ; GETLINE / PRINT / PRINTHEX / NEWLINE
    repl.asm            ; command dispatch loop
    parse.asm           ; hex + decimal parsers
    vars.asm            ; A-Z reals + Str0-9
    loader.asm          ; NDF directory, LOAD/SAVE/RUN/NEW
    sys.asm             ; vector 4 SYS mailbox
    ndefs.asm           ; the EQU block from memory-map.md §4
  build/                ; kernel.bin/.org/.sym
  docs/
    plans/ design.md memory-map.md implementation-phase*.md build-and-test.md
    notes/ start.md
  tests/
    conftest.py test_phase1_boot.py test_phase1_repl.py test_phase1_loader.py
```

Use `INCLUDE` to splice parts — one `.asm` produces one `.bin` + `.org` + `.sym`.

## 2. Build / run loop

```powershell
py -3.13 nova_assembler.py NovaDOS/src/kernel.asm      # -> build/kernel.bin
py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin --cycles 20000
py -3.13 nova_disassembler.py NovaDOS/build/kernel.bin   # inspect emitted code
pytest NovaDOS/tests -q -m unit                          # regression
```

Loader detail (verified in `nova/memory/memory.py`): the `.org` file is read and
the **first ORG segment's start address is returned as the entry point**, then
set as PC. So `kernel.asm` must begin with:

```asm
    ORG 0x0120        ; FIRST ORG => entry point 0x0120 (PC after load)
START:
    JMP BOOT
```

## 3. Boot sequence (`boot.asm`)

```asm
BOOT:
    MOV SP, 0xFFFF        ; reset hardware stack (P8)
    MOV FP, 0xFFFF        ; reset frame pointer
    MOV VM, 0             ; coordinate mode for graphics
    MOV VL, 0             ; console text on layer 0
    MOV VC, 0x0F          ; white pen
    CALL CLRSCREEN        ; clear layer (see console.asm)
    MOV P0, 0             ; reset text cursor
    MOV [ZP_VID_CUR], :P0 ; cursor X = 0, Y = 0 (low byte)
    MOV [ZP_VID_CUR+1], P0:
    MOV BANK, 0
    CALL WIRE_VECTORS     ; write handler addresses into the IVT
    CALL INIT_VARS        ; set VARS_BASE/END, PROG_BASE, CUR_BANK=0
    CALL PRINT_BANNER
    STI                   ; enable interrupts (I flag)
    JMP REPL_MAIN
```

> `MOV [ZP_VID_CUR], :P0` needs a memory/register source; if the assembler
> balks, keep the cursor in two scratch bytes and write them via `MOV R0, 0`
> then `MOV [ZP_VID_CUR], R0`. Log the pattern that works in `notes/start.md`.

## 4. Vector wiring (`boot.asm`)

The CPU reads handler addresses as **words at `0x0100 + v*4`**
(`core/exec_handlers.py:_int`). One `MEMCPY` of a 32-byte table:

```asm
WIRE_VECTORS:
    MOV P0, VECTOR_TABLE    ; source table (kernel data)
    MOV P1, 0x0100          ; IVT base
    MOV R0, 32              ; 8 slots x 4 B
    MEMCPY P1, P0, R0
    RET

VECTOR_TABLE:
    DW V0_TIMER_HANDLER     ; word 0 = handler address
    DB 0x01, 0x00           ; flags, src id
    DW V1_SERIAL_HANDLER
    DB 0x01, 0x01
    DW V2_KEYBOARD_HANDLER
    DB 0x01, 0x02
    DW V3_MOUSE_HANDLER
    DB 0x01, 0x03
    DW SYS_DISPATCHER
    DB 0x01, 0x04
    DW USER2_HANDLER
    DB 0x01, 0x05
    DW USER3_HANDLER
    DB 0x01, 0x06
    DW DBG_HANDLER
    DB 0x01, 0x07
```

Handler style — vectors 0-3 only set a flag byte and return:

```asm
V0_TIMER_HANDLER:
    PUSH R0            ; save caller's register before touching it
    MOV R0, 1
    MOV [0x0030], R0   ; TICK_FLAG
    POP R0
    IRET               ; restore PC + flags, re-enable I
```

## 5. Console I/O (`console.asm`)

### 5.1 PRINT — draw a null-terminated string at the text cursor

```asm
; P0 = pointer to null-terminated string (DEFSTR). Draws at VID_CURSOR.
PRINT:
    MOV R0, [ZP_VID_CUR]   ; X = cursor low byte
    MOV VX, R0
    MOV R0, [ZP_VID_CUR+1] ; Y = cursor high byte
    MOV VY, R0
    TEXT P0                ; render until 0x00, advance VX by 8 per glyph
    MOV R0, [ZP_VID_CUR]   ; store glyph X back
    MOV [ZP_VID_CUR], R0
    RET
```

### 5.2 PRINTHEX — port the verified routines from `asm/progs/monitor.asm`

`PRINT_HEX_BYTE`, `PRINT_HEX_WORD_P0`, `READ_HEX_WORD`, `READ_HEX_BYTE`, and
`DELAY` already exist and are emulator-verified. Copy them into `console.asm`
and set `VL` to the console layer. This is the fastest route to working
PEEK/POKE.

### 5.3 GETLINE — line editor (echo + Backspace + Enter)

```asm
; Returns: LINE_LEN (0x0022) chars in buffer at CLI_LINE_PTR (0x0020).
GETLINE:
    MOV P1, [ZP_LINE_PTR]   ; line buffer pointer
    MOV R4, 0               ; cursor position
    MOV R5, 0               ; length
GL_LOOP:
    KEYSTAT R0
    CMP R0, 0
    JZ GL_LOOP              ; busy-wait for a key (fine headless)
    KEYIN R0
    CMP R0, K_ENTER
    JZ GL_DONE
    CMP R0, K_BACKSP
    JZ GL_BS
    CMP R4, 127             ; hard cap (buffer is 128 B)
    JGE GL_LOOP
    MOV [P1+R4], R0         ; store key byte (indexed addressing)
    CHAR R0                 ; echo at current VX,VY
    ADD VX, 8
    INC R4
    INC R5
    JMP GL_LOOP
GL_BS:
    CMP R4, 0
    JZ GL_LOOP
    DEC R4
    DEC R5
    ; redraw blank: move cursor back 8 px and draw space
    SUB VX, 8
    MOV R0, K_SPACE
    CHAR R0
    SUB VX, 8
    JMP GL_LOOP
GL_DONE:
    MOV [ZP_LINE_LEN], R5
    MOV [ZP_CURSOR], R4
    CALL NEWLINE
    RET
```

> `ADD VX, -8` wraps to 8-bit math — prefer `SUB VX, 8`. Cursor-key support
> (left/right/home/end) can come in Phase 1b; Backspace + overtype is enough
> for an MVP.

## 6. REPL dispatch (`repl.asm`)

Tokenize the first word, compare against `DEFSTR` command constants, jump.
Uppercasify the buffer once with `STRUPR` so matching is case-insensitive.

```asm
REPL_MAIN:
    CALL PRINT_PROMPT       ; "> "
    CALL GETLINE
    ; uppercasify line buffer in place
    MOV P0, [ZP_LINE_PTR]
    MOV R0, [ZP_LINE_LEN]
    STRUPR P0, R0           ; verify operand order during bring-up
    ; compare first token against each command constant
    MOV P0, [ZP_LINE_PTR]
    MOV P1, CMD_HELP        ; "HELP"
    CALL STRCMPEQ
    JZ CMD_HELP
    MOV P0, [ZP_LINE_PTR]
    MOV P1, CMD_DIR
    CALL STRCMPEQ
    JZ CMD_DIR
    ; ... LOAD RUN BANK PEEK POKE CALL LIST NEW CLS SAVE BYE
    JMP CMD_UNKNOWN
REPL_END:
    JMP REPL_MAIN

STRCMPEQ:                   ; Z flag set on success
    PUSH R0
    MOV R0, 0
    STRCMP R0, P0, P1       ; returns 0 in first arg if equal
    POP R0                  ; NOTE: POP restores but Z survives from POP?
    RET
```

> `POP` may clobber flags — move the comparison result to a register *before*
> the `POP`, or test immediately after `STRCMP` inside the helper and return a
> flag byte in SCRATCH. Log the working pattern.

## 7. Variable system (`vars.asm`)

Address math (see `memory-map.md` §2/§4):

- **Reals A-Z** → `addr = VARS_BASE + n*2`, `n = letter - 'A'` (0-25).
- **Strings Str0-Str9** → `base = VARS_BASE + 52 + n*256`; byte 0 = length,
  bytes 1..255 = data (null-padded). `VARS_END` = `VARS_BASE + 52 + 10*256`.

```asm
; Resolve a var-name letter in R0 ('A'-'Z') -> word address in P0.
VAR_ADDR:
    SUB R0, 'A'
    SHL R0, 1               ; n * 2
    MOV P0, [ZP_VARS_B]
    MOV R1, 0
    MOV R1, R0              ; promote to 16-bit offset
    ADD P0, R1
    RET

; "A = 5" path: store word at address (value stays in P-register)
CMD_ASSIGN:
    ; (parse name letter into R2, RHS value into P2 done by caller)
    CALL VAR_ADDR           ; uses R0 = letter
    MOV [P0], :P2           ; store value low byte
    MOV [P0+1], P2:         ; store value high byte
    RET
```

`LIST` walks the 26 reals printing `A=0x####` lines using `PRINTHEX`; `PRINT A`
reads the word and prints it (decimal output: port the hex routine and divide).
Keep `VARS_BASE`/`VARS_END` written into the zero page at boot (`INIT_VARS`).

## 8. NDF loader (`loader.asm`)

NDF volume layout on a bank page (window-relative addresses):

| Offset | Size | Content                          |
|--------|------|----------------------------------|
| 0x0000 | 4    | signature `"NDB1"`               |
| 0x0004 | 2    | directory offset (0x0010)        |
| 0x0006 | 2    | entry size (16)                  |
| 0x0008 | 2    | max entries (60)                 |
| 0x0010 | 960  | directory (60 × 16 B)            |
| 0x0400 | rest | file bytes                       |

Entry (16 B): `name(10) + type(1) + flags(1) + start(2) + len(2) + entry(2)`.
`type`: 0 = program, 1 = data, 2 = script. `flags` bit0 = runnable, bit1 = protected.

```asm
; LOAD "GAME": FIND -> BANK n -> MEMCPY window[start..start+len] -> PROG_BASE -> BANK 0
CMD_LOAD:
    CALL PARSE_STRING_ARG        ; name -> SCRATCH0 (buffer) + SCRATCH1 (len)
    CALL FIND_NDF_ENTRY          ; Z set if found; else PRINT "NOT FOUND" + RET
    MOV R8, [ZP_CUR_BANK]        ; current bank (0-15)
    MOV BANK, R8
    MOV P0, 0x8000
    ADD P0, R6                   ; + entry.start (2-byte field, R6)
    MOV P1, [ZP_PROG_B]
    MOV R0, R7                   ; entry.len (R7)
    MEMCPY P1, P0, R0
    MOV P0, [ZP_CUR_ENT]         ; stash entry point
    MOV [0x000E], :P0
    MOV BANK, 0
    RET

; RUN: call the entry point; the program returns via RET.
CMD_RUN:
    MOV P0, [ZP_CUR_ENT]
    CALL P0                      ; indirect CALL - verify assembler support
    CALL NEWLINE
    RET
```

> **If the assembler does not support indirect `CALL P0`**, use a trampoline
> stub: keep a 3-byte `JMP <target>` at a fixed address whose operand is
> patched with the entry point, then `CALL TRAMPOLINE`. (Or `PUSH` a return
> address and `JMP [P0]` directly.) Log the decision.

`SAVE` (Phase 1b) reverses `LOAD`: `BANK n`; `MEMCPY window[0x4000-len..] = RAM[PROG_BASE..]`; update the directory entry; `BANK 0`.

## 9. SYS mailbox (`sys.asm`)

Vector 4 = `SYS_DISPATCHER`. The mailbox in the zero page (0x0012-0x001B) is
the *only* channel between user programs and kernel services.

```asm
SYS_DISPATCHER:
    PUSHA                     ; protect all kernel registers
    MOV P0, [ZP_SYS_NUM]      ; opcode
    ; branch table: SYS 1=GETKEY 2=PUTCHAR 3=PEEK 4=POKE 5=BANKGET 6=BANKPUT ...
    ; each implementation reads SYS_ARG0..2 and writes SYS_RET
    POPA
    IRET
```

Rules for every SYS entrypoint:

- Do all work between `PUSHA`/`POPA`; return status in `SYS_RET` (0 = ok).
- Never `HLT` inside the dispatcher.
- Keep handlers short — interrupts are off (I cleared by `INT`) while running,
  and peripheral events just set flag bytes (they do not nest).

## 10. Contracts (register/flag discipline)

- Subroutines may clobber R0-R9/P0-P3 unless the caller saves. Use the FP frame
  pattern from `docs/CPU Specification.md` when nesting calls.
- `CMP`/`SUB` set C/Z/S/O — do not rely on flags across a `CALL`; re-compare.
- Interrupt handlers end with `IRET` (never `RET`).
- Text cursor (`VID_CURSOR`), line buffer, and SYS fields are persistent state;
  everything else in the zero page is scratch.
- The REPL must treat `BYE`/`HLT` as "shut down gracefully" (frame the tail of
  the REPL with `HLT`), and user programs must *never* issue `HLT` — the loader
  enforces this by convention (no protection exists).

## 11. Known pitfalls (verified in emulator source)

- `SREAD` reads the **composite** screen, not the active layer — do not use it
  for layer readback (see `implementation-phase2.md` §3.2).
- `ADD VX, -8` is 8-bit wrapping — use `SUB VX, 8`.
- `HLT` halts the whole emulator. Only the REPL's `BYE` path may use it.
- Bank 0 window = base RAM pass-through; only banks 1-15 are "disks".
- `MEMCPY` argument order is `(dest, src, len)` — verify with a 1-instruction
  probe before the loader depends on it.
- `INT` requires the I flag: `STI` before any software interrupt.

## 12. Acceptance tests (harness in build-and-test.md)

| # | Test | Assert |
|---|------|--------|
| 1 | boot `--cycles 20000` | PC reaches `REPL_MAIN`; banner pixels on layer 0 |
| 2 | `HELP <Enter>` | help text pixels; PC still in REPL |
| 3 | `A = 5 <Enter>` `PRINT A <Enter>` | word at `VARS_BASE` == 5; decimal text on screen |
| 4 | `PEEK 0x0000 <Enter>` | `4E 44` printed (signature "ND") |
| 5 | seed bank 3 with sample; `BANK 3 <Enter>` `DIR <Enter>` `LOAD "SAMPLE" <Enter>` `RUN <Enter>` | sample sets marker byte at 0x00E0; PC returns to REPL |

---
*Up: [`design.md`](design.md) / [`memory-map.md`](memory-map.md).
Next: [`implementation-phase2.md`](implementation-phase2.md).
Log findings in [`notes/start.md`](../notes/start.md).*