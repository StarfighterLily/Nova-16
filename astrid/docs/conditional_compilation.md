# Astrid conditional compilation

Astrid is a C-like Nova-16 language with 8-bit `char`, 16-bit integers and
pointers, Q8.8 `float`, structs/unions, implementation blocks, inline assembly,
and parser-managed `include`/`inherits` units. Its pipeline is now:

**conditional preprocessing → lexer → parser/file-unit merging → optimized assembly**.

Preprocessing runs automatically in `Lexer.tokenize()`, including CLI, compiler
API, MCP compilation through that API, and recursively loaded file units.
Excluded source never reaches the parser or code generator and emits no runtime
branch instructions. Disabled includes are not loaded.

## Example

```c
#ifndef LEVEL
#define LEVEL 1
#endif

int main() {
#if defined(DEBUG) && LEVEL >= 2
    return 42;
#elif LEVEL == 1
    return 7;
#else
    return 0;
#endif
}
```

```powershell
py -3.13 c:\Code\projects\Nova\astrid\astrid_compiler.py c:\Code\projects\Nova\astrid\progs\game.ast -DDEBUG -DLEVEL=2
```

`-D` / `--define` is repeatable. `-DNAME` means `NAME=1`; `-DNAME=` defines an
empty replacement. In Python:

```python
from astrid.compiler_api import compile_astrid
compile_astrid(r'c:\Code\projects\Nova\astrid\progs\game.ast',
               defines={'DEBUG': None, 'LEVEL': 2})
```

## Directives and expressions

Directives are case-sensitive, occupy their own physical line, and start with
`#` as the first non-whitespace/non-comment character. No semicolon is needed.

- `#define NAME replacement`: object-like token replacement; a missing
  replacement is empty, but the name is still defined.
- `#undef NAME`: removes a definition; unknown names are harmless.
- `#ifdef NAME`, `#ifndef NAME`, `#if expression`: begin a nested conditional.
- `#elif expression`, `#else`, `#endif`: choose the first matching branch/end it.
- `#error message`: produces a compiler diagnostic when active.

Conditions support decimal, hexadecimal, binary and explicit `0o` octal integers,
parentheses, `defined NAME` / `defined(NAME)`, unary `! ~ + -`, arithmetic
`+ - * / %`, shifts, comparisons, bitwise operators and `&& ||`, with C-style
precedence. Unknown identifiers evaluate to zero. Logical evaluation
short-circuits; arithmetic in unselected branches is not evaluated. Integers
are mathematical integers, not Nova-16 wrapping values; division truncates
toward zero and remainder follows the dividend's sign. Shift counts are limited
to 0–65535.

Macros expand whole tokens, recursively, without replacing text in strings,
character literals, comments or larger identifiers. Recursive references stop
expanding; expansion is limited to 64 levels and 1 MiB per expansion. Identical
redefinitions are allowed; use `#undef` before changing a definition.

## File-unit scope (not C textual includes)

Use Astrid's existing `include "file.ast";` and `inherits "base.ast";` syntax.
Children inherit a **snapshot of definitions at the directive's location**.
Definitions/undefinitions in a child do not flow back into its caller or siblings.
Each file must balance its own conditional blocks. Existing cycle detection,
diamond deduplication (first load wins), and inheritance overrides remain intact.

## Diagnostics and limits

Inactive lines and directives retain their line positions. Macro-generated
tokens point to the invocation column; following tokens retain their original
columns. Preprocessor errors report the filename, line, column and source snippet.

This is not a full C preprocessor: function-like macros, line continuations,
stringification, token pasting, `#include`, `#pragma`, ternary conditions, character
conditions and floating-point conditions are not supported. Quoted multiline
source text remains literal, not a source of directives. Comments and quoted
text must remain lexically balanced even around disabled code.
