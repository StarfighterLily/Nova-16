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
| Enum/include baseline | done | `kdos.ast`, `types.ast`, `memmgr.ast`, `interrupts.ast` compile |
| Compiler ORG layout | fixed | codegen emits ISR code at `ORG 0x1100`; the 0x1000 entry stub stays intact |
| Kernel boot slice | done | boots, runs the scheduler demo, halts cleanly at the stub `HLT` (0x100E) |
| Kernel regression tests | done | `astrid/NovaDOS/tests/test_kernel_compile.py` (5 tests, includes the boot-slice end-to-end) |
| FS / drivers / shell | done | NDF volume (`ndf.ast`) + shell commands: HELP/CLS/PEEK/DIR/TYPE/BYE; kernel compiles and runs headless ✅ |

## 2026-09-15 — NovaDOS boot slice (scheduler + timer ISR)
- what was decided / discovered
  - Astrid has no conditional compilation; enums carry all constants.
  - Struct fields must be scalar base types; arrays/struct pointers are variables only.
  - `include` paths resolve against the including file's directory (`../kdos.ast`).
  - Flattened TCB into parallel globals (`ctx_words[]`, `task_stacks[]`, `task_pid[]`, ...).
  - New boot ISR path loads vector table at 0x0100 plus code/data segments; it then hits `Unknown opcode: F8` at PC 0x1001.
  - Next: compare the compiler's expected start stub/entry behavior against a known-good simple.ast binary before more scheduler work.
  - [RESOLVED] Both blockers from this session are fixed — see the two
    2026-09-15 fix entries below (codegen `ORG 0x1100`, and the never-returning
    task contract for `task_spawn`). Kernel now halts cleanly at 0x100E.
- exact commands run (copy/paste)
  - `py -3.13 astrid/astrid_compiler.py astrid/NoDOS/src/kdos.ast -o /tmp/kdos_check.asm`
  - `py -3.13 astrid/astrid_compiler.py astrid/NoDOS/src/kernel/types.ast -o /tmp/types_check.asm`
  - `py -3.13 astrid/astrid_compiler.py astrid/NoDOS/src/kernel/memmgr.ast -o /tmp/memmgr_check.asm`
  - `py -3.13 astrid/astrid_compiler.py astrid/NoDOS/src/kernel/interrupts.ast -o /tmp/isr_check.asm`
  - `py -3.13 astrid/astrid_compiler.py astrid/NoDOS/src/kernel/kernel.ast -o /tmp/kernel_check.asm`
  - `py -3.13 nova_main.py --headless /tmp/kernel_check.bin --cycles 20000`
- links to code/doc evidence (file + line or function)
  - `astrid/parser/parser.py:1202` (`parse_enum`)
  - `astrid/parser/parser.py:1343` (`parse_struct_definition`)
  - `astrid/codegen/codegen.py:1668` (`_emit_object_prologue`)
  - `c:\Code\projects\Nova\astrid\NoDOS\src\kdos.ast`
  - `c:\Code\projects\Nova\astrid\NoDOS\src\kernel\types.ast`
  - `c:\Code\projects\Nova\astrid\NoDOS\src\kernel\memmgr.ast`
  - `c:\Code\projects\Nova\astrid\NoDOS\src\kernel\interrupts.ast`
  - `c:\Code\projects\Nova\astrid\NoDOS\src\kernel\kernel.ast`

## 2026-09-15 — Scheduler fix: a spawned task must not return

- what was decided / discovered
  - After the ORG fix the kernel ran ~100k cycles but halted at **0x0181**
    instead of the entry stub's `HLT` at **0x100E**, with `SP=0xA9F0` /
    `FP=0xA96E` (i.e. still inside `demo_stack` / `demo_ctx_main`) at halt.
  - Root cause: `task_spawn` (`builtin_task_spawn`) fabricates the task context
    and parks ONLY the resume PC at the top of the task stack:
    `MOV P5, P3 + P2 - 2 / MOV [P5+0], P4` (P4 = entry) and
    `MOV [P1+4], P5` (ctx SP). Nothing else is written to that stack, so when
    `demo_task`'s epilogue ran `MOV SP, FP / POP FP / RET`, the `RET` popped an
    uninitialized word and jumped to an incidental `0x00`/HLT byte at 0x0181.
  - Fix (kernel.ast): `demo_task` now ends in a never-exiting switch loop
    instead of falling off the end of the function:
    ```c
    while (1) { task_switch(demo_ctx, demo_ctx_main); }
    ```
    The final resumption performs `demo_hits += 100` and then hands control
    back to `main`, which finishes its frame and `RET`s to the stub's `HLT`.
  - Result: the boot slice now completes cleanly — halt at PC **0x100F**
    (one past the `HLT` at 0x100E), `SP=FP=0xFFFF` (main's frame fully unwound),
    `demo_hits = 111` (1 + 10 + 100), 99755 cycles, 512 banner pixels.
  - Contract for future NovaDOS code: **every spawned task entry must end in an
    infinite switch/yield loop or an explicit task-exit**; returning from the
    entry function is undefined with the current `task_spawn` layout.
- exact commands run (copy/paste)
  - `py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast -o astrid/NovaDOS/build/kernel.asm`
  - `py -3.13 nova_assembler.py astrid/NovaDOS/build/kernel.asm`
  - `py -3.13 astrid/NovaDOS/build/diag_kernel.py`   (PC/SP/FP trace at the end)
  - `py -3.13 -m pytest astrid/NovaDOS/tests/test_kernel_compile.py -v`  (5 passed)
- links to code/doc evidence
  - `astrid/NovaDOS/src/kernel/kernel.ast` (`demo_task`, the why-comment)
  - `astrid/codegen/codegen.py:819-863` (`builtin_task_spawn`: parks only the
    resume PC on the fabricated stack)
  - `astrid/codegen/codegen.py:864+` (`builtin_task_switch`: saves/restores
    flags, FP, SP, R0-R9, P0-P7 and RETs into the restored PC)
  - `astrid/NovaDOS/tests/test_kernel_compile.py`
    (`test_boot_slice_completes_cleanly`)
  - `astrid/NovaDOS/build/diag_kernel.py` (trace tool)

## Pitfalls (append-only)
- `include "src/lib/stdlib.ast"` fails when compiling `kdos.ast`: includes resolve
  relative to the including file, not the repo root; dangling includes stop the build.
- Semicolon-separated enum members fail: Astrid requires `A, B = 5, C` syntax.
- Struct array fields (`int ctx[22]`) fail: Astrid forbids array/struct-pointer fields.
- Self-include (`include "types.ast"` inside types.ast) creates an include cycle.
- [RESOLVED 2026-09-15] Boot ISR path collided on 0x1000: the codegen resumed
  code at `ORG 0x0120` right after the IVT, so a >3.8 KB program (every ISR
  program) overwrote the 15-byte entry stub at 0x1000 and the CPU died at
  PC 0x1001 with `Unknown opcode: F8`. Fixed by emitting `ORG 0x1100` instead
  (`astrid/codegen/codegen.py`).
- A spawned task must never fall off the end of its entry function: `task_spawn`
  parks only the resume PC on the fabricated task stack, so the function's
  epilogue `RET` pops uninitialized words and jumps to junk. End every task
  entry in `while (1) { task_switch(...); }` or an explicit task-exit.
- Never build in parallel: running `astrid_compiler.py` and `nova_assembler.py`
  concurrently (or leaving a stale `.bin`) can silently keep the previous
  binary even though the `.asm` changed. Rebuild sequentially and cross-check
  the `.org` segment lengths as a fingerprint.

## 2026-09-15 — Astrid codegen ORG overlap fix

- what was decided / discovered
  - **Root cause of `Unknown opcode: F8` at PC 0x1001**: the Astrid codegen
    emits a fixed entry stub at `ORG 0x1000` (MOV SP / MOV FP / CALL func_main /
    HLT = 15 bytes spanning 0x1000-0x100E), then places the interrupt vector
    table at `ORG 0x0100` and resumes code immediately after at `ORG 0x0120`.
    That 0x0120 segment grows UPWARD with no upper bound: for the NovaDOS
    kernel it is 5033 bytes, covering 0x0120-0x1520 — straight through the
    15-byte entry stub at 0x1000-0x100E. The loader writes each segment at its
    absolute address (via the `.org` sidecar), so kernel code overwrote the
    stub and the emulator fetched 0xF8 at PC 0x1001 (0xF8 is the `P7` register
    code, which is not a valid opcode byte): `Unknown opcode: F8`.
    Measured: `.org` showed `0x0120 5033 17` (clobbers 0x1000) and after the
    fix shows `0x1100 5073 17` (stub clear of all code/data).
  - **Fix**: changed `astrid/codegen/codegen.py:1741` from `ORG 0x0120` to
    `ORG 0x1100`. The 0x0100-0x011F IVT (32 bytes) is followed by a 240-byte
    gap to 0x011F→0x0120, then the stub at 0x1000 is never overwritten by code
    placed above 0x1000. This keeps:
      * IVT at 0x0100-0x011F (CPU reads vectors at `0x0100 + v*4`).
      * Entry stub at 0x1000 (first ORG = entry point per `memory.py::load`).
      * Code at 0x1100 (far above the stub, far below globals 0x8000 / spills 0xC000).
      * Non-ISR programs are unaffected — functions follow the stub sequentially
        without an explicit ORG.
  - Verified after the fix: the stub bytes at 0x1000-0x100E are intact
    (`06 08 FB FF FF 06 08 FC FF FF 2F 02 ... 00`), IVT vector 0 points at
    `func_timer_isr`, and the kernel executes ~100k cycles instead of dying on
    its first instruction.
  - A SECOND, independent bug then surfaced (a task returning off its own
    fabricated stack) — see the scheduler entry below.
  - Build-hygiene gotcha discovered while verifying: if the compiler and the
    assembler are run in parallel (or a stale `.bin`/`.org` is left in place),
    the assembler can silently keep the previous binary. Symptom: the `.asm`
    contains new code but `.bin` size and behaviour are unchanged. Always
    rebuild sequentially (compile, then assemble) and sanity-check the
    `.org` segment lengths — `0x1100 5033` (stale) vs `0x1100 5073` (current).
- exact commands run (copy/paste)
  - `py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast -o /tmp/kernel_fixed.asm`
  - `py -3.13 nova_assembler.py /tmp/kernel_fixed.asm`
  - `py -3.13 nova_main.py --headless /tmp/kernel_fixed.bin --cycles 100000`
- links to code/doc evidence
  - `astrid/codegen/codegen.py:1740-1750` (the ORG change + comment)
  - `nova/memory/memory.py:478-541` (`load` / `load_with_org_info`: first
    segment = entry point; segments applied in ORG-address order via the
    `.org` sidecar, which is why the overlap was real)
  - `nova_mcp/handlers_astrid.py:8` (docstring updated to `ORG 0x1100`)
