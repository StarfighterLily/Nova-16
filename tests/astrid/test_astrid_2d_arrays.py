"""Tests for 2-D arrays in the Astrid compiler.

2-D arrays desugar to flat row-major storage: `int grid[rows][cols]` allocates
rows*cols elements and `grid[i][j]` compiles to `grid[i*cols + j]`.

Covers:
1. Global 2-D array with flat initializer.
2. Local 2-D array, row/column writes and reads.
3. Chained subscript assignment grid[i][j] = v.
4. Compound assignment grid[i][j] += v.
5. Flat indexing into a 2-D array (grid[k] == grid[k/cols][k%cols]).
6. char 2-D array (byte stride).
7. Loop traversal over a 2-D array (row-major order).
8. 2-D array address-of: &grid[i][j].
9. Error cases: 3-D rejected, missing dims rejected, non-2D chained
   subscript rejected with a clear message.
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
# 1. Global 2-D array with a flat initializer
# ---------------------------------------------------------------------------

def test_global_2d_initializer():
    """int m[2][3] = {1,2,3,4,5,6}; m[1][2] is element 5 (value 6)."""
    source = """
int m[2][3] = {1, 2, 3, 4, 5, 6};

int main() {
    return m[0][0] * 10000 + m[0][2] * 100 + m[1][2];  /* 1*10000+3*100+6 */
}
"""
    # 10306 needs 16 bits: P0 carries the full value, R0 only its low byte.
    proc, cycles, mem = compile_and_run(source, expected_p0=10306,
                                        expected_r0=10306 & 0xFF)
    print(f"PASS test_global_2d_initializer (cycles={cycles}, P0={proc.p0})")


def test_global_2d_runtime_write():
    """A global 2-D array written at runtime reads back row/column exact."""
    source = """
int grid[4][4];

int main() {
    grid[1][2] = 42;
    grid[3][3] = 7;
    return grid[1][2] + grid[3][3] + grid[0][0];  /* 42 + 7 + 0 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=49)
    print(f"PASS test_global_2d_runtime_write (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 2. Local 2-D array
# ---------------------------------------------------------------------------

def test_local_2d_assign_and_read():
    """Local int grid[3][3]: assignments and reads through both subscripts."""
    source = """
int main() {
    int grid[3][3];
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            grid[i][j] = i * 10 + j;
        }
    }
    return grid[0][0] * 100 + grid[1][1] * 10 + grid[2][2];
    /* 0*100 + 11*10 + 22 = 132 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=132)
    print(f"PASS test_local_2d_assign_and_read (cycles={cycles}, R0={proc.r0})")


def test_local_2d_products_16bit():
    """The 16-bit P0 return carries a product that R0 cannot hold."""
    source = """
int main() {
    int grid[3][3];
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            grid[i][j] = i * 10 + j;
        }
    }
    return grid[1][1] + grid[2][2] * 256;   /* 11 + 22*256 = 5643 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=5643)
    print(f"PASS test_local_2d_products_16bit (cycles={cycles}, P0={proc.p0})")


def test_local_2d_compound_assign():
    """grid[i][j] += v / -= v / *= v keep read-modify-write semantics."""
    source = """
int main() {
    int grid[2][2];
    grid[0][0] = 10;
    grid[0][1] = 20;
    grid[1][0] = 5;
    grid[1][1] = 6;
    grid[0][0] += 7;    /* 17 */
    grid[0][1] -= 4;    /* 16 */
    grid[1][0] *= 3;    /* 15 */
    grid[1][1] += grid[0][0];  /* 6 + 17 = 23 */
    return grid[0][0] + grid[0][1] + grid[1][0] + grid[1][1];
    /* 17 + 16 + 15 + 23 = 71 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=71)
    print(f"PASS test_local_2d_compound_assign (cycles={cycles}, R0={proc.r0})")


def test_flat_index_equivalence():
    """grid[k] is the same storage as grid[k/cols][k%cols] (flat layout)."""
    source = """
int main() {
    int grid[2][4];
    grid[1][2] = 99;        /* linear index 6 */
    int a = grid[6];        /* flat read of the same slot */
    grid[5] = 55;           /* linear write: row 1, col 1 */
    int b = grid[1][1];
    return a * 100 + b;     /* 99*100 + 55 = 9955 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=9955)
    print(f"PASS test_flat_index_equivalence (cycles={cycles}, P0={proc.p0})")


# ---------------------------------------------------------------------------
# 3. char 2-D array (byte stride)
# ---------------------------------------------------------------------------

def test_char_2d_array():
    """char map[2][3]: byte elements, chained subscripts."""
    source = """
int main() {
    char map[2][3];
    map[0][0] = 'A';
    map[1][2] = 'B';
    int sum = map[0][0] + map[1][2];   /* 65 + 66 = 131 */
    map[1][1] = 3;
    sum += map[1][1] * 3;              /* +9 -> 140 */
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=140)
    print(f"PASS test_char_2d_array (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 4. Address-of a 2-D element
# ---------------------------------------------------------------------------

def test_address_of_2d_element():
    """&grid[i][j] yields the flat slot address; write through the pointer."""
    source = """
int grid[2][3];

int main() {
    int *p = &grid[1][1];
    *p = 77;                 /* linear index 4 */
    int v = grid[1][1];      /* same slot through the 2-D form */
    int w = grid[4];         /* same slot through the flat form */
    return v * 100 + w;      /* 77*100 + 77 = 7777 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=7777)
    print(f"PASS test_address_of_2d_element (cycles={cycles}, P0={proc.p0})")


# ---------------------------------------------------------------------------
# 5. Row-major traversal order
# ---------------------------------------------------------------------------

def test_row_major_traversal():
    """Sequential writes appear as row-major rows: img[0][4]==5, img[1][0]==6."""
    source = """
int img[2][5];

int main() {
    int k = 0;
    for (int i = 0; i < 2; i++) {
        for (int j = 0; j < 5; j++) {
            img[i][j] = k + 1;
            k++;
        }
    }
    /* row 1 starts at linear index 5 -> img[1][0] == 6 */
    return img[0][4] * 100 + img[1][0];   /* 5*100 + 6 = 506 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=506)
    print(f"PASS test_row_major_traversal (cycles={cycles}, P0={proc.p0})")


# ---------------------------------------------------------------------------
# 6. 2-D array in a function call (decay to base address)
# ---------------------------------------------------------------------------

def test_2d_decay_to_pointer():
    """A 2-D array name decays to its base address; the callee indexes flat."""
    source = """
int fill_row(int *base, int row, int cols, int v) {
    for (int j = 0; j < cols; j++) {
        base[row * cols + j] = v;
    }
    return 0;
}

int main() {
    int grid[3][4];
    fill_row(grid, 2, 4, 9);   /* row 2 all 9s */
    return grid[2][0] + grid[2][3] + grid[0][0];
    /* 9 + 9 + 0 = 18 */
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=18)
    print(f"PASS test_2d_decay_to_pointer (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# 7. Error cases
# ---------------------------------------------------------------------------

def test_three_dimensions_rejected():
    """int cube[2][2][2] must be a parse error."""
    source = """
int main() {
    int cube[2][2][2];
    return 0;
}
"""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser
    tokens = Lexer(source).tokenize()
    with pytest.raises(Exception):
        Parser(tokens).parse()
    print("PASS test_three_dimensions_rejected")


def test_2d_access_on_1d_array_rejected():
    """a[i][j] on a 1-D array must fail in codegen with a clear message."""
    source = """
int main() {
    int flat[4];
    flat[0][1] = 1;
    return 0;
}
"""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser
    from astrid.codegen.codegen import CodeGenerator
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    gen = CodeGenerator()
    with pytest.raises(Exception):
        gen.generate(ast)
    print("PASS test_2d_access_on_1d_array_rejected")


def test_2d_missing_col_dimension_rejected():
    """int grid[2][] must be a parse error."""
    source = """
int main() {
    int grid[2][];
    return 0;
}
"""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser
    tokens = Lexer(source).tokenize()
    with pytest.raises(Exception):
        Parser(tokens).parse()
    print("PASS test_2d_missing_col_dimension_rejected")


if __name__ == '__main__':
    test_global_2d_initializer()
    test_global_2d_runtime_write()
    test_local_2d_assign_and_read()
    test_local_2d_products_16bit()
    test_local_2d_compound_assign()
    test_flat_index_equivalence()
    test_char_2d_array()
    test_address_of_2d_element()
    test_row_major_traversal()
    test_2d_decay_to_pointer()
    test_three_dimensions_rejected()
    test_2d_access_on_1d_array_rejected()
    test_2d_missing_col_dimension_rejected()
