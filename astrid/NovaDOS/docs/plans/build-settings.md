# NovaDOS (Astrid) Build Settings

Updated: 2026-10-15 (first version 2026-09-21)
Scope: `astrid/NovaDOS/src/` (the Astrid kernel); tests in
`astrid/NovaDOS/tests/`.

## 1. Build settings

Each is a preprocessor macro with a default in the source; override with
`-D NAME=VALUE`. Out-of-range values stop the build with `#error` before any
output is written (tested).

| Macro | Default | Valid | Controls | Defined in |
|---|---|---|---|---|
| `NOVADOS_ENABLE_NDF` | `1` | 0/1 | NDF disk layer, boot volume, DIR/TYPE/BANK/FORMAT/LOAD/SAVE | `kernel.ast` |
| `NOVADOS_ENABLE_TIMER` | `1` | 0/1 | vector-0 heartbeat ISR and its arming in `main()` | `kernel.ast`, `interrupts.ast` |
| `NOVADOS_ENABLE_SYSCALLS` | `1` | 0/1 | INT 4 SYS mailbox for loaded programs | `kernel.ast`, `syscall.ast` |
| `NOVADOS_POLL_LIMIT` | `200` | 1-32767 | keyboard poll iterations before the shell stops (headless runs must end) | `kernel.ast` |
| `NOVADOS_ENABLE_FULL_SCHEDULER` | `0` | 0/1 | 16-slot `task_create`/`task_yield`/`task_sleep` with per-task stacks | `memmgr.ast` |
| `NOVADOS_MAX_TASKS` | `16` | 1-16 | size of the task tables | `memmgr.ast` |
| `NOVADOS_TASK_STACK_WORDS` | `64` | 32-256 | stack per task in the full scheduler | `memmgr.ast` |

The full scheduler's tables must end below `KHEAP_START` (`0x5000`);
`test_full_scheduler_build_fits` checks the default sizes.

## 2. Commands

```powershell
# Default build (writes build/kernel.asm/.bin/.org/.sym)
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast -o astrid/NovaDOS/build/kernel.asm --memory-layout bank-safe
py -3.13 nova_assembler.py astrid/NovaDOS/build/kernel.asm

# Diskless build
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast -o astrid/NovaDOS/build/diskless.asm --memory-layout bank-safe -DNOVADOS_ENABLE_NDF=0

# Run headless / run the test suite
py -3.13 nova_main.py --headless astrid/NovaDOS/build/kernel.bin --cycles 200000
py -3.13 -m pytest astrid/NovaDOS/tests tests/astrid/test_ndf_probe.py -q
```

Build sequentially: compile, then assemble. A stale `.bin` next to a new
`.asm` is easy to miss; the `.org` segment lengths are a quick fingerprint.

## 3. Measured sizes (bank-safe)

| Build | Code (limit 12,544) | Globals | Read-only data |
|---|---|---|---|
| 2026-09-21 kernel, compiler of that day | 11,601 | 392 | — |
| same source, compiler of 2026-10-15 before the fixes | **16,413 (overflow)** | 392 | — |
| same source, fixed compiler | 8,510 | 392 | — |
| 2026-10-15 kernel (20 commands, LOAD/RUN, SYS calls) | 11,947 | 495 | 755 |
| ... diskless | 7,754 | 452 | 327 |
| ... full scheduler | 11,943 | 3,279 | 755 |

Read-only data is the command table, hex digits, the HI program and the
string literals in `0x0120-0x0EFF`, outside the code budget.

## 4. History

* 2026-09-21: build settings introduced; dead RAM (8 KB task stacks, shell
  stack, 22-word context windows) moved behind the full-scheduler gate;
  naked timer ISR; NDF geometry as enums. Binary 22,110 -> 11,214 bytes.
* 2026-10-15: compiler inliner regression fixed, kernel reworked onto newer
  Astrid features, SYS calls and program loading added. See
  `docs/notes/start.md` (2026-10-15 entries).
