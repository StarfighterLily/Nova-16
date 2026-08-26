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
