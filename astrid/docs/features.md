1. __No direct P/R/Special register access__ — `P0`-`P9`, `R0`-`R9`, `SP`, `FP`, `VX/VY/VM/VL`, `SA/SF/SV/SW`, `TT/TM/TC/TS` are invisible to Astrid source.
2. __No SP/FP manipulation__ — can't read the stack pointer, can't build custom frames, task switches, or alloca.
3. __No PC control__ — no setjmp/longjmp, computed jumps, coroutines.
4. __No inline assembly__ — NoBASIC has `Asm` blocks; Astrid has *nothing*, so any instruction not covered by a builtin is unreachable.
5. __ISR support is name-convention only__ — only `timer_interrupt` (vector 0), hardcoded; the other 7 vectors at 0x0100–0x011F are unreachable.
6. __No address-placement syntax__ — globals can't be pinned at fixed addresses (e.g., sprite SCB at 0xF000) except by poking at runtime.
7. __No int→pointer cast__ — `*(int*)0xF000 = x` is not expressible; MMIO must go through peek/poke (fine, but casting is natural in C).
8. __`volatile`/`register` are accepted and (mostly) ignored__ — dangerous if the optimizer reorders around hardware reads.
9. __No naked functions__ — the ISR path has a hidden variant of this; it should be a first-class attribute.

---

## 2. Why the Natural Expansion Path Is "Lazy Builtins + Attributes"

The register allocator (`self.register_usage`, `var_reg`, `allocation_order`) owns every hardware register: P0 is the __return-value register__, P3 is reserved for DIV remainder, SP/FP are reserved, and locals live either in allocated registers or FP-relative/absolute spill slots at 0xC000–0xEFFF. This means:

> __You cannot expose registers as assignable variables__ without the allocator fighting the user. The correct design is the one the kernel primitives already proved: __volatile builtins that the scheduler/optimizer treat as opaque barriers__, emitted lazily so unused ones cost zero bytes.

That's exactly how `peek`/`poke`/`set_bank` work (`builtin_peek` … in `BUILTIN_IMPLEMENTATIONS`, marked side-effecting in the constant-folding tables so they're never folded). Everything below follows that pattern.

---

## 3. Proposed Expansion, Prioritized

### Tier 1 — Register Access (biggest win, lowest risk)

Add to `_init_builtins()` and `BUILTIN_IMPLEMENTATIONS`:

```c
int  get_reg(int n);          // read P-registers: get_reg(0) == P0
void set_reg(int n, int v);   // write P-registers
int  get_rreg(int n);         // R0-R9 (8-bit)
void set_rreg(int n, int v);  // 
int  get_sp();  void set_sp(int v);   // read: MOV P0, SP / write: MOV SP, P0
int  get_fp();  void set_fp(int v);
int  get_flags();  void set_flags(int f);  // 16-bit flag word (generic PUSHF/POPF alternative)
```

Implementation notes:

- Each stub is 1–3 instructions (`builtin_get_sp: MOV P0, SP / RET`), returning in P0 per the existing ABI (see `test_primitives_return_in_p0`).
- Register them in the __side-effect builtin list__ (the one containing `nop()`, `pushf()`, `popf()`, `halt()` in `test_astrid_builtin_folding.py`) so constant folding never elides them and the live-range scheduler treats them as barriers.
- Add `get_special(name)`/`set_special(name, v)` or named builtins (`get_vx()`, `set_sf()` …) for the MMIO-ish register file (VX=0xFD, VY=0xFE, SA=0xDD, SF=0xDE, SV=0xDF, SW=0xE0, TT=0xE3…TS=0xE6, MX=0xC5…). Many already exist as *opcodes*; they just lack Astrid builtins.
- __ABI hazard to document__: `set_reg` on a register the allocator is currently using for a live variable is a footgun. Mitigate by recording which registers `self.var_reg` has allocated in the current function and emitting a compile-time *warning* (not error — systems programmers sometimes want exactly this for handoff conventions) when `set_reg(n)`/`get_reg(n)` targets a live allocated register. The allocator state is right there in `self.var_reg` at call-site generation time.

### Tier 2 — Stack Manipulation & Task Switching

```c
// Already possible after Tier 1: set_sp() + set_reg() give you full
// context save/restore. But make the common patterns first-class:

int  stack_free();                  // SP - stack_floor (0xFF00 stack top per codegen comments)
void push(int v);  int pop();       // raw PUSH/POP (word) — pairs with pusha/popa
void *alloca(int bytes);            // SUB SP, n; return old SP  (frame-lifetime scratch)
void push_flags(); void pop_flags(); // exists as pushf()/popf() — keep

// Task switching (the killer feature — pure user-space, no OS needed):
int  context_save(int *ctx);        // pusha-order save of R0-R9,P0-P7 + SP/FP into ctx
void context_restore(int *ctx);     // inverse; combined = coroutine/context switching
```

`context_save`/`context_restore` compile to straight-line PUSHA-style sequences with a target buffer instead of the stack — the emulator already proves the semantics (`test_pusha_instruction_saves_register_frame`). Combined with `set_bank()` this gives you banked task stacks = a green-thread runtime written entirely in Astrid. That's the moment it becomes a *systems* language.

`alloca` needs a small codegen rule: mark the function "has dynamic locals," and force its stack-relative local addressing (reuse the exact formula the ISR path already uses — `timer_interrupt` computes SP-relative offsets with no FP, so the machinery exists).

### Tier 3 — Inline Assembly (the escape hatch)

```c
asm("MOV R0, 5\nJMP done");          // whole-string form
asm {                                 // block form (NoBASIC precedent)
    MOV R0, 5
    JMP done
}
```

Two integration options, in order of robustness:

1. __String form first__: pass through to the assembler with `func_` label context, expose Astrid variables by their codegen identity (register or `[0xAAAA]` spill address) via simple `"{varname}"` substitution — the substitution logic can literally reuse `_emit_local_load`'s resolution. The `nova_assembler.py` already assembles the output, so inline asm is just concatenated text.
2. __Block form__ later with the same lexer additions as NoBASIC (`'asm'` keyword).

Constraint to enforce: inline asm may clobber all caller-saved registers; document that P0 holds the expression result if the asm appears in an expression context. Until you have a constraint system, treat `asm` as a full compiler barrier (like `cli`).

### Tier 4 — Generalized Interrupts & Naked/ISR Attributes

Replace the `timer_interrupt` name convention with an attribute syntax (lexer: add `interrupt` keyword):

```c
interrupt(2) void uart_isr() { ... }   // vector 2 at 0x0108
naked void boot_stub() { asm("JMP main"); }
```

The generalization is mechanical because `_generate_function` already branches on `is_interrupt_handler`: emit `DW func_<name>` at `0x0100 + 4*n` instead of only vector 0, and let the existing save/restore/SP-relative-locals path apply to any `interrupt(n)` function. Keep `timer_interrupt` as a deprecated alias so existing programs (sintest etc.) keep compiling. The object-mode rejection (`interrupt vectors require fixed ORG 0x0100 placement`) generalizes trivially.

`naked` = the ISR prologue/epilogue switch minus the register save — it already exists as a code path; it just needs a name and a "no locals, no register allocation in this function" rule.

### Tier 5 — Placement & Casting (C-parity niceties)

```c
int scb[16] @ 0xF000;                 // absolute placement → ORG 0xF000 / DW in output
int *scbp = (int *)0xF000;            // int-to-pointer cast → alias of peek2/poke2
volatile int *kbd = (int *)0xC5;      // also make volatile finally *mean* something:
                                      //   mark var as no-CSE, no-fold, no-register-allocate
```

- Placement: in `generate()`, collect `@addr` globals, emit `ORG addr` segments exactly like the vector table already does (the assembler's ORG/.org segment system handles it).
- Casting: desugar `*(T*)addr` into the peek2/poke2 call sites — no new codegen needed.
- `volatile`: in `_collect_storage_qualifiers` (which already reads extern/static/volatile/register), set a `no_optimize` flag on the variable that (a) excludes it from `var_reg` allocation, (b) blocks CSE/folding on its loads/stores, (c) blocks spill-window assignment (forces FP-relative, which is already the fallback when `SPILL_REGION` is exhausted).
