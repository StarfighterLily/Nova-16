## Missing features, ranked by value

> **Status.**
> * **Item 1 (function pointers) — IMPLEMENTED.** C declarator forms
>   (`int (*fp)(int)`, `int (*tbl[3])(int) = {…}`, as locals, globals,
>   statics and parameters), all call forms (`fp(x)`, `(*fp)(x)`,
>   `(&f)(x)`, `tbl[i](x)`), register-indirect `CALL`, and `&builtin`
>   linkage. Documented in `astrid.md` → *Function pointers and indirect
>   calls*. Tests: `tests/astrid/test_astrid_func_ptrs.py`.
> * **Item 2 (multi-dimensional arrays) — IMPLEMENTED.** `T name[R][C]` for
>   any scalar/pointer element type, row-major flat storage, chained
>   subscripts on reads, writes, compound assignment and `++`/`--`,
>   `&g[i][j]`, flat/2-D equivalence, array decay, and explicit diagnostics
>   for 3-D, missing dimensions and 2-D access on 1-D arrays. Documented in
>   `astrid.md` → *Two-dimensional arrays*. Tests:
>   `tests/astrid/test_astrid_2d_arrays.py`.
> * **Item 3 (nested struct/union fields) — IMPLEMENTED.** Nested aggregate
>   fields in struct/union definitions (including typedef-aliased field
>   types), deep member chains (`a.b.c`, `arr[i].inner.x`, `p->inner.x`),
>   footprint-accumulating layout, whole-struct copy of every nested word,
>   and full-size reservation for nested globals. Documented in `astrid.md`
>   → *Nested struct and union members*. Tests:
>   `tests/astrid/test_astrid_nested_structs.py`.
> * **Item 4 (struct parameters by value) — IMPLEMENTED.** `struct Tag p` /
>   `union Tag u` parameters, multi-word cdecl push of the aggregate, private
>   copy semantics, nested member addressing on the parameter, mixed scalar
>   + aggregate param lists, `impl` method args, and type-checked call sites
>   (variables, array elements, nested members). Struct *returns* remain
>   unsupported (out-parameter only). Documented in `astrid.md` → *By-value
>   struct and union parameters*. Tests:
>   `tests/astrid/test_astrid_struct_byval.py`.
>
> The items below are still open, in the recommended order.

### Tier 1 — Confirmed missing, high value

__1. Function pointers / indirect calls__ — ✅ **DONE** (see status above). `&func` already yields a function address (used by `task_spawn(..., &task_b)`), but there is no way to *call through* one. `FuncCall` carries only a static name string and `generate_call()` (codegen.py:6012) resolves strictly via `self.functions`/`builtin_functions`. This blocks callbacks, jump tables, vtable-style driver structs, and state machines — the classic C systems patterns. Implementation sketch: extend `FuncCall.callee` to hold an expression; when the callee isn't a known name, evaluate it to a register and emit the CPU's register-indirect CALL. Priority of the three: __highest__, moderate effort (parser + codegen + ABI is already cdecl, so nothing changes for existing calls).

__2. Multi-dimensional arrays__ — ✅ **DONE** (see status above). `VarDecl` previously supported exactly one `array_size`. On a game-console language this was the most *felt* gap — every 2D tilemap had to be written as flat `grid[y*8+x]`. Implemented as row-major flat storage with compile-time desugaring of `a[i][j]` to `a[i*COLS+j]`.

__3. Nested struct/union fields__ — ✅ **DONE** (see status above). Struct/union fields may now themselves be structs or unions (`struct Rect { struct Point topLeft; };`), including typedef-aliased field types, and member access chains to any depth (`a.b.c`, run-time-indexed `arr[i].inner.x`, pointer receivers `p->inner.x`). Layout accumulates each field's real footprint (a nested aggregate spans several words), whole-struct assignment copies every word of the footprint, and nested globals reserve their full byte size. Documented in `astrid.md` → *Nested struct and union members*. Tests: `tests/astrid/test_astrid_nested_structs.py`.

__4. Struct parameters by value (and struct returns)__ — ✅ **DONE for parameters** (see status above). `struct Tag p` / `union Tag u` parameters push the aggregate's words (cdecl); the push sequence IS the callee's private copy. Nested members, mixed param lists, array-element / nested-member arguments, recursion, chaining, and `impl` method args all work. **Struct returns remain open** (out-parameter only for now).

### Tier 2 — Accepted-but-vestigial keywords (semantic gaps)

__5. `const` is decorative__ — lexer comment says it plainly: *"const qualifier (accepted; treated as a normal variable)"*. No read-only enforcement, no ROM/code-segment emission for const tables. On a Princeton-architecture machine, `const int table[] = {...}` emitted as initialized data in the code region + a compile error on any assignment would be genuinely useful (lookup tables are everywhere in game code) and pairs naturally with the existing `@ addr` placement machinery.

__6. `unsigned` is decorative__ — `unsigned_int` exists only as a type *tag* (codegen.py:2681 literally maps `unsigned_int → int`; it's used only so `get_rtc` prints correctly). No unsigned comparison (JNC-based), no unsigned division. C-parity gap with real behavioral consequences for mixed sign/pointer code. The `signed/long/short` keywords are likewise normalized away.

__7. Bitfields__ — `unsigned flags : 3;` has no support at all. On a 64KB machine under real memory pressure this is a legitimate space-saver for flag/attribute packs inside structs. Implementation: layout in struct stride computation + read-modify-write sequences for member access.

### Tier 3 — Smaller C-parity polish

__8. Function-like macros in the preprocessor__ — explicitly rejected (`function-like macros are not supported`). Object-like `#define` works, but parameterized macros are the single most-missed preprocessor feature. Given inline functions exist, this is medium value; the preprocessor's token-expander already does the hard part.

__9. Variadic builtins / `printf`-style formatting__ — no `...` support; user variadics are probably not worth it, but a single `format/writef(fmt, ...)` builtin (%d/%x/%s/%c reusing ITOS + the existing concat buffers) would remove a lot of `write_text` + ITOS boilerplate seen in `game.ast`/`rpg.ast`.

__10. Adjacent string literal concatenation__ (`"abc" "def"`) — C/JS/Python all have it; trivial lexer-level fold.

__11. String-typed stdlib gaps__ — `strchr`/`strrchr`/`strstr`/`strncpy`/`strncat`/`atoi` are absent (you can fake them with `strfind`/`memcpy`, but the asymmetry with the existing `strlen/strcmp/strcpy/strcat/strupr/strlwr/strrev/strfind/strfindi` set is noticeable). Note: an earlier draft of this list wrongly claimed `strcpy`/`strcat` were missing — both DO exist (`codegen.py:1398`).

__12. `static_assert(cond, msg)`__ — constant folding already exists; this is nearly free and gives compile-time layout guards (e.g., struct sizes vs. the SCB page).

__13. Extended-asm operands__ — the docs themselves flag it: `asm` is a full compiler barrier with no read/write operand constraints. A minimal `asm("...": out, in...)` would let hand-optimized kernels cooperate with the register allocator instead of fighting it.

### Stale doc (not a language gap, but worth fixing)

`astrid/docs/astrid.md`'s Table of Contents lists sections 9–15 (*Basic syntax, Types, Memory model, Function calling conventions, Structs and unions, Standard builtins, Common patterns*) that don't exist in the file — `string`/`binary`/`stringh`, the `float` Q8.8 model, and most of the builtin library are __undocumented__, and `docs/features.md` is 0 bytes.
