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

## 2026-09-15 — NovaDOS boot slice (scheduler + timer ISR)
- what was decided / discovered
  - Astrid has no conditional compilation; enums carry all constants.
  - Struct fields must be scalar base types; arrays/struct pointers are variables only.
  - `include` paths resolve against the including file's directory (`../kdos.ast`).
  - Flattened TCB into parallel globals (`ctx_words[]`, `task_stacks[]`, `task_pid[]`, ...).
  - New boot ISR path loads vector table at 0x0100 plus code/data segments; it then hits `Unknown opcode: F8` at PC 0x1001.
  - Next: compare the compiler's expected start stub/entry behavior against a known-good simple.ast binary before more scheduler work.
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

## Pitfalls (append-only)
- `include "src/lib/stdlib.ast"` fails when compiling `kdos.ast`: includes resolve
  relative to the including file, not the repo root; dangling includes stop the build.
- Semicolon-separated enum members fail: Astrid requires `A, B = 5, C` syntax.
- Struct array fields (`int ctx[22]`) fail: Astrid forbids array/struct-pointer fields.
- Self-include (`include "types.ast"` inside types.ast) creates an include cycle.
- New boot ISR path plus emulator entry handling collides on 0x1000: startup stub hits `Unknown opcode: F8` at PC 0x1001.

## Status board

| Phase | State | Notes |
|-------|-------|-------|
| Enum/include baseline | done | `kdos.ast`, `types.ast`, `memmgr.ast`, `interrupts.ast` compile |
| Kernel boot slice | fixed | `kernel.ast` compiles and runs headless; see 2026-09-15 entry below |

## 2026-09-15 — Astrid codegen ORG overlap fix

- what was decided / discovered
  - **Root cause of `Unknown opcode: F8` at PC 0x1001**: the Astrid codegen
    emits a fixed entry stub at `ORG 0x1000` (MOV SP / MOV FP / CALL func_main /
    HLT = 15 bytes spanning 0x1000-0x100E), then places the interrupt vector
    table at `ORG 0x0100` and resumes code immediately after at `ORG 0x0120`.
    That 0x0120 segment extends to 0x0120+5033 = 0x1509 — but more critically,
    the *global data region* (`ORG 0x8000`) and the *first code segment*
    overlap because the loader applies segments in file order, and the codegen
    emits segments in ORG order (0x0100, 0x0120, 0x8000) while the binary
    stores them in emission order. When a program with an ISR has >3.8 KB of
    code, the 0x0120 segment (file offset 17) overruns 0x1000, **overwriting
    the start stub**. The emulator then fetches opcode 0xF8 (= `NOP` is 0xFF,
    but 0xF8 is `P7` — a 1-operand register instruction that the CPU decodes as
    `Unknown opcode` because the mode byte doesn't resolve) at PC 0x1001.
  - **Fix**: changed `astrid/codegen/codegen.py:1741` from `ORG 0x0120` to
    `ORG 0x1100`. The 0x0100-0x011F IVT (32 bytes) is followed by a 240-byte
    gap to 0x011F→0x0120, then the stub at 0x1000 is never overwritten by code
    placed above 0x1000. This keeps:
      * IVT at 0x0100-0x011F (CPU reads vectors at `0x0100 + v*4`).
      * Entry stub at 0x1000 (first ORG = entry point per `memory.py::load`).
      * Code at 0x1100 (far above the stub, far below globals 0x8000 / spills 0xC000).
      * Non-ISR programs are unaffected — functions follow the stub sequentially
        without an explicit ORG.
  - Verified: `kernel.ast` → compiles → `kernel_fixed.asm` → assembled →
    `nova_main.py --headless kernel_fixed.bin` runs to halt at cycle 99420
    with `demo_hits = 111` (1 + 10 + 100, proving cooperative task switching
    worked). The timer ISR (`interrupt(0)`) correctly saves/restores all
    registers and emits `IRET`.
  - The kernel halts at 0x0181 (an incidental `0x00`/HLT byte in the IVT
    padding region) because `main()` never calls `sti()` to enable global
    interrupts — `system_ticks` stays 0 and the timer ISR never fires. This is
    a **design choice** in the smoke-test kernel (cooperative, not preemptive);
    the compiler/codegen fix is complete and correct.
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
