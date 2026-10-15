# NovaDOS (Astrid) — Programs, SYS Calls and Disks

Status: implemented 2026-10-15. Normative for the Astrid kernel in
`astrid/NovaDOS/src/`. Tests: `astrid/NovaDOS/tests/test_programs.py`.

## 1. Memory map

The kernel is built with the Astrid `bank-safe` layout. The compiler owns
code, globals, string scratch, spills and the stack; NovaDOS owns the rest.
The values live in `src/kdos.ast` (`enum Memory`).

| Range | Owner | Notes |
|---|---|---|
| `0x0000-0x0003` | kernel | OS signature `"ND" 01 00`, an `@`-placed const |
| `0x0012-0x001B` | SYS mailbox | five words, see §3 |
| `0x0100-0x011F` | IVT | vector 0 timer, vector 4 SYS |
| `0x0120-0x0EFF` | read-only data | const tables and string literals (compiler) |
| `0x1000-0x100E` | entry stub | `MOV SP/FP`, `CALL main`, `HLT` |
| `0x1100-0x41FF` | kernel code | must end below the globals (tested) |
| `0x4200-0x4FFF` | kernel globals | room for the full scheduler's task tables |
| `0x5000-0x57FF` | kmalloc heap | 2 KB bump allocator |
| `0x5800-0x7EFF` | program area | `LOAD` target, `RUN` entry point (9.75 KB) |
| `0x7F00-0x7FFF` | static locals | compiler |
| `0x8000-0xBFFF` | bank window | disks: banks 1-15 (bank 0 is base RAM) |
| `0xC000-0xEFFF` | compiler | string scratch, spill windows |
| `0xF000-0xF0FF` | SCB | hardware sprites |
| `0xF100-0xFFFF` | stack | grows down from `0xFFFF` |

## 2. Program contract

A NovaDOS program is raw machine code:

* assembled for `ORG 0x5800` (`PROG_BASE`); absolute addresses are fine
  because `LOAD` always copies to that address;
* entered with `CALL 0x5800` (`RUN`, or `CALL addr` for any address);
* returns with `RET`, with SP and FP as it found them. `HLT` would stop the
  whole machine;
* may use every general register (the kernel keeps nothing in registers
  across the call);
* reaches the kernel only through the SYS mailbox (§3), never by calling
  kernel addresses, which move whenever the kernel is rebuilt.

The sample program is `src/progs/hi.asm`. Its bytes are embedded in
`kernel.ast` (`hi_prog`) and written to the boot volume as `HI` at boot. A
test reassembles `hi.asm` and fails if the two disagree.

Make a program file from memory with `SAVE name addr len`, or `LOAD` one,
change it with `POKE`, and `SAVE name` it back.

## 3. SYS mailbox (INT 4)

| Address | Name | Direction |
|---|---|---|
| `0x0012` | `SYS_NUM` | operation, written by the program |
| `0x0014` | `SYS_RET` | result, written by the kernel |
| `0x0016` | `SYS_ARG0` | argument |
| `0x0018` | `SYS_ARG1` | argument |
| `0x001A` | `SYS_ARG2` | argument |

Store the operation and arguments, execute `INT 4`, read `SYS_RET`. The
handler (`src/kernel/syscall.ast`) saves and restores every register, so
registers survive a call. `INT` is ignored while the I flag is clear; the
kernel sets it at boot whenever syscalls are compiled in.

| `SYS_NUM` | Operation | Arguments | `SYS_RET` |
|---|---|---|---|
| 9 `SYS_WRITE` | print a NUL-terminated string at the cursor | ARG0 = address | 0 |
| 11 `SYS_GETC` | next key without waiting | | key code, or 0 |
| 12 `SYS_PUTC` | print one character (10/13 = newline, 8 = backspace) | ARG0 = code | 0 |
| 24 `SYS_TIME` | timer ticks since boot (about 3200 cycles each) | | ticks |
| anything else | | | `0xFFFF` (`SYS_EBADOP`) |

The other numbers in `enum SysCall` are reserved from the parent design.

Example (`hi.asm`):

```asm
    MOV P0, msg
    MOV [0x0016], P0      ; SYS_ARG0 = address of the text
    MOV P0, 9             ; SYS_WRITE
    MOV [0x0012], P0      ; SYS_NUM
    INT 4
    RET
msg:
    DEFSTR "HI FROM DISK"
```

## 4. NDF volumes

Each bank page 1-15 can hold one volume, seen through the window at
`0x8000`. Offsets below are window offsets; words are big-endian.

| Offset | Size | Field |
|---|---|---|
| `0x0000` | 4 | magic `"NDF1"` |
| `0x0004` | 2 | entries in use (0-16) |
| `0x0006` | 2 | next free data offset |
| `0x0010` | 256 | directory: 16 entries of 16 bytes |
| `0x0400` | to `0x3FFF` | file data, packed in creation order |

Directory entry (`struct NdfEntry` in `src/fs/ndf.ast`):

| Offset | Size | Field |
|---|---|---|
| +0 | 8 | name, NUL-padded, upper case |
| +8 | 1 | type: 0 text, 1 program |
| +9 | 1 | flags (0) |
| +10 | 2 | size in bytes |
| +12 | 2 | data offset |
| +14 | 2 | reserved |

Files cannot be deleted or grown yet; `FORMAT` empties a volume. RAM banks
start empty, so the kernel builds the boot volume (bank 1: `BOOT`, `HI`) on
every boot.
