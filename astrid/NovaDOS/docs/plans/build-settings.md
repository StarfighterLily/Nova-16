# NovaDOS (Astrid) Build Settings — Preprocessor Report

Date: 2026-09-21
Status: implemented and validated
Scope: `astrid/NovaDOS/src/kernel/` (the Astrid kernel), tests in
`astrid/NovaDOS/tests/test_kernel_compile.py`

## 1. Analysis: what the new Astrid features offer this codebase

Cross-check of `astrid/docs/astrid.md` against the boot-slice kernel:

| Feature | Verdict | Reason |
|---|---|---|
| Optional subsystems via `#if` (NDF, timer arm, full scheduler) | **Implemented** | Excluded source never reaches the parser/codegen. |
| Build-time shell polling limit | **Implemented** | `NOVADOS_POLL_LIMIT` replaces the magic 200. |
| Drop dead globals (shell_stack, root_dir, full TCB) | **Implemented** | ~10 KB of DS reservations with zero readers. |
| `NOVADOS_ENABLE_FULL_SCHEDULER` gate | **Implemented** | task_create/yield/sleep + 8 KB stacks opt-in only. |
| Naked timer ISR + `{varname}` asm | **Implemented** | Drops 19-register save/restore every tick. |
| NDF geometry as enums (not globals) | **Implemented** | Compile-time immediates; no DS, no memory loads. |
| Coalesce NDF bank brackets | **Implemented** | format/add/mounted/read16/write16 hold BANK open. |
| `impl` methods on kernel structs | Deferred | No hot paths benefit yet; zero byte win alone. |
| `task_spawn`/`task_switch` for multi-task shell | Already used | Demo path; full create/yield stays gated. |
| Absolute `@ addr` placement | Deferred | No MMIO views needed in the boot slice. |
| Replacing enums with macros | Rejected | Enums already fold to immediates. |

## 2. Build settings (defined in `kernel.ast` / `memmgr.ast`, overridable via `-D`)

| Macro | Default | Valid range | Controls |
|---|---|---|---|
| `NOVADOS_ENABLE_NDF` | `1` | `0` or `1` | `ndf.ast` include, boot volume, DIR/TYPE |
| `NOVADOS_POLL_LIMIT` | `200` | `1..32767` | shell keyboard-poll iterations |
| `NOVADOS_ENABLE_TIMER` | `1` | `0` or `1` | arm sequence in `main()` (ISR stays linked) |
| `NOVADOS_ENABLE_FULL_SCHEDULER` | `0` | `0` or `1` | task_create/yield/sleep + TCB/stacks |
| `NOVADOS_MAX_TASKS` | `16` | `1..16` | size of compact task_* tables |

## 3. Commands

```powershell
# Default build (slim boot slice)
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe

# Diskless build
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe -DNOVADOS_ENABLE_NDF=0

# Full multi-task scheduler tables restored
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe -DNOVADOS_ENABLE_FULL_SCHEDULER=1

py -3.13 nova_assembler.py <output.asm>
py -3.13 nova_main.py --headless <output.bin> --cycles 50000
python -m pytest astrid/NovaDOS/tests -q
```

## 4. Measured gains (bank-safe layout, 2026-09-21)

Baseline was the pre-trim boot slice (~22 KB binary, ~10.8 KB globals).

| Metric | Before | After (default) | Delta |
|---|---|---|---|
| Binary size | 22,110 bytes | **11,214 bytes** | **−49.3% (−10,896)** |
| Code segment at `0x1100` | 11,243 bytes | **10,805 bytes** | −438 |
| Globals at `0x4200` | 10,850 bytes | **392 bytes** | **−96.4% (−10,458)** |
| `task_stacks` / `shell_stack` / `ctx_words` | present | **absent** | |
| `gvar_ndf_*` geometry | 7 words | **enum immediates** | |
| `func_timer_isr` body | 19×PUSH + body + 19×POP | **5 MOV/ADD + IRET** | |
| Headless behaviour | boots, demo_hits=111, DIR/TYPE/PEEK | **unchanged** (37/37 tests) |

Correctness: `astrid/NovaDOS/tests` **37 passed**; NDF probe suite also green.

## 5. Future candidates (not implemented)

- Feature-conditional IVT wiring that drops `timer_isr` entirely when
  `NOVADOS_ENABLE_TIMER=0` (today the ISR stays linked; only the arm sequence
  is gated).
- `impl` methods on `DirEntry`/`ProcEntry` once those types gain live users.
- Per-bank volume count (`NOVADOS_DISK_BANKS`) if multi-volume support lands.
- Dead-function elimination in the Astrid codegen (kmalloc still ships even
  when unused; a used-function pass would reclaim more code bytes).
