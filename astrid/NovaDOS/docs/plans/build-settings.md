# NovaDOS (Astrid) Build Settings — Preprocessor Report

Date: 2026-09-17
Status: implemented and validated
Scope: `astrid/NovaDOS/src/kernel/` (the Astrid kernel), tests in
`astrid/NovaDOS/tests/test_kernel_compile.py`

## 1. Analysis: what the new preprocessor offers this codebase

The conditional-compilation preprocessor (commit `65d0720`, see
`astrid/docs/conditional_compilation.md`) runs before the Astrid lexer and
supports `#define/#undef`, `#if/#ifdef/#ifndef/#elif/#else/#endif`, `#error`,
`defined()`, and object-like macro expansion with C-style `#if` arithmetic.

Application to the Astrid NovaDOS kernel (`kernel.ast` -> `memmgr.ast` ->
`types.ast` -> `kdos.ast`, plus `../fs/ndf.ast`):

| Candidate use | Verdict | Reason |
|---|---|---|
| Optional subsystems (NDF disk layer + DIR/TYPE commands) | **Implemented** | Excluded source never reaches the parser/codegen: no runtime bytes, no globals, no dead branches. |
| Build-time shell polling limit | **Implemented** | A one-token macro replaces the magic `200` loop bound; `#error` validation catches nonsense before any output is produced. |
| Replacing `enum SysCall`/`Memory`/... with macros | Rejected | Enums already compile to immediate constants; a macro conversion would churn ~150 lines for zero runtime gain. |
| Selecting the bank-safe memory layout | Not possible | The layout is a codegen option (`--memory-layout bank-safe`), not source text; a macro cannot reach it. Keep the CLI flag. |
| `#include`-style header guards | Not applicable | Astrid's `include` is parser-managed with diamond dedupe; the preprocessor has no `#include`, and child units inherit only a snapshot of the caller's defines (definitions do not flow back). |

## 2. Build settings (defined in `kernel.ast`, overridable via `-D`)

| Macro | Default | Valid range | Controls |
|---|---|---|---|
| `NOVADOS_ENABLE_NDF` | `1` | `0` or `1` | `ndf.ast` include, boot volume setup, DIR/TYPE dispatch, HELP text |
| `NOVADOS_POLL_LIMIT` | `200` | `1..32767` | shell keyboard-poll iterations in `main()` |

Invalid values fail compilation with `#error` (filename/line/snippet
diagnostic) **before** any `.asm` is written; the upper bound keeps the
counter inside Astrid's signed 16-bit arithmetic.

## 3. Commands

```powershell
# Default build (identical behavior and bytes to pre-feature builds)
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe

# Diskless build (no NDF layer, no DIR/TYPE, HELP lists fewer commands)
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe -DNOVADOS_ENABLE_NDF=0

# Custom polling limit (e.g. quick headless probes)
py -3.13 astrid/astrid_compiler.py astrid/NovaDOS/src/kernel/kernel.ast --memory-layout bank-safe -DNOVADOS_POLL_LIMIT=2

py -3.13 nova_assembler.py <output.asm>
py -3.13 nova_main.py --headless <output.bin> --cycles 50000
python -m pytest astrid/NovaDOS/tests -q
```

## 4. Measured gains (bank-safe layout, 50,000-cycle headless runs)

| Metric | Default (`NDF=1`) | Diskless (`NDF=0`) |
|---|---|---|
| Binary size | 23,388 bytes | **19,086 bytes (−18.4%)** |
| Code segment at `0x1100` | 12,521 bytes | 8,233 bytes (−4,288) |
| Globals at `0x4200` | 10,850 bytes | 10,836 bytes (−14: the 7 `ndf_*` constants) |
| `ndf_*` / `set_bank` symbols | present | **absent from `.sym`** |
| Headless behaviour | boots, banner + prompts, 604 layer-0 pixels | identical visuals/state; no bank switching |

Correctness guards added (`test_kernel_compile.py`, 35 tests total):
- default build binary is byte-for-byte unchanged (SHA-256 verified during
  development; the compile is deterministic),
- diskless build contains no `func_ndf_*`/`gvar_ndf_*`/`set_bank` symbols and
  is strictly smaller; segments still clear of the entry stub and bank window,
- diskless shell: `D`/`TBOOT` fall through (`shell_cmd == 0`), `H` prints
  `HELP PEEK CLS BYE`, `P` prints `4E 44`, `B` exits; `demo_hits == 111`
  (scheduler fingerprint) and the OS signature `ND\x01\x00` are intact,
- `NOVADOS_POLL_LIMIT=1/2` bound the loop (0/1 commands dispatched),
  `-1/0/32768` and `NOVADOS_ENABLE_NDF=-1/2` raise `PreprocessorError` naming
  the macro and write no output file, `32767` compiles.

## Final validation

The combined NovaDOS, preprocessor, NDF-probe and memory-layout suite passed
**107 tests** (93 baseline plus 14 new parametrized cases). No emulator or
compiler implementation was modified; the full repository suite was not run.
Standalone NovaDOS-only pytest runs report existing marker-registration warnings.

With a 300,000-cycle cap, both CLI headless runs reached `PC=0x100F`,
`SP=FP=0xFFFF`, `R0=0x31`, and **643 visible layer-0 pixels**. The default
completed in 113,469 cycles; diskless completed in 111,092. The earlier
50,000-cycle observations above are intermediate snapshots, not final states.
Byte identity with the baseline was checked manually by SHA-256, not by an
added automated regression test. The diskless structural test checks segment
non-overlap; the existing default-build tests also check the bank window.

Settings use integer preprocessor expressions, not typed configuration values:
unknown identifiers evaluate to zero per Astrid's preprocessor contract. The
range checks are not a substitute for validating arbitrary external build input.
A failed compile does not remove an already-existing output file; assemble only
after a successful compile to avoid stale artifacts.

## 5. Future candidates (not implemented)

- `NOVADOS_ENABLE_SCHEDULER=0` would shed `memmgr.ast`'s scheduler
  (`task_*` tables) for single-threaded embeds; larger win than NDF but needs
  a kernel entry path that skips `task_spawn`/`task_switch`.
- Feature-conditional IVT wiring in `interrupts.ast` (e.g. drop the timer ISR
  when no scheduler is present).
- Per-bank volume count (`NOVADOS_DISK_BANKS`) if multi-volume support lands.
