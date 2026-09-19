"""Tests for function pointers / indirect calls in the Astrid compiler.

Covers:
1. Function pointer declaration + indirect call: int (*fp)(int) = &f; fp(3).
2. Asterisk call form: (*fp)(args) -- the classic C syntax.
3. Parenthesized address call: (&f)(args).
4. Function pointer PARAMETER (callback): void apply(int (*cb)(int), int v).
5. Array of function pointers: int (*handlers[3])(int); handlers[i](n).
6. Global function pointer variable.
7. Reassignment / state machine through a pointer.
8. Multi-argument indirect calls in a loop (stack-cleanup regression).
9. Recursion through a function pointer.
10. Static function pointer.
11. Global function-pointer array with an initializer list (user + builtin).
"""
import os
import sys
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


def run_binary(bin_path, max_cycles=3000000):
    """Run a binary headlessly and return (proc, cycles, mem)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name

    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')

        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)

        proc, cycles, mem = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# 1. Basic function pointer declaration + indirect call
# ---------------------------------------------------------------------------

def test_indirect_call_basic():
    """int (*fp)(int) = &f; fp(3) dispatches through the pointer."""
    source = """
int addone(int v) { return v + 1; }

int main() {
    int (*fp)(int) = &addone;
    return fp(3);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_indirect_call_basic (cycles={cycles}, R0={proc.r0})")


def test_indirect_call_star_form():
    """(*fp)(args) -- the classic C indirect-call syntax."""
    source = """
int double_it(int v) { return v * 2; }

int main() {
    int (*fp)(int) = &double_it;
    return (*fp)(21);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_indirect_call_star_form (cycles={cycles}, R0={proc.r0})")


def test_indirect_call_address_form():
    """(&f)(args) calls directly through the address expression."""
    source = """
int neg(int v) { return 0 - v; }

int main() {
    return (&neg)(7);   /* -7 -> P0=0xFFF9, R0 is the low byte 0xF9 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=0xFFF9, expected_r0=0xF9)
    print(f"PASS test_indirect_call_address_form (cycles={cycles}, P0=0x{proc.p0:04X}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 2. Function pointer as a callback parameter
# ---------------------------------------------------------------------------

def test_callback_parameter():
    """int apply(int (*cb)(int), int v) invokes the caller's function."""
    source = """
int inc(int v) { return v + 10; }
int dec(int v) { return v - 10; }

int apply(int (*cb)(int), int v) {
    return cb(v);
}

int main() {
    int a = apply(&inc, 5);
    int b = apply(&dec, 5);
    return a * 100 + b + 100;   /* 15*100 + (-5) + 100 = 1595 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=1595, expected_r0=1595 & 0xFF)
    print(f"PASS test_callback_parameter (cycles={cycles}, P0={proc.p0}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 3. Dispatch table: array of function pointers
# ---------------------------------------------------------------------------

def test_fnptr_array_dispatch():
    """int (*handlers[3])(int); handlers[i](n) dispatches by index."""
    source = """
int op_add(int v) { return v + 1; }
int op_sub(int v) { return v - 1; }
int op_zero(int v) { return 0; }

int (*handlers[3])(int);

int main() {
    handlers[0] = &op_add;
    handlers[1] = &op_sub;
    handlers[2] = &op_zero;
    int r = handlers[0](10);    /* 11 */
    r = r + handlers[1](10);    /* +9  -> 20 */
    r = r + handlers[2](99);    /* +0  -> 20 */
    return r;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=20)
    print(f"PASS test_fnptr_array_dispatch (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 4. Global function pointer with initializer
# ---------------------------------------------------------------------------

def test_global_fnptr_initializer():
    """int (*gfp)(int) = &f; at global scope (label resolved in the DW)."""
    source = """
int triple(int v) { return v * 3; }

int (*gfp)(int) = &triple;

int main() {
    return gfp(4);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_global_fnptr_initializer (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 5. Reassignment / state machine through a pointer
# ---------------------------------------------------------------------------

def test_fnptr_state_machine():
    """A pointer that is re-assigned between calls behaves like a state machine."""
    source = """
int state_a(int v) { return v + 2; }
int state_b(int v) { return v * 2; }

int main() {
    int (*step)(int) = &state_a;
    int v = step(3);        /* 5  */
    step = &state_b;
    v = step(v);            /* 10 */
    step = &state_a;
    v = step(v);            /* 12 */
    return v;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_fnptr_state_machine (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 6. Multi-argument indirect calls + loop stack-cleanup regression
# ---------------------------------------------------------------------------

def test_indirect_call_multiarg_loop():
    """fp(a, b, ...) inside a loop must not leak stack bytes (caller cleanup)."""
    source = """
int clamp_add(int a, int b, int lo, int hi) {
    int s = a + b;
    if (s < lo) s = lo;
    if (s > hi) s = hi;
    return s;
}

int main() {
    int (*fp)(int, int, int, int) = &clamp_add;
    int total = 0;
    for (int i = 0; i < 50; i++) {
        total = fp(total, 3, 0, 100);
    }
    return total;   /* 50 * 3 = 150 clamped to 100 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=100)
    # Stack sanity: after main returns, SP must be back near the top.
    assert proc.p8 >= 0xFFF0, f"Stack leaked: SP=0x{proc.p8:04X}"
    print(f"PASS test_indirect_call_multiarg_loop (cycles={cycles}, R0={proc.r0}, SP=0x{proc.p8:04X})")


# ---------------------------------------------------------------------------
# 7. Recursion through a function pointer
# ---------------------------------------------------------------------------

def test_indirect_recursion():
    """A function calling itself through a pointer parameter."""
    source = """
int sum_to(int (*self)(int, int), int n, int acc) {
    if (n == 0) return acc;
    return self(self, n - 1, acc + n);
}

int main() {
    return sum_to(&sum_to, 10, 0);  /* 55 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f"PASS test_indirect_recursion (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 8. Static function pointer
# ---------------------------------------------------------------------------

def test_static_fnptr():
    """static int (*fp)(int); persists across calls."""
    source = """
int bump(int v) { return v + 1; }

int call_twice() {
    static int (*fp)(int);
    fp = &bump;
    return fp(1);
}

int main() {
    return call_twice() + call_twice() * 10;  /* 2 + 2*10 = 22 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=22)
    print(f"PASS test_static_fnptr (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 9. Clear error for calling an undefined name
# ---------------------------------------------------------------------------

def test_undefined_function_still_errors():
    """A call to a name that is neither function, builtin, nor pointer
    variable must still fail to compile."""
    source = """
int main() {
    return nosuchfn(1);
}
"""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser
    from astrid.codegen.codegen import CodeGenerator
    from astrid.errors import CodeGenError
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()  # parse succeeds; codegen must reject
    gen = CodeGenerator()
    # codegen wraps per-function failures in CodeGenError, but the original
    # NameError text is preserved -- accept either shape and check the name.
    with pytest.raises((NameError, CodeGenError)) as excinfo:
        gen.generate(ast)
    assert 'nosuchfn' in str(excinfo.value)
    print("PASS test_undefined_function_still_errors")


def test_global_fnptr_array_initializer():
    """int (*g[3])(int) = {&a, &b, &c}; at global scope.

    Global function-pointer ARRAY initializers emit `DW func_a, func_b, ...`
    labels. Regression: global allocation runs before function
    pre-registration, so the label must resolve from the AST, not from
    self.functions (which is still empty at that point).
    """
    source = """
int op_add(int v) { return v + 1; }
int op_sub(int v) { return v - 1; }
int op_mul(int v) { return v * 2; }

int (*tbl[3])(int) = { &op_add, &op_sub, &op_mul };

int main() {
    int r = 0;
    for (int i = 0; i < 3; i++) {
        r = r + tbl[i](10);
    }
    return r;   /* 11 + 9 + 20 = 40 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=40)
    print(f"PASS test_global_fnptr_array_initializer (cycles={cycles}, R0={proc.r0})")


def test_builtin_address_links_implementation():
    """Taking a builtin's address records its use, so the label AND its
    implementation are emitted (DW func_op_add, builtin_abs + `builtin_abs:`).

    Compile-only: an indirect call cannot know whether its target is a user
    function (which LEAVES arguments for the caller to pop) or a builtin stub
    (which POPS its own arguments), so mixing them in one indirect call site
    is not stack-safe -- wrap a builtin in a user function if you need it in
    a dispatch table.
    """
    source = """
int op_add(int v) { return v + 1; }

int (*gtbl[2])(int) = { &op_add, &abs };

int main() {
    return gtbl[0](1);
}
"""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser
    from astrid.codegen.codegen import CodeGenerator
    gen = CodeGenerator()
    asm = gen.generate(Parser(Lexer(source).tokenize()).parse())
    dw = [l.strip() for l in asm
          if l.strip().startswith('DW ') and 'func_op_add' in l]
    assert dw and 'builtin_abs' in dw[0], f"expected DW with builtin_abs, got {dw}"
    assert 'builtin_abs:' in asm, "builtin_abs implementation was not emitted"
    print("PASS test_builtin_address_links_implementation")


if __name__ == '__main__':
    test_indirect_call_basic()
    test_indirect_call_star_form()
    test_indirect_call_address_form()
    test_callback_parameter()
    test_fnptr_array_dispatch()
    test_global_fnptr_initializer()
    test_fnptr_state_machine()
    test_indirect_call_multiarg_loop()
    test_indirect_recursion()
    test_static_fnptr()
    test_undefined_function_still_errors()
    test_global_fnptr_array_initializer()
    test_builtin_address_links_implementation()
