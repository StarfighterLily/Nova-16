A C language for the Nova-16, built from the ground up.

## Table of Contents

1. [Multi-file compilation units](#multi-file-compilation-units)
2. [Implementation blocks](#implementation-blocks)
3. [Systems builtins: registers, stack, and flags](#systems-builtins-registers-stack-and-flags)
4. [Stack manipulation and cooperative tasks](#stack-manipulation-and-cooperative-tasks)
5. [Inline assembly](#inline-assembly)
6. [Interrupt handlers and naked functions](#interrupt-handlers-and-naked-functions)
7. [Absolute placement, address casts, and volatile](#absolute-placement-address-casts-and-volatile)
8. [Getting started](#getting-started)
9. [Basic syntax](#basic-syntax)
10. [Types](#types)
11. [Memory model](#memory-model)
12. [Function calling conventions](#function-calling-conventions)
13. [Structs and unions](#structs-and-unions)
14. [Standard builtins](#standard-builtins)
15. [Common patterns](#common-patterns)
16. [Function pointers and indirect calls](#function-pointers-and-indirect-calls)
17. [Two-dimensional arrays](#two-dimensional-arrays)
18. [Nested struct and union members](#nested-struct-and-union-members)

---

## Getting started

Astrid programs can be split across files with two top-level directives:

```c
include "lib.ast";     // splice lib.ast's functions/globals/enums in
inherits "engine.ast"; // pull in engine.ast as a base, with overrides
```

Both directives must appear at top level (not inside function bodies) and
take a quoted path. Relative paths resolve against the directory of the
file containing the directive, recursively.

### include -- strict splice
Every definition from the included file is merged into the program.
Redefining an included function or global (in this file or another
included file) is a compile error. Enum constants merge too; redefining
a constant with a different value is an error. The same file reached
through multiple paths (diamond includes) merges exactly once; include
cycles are detected and reported with the full chain.

### inherits -- base units with overrides
The inherited file acts as a base: its functions, globals, and enum
constants are used only where the inheriting program does not define its
own version. Overrides apply globally -- if `main.ast` overrides `greet()`,
then even calls made from inside other inherited/included files resolve
to the override, because call sites resolve by name at compile time.
Precedence when names collide:

1. Definitions written directly in the inheriting file always win.
2. Inherited ("more derived") definitions shadow same-named definitions
   that arrived via plain `include`.
3. Inherited enum constants only fill gaps; the child's own enum values win.

### Example
```c
// draw.ast
void clear_screen() { screen_fill(0x00); }
int border = 15;

// main.ast
include "draw.ast";
int clear_screen() { return 0; }   // ERROR: duplicate after include

// game.ast
inherits "draw.ast";
void clear_screen() { set_layer(0); screen_fill(0x00); }  // OK: override
int main() { clear_screen(); return border; }             // uses both
```

## Implementation blocks

Astrid supports Rust-style `impl` blocks that attach methods to a struct or
union type. Methods are ordinary functions scoped to a type; the first
parameter must be the receiver `self`, which is implicitly typed
`struct Tag *` (unions use `union Tag *`). Because Astrid has no by-value
struct parameters, the receiver is always passed by address, so `self.field`
resolves through the pointee layout.

```c
struct Point { int x; int y; };

impl Point {
    void set(self, int x, int y) { self.x = x; self.y = y; }
    int sum(self, int b) { return self.x + self.y + b; }
    int mag(self) { return self.x * self.x + self.y * self.y; }
}
```

### Method calls

Methods are invoked with the usual member-access syntax, and the receiver is
passed implicitly as the first argument (`self`):

```c
struct Point p;
p.set(3, 4);          // local variable receiver
int m = p.mag();

struct Point *pp = &p;
pp->set(1, 2);        // pointer receiver (->)

struct Point pts[3];
pts[0].set(5, 6);     // array-element receiver
```

The call `p.method(a, b)` is sugar for passing `&p` as `self` followed by the
explicit arguments. The callee reads and writes the receiver's fields through
the `self` pointer.

### Namespacing

Method labels are namespaced to their type, so two structs may define the same
method name without collision:

```c
struct Point { int x; int y; };
struct Rect  { int w; int h; };

impl Point { int area(self) { return self.x * self.y; } }
impl Rect  { int area(self) { return self.w * self.h; } }
```

### Rules

- Every method's **first** parameter must be the named identifier `self`.
  Its type is implied by the block and must not be declared explicitly.
- `impl` blocks may appear at top level and are subject to the same
  include/inherits merging rules as functions: an included method cannot be
  redefined (compile error), and an inherited method is used only when the
  inheriting program does not define its own version (override).
- Duplicate methods within the same type, and empty `impl` blocks, are compile
  errors. The named type must be a defined struct or union.

## Systems builtins: registers, stack, and flags

Ten volatile hardware-view builtins give Astrid programs direct access to the
CPU's register file, stack/frame pointers, and the 12-bit flag word. They are
emitted lazily (zero bytes when unused), never constant-folded, and every call
re-reads live CPU state.

```c
int  get_reg(int n);        // P[n] (16-bit); n 0-9, out of range -> 0
int  set_reg(int n, int v); // P[n] = v; returns the previously-held value
int  get_rreg(int n);       // R[n] zero-extended (0-255)
int  set_rreg(int n, int v);// R[n] = low byte of v; returns previous value
int  get_sp();              // live stack pointer (non-destructive read)
void set_sp(int v);         // switches SP; returns with SP exactly == v
int  get_fp();              // live frame pointer
void set_fp(int v);         // redirects FP (context switching only)
int  get_flags();           // 12-bit flag word (T,S,O,B,D,I,C,Z,P,H,A,E)
void set_flags(int f);      // wholesale-replace the flag word
```

### Scratch-register contract

P0-P7 are compiler expression scratch (round-robin allocation, P3 excluded),
and R0 is builtin-call scratch, so a `set_reg(n, ...)` / `get_reg(n)` pair
only reads back reliably when nothing else evaluates in between -- in
practice P3 (never expression scratch; also the CPU's DIV remainder target)
and the R1-R9 range (never compiler scratch) are the stable slots. The
intended uses are hardware hand-off moments, not persistent storage:

```c
// Observe the live DIV remainder (DIV unconditionally writes P3):
int q = value / divisor;
int r = get_reg(3);

// Task-context switching: save/restore SP, FP, and flags around a stack swap.
int sp = get_sp();
int fp = get_fp();
int fl = get_flags();
/* ... switch stacks ... */
set_flags(fl);
set_fp(fp);
set_sp(sp);   // set_sp returns with SP == v; it JMPs instead of RETing
```

`set_flags` replaces the whole word; bracket expensive sections with a
save/restore pair. Bits T (single-step) and D (BCD mode) have global side
effects -- avoid setting them unintentionally. Bit 11 (E, the hacker flag)
is never modified by the CPU itself and is free for user/system tagging.

## Stack manipulation and cooperative tasks

Six more volatile builtins give Astrid direct stack control and the primitives
for cooperative multitasking. They are lazily emitted (zero bytes when unused),
never constant-folded, and re-read live hardware at every call site.

```c
void push(int v);               // push v onto the stack, return void
int  pop(void);                 // pop and return the top-of-stack word
int  alloca(int bytes);         // allocate `bytes` bytes of frame-lifetime stack scratch; return address
int  stack_free(void);          // return bytes of headroom between SP and 0x8000
void task_spawn(int *ctx, int *stack, int words, int entry);  // fabricate a task context
void task_switch(int *save, int *restore);                     // symmetric coroutine switch
```

### Raw stack words (push/pop)

`push(v)` writes `v` as the new top-of-stack word and returns void. `pop()`
removes and returns that word. They operate on the same hardware stack that
CALL/RET use, so caller-saved registers and return addresses live above the
pushed words; the pushed words share the stack but never collide with a
balanced CALL/RET frame as long as push/pop are paired within one expression.

```c
int main() {
    push(0x00AA);              // push a raw word
    int x = twice(21);         // normal calls come and go underneath
    int v = pop();             // recover the pushed word
    return (x == 42 && v == 0x00AA) ? 0x0D1D : 2;
}
int twice(int v) { return v * 2; }
```

### Frame-lifetime scratch (alloca/stack_free)

`alloca(bytes)` decrements SP by `bytes` and returns the old SP -- the address
of a scratch block that lives until the *current* function returns. The epilogue
(`MOV SP, FP` / `POP FP`) reclaims the space for free; no explicit free is
needed. Do not call `alloca()` inside an unbounded loop: every iteration eats
more stack until the frame unwinds.

`stack_free()` returns the current headroom -- the byte distance between SP and
the 0x8000 global-variable base (the low bound of the stack arena). It is
useful for guards and for reasoning about how much space a frame still has.
Each pushed word shrinks `stack_free()` by 2.

```c
int main() {
    int p = alloca(8);                 // 8 bytes of scratch, lives to return
    poke2(p, 0xCAFE);                  // write through the scratch address
    poke2(p + 2, 0xBEEF);
    int ok = (peek2(p) == 0xCAFE && peek2(p + 2) == 0xBEEF) ? 1 : 0;
    int q = twice_help(ok);
    return (ok == 1 && q == 2) ? 0x0D2D : 3;
}
int twice_help(int v) { return v * 2; }

int main() {
    int f1 = stack_free();     // initial headroom
    push(0);                    // push eats 2 bytes
    int f2 = stack_free();      // should be f1 - 2
    int v = pop();              // restore
    return (f1 == f2 + 2 && v == 0 && f1 > 0) ? 0x0D3D : 4;
}
```

### Cooperative task contexts (task_spawn / task_switch)

A task context is a 22-word (44-byte) block of registers plus stack state:

```
word 0: flags            words 4--13:  R0--R9
word 1: FP               words 14--21: P0--P7
word 2: SP-resume        (a stack address; the word it points at holds the resume PC)
word 3: unused
```

`task_spawn(ctx, stack, words, entry)` fabricates an initial context for a new
task. `stack` is the byte address of a region at least `words*2` bytes long;
the entry point `entry` (an address, typically `&function`) is parked at the top
of that region, the resume SP is set to point at that parked word, and the
remaining fields are zeroed (R0--R9, P0--P7) or filled in (FP = `stack`, flags
inherited from the spawning task's current flag word).

`task_switch(save, restore)` saves the *current* task into `save`, restores the
task described by `restore`, and enters it via `RET` (which pops the resume PC
from the restored stack). The save side includes P3 (the DIV remainder) so that
it survives switches; the save/restore permutation covers all 10 R registers, 8
P registers, FP, SP, and the flag word.

A minimal ping-pong: `main` spawns `task_b` on a fresh stack, then the two
tasks alternate through `task_switch`. Each resume continues exactly after the
`task_switch` that yielded, as if it had just returned. Per-task locals in
separate frames survive independently, and P3 (DIV remainder) is preserved on
both sides across every switch.

```c
int ctx_main[22];
int ctx_b[22];
int bstack[64];
int seq[8];
int n = 0;

void task_b() {
    seq[n] = 20; n = n + 1;
    task_switch(&ctx_b, &ctx_main);

    seq[n] = 21; n = n + 1;
    task_switch(&ctx_b, &ctx_main);
    seq[n] = 22; n = n + 1;
    task_switch(&ctx_b, &ctx_main);
}

int main() {
    task_spawn(&ctx_b, bstack, 64, &task_b);
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 10; n = n + 1;
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 11; n = n + 1;
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 12; n = n + 1;
    return (n == 6 && seq[0] == 20 && seq[1] == 10 && seq[2] == 21
            && seq[3] == 11 && seq[4] == 22 && seq[5] == 12)
           ? 0x0D5D : n;
}
```

### Scratch and preservation contract

Task builtins treat the same scratch registers as the register/flag builtins:
P0--P7 are compiler expression temporaries and R0 carries builtin-call scratch,
so only the values those slots hold *at the instant task_switch runs* are saved.
P3 (the DIV remainder) is explicitly preserved by task_switch because the
function call into task_b may clobber P3 after main's DIV commits its remainder;
task_spawn dodges this by saving the caller's P3 into P7 before computing the
stack top, then restoring it from P7 after zeroing -- so a freshly spawned task
does not inherit a stray stack-word value in P3, and the parent's remainder
survives the spawn and the first switch.

```c
int ctx_main[22];
int ctx_b[22];
int bstack[64];
int slot = 0;

void task_b() {
    set_rreg(0, 100);
    int a = get_rreg(0);
    int q = a / 7;                 // P3 = 2 in task_b's context
    task_switch(&ctx_b, &ctx_main);
    slot = get_reg(3);             // after resume: B's own remainder = 2
    task_switch(&ctx_b, &ctx_main);
}

int main() {
    set_rreg(1, 50);
    int m = get_rreg(1);
    int mq = m / 7;                 // P3 = 1 in main's context
    task_spawn(&ctx_b, bstack, 64, &task_b);
    task_switch(&ctx_main, &ctx_b);
    task_switch(&ctx_main, &ctx_b);
    int own = get_reg(3);           // main sees its own P3 = 1 again
    if (slot != 2) return slot;
    if (own != 1) return 9;
    return 0x0D7D;
}
```


## Inline assembly

When a computation cannot be expressed through Astrid's builtins, `asm` blocks
drop to raw Nova-16 assembly. Two forms are available: a string form for
one-liners and a block form for multi-instruction sequences.

```c
// String form -- the whole program in one asm string
int x = asm("MOV P0, 5\nADD P0, R0");

// Block form -- one instruction per line, semicolons optional
asm {
    MOV R0, 5
    ADD P0, R0
    JMP done
}
```

`asm` blocks are compiler barriers: they are never constant-folded, never
CSE'd, and the live-range scheduler treats them as clobbering all registers.
The programmer is fully responsible for correctness -- the calling convention,
flag state, and any registers the asm touches.

### Inline variable references with `{varname}`

Inside an `asm` block, Astrid variables can be referenced with `{varname}`
syntax. Each occurrence is replaced at compile time with the variable's actual
storage location -- either a hardware register (when the allocator has placed it
one) or a memory reference (FP-relative for locals like `[FP-4]`, absolute for
globals like `[0x8020]`, or SP-relative inside interrupt handlers). This lets
hand-written asm interoperate with the compiler's register allocation without
fighting it.

```c
int x = 10;
int y = 20;
int g = 30;  // global

void add_them() {
    asm {
        MOV R0, {x}     // resolves to x's actual location (register or [FP+n])
        ADD R0, {y}     // resolves to y's actual location
        ADD R0, {g}     // resolves to [0x8020] (g's absolute address)
    }
}
```

Unknown `{name}` tokens are left as bare names (without the braces), so the
assembler can attempt label resolution -- useful for referencing user-defined
labels:

```c
asm {
    CMP R0, 0
    JMP {done}          // references a label named 'done'
done:
}
```

### Inline assembly in expressions

When `asm` appears in an expression context, the result is taken from P0 (the
Astrid ABI return-value register). The asm is expected to leave its result in
P0:

```c
int main() {
    int x = asm("MOV P0, 42");   // x = 42
    int y = asm("MOV P0, 10") + asm("MOV P0, 20");  // y = 30
    return x + y;
}
```

This is the idiomatic way to get a computed value out of inline asm -- assign
the `asm(...)` expression to a variable or use it directly in arithmetic.

### Calling convention

Inline asm may clobber all caller-saved registers (P0--P7, R0, and the flags).
Until a full constraint system exists, `asm` is treated as a full compiler
barrier (like `cli`). Hardware registers set via `set_reg()` before an `asm`
block may be overwritten unless the asm preserves them.

## Interrupt handlers and naked functions

Astrid supports interrupt service routines (ISRs) through the `interrupt(N)`
attribute syntax, generalizing the deprecated `timer_interrupt` name convention
to all 8 interrupt vectors (0--7).

### interrupt(N) attribute

```c
interrupt(2) void uart_isr() {
    // handler body
    iret();
}
```

The attribute takes a vector number `N` (0--7). The compiler programs the
corresponding interrupt vector at `0x0100 + 4*N` with the handler's address,
so the CPU dispatches to your handler when that interrupt fires. Multiple
handlers at different vectors are supported:

```c
interrupt(0) void timer_isr() { /* ... */ iret(); }
interrupt(2) void uart_isr()  { /* ... */ iret(); }
interrupt(5) void custom_isr(){ /* ... */ iret(); }
```

The deprecated `timer_interrupt` name is still accepted as an alias for
`interrupt(0)` -- existing programs continue to compile unchanged.

### Interrupt handler prologue/epilogue

Non-naked interrupt handlers automatically emit a full register save/restore
prologue and epilogue. The CPU's interrupt entry only preserves PC + flags;
general registers (R0--R9, P0--P7), FP, and SP are **not** preserved across the
interrupt. The compiler saves them before allocating locals and restores them
before `iret()`, using SP-relative local addressing (no ENTER/LEAVE, because the
CPU has already pushed context onto the stack).

```c
interrupt(1) void my_isr() {
    int a = random();       // SP-relative local
    ticks = ticks + a;      // safe: registers are preserved
    iret();                  // restore + return from interrupt
}
```

An implicit `iret()` is emitted if the handler returns without an explicit
call -- a handler body that falls through still restores correctly.

### naked attribute

`naked` functions skip the register save/restore prologue and epilogue. This
is useful for hand-optimized ISRs that manage their own register state, or for
boot stubs that need total control over the generated code:

```c
naked void boot_stub() {
    asm("JMP main");
}

naked interrupt(3) void fast_isr() {
    // No register save/iret emitted -- you own everything
    asm {
        MOV R0, [0xF000]    // read hardware directly
        ADD R0, 1
        MOV [0xF000], R0    // write back
        IRET                // must emit IRET yourself
    }
}
```

A naked ISR receives no automatic register preservation and must emit its own
`IRET`. A naked non-ISR function receives no prologue/epilogue at all -- it is
emitted as straight-line code ending in `RET`, with no stack frame setup.

### iret() builtin

The `iret()` builtin returns from an interrupt context. It is recognized
inside any interrupt handler (declared via `interrupt(N)` or the deprecated
`timer_interrupt` name) and emits the restore-from-interrupt sequence followed
by the `IRET` opcode. In a naked handler, you must emit `IRET` directly via
`asm("IRET")`.

```c
interrupt(0) void timer_isr() {
    ticks++;
    iret();   // restores registers + IRET
}
```

## Absolute placement, address casts, and volatile

Three C-parity features that round out systems programming in Astrid.

### Absolute placement with `@ addr`

A global variable can be pinned at a fixed address with the `@` attribute,
which emits the variable in its own `ORG` segment:

```c
int scb[16] @ 0xF000;   // sprite SCB block: 16 words at 0xF000-0xF01F
int flags  @ 0xC5;      // byte-sized MMIO view (mouse control register)
int count  @ 0xC000 + 0x40;   // any compile-time constant expression
```

Placement rules:

* The address must be a compile-time constant expression (numeric literals,
  enum constants, and constant arithmetic all fold).
* Only globals may be placed; `@` on a local is a compile error.
* A placed global does **not** consume a slot in the sequential 0x8000
  global region -- unplaced globals keep their contiguous layout, and the
  placed variable appears in its own `ORG <addr>` segment in the output.
* Once placed, the variable is addressed exactly like any other global:
  `scb[3] = 77` writes to `0xF006`, and `&scb` yields `0xF000`.

```c
int scb[16] @ 0xF000;
int ordinary;      // still at 0x8000; placement did not shift it

int main() {
    scb[0] = 0x1234;    // writes 0xF000
    scb[2] = 0xBEEF;    // writes 0xF004
    return 0;
}
```

### Address casts: `(T *)addr` and `*(T *)addr`

Casting an integer to a pointer type is an identity conversion -- a pointer is
a plain 16-bit address. Dereferencing such a cast loads or stores through that
address, desugaring to exactly what `peek2`/`poke2` (or `peek`/`poke` for byte
pointees) do, but with C's natural syntax:

```c
int *scbp = (int *)0xF000;   // scbp == 0xF000, the full address
*scbp = 0x1234;              // word store at 0xF000
int x = *(int *)0xF004;      // word load from 0xF004
*(char *)0xC5 = 7;           // byte store at 0xC5

int *p = (int *)0xF000;
p[3] = 77;                   // word store at 0xF006 (index scales by 2)
int v = *(p + 3);            // same address through pointer arithmetic
```

Because addresses are full 16-bit values, a `(char *)addr` cast keeps the
whole address -- it is never folded to the low byte. The optimizer treats
address casts as identity conversions and never constant-folds them.

### volatile finally means something

`volatile` on a variable now enforces the hardware-observation contract. A
volatile variable is:

* **Never register-allocated** -- it is excluded from the register-coloring
  candidate set, so every access touches memory.
* **Never spill-allocated** -- volatile locals stay FP-relative (or, for
  globals, at their absolute address); the spill window is never used.
* **Never folded or CSE'd** -- each read compiles to a fresh memory load, so
  hardware state changed by an interrupt or peripheral is always observed.

```c
volatile int v;
volatile int hw_flag = 0;

int main() {
    v = 42;
    int x = v + v;   // TWO memory loads: any change between them is seen
    while (!hw_flag) { }   // re-reads hw_flag every iteration
    return x;
}
```

Applies to globals, locals, and parameters alike:

```c
void poll(volatile int *status) { ... }   // volatile parameter
volatile int lv = 5;                      // volatile local (FP-relative)
```
---

## Function pointers and indirect calls

A function name used as a value is its 16-bit entry address, so a function
pointer is stored and moved exactly like any other pointer -- one word.

### Declaring a function pointer

The declarator uses C syntax: the `(` comes **before** the stars.

```c
int addone(int v) { return v + 1; }

int (*fp)(int) = &addone;   // local, initialized with a function address
int (*gfp)(int);            // global (also works as a static local)

int apply(int (*cb)(int), int v) {   // function pointer PARAMETER
    return cb(v);
}
```

The parameter type list (`(int)`, `(int, char)`) is parsed for syntax and
**discarded**: Astrid pointers are untyped 16-bit addresses, so callers and
callees are not signature-checked. A function pointer occupies one word and
is loaded/stored by the ordinary pointer machinery.

### Calling through a pointer

All of the C call forms work, and they all compile to a register-indirect
`CALL`:

```c
int (*fp)(int) = &addone;
int (*handlers[3])(int);          // array of function pointers

int main() {
    int a = fp(3);                // through the variable
    int b = (*fp)(3);             // classic C star form
    int c = (&addone)(3);         // through a taken address
    handlers[0] = &addone;
    int d = handlers[0](3);       // through a table entry
    return apply(&addone, a + b + c + d);   // callback argument
}
```

`(*fp)(x)` follows the C decay rule: `fp` is a *function designator*, so the
dereference yields the stored address rather than loading memory at that
address. A genuine pointer-to-function-pointer (`int **pp = &fp;
(*pp)(x)`) still performs the real load.

Because the target is not known at compile time, an indirect call:

* cannot be inlined or constant-folded,
* returns its result the same way a direct call does (16-bit value in `P0`,
  low byte mirrored in `R0`),
* follows the ordinary cdecl-style convention -- arguments are pushed by the
  caller and the **caller** deallocates them, so indirect calls inside loops
  do not leak stack bytes.

### Addresses, tables, and dispatch

`&func` on a **user** function yields its assembly label; on a **builtin** it
also marks that builtin as used, so taking a builtin's address links its
implementation:

```c
int (*math_op)(int, int) = &max;     // builtin address
```

Arrays of function pointers may be initialized with an initializer list,
locally or at global scope:

```c
int op_add(int v) { return v + 1; }
int op_sub(int v) { return v - 1; }

int (*gtbl[2])(int) = { &op_add, &op_sub };   // global: DW func_op_add, func_op_sub

int main() {
    int (*ltbl[2])(int) = { &op_add, &op_sub };  // local: filled by the prologue
    return gtbl[0](1) + ltbl[1](2);
}
```

Both user functions and builtins (`&abs`, `&min`) are accepted as global
initializer elements; referencing a builtin this way links its
implementation. Assigning into a pointer array element at runtime works too
(`handlers[0] = &op_add;`).

> **Caveat -- indirect calls must target user functions.** An indirect call
> site cannot know *what* it will call. User functions follow the cdecl-style
> convention (they **leave** the pushed arguments for the caller to pop),
> while builtin stubs **pop their own** arguments. Because an indirect call
> always cleans up the argument words itself, calling a *builtin* through a
> function pointer double-pops the stack. Taking a builtin's address is still
> useful (it links the implementation, and the address is a legal 16-bit
> value), but to put a builtin in a dispatch table, wrap it in a one-line
> user function:
>
> ```c
> int my_abs(int v) { return abs(v); }      // correct stack ownership
> int (*gtbl[2])(int) = { &op_add, &my_abs };
> ```

Re-assigning the pointer between calls gives a state machine without any
control-flow machinery:

```c
int (*step)(int) = &state_a;
int v = step(3);
step = &state_b;
v = step(v);
```

Calling a name that is neither a function, a builtin, nor a declared
function-pointer variable is still a compile error (`Undefined function
'x'`).

---

## Two-dimensional arrays

`int grid[rows][cols];` declares a 2-D array. Both dimensions must be
**positive compile-time constants** (this is not C99 VLA territory), and the
storage is flat and row-major: `rows * cols` elements, exactly as if it had
been declared `int grid[rows * cols]`.

```c
int grid[4][4];                 // global
char map[2][3];                 // byte elements
int m[2][3] = {1, 2, 3, 4, 5, 6};  // flat initializer list, row-major

int main() {
    int local[3][3];            // local
    grid[1][2] = 42;            // chained subscript write
    local[0][0] = grid[1][2];   // chained subscript read
    local[1][1] += 7;           // compound assignment
    local[2][2]++;              // postfix increment
    return local[0][0] + local[1][1] + local[2][2];
}
```

`grid[i][j]` is desugared to the flat index `grid[i * cols + j]` before any
addressing code is emitted, so 2-D arrays inherit every 1-D array feature:

* **Flat equivalence.** Because the storage is one flat block, a single
  subscript reaches the same slot: `grid[i * cols + j]` and `grid[i][j]` are
  the same element -- handy for linear traversal and for `memcpy`/`memset`.

  ```c
  grid[1][2] = 99;
  int a = grid[6];            // int grid[?][4]: linear index 6 == row 1, col 2
  ```

* **Address-of.** `&grid[i][j]` yields the flat slot address, and the array
  name decays to its base address when passed to a function.

  ```c
  int *p = &grid[1][1];
  *p = 77;
  fill_row(grid, 2, 4, 9);    // callee indexes flat: base[row * cols + j]
  ```

* **Loop traversal** visits memory in row-major order, so a nested
  `for (i) for (j)` walk is sequential and cache-friendly.

### Restrictions

* Exactly **two** dimensions: `int cube[2][2][2];` is a parse error
  (`more than two subscripts are not supported`).
* Both dimensions are required: `int grid[2][];` is rejected.
* Applying a second subscript to a 1-D array is rejected with a clear
  message (`'flat[...][...]' requires a 2-D array`).
* Member access on a 2-D element (`grid[i][j].field`) is not supported --
  copy the element into a struct variable first, or use a 1-D array of
  structs.

## Nested struct and union members

A struct or union field may itself be a struct or union ("nested aggregate"),
and member access chains to any depth.

```c
struct Point { int x; int y; };
struct Rect  { struct Point topLeft; struct Point botRight; };
struct Box   { struct Rect outer; int depth; };   // three levels deep

typedef struct Point Coord;                       // alias as a field type
struct Line  { Coord from; Coord to; };

int main() {
    struct Box b;
    b.outer.topLeft.x   = 10;     // a.b.c.d -- full name each level
    b.depth             = 4;
    return b.outer.topLeft.x + b.depth;
}
```

The inner type must be **already defined** when used as a by-value field (C
requires a complete type for a by-value member), and the diagnostic points at
the offending field:

```
Undefined struct 'Inner' used as a field of struct 'Outer' (line 4);
define it first -- nested aggregates must be complete types
```

### Layout

Layout follows the same rule Astrid already used for flat structs, applied
recursively: **every scalar field occupies exactly one 16-bit word slot**
(chars are word-padded, mirroring how locals are laid out), and a nested
aggregate field occupies as many consecutive words as its own layout needs.

```c
struct Point { int x; int y; };            // 2 words / 4 bytes
struct Rect  { struct Point tl; struct Point br; };  // 4 words / 8 bytes

// Rect.tl lives at byte offset 0, Rect.br at byte offset 4.
// tl.x = +0, tl.y = +2, br.x = +4, br.y = +6.
```

Offsets are therefore *not* simply `index * 2` once an aggregate is involved;
the compiler accumulates each preceding field's real footprint. A global
scalar struct of nested type reserves its full size (`DS 8` for `struct Rect`
above, not `DS 4`), so nested globals cannot overlap the next global.

### What works everywhere

Nested access is resolved for every base kind, including run-time indices and
pointer receivers:

```c
struct Wrap { struct Inner inner; int z; };

struct Wrap g;

int main() {
    struct Wrap local;          // local: FP-relative
    struct Wrap arr[3];
    struct Wrap *p;
    int i;

    g.inner.x = 1;              // global
    local.inner.y = 2;          // local
    p = &local;
    p->inner.x = 3;             // struct pointer receiver
    arr[2].inner.y = 4;         // run-time index into an array of structs
    for (i = 0; i < 3; i = i + 1) {
        arr[i].inner.x = i;     // chained access inside a loop
    }
    return local.inner.x + arr[2].inner.y;
}
```

`arr[i].inner.x` is handled by computing the element address first and then
adding the accumulated chain offset, so the run-time index is never dropped
(the emitter keys off the *innermost* base, not the outer member node).

Whole-struct assignment copies every word of the footprint, so nested children
are copied completely rather than truncated to their first word:

```c
struct Wrap a;
struct Wrap b;
a = b;                          // copies all words of a's nested children too
```

### Restrictions

* **Unions share offset 0.** All fields of a union -- nested or not --
  overlap at byte offset 0, and a union's size is its largest member
  footprint. Nested member access through a union field is resolved the same
  way as for structs.
* **Self-reference is rejected.** A struct or union may not contain itself,
  directly (`struct A { struct A inner; };`) or indirectly
  (`struct A { struct B b; }; struct B { struct A a; };`). Because a by-value
  field requires a complete type, these are caught by the same completeness
  check as an undefined tag rather than by a separate cycle pass.
* **Member access on a 2-D array element** (`grid[i][j].field`) is still not
  supported; use a 1-D array of structs.
* **Nested method-call receivers** (`obj.inner.method()`) are not supported --
  only a single member level is accepted as an `impl` receiver.
