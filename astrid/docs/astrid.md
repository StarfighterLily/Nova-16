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
