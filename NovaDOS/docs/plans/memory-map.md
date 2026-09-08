# NovaDOS Canonical Memory Map

**Normative.** Defines every fixed address NovaDOS uses. Kernel assembly must
reference these via `EQU` constants (see §4), never raw literal addresses.

## 1. Full address space

| From  | To     | Size   | Owner / purpose                                  |
|-------|--------|--------|--------------------------------------------------|
| 0x0000| 0x00FF | 256 B  | Zero page: OS globals, SYS mailbox (hot region)   |
| 0x0100| 0x011F | 32 B   | Interrupt vectors (8 × 4 B)                       |
| 0x0120| 0x0FFF | 3,808 B| Kernel code — **entry point 0x0120**              |
| 0x1000| 0x17FF | 2 KB   | Kernel extent (overflow zone)                     |
| 0x1800| 0x7FFF | 26 KB  | User program area (else starts 0x1000)            |
| 0x8000| 0xBFFF | 16 KB  | **Bank window** — `BANK` 0-15 selects page        |
| 0xC000| 0xCFFF | 4 KB   | Asset store: sprite bitmaps, sound sample data    |
| 0xD000| 0xE7FF | 6 KB   | Variable heap (VARS_BASE)                         |
| 0xE800| 0xEFFF | 2 KB   | Kernel scratch: line buffer, syscall mirrors      |
| 0xF000| 0xF0FF | 256 B  | Sprite Control Blocks (hardware)                  |
| 0xF100| 0xFBFF | 1,280 B| OS settings + bank FAT directory cache            |
| 0xFC00| 0xFFFF | 1 KB   | Hardware stack (grows down from 0xFFFF)           |

## 2. Zero page (0x0000-0x00FF) — OS globals

| Addr  | Sz | Name         | Notes                                             |
|-------|----|--------------|---------------------------------------------------|
| 0x0000| 4  | OS_SIGNATURE | `"ND\x01\x00"` = NovaDOS v1.0 (written at boot)   |
| 0x0008| 2  | VARS_BASE    | variable heap start (default 0xD000)              |
| 0x000A| 2  | VARS_END     | variable heap end-exclusive (default 0xE800)      |
| 0x000C| 2  | PROG_BASE    | user program load address (0x1000 / 0x1800)       |
| 0x000E| 2  | CUR_ENTRY    | entry point of the loaded program                 |
| 0x0010| 1  | CUR_BANK     | active bank 0-15                                  |
| 0x0012| 2  | SYS_NUM      | SYS-call opcode (word)                            |
| 0x0014| 2  | SYS_RET      | SYS result code (0 = ok)                          |
| 0x0016| 2  | SYS_ARG0     | SYS argument word 0                               |
| 0x0018| 2  | SYS_ARG1     | SYS argument word 1                               |
| 0x001A| 2  | SYS_ARG2     | SYS argument word 2                               |
| 0x001C| 2  | DEV_ACTIVE   | currently open device id                          |
| 0x0020| 2  | CLI_LINE_PTR | line buffer address (default 0xE800)              |
| 0x0022| 1  | LINE_LEN     | current command-line length                       |
| 0x0023| 1  | CURSOR       | edit cursor position within line                  |
| 0x0024| 2  | VID_CURSOR   | text cursor `(VX << 8) | VY`                      |
| 0x0026| 1  | CONS_LAYER   | console text layer (0)                            |
| 0x0027| 1  | CONS_COLOR   | console text color (0x0F = white)                 |
| 0x0028| 4  | TIMER_MIRROR | TT/TM/TC/TS shadow (updated by vector 0)          |
| 0x002C| 4  | KBD_MIRROR   | key status / data / count / control shadows       |
| 0x0030-0x00AF | 128 | SCRATCH | kernel scratch (hex/decimal I/O, parse temps) |
| 0x00B0-0x00FF | 80   | RESERVED |                                          |

## 3. Interrupt vector table (0x0100-0x011F)

Per-vector slot v (base `0x0100 + v*4`):

| Offset | Size | Meaning                                          |
|--------|------|--------------------------------------------------|
| +0     | word | handler address — **the only part the CPU reads** |
| +2     | byte | flags: bit0 installed, bit1 kernel-routed, bit7 debug |
| +3     | byte | source id (0 timer, 1 serial, 2 keyboard, 3 mouse, 4 sys, 5-6 user, 7 debug) |

| V | Addr  | Default handler      | Notes                                         |
|---|-------|----------------------|-----------------------------------------------|
| 0 | 0x0100| `V0_TIMER`           | set TICK_FLAG (0x0030), `IRET`                |
| 1 | 0x0104| `V1_SERIAL`          | set UART_FLAG (0x0031), `IRET`                |
| 2 | 0x0108| `V2_KEYBOARD`        | set KEY_FLAG (0x0032), `IRET`                 |
| 3 | 0x010C| `V3_MOUSE`           | set MOUSE_FLAG (0x0033), `IRET`               |
| 4 | 0x0110| `SYS_DISPATCHER`     | mailbox dispatch, `IRET` (kernel)             |
| 5 | 0x0114| `USER2_DEFAULT`      | `IRET` (user override allowed)                |
| 6 | 0x0118| `USER3_DEFAULT`      | `IRET`                                        |
| 7 | 0x011C| `DBG_DEFAULT`        | ignore + `IRET`                               |

## 4. Kernel `EQU` constants (paste into `kernel.asm`)

```asm
; ---- Regions ----
K_KERNEL    EQU 0x0120     ; kernel entry
K_EXTENT    EQU 0x1000     ; overflow zone start
K_PROG      EQU 0x1000     ; default program base (0x1800 if extent used)
K_VARS      EQU 0xD000     ; variable heap base
K_VARS_END  EQU 0xE800     ; variable heap end
K_LINEBUF   EQU 0xE800     ; command line buffer
K_SCRATCH   EQU 0x0030     ; zero-page scratch byte
K_DEV_TBL   EQU 0x0F00     ; device table (16 x 8 B), inside kernel data
; ---- Zero page ----
ZP_SIG      EQU 0x0000
ZP_VARS_B   EQU 0x0008
ZP_VARS_E   EQU 0x000A
ZP_PROG_B   EQU 0x000C
ZP_CUR_ENT  EQU 0x000E
ZP_CUR_BANK EQU 0x0010
ZP_SYS_NUM  EQU 0x0012
ZP_SYS_RET  EQU 0x0014
ZP_SYS_ARG0 EQU 0x0016
ZP_SYS_ARG1 EQU 0x0018
ZP_SYS_ARG2 EQU 0x001A
ZP_LINE_PTR EQU 0x0020
ZP_LINE_LEN EQU 0x0022
ZP_CURSOR   EQU 0x0023
ZP_VID_CUR  EQU 0x0024
ZP_CONS_LAY EQU 0x0026
ZP_CONS_CLR EQU 0x0027
; ---- IVT ----
IVT_BASE    EQU 0x0100
V0_TIMER    EQU 0x0100
V1_SERIAL   EQU 0x0104
V2_KEYBOARD EQU 0x0108
V3_MOUSE    EQU 0x010C
V4_SYS      EQU 0x0110
V5_USER2    EQU 0x0114
V6_USER3    EQU 0x0118
V7_DEBUG    EQU 0x011C
; ---- Special register codes (informational) ----
REG_BANK    EQU 0xC2
REG_C0      EQU 0xC3
REG_C1      EQU 0xC4
REG_MX      EQU 0xC5
REG_MY      EQU 0xC6
REG_MB      EQU 0xC7
REG_VC      EQU 0xC8
REG_SA      EQU 0xDD
REG_SF      EQU 0xDE
REG_SV      EQU 0xDF
REG_SW      EQU 0xE0
REG_VM      EQU 0xE1
REG_VL      EQU 0xE2
REG_TT      EQU 0xE3
REG_TM      EQU 0xE4
REG_TC      EQU 0xE5
REG_TS      EQU 0xE6
REG_VX      EQU 0xFD
REG_VY      EQU 0xFE
; ---- Constants ----
K_ENTER     EQU 0x93      ; Enter scan code
K_BACKSP    EQU 0x92      ; Backspace scan code
K_DEL       EQU 0x91      ; Delete
K_LEFT      EQU 0x80
K_RIGHT     EQU 0x81
K_HOME      EQU 0x98
K_END       EQU 0x99
K_ESC       EQU 0x9A
K_SPACE     EQU 0x9B
C_BLACK     EQU 0x00
C_WHITE     EQU 0x0F
CONS_COLS   EQU 32        ; 256 / 8 font width
CONS_ROWS   EQU 32        ; 256 / 8 font height
```

> Register operands use mnemonics directly in assembly (`MOV BANK, 3`). Verify the
> assembler accepts `BANK` early; fall back to raw `0xC2` if not (log in notes).

## 5. Bank & stack discipline

- Hardware stack (SP = P8, starts 0xFFFF) grows **downward**. `PUSH`/`CALL`
  below 0xFC00 corrupts the FAT/settings area — guard recursion depth.
- Banks 1-15 are private 16 KB pages — treat them as **disk**, not RAM.
  Bank 0 aliases base memory: never "format"/CLS it casually.
- The window is `0x8000-0xBFFF` while `BANK > 0`. Instruction-cache entries in the
  window are invalidated on bank switch (emulator handles it); still, **never
  execute code from the window**.

---
*Up: [`design.md`](design.md). Down: [`implementation-phase1.md`](implementation-phase1.md).*