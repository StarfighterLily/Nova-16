"""High-coverage tests for the Astrid array implementation.

Covers the array subsystem end-to-end (parser -> codegen -> assembled
binary -> emulated execution):

1. Declaration-size semantics: an explicit size is authoritative (C
   semantics). A partial initializer zero-fills the remainder (locals via
   runtime stores, globals via DS data); an overlong initializer is a
   compile-time error. Regression guard: `_resolve_array_count` used to
   derive the count from the initializer list, silently under-allocating
   `int arr[8] = {1,2,3}` (writes to arr[3..] corrupted adjacent frame
   storage) and silently over-allocating `int arr[3] = {1,2,3,4,5}`.
2. Element access: variable/expression/nested indices, byte-precision
   char arrays, element arguments, array-decay parameters.
3. Compound assignment on elements (all operators, constant and
   expression RHS), local and global targets.
4. Pointer aliasing: p = arr; p[i] read/write through the pointer.
5. Struct arrays: flat word initializers, partial zero-fill, sizeless
   derivation, member compound assignment, sizeof tightness.
6. Interrupt-handler (ISR) array codegen. The ISR cannot use PUSH to
   protect the target index across RHS evaluation (the stack holds the
   handler's SP-relative frame), so the RHS is evaluated first and the
   result re-homed into a register allocated after the whole RHS
   evaluation. Regression guard: a deep RHS (>= 3 array reads) used to
   wrap the round-robin register counter onto the target index register,
   storing through the wrong element.
7. sizeof() consistency for declared-size arrays.
"""
import os
import sys
import tempfile

import pytest

# Add project root and astrid dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


def _compile_source(source):
    """Compile Astrid source text; return the .asm path (no assemble)."""
    # UTF-8 is required: source may contain characters cp1252 cannot encode.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], source_path,
                '-o', source_path.replace('.ast', '.asm')]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return source_path.replace('.ast', '.asm')


def _cleanup(paths):
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


def compile_and_run(source, expected_r0=None, expected_p0=None,
                    max_cycles=2000000):
    """Compile, assemble, and run headlessly. Returns (proc, cycles, mem)."""
    asm_path = _compile_source(source)
    bin_path = asm_path.replace('.asm', '.bin')
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycle = 0
        while cycle < max_cycles and not proc.halted:
            proc.step()
            cycle += 1
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, \
                f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, \
                f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycle, mem
    finally:
        _cleanup([asm_path, bin_path, asm_path.replace('.asm', '.org'),
                  asm_path.replace('.asm', '.sym')])


def compile_rejected(source):
    """Assert the compiler rejects the source (no .asm produced)."""
    asm_path = None
    try:
        asm_path = _compile_source(source)
    except Exception:
        return  # raised -> rejected
    rejected = not os.path.exists(asm_path)
    _cleanup([asm_path])
    assert rejected, "compiler accepted source that should be rejected"


# ---------------------------------------------------------------------------
# Declared-size semantics (C semantics for initializers)
# ---------------------------------------------------------------------------

def test_local_partial_initializer_reserves_declared_size():
    """int arr[8] = {1,2,3} reserves all 8 slots; arr[7] must not corrupt
    adjacent frame storage and elements 3..7 read back as zero."""
    source = """
int main() {
    int arr[8] = {1, 2, 3};
    int guard;
    guard = 777;
    arr[7] = 5;
    arr[5] = 9;
    return guard + arr[3] + arr[4] + arr[5] + arr[6] + arr[7] * 0;
}
"""
    # guard(777) + zero-filled 3,4,6 + arr[5]=9 => 786
    proc, cycles, mem = compile_and_run(source, expected_p0=786,
                                        expected_r0=786 % 256)
    print(f"PASS test_local_partial_initializer_reserves_declared_size "
          f"(cycles={cycles}, P0={proc.p0})")


def test_local_char_string_partial_init_zero_fills():
    """char buf[8] = "Hi" zero-fills elements 2..7 (C string semantics)."""
    source = """
int main() {
    char buf[8] = "Hi";
    return buf[2] + buf[3] + buf[4] + buf[5] + buf[6] + buf[7]
           + buf[0] + buf[1];
}
"""
    # 'H'=72, 'i'=105, rest zero => 177
    proc, cycles, mem = compile_and_run(source, expected_r0=177)
    print(f"PASS test_local_char_string_partial_init_zero_fills "
          f"(cycles={cycles}, R0={proc.r0})")


def test_local_full_initializer():
    source = """
int main() {
    int arr[4] = {11, 22, 33, 44};
    return arr[0] + arr[1] + arr[2] + arr[3];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=110)
    print(f"PASS test_local_full_initializer (cycles={cycles})")


def test_local_sizeless_initializer():
    source = """
int main() {
    int arr[] = {5, 10, 15, 20};
    return sizeof(arr) * 100 + arr[0] + arr[1] + arr[2] + arr[3];
}
"""
    # sizeof = 4 elems * 2 bytes = 8 => 800 + 50
    proc, cycles, mem = compile_and_run(source, expected_p0=850)
    print(f"PASS test_local_sizeless_initializer (cycles={cycles})")


def test_global_partial_initializer_zero_fills():
    """Global int g[8] = {9,8,7}: DW data prefix + DS zero remainder."""
    source = """
int g[8] = {9, 8, 7};

int main() {
    g[7] = 1;
    return g[0] + g[1] + g[2] + g[3] + g[4] + g[5] + g[6] + g[7] * 10;
}
"""
    # 9+8+7 + zeros + 1*10 = 34
    proc, cycles, mem = compile_and_run(source, expected_r0=34)
    print(f"PASS test_global_partial_initializer_zero_fills (cycles={cycles})")


def test_global_char_partial_init():
    source = """
char msg[12] = "Nova";

int main() {
    return msg[0] + msg[3] + msg[11] * 2;   // 78+97+0 = 175
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=175)
    print(f"PASS test_global_char_partial_init (cycles={cycles})")


def test_overlong_local_initializer_rejected():
    compile_rejected("""
int main() {
    int arr[3] = {1, 2, 3, 4, 5};
    return arr[0];
}
""")
    print("PASS test_overlong_local_initializer_rejected")


def test_overlong_global_initializer_rejected():
    compile_rejected("""
int g[3] = {1, 2, 3, 4};

int main() {
    return g[0];
}
""")
    print("PASS test_overlong_global_initializer_rejected")


def test_zero_and_negative_sizes_rejected():
    compile_rejected("int main() { int a[0]; return 0; }")
    compile_rejected("int main() { int a[-2]; return 0; }")
    print("PASS test_zero_and_negative_sizes_rejected")


def test_nonconstant_size_rejected():
    compile_rejected("""
int main() {
    int n = 4;
    int a[n];
    return 0;
}
""")
    print("PASS test_nonconstant_size_rejected")


def test_enum_constant_size_still_works():
    source = """
enum { SIZE = 4 };

int main() {
    int a[SIZE] = {1, 2, 3, 4};
    return a[0] + a[1] + a[2] + a[3];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_enum_constant_size_still_works (cycles={cycles})")


def test_sizeof_matches_declared_size_with_partial_init():
    source = """
int main() {
    int arr[8] = {1, 2, 3};
    return sizeof(arr) + arr[0] + arr[2];
}
"""
    # 16 + 1 + 3 = 20
    proc, cycles, mem = compile_and_run(source, expected_r0=20)
    print(f"PASS test_sizeof_matches_declared_size_with_partial_init "
          f"(cycles={cycles})")


# ---------------------------------------------------------------------------
# Element access
# ---------------------------------------------------------------------------

def test_variable_index_roundtrip():
    source = """
int main() {
    int arr[6];
    int i;
    int sum;
    for (i = 0; i < 6; i++) {
        arr[i] = i * i;
    }
    sum = 0;
    for (i = 0; i < 6; i++) {
        sum += arr[i];
    }
    return sum;   // 0+1+4+9+16+25 = 55
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f"PASS test_variable_index_roundtrip (cycles={cycles})")


def test_expression_and_nested_index():
    source = """
int main() {
    int arr[5] = {2, 4, 6, 8, 10};
    int i = 1;
    arr[i + 2] = 7;          // arr[3] = 7
    return arr[arr[0]] + arr[3] + arr[i * 2];
             // arr[2]=6 + 7 + arr[2]=6 => 19
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=19)
    print(f"PASS test_expression_and_nested_index (cycles={cycles})")


def test_char_array_byte_precision():
    """Byte stores/loads must not contaminate neighboring cells."""
    source = """
int main() {
    char c[4];
    c[0] = 0xF0;
    c[1] = 0x0F;
    c[2] = 0xAA;
    c[3] = 0x55;
    if (c[0] != 0xF0) return 1;
    if (c[1] != 0x0F) return 2;
    if (c[2] != 0xAA) return 3;
    if (c[3] != 0x55) return 4;
    return 42;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_char_array_byte_precision (cycles={cycles})")


def test_array_element_as_argument():
    source = """
int doubler(int v) {
    return v * 2;
}

int main() {
    int arr[3] = {5, 10, 15};
    return doubler(arr[0]) + doubler(arr[1]) + doubler(arr[2]);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=60)
    print(f"PASS test_array_element_as_argument (cycles={cycles})")


def test_array_decay_to_pointer_param():
    """Arrays decay to their base address when passed to functions."""
    source = """
int sum_range(int arr[], int n) {
    int i;
    int s = 0;
    for (i = 0; i < n; i++) {
        s += arr[i];
    }
    return s;
}

int main() {
    int data[5] = {1, 2, 3, 4, 5};
    return sum_range(data, 5);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_array_decay_to_pointer_param (cycles={cycles})")


def test_fill_through_array_param():
    """Writes through an array parameter modify the caller's array."""
    source = """
void fill(int arr[], int n, int v) {
    int i;
    for (i = 0; i < n; i++) {
        arr[i] = v;
    }
}

int main() {
    int buf[4];
    fill(buf, 4, 7);
    return buf[0] + buf[1] + buf[2] + buf[3];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=28)
    print(f"PASS test_fill_through_array_param (cycles={cycles})")


# ---------------------------------------------------------------------------
# Compound assignment on elements
# ---------------------------------------------------------------------------

def test_compound_ops_on_elements():
    source = """
int main() {
    int arr[3];
    arr[0] = 100;
    arr[1] = 7;
    arr[2] = 9;
    arr[0] -= 58;      // 42
    arr[1] *= 6;       // 42
    arr[2] <<= 2;      // 36
    arr[2] >>= 1;      // 18
    arr[2] += 24;      // 42
    return arr[0] + arr[1] + arr[2];   // 126 -> R0 = 126
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=126)
    print(f"PASS test_compound_ops_on_elements (cycles={cycles})")


def test_compound_bitwise_ops_on_elements():
    source = """
int main() {
    int v[2];
    v[0] = 0xF0;
    v[1] = 0x0F;
    v[0] |= 0x0F;      // 0xFF
    v[1] &= 0x3C;      // 0x0C
    v[0] ^= 0x0F;      // 0xF0
    v[1] %= 5;         // 12 % 5 = 2
    return v[0] + v[1];   // 242
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=242)
    print(f"PASS test_compound_bitwise_ops_on_elements (cycles={cycles})")


def test_compound_with_expression_rhs():
    source = """
int main() {
    int arr[3] = {10, 20, 30};
    arr[1] += arr[0] * 2;          // 20 + 20 = 40
    arr[2] -= arr[1] / 4;          // 30 - 10 = 20
    return arr[1] + arr[2];        // 60
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=60)
    print(f"PASS test_compound_with_expression_rhs (cycles={cycles})")


def test_global_element_compound():
    source = """
int slots[4];

void bump(int idx) {
    slots[idx] += 5;
}

int main() {
    bump(0);
    bump(2);
    bump(2);
    return slots[0] + slots[1] + slots[2];   // 5+0+10 = 15
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_global_element_compound (cycles={cycles})")


# ---------------------------------------------------------------------------
# Pointer aliasing
# ---------------------------------------------------------------------------

def test_pointer_aliasing_read_write():
    source = """
int main() {
    int arr[4] = {11, 22, 33, 44};
    int *p = arr;
    p[2] = 99;
    return arr[2] + p[0] + p[3];   // 99+11+44 = 154
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=154)
    print(f"PASS test_pointer_aliasing_read_write (cycles={cycles})")


def test_char_pointer_into_buffer():
    source = """
int main() {
    char buf[6] = "abc";
    char *cp = buf;
    cp[3] = 'd';
    return cp[0] + cp[3];   // 97+100 = 197
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=197)
    print(f"PASS test_char_pointer_into_buffer (cycles={cycles})")


# ---------------------------------------------------------------------------
# Struct arrays
# ---------------------------------------------------------------------------

def test_local_struct_array_flat_init():
    source = """
struct Point { int x; int y; };

int main() {
    struct Point pts[2] = {10, 20, 30, 40};
    return pts[0].y + pts[1].x + sizeof(pts);   // 20+30+8 = 58
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=58)
    print(f"PASS test_local_struct_array_flat_init (cycles={cycles})")


def test_local_struct_array_partial_init_zero_fills():
    source = """
struct Point { int x; int y; };

int main() {
    struct Point pts[3] = {10, 20, 30};
    // pts = {x:10,y:20}, {x:30,y:0}, {x:0,y:0}
    return pts[0].y + pts[1].x + pts[1].y + pts[2].x + pts[2].y;
           // 20+30+0+0+0 = 50
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=50)
    print(f"PASS test_local_struct_array_partial_init_zero_fills "
          f"(cycles={cycles})")


def test_local_sizeless_struct_array():
    source = """
struct Point { int x; int y; };

int main() {
    struct Point pts[] = {10, 20, 30, 40};
    return sizeof(pts) * 10 + pts[1].y;   // 80 + 40 = 120
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=120)
    print(f"PASS test_local_sizeless_struct_array (cycles={cycles})")


def test_global_struct_array_partial_init_zero_fills():
    source = """
struct Point { int x; int y; };
struct Point tri[3] = {1, 2, 3};

int main() {
    return tri[0].x + tri[0].y + tri[1].x + tri[1].y + tri[2].x + tri[2].y;
           // 1+2+3+0+0+0 = 6
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_global_struct_array_partial_init_zero_fills "
          f"(cycles={cycles})")


def test_global_struct_array_overfull_rejected():
    compile_rejected("""
struct Point { int x; int y; };
struct Point tri[2] = {1, 2, 3, 4, 5, 6};

int main() { return 0; }
""")
    print("PASS test_global_struct_array_overfull_rejected")


def test_local_struct_array_overfull_rejected():
    compile_rejected("""
struct Point { int x; int y; };

int main() {
    struct Point pts[2] = {1, 2, 3, 4, 5};
    return 0;
}
""")
    print("PASS test_local_struct_array_overfull_rejected")


def test_struct_array_member_compound_and_loop():
    source = """
struct Point { int x; int y; };

int main() {
    struct Point pts[3];
    int i;
    for (i = 0; i < 3; i++) {
        pts[i].x = i + 1;
        pts[i].y = i * 10;
    }
    pts[1].x += 5;            // 2+5 = 7
    pts[2].y *= 2;            // 40
    return pts[0].x + pts[1].x + pts[2].y;   // 1+7+40 = 48
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=48)
    print(f"PASS test_struct_array_member_compound_and_loop (cycles={cycles})")


# ---------------------------------------------------------------------------
# Interrupt-handler (ISR) array codegen
# ---------------------------------------------------------------------------

def _isr_source(isr_body, extra_globals=""):
    return ("int total;\n"
            "int ok;\n"
            + extra_globals +
            "\n"
            "void timer_interrupt() {\n"
            + isr_body +
            "    iret();\n"
            "}\n"
            "\n"
            "int main() {\n"
            "    sti();\n"
            "    set_timer(0, 5000, 2, 3);\n"
            "    while (1) {\n"
            "        if (ok == 1) {\n"
            "            return 42;\n"
            "        }\n"
            "    }\n"
            "}\n")


def _run_isr(source, max_cycles=2000000):
    asm_path = _compile_source(source)
    bin_path = asm_path.replace('.asm', '.bin')
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycle = 0
        while cycle < max_cycles and not proc.halted:
            proc.step()
            cycle += 1
        return proc, cycle, mem
    finally:
        _cleanup([asm_path, bin_path, asm_path.replace('.asm', '.org'),
                  asm_path.replace('.asm', '.sym')])


def _assert_isr_ok(proc, cycles, label):
    assert proc.halted, f"{label}: ISR program never halted (cycles={cycles})"
    assert proc.p0 == 42, (
        f"{label}: ISR array codegen corrupted state: "
        f"P0={proc.p0} (expected 42)")


def test_isr_array_assignment_deep_rhs():
    """Regression: inside timer_interrupt the target index register cannot
    be PUSH-protected (the stack holds the SP-relative frame); an RHS with
    several array reads used to wrap the round-robin register counter onto
    the index register and store through the wrong element."""
    source = _isr_source("""
    int buf[4];
    buf[0] = 10;
    buf[1] = 20;
    buf[2] = 30;
    buf[3] = buf[0] + buf[1] + buf[2];
    total = buf[3];
    if (total == 60) {
        ok = 1;
    }
""")
    proc, cycles, mem = _run_isr(source)
    _assert_isr_ok(proc, cycles, "test_isr_array_assignment_deep_rhs")
    print(f"PASS test_isr_array_assignment_deep_rhs (cycles={cycles})")


def test_isr_array_compound_assignment():
    """Compound assignment in an ISR with an array-reading RHS."""
    source = _isr_source("""
    int buf[4];
    buf[0] = 10;
    buf[1] = 20;
    buf[2] = 30;
    buf[2] += buf[0] + buf[1];   // 60
    total = buf[2];
    if (total == 60) {
        ok = 1;
    }
""")
    proc, cycles, mem = _run_isr(source)
    _assert_isr_ok(proc, cycles, "test_isr_array_compound_assignment")
    print(f"PASS test_isr_array_compound_assignment (cycles={cycles})")


def test_isr_array_shift_compound_assignment():
    source = _isr_source("""
    int buf[2];
    buf[0] = 3;
    buf[1] = 96;
    buf[0] <<= 2;     // 12
    buf[1] >>= 2;     // 24
    total = buf[0] + buf[1];
    if (total == 36) {
        ok = 1;
    }
""")
    proc, cycles, mem = _run_isr(source)
    _assert_isr_ok(proc, cycles, "test_isr_array_shift_compound_assignment")
    print(f"PASS test_isr_array_shift_compound_assignment (cycles={cycles})")


def test_isr_global_array_update():
    source = _isr_source("""
    hits[0] += 2;
    hits[1]++;
    total = hits[0] + hits[1];
    if (total >= 12) {
        ok = 1;
    }
""", extra_globals="int hits[2];\n")
    proc, cycles, mem = _run_isr(source, max_cycles=4000000)
    _assert_isr_ok(proc, cycles, "test_isr_global_array_update")
    print(f"PASS test_isr_global_array_update (cycles={cycles})")


def test_isr_struct_array_and_decay():
    """Regression: ISR array addressing must use the struct stride (not
    elem_size), and array decay inside an ISR must yield the SP-relative
    base consistent with element addressing."""
    source = _isr_source("""
    struct Pair ps[2];
    struct Pair *q;
    ps[0].a = 11;
    ps[0].b = 22;
    ps[1].a = 33;
    ps[1].b = 44;
    q = ps;
    if (ps[1].b == 44 && q[0] + q[3] == 55) {
        ok = 1;
    }
""", extra_globals="struct Pair { int a; int b; };\n")
    proc, cycles, mem = _run_isr(source)
    _assert_isr_ok(proc, cycles, "test_isr_struct_array_and_decay")
    print(f"PASS test_isr_struct_array_and_decay (cycles={cycles})")


def test_isr_scalar_struct_members():
    """Regression guard: scalar struct locals inside an ISR keep both
    members at their correct SP-relative slots."""
    source = _isr_source("""
    struct Pair p;
    p.a = 11;
    p.b = 22;
    if (p.a + p.b == 33) {
        ok = 1;
    }
""", extra_globals="struct Pair { int a; int b; };\n")
    proc, cycles, mem = _run_isr(source)
    _assert_isr_ok(proc, cycles, "test_isr_scalar_struct_members")
    print(f"PASS test_isr_scalar_struct_members (cycles={cycles})")


if __name__ == "__main__":
    test_local_partial_initializer_reserves_declared_size()
    test_local_char_string_partial_init_zero_fills()
    test_local_full_initializer()
    test_local_sizeless_initializer()
    test_global_partial_initializer_zero_fills()
    test_global_char_partial_init()
    test_overlong_local_initializer_rejected()
    test_overlong_global_initializer_rejected()
    test_zero_and_negative_sizes_rejected()
    test_nonconstant_size_rejected()
    test_enum_constant_size_still_works()
    test_sizeof_matches_declared_size_with_partial_init()
    test_variable_index_roundtrip()
    test_expression_and_nested_index()
    test_char_array_byte_precision()
    test_array_element_as_argument()
    test_array_decay_to_pointer_param()
    test_fill_through_array_param()
    test_compound_ops_on_elements()
    test_compound_bitwise_ops_on_elements()
    test_compound_with_expression_rhs()
    test_global_element_compound()
    test_pointer_aliasing_read_write()
    test_char_pointer_into_buffer()
    test_local_struct_array_flat_init()
    test_local_struct_array_partial_init_zero_fills()
    test_local_sizeless_struct_array()
    test_global_struct_array_partial_init_zero_fills()
    test_global_struct_array_overfull_rejected()
    test_local_struct_array_overfull_rejected()
    test_struct_array_member_compound_and_loop()
    test_isr_array_assignment_deep_rhs()
    test_isr_array_compound_assignment()
    test_isr_array_shift_compound_assignment()
    test_isr_global_array_update()
    test_isr_struct_array_and_decay()
    test_isr_scalar_struct_members()
    print("All array implementation tests passed!")
