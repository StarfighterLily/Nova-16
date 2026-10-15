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
> * **Item 4 (struct parameters by value + struct returns) — IMPLEMENTED.**
>   `struct Tag p` / `union Tag u` parameters (multi-word cdecl push, private
>   copy semantics) and `struct Tag f(...)` / `union Tag f(...)` returns via a
>   hidden sret pointer. Nested members, mixed param lists, array-element /
>   nested-member arguments, assignment/init destinations, `impl` method
>   args and returns, recursion/chaining, and type-checked call sites all
>   work. Documented in `astrid.md` → *By-value struct and union parameters*
>   and *By-value struct and union returns*. Tests:
>   `tests/astrid/test_astrid_struct_byval.py`,
>   `tests/astrid/test_astrid_struct_return.py`.
> * **Item 5 (`const` enforcement + const-ROM emission) — IMPLEMENTED.**
>   Read-only enforcement rejects every direct write form (`=`, compound
>   assignment, `++`/`--`, through a `const T *` pointee, on struct members to
>   any depth, locals shadowing globals per C scoping) and now also the
>   const-discarding escape (`int *p = &const_obj`, including array decay).
>   Unplaced `const` globals are emitted as initialized data inside the
>   program image's read-only window (above the interrupt vectors, below the
>   entry stub), saving writable global RAM; placed `const` (`@ addr`) keeps
>   its own segment. Documented in `astrid.md` → *Const enforcement and
>   read-only data*. Tests: `tests/astrid/test_astrid_const_enforcement.py`,
>   `tests/astrid/test_astrid_const_rom.py`.
> * **Item 6 (`unsigned` / `signed` semantics) — IMPLEMENTED.** `unsigned_int`
>   selects the unsigned comparison family (JC/JNC borrow-based) and raw
>   hardware DIV/MOD; `signed_int` (and float, and any comparison against
>   zero) selects the sign-corrected paths. The typing now survives every
>   value shape -- identifier, struct member (including bit-fields), array
>   element, function parameter, typedef, cast, dereference (`*p` inherits
>   the pointee's sign), and postfix on all of those. Documented in
>   `astrid.md` → *Signed and unsigned integers*. Tests:
>   `tests/astrid/test_astrid_signed_type.py`,
>   `tests/astrid/test_astrid_signed_division.py`,
>   `tests/astrid/test_astrid_unsigned_ops.py`.
> * **Item 7 (bitfields) — IMPLEMENTED.** `unsigned flags : 3;` packs into the
>   low bits of the containing 16-bit word (greedy low-bit packing, spill to
>   a new word when a field does not fit, C's unit rule), in structs and
>   unions, comma lists, and nested aggregates. Reads extract-and-mask,
>   `signed` fields sign-extend, writes are read-modify-write so word-mates
>   survive, compound assignment and `++`/`--` operate on the field value,
>   `sizeof` reflects the packed size, and widths 0/>16/non-constant are
>   diagnosed at parse time. Documented in `astrid.md` → *Bit-fields*.
>   Tests: `tests/astrid/test_astrid_bitfields.py`.
> * **Items 8–13 (Tier 3 C-parity polish) — IMPLEMENTED.** Function-like
>   macros, `format`/`writef`, adjacent string literal folding, the
>   `strchr`/`strrchr`/`strstr`/`strncpy`/`strncat`/`atoi` builtins,
>   `static_assert`, and extended-asm operands (`"r"`, `"=r"`, `"+r"`, `"i"`
>   bound to registers and referenced as `{k}`). Documented in `astrid.md`
>   (sections 24–28 and *Inline assembly → Extended asm operands*) and
>   `conditional_compilation.md`. Tests: `tests/astrid/test_astrid_tier3_*.py`.
>
> Every ranked item is now implemented; only the stale-doc note at the end
> remains partly open.

### Tier 1 — Confirmed missing, high value

__1. Function pointers / indirect calls__ — ✅ **DONE** (see status above). `&func` already yields a function address (used by `task_spawn(..., &task_b)`), but there is no way to *call through* one. `FuncCall` carries only a static name string and `generate_call()` (codegen.py:6012) resolves strictly via `self.functions`/`builtin_functions`. This blocks callbacks, jump tables, vtable-style driver structs, and state machines — the classic C systems patterns. Implementation sketch: extend `FuncCall.callee` to hold an expression; when the callee isn't a known name, evaluate it to a register and emit the CPU's register-indirect CALL. Priority of the three: __highest__, moderate effort (parser + codegen + ABI is already cdecl, so nothing changes for existing calls).

__2. Multi-dimensional arrays__ — ✅ **DONE** (see status above). `VarDecl` previously supported exactly one `array_size`. On a game-console language this was the most *felt* gap — every 2D tilemap had to be written as flat `grid[y*8+x]`. Implemented as row-major flat storage with compile-time desugaring of `a[i][j]` to `a[i*COLS+j]`.

__3. Nested struct/union fields__ — ✅ **DONE** (see status above). Struct/union fields may now themselves be structs or unions (`struct Rect { struct Point topLeft; };`), including typedef-aliased field types, and member access chains to any depth (`a.b.c`, run-time-indexed `arr[i].inner.x`, pointer receivers `p->inner.x`). Layout accumulates each field's real footprint (a nested aggregate spans several words), whole-struct assignment copies every word of the footprint, and nested globals reserve their full byte size. Documented in `astrid.md` → *Nested struct and union members*. Tests: `tests/astrid/test_astrid_nested_structs.py`.

__4. Struct parameters by value (and struct returns)__ — ✅ **DONE** (see status above). By-value parameters push the aggregate's words (cdecl); by-value returns use a hidden sret destination pointer. Nested members, mixed param lists, array-element / nested-member arguments, assignment/init destinations, recursion, chaining, and `impl` method args/returns all work.

### Tier 2 — Accepted-but-vestigial keywords (semantic gaps)

__5. `const` is decorative__ — ✅ **DONE** (see status above). Read-only
enforcement rejects every write form plus the const-discarding escape;
unplaced `const` globals are emitted as initialized data in the code region's
read-only window, which pairs with the existing `@ addr` placement machinery
(a placed `const` keeps its own segment).

__6. `unsigned` is decorative__ — ✅ **DONE** (see status above).
Unsigned comparison is JNC/JC-based, unsigned division is raw hardware
DIV/MOD, `signed`/`unsigned`/`long` normalize through the parser with the
sign bit preserved for `int`, and the sign survives dereferences, struct
members, array elements, postfix increments and casts, so mixed sign/pointer
code compares with the right jump family.

__7. Bitfields__ — ✅ **DONE** (see status above). `unsigned flags : 3;`
packs into the low bits of a shared 16-bit word, with layout in the struct
stride computation and read-modify-write sequences for member access; the
genuine space saver for flag/attribute packs inside structs on a 64KB
machine, including `signed` sign-extension and `signed` comparisons.

### Tier 3 — Smaller C-parity polish

__8. Function-like macros in the preprocessor__ — ✅ **DONE**. C semantics (pre-expanded arguments, paren/string-aware argument splitting, arity diagnostics); variadic, `#` and `##` are not supported. Tests: `test_astrid_tier3_function_macros.py`. Original note: explicitly rejected (`function-like macros are not supported`). Object-like `#define` works, but parameterized macros are the single most-missed preprocessor feature. Given inline functions exist, this is medium value; the preprocessor's token-expander already does the hard part.

__9. Variadic builtins / `printf`-style formatting__ — ✅ **DONE** as compile-time-expanded `format(fmt, ...)` and `writef(fmt, ...)` with `%d %x %s %c %%`. Tests: `test_astrid_tier3_format.py`. Original note: no `...` support; user variadics are probably not worth it, but a single `format/writef(fmt, ...)` builtin (%d/%x/%s/%c reusing ITOS + the existing concat buffers) would remove a lot of `write_text` + ITOS boilerplate seen in `game.ast`/`rpg.ast`.

__10. Adjacent string literal concatenation__ (`"abc" "def"`) — ✅ **DONE**, folded in the parser, including `asm` templates.

__11. String-typed stdlib gaps__ — ✅ **DONE**: all six are lazily linked asm builtins. Tests: `test_astrid_tier3_string_stdlib.py`. Original note: `strchr`/`strrchr`/`strstr`/`strncpy`/`strncat`/`atoi` are absent (you can fake them with `strfind`/`memcpy`, but the asymmetry with the existing `strlen/strcmp/strcpy/strcat/strupr/strlwr/strrev/strfind/strfindi` set is noticeable). Note: an earlier draft of this list wrongly claimed `strcpy`/`strcat` were missing — both DO exist (`codegen.py:1398`).

__12. `static_assert(cond, msg)`__ — ✅ **DONE** at file and statement scope. Tests: `test_astrid_tier3_static_assert.py`. Original note: constant folding already exists; this is nearly free and gives compile-time layout guards (e.g., struct sizes vs. the SCB page).

__13. Extended-asm operands__ — ✅ **DONE**: `asm("..." : "=r"(out) : "r"(in), "+r"(acc), "i"(K))` with `{k}` placeholders; outputs may be any lvalue. `asm` stays a full barrier. Tests: `test_astrid_tier3_extended_asm.py`. Original note: the docs themselves flagged it: `asm` is a full compiler barrier with no read/write operand constraints. A minimal `asm("...": out, in...)` would let hand-optimized kernels cooperate with the register allocator instead of fighting it.

### Stale doc (not a language gap, but worth fixing)

*Partly addressed:* every feature added from this list is now documented in `astrid.md`, but the gap below still stands. `astrid/docs/astrid.md`'s Table of Contents lists sections 9–15 (*Basic syntax, Types, Memory model, Function calling conventions, Structs and unions, Standard builtins, Common patterns*) that don't exist in the file — `string`/`binary`/`stringh`, the `float` Q8.8 model, and most of the builtin library are __undocumented__, and `docs/features.md` is 0 bytes.
