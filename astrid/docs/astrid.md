A C language for the Nova-16, built from the ground up.

## Multi-file compilation units

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
