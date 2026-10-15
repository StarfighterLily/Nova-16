"""Tier 3 item 13: extended-asm operands.

    asm("template" : "=r"(out) : "r"(in), "+r"(acc), "i"(CONST));

Covers:
- "r" inputs bound to registers (evaluated left to right, including calls)
- "=r" outputs stored to every lvalue form: local, global, array element,
  struct member, pointer target
- "+r" read-write operands
- "i" compile-time constants (literal, enum, sizeof arithmetic)
- one- and two-colon operand lists, adjacent template literals, \\n splits
- extended asm in expression context (P0 result survives output stores)
- {name} variable substitution still works alongside {k}
- a bare `asm "..."` inside a ternary keeps the ':' for the ternary
- diagnostics: bad constraint, out-of-range {k}, non-constant "i",
  non-lvalue output, const output, too many register operands
- regression: block form `asm { ... }` (crashed during the rework)
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system
from astrid.errors import CompileError, CodeGenError
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, AsmBlock, AsmOperand
from astrid.codegen.codegen import CodeGenerator


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def generate(source):
    return CodeGenerator().generate(parse(source))


def run(source, max_cycles=2000000):
    """Compile, assemble and run; return P0 at halt (main's return)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    asm_path = source_path.replace('.ast', '.asm')
    bin_path = source_path.replace('.ast', '.bin')
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', asm_path]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycles = 0
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, "program did not halt"
        return proc.p0
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def _first_asm(ast):
    for stmt in ast.functions[0].body:
        if isinstance(stmt, AsmBlock):
            return stmt
    raise AssertionError("no AsmBlock in main")


# --- parser ---------------------------------------------------------------

class TestParse:
    def test_operands_are_nodes_in_source_order(self):
        ast = parse('int main(){ int r; int a; '
                    'asm("MOV {0}, {1}" : "=r"(r) : "r"(a), "i"(3)); '
                    'return r; }')
        ops = _first_asm(ast).operands
        assert [type(o) for o in ops] == [AsmOperand] * 3
        assert [o.constraint for o in ops] == ['=r', 'r', 'i']

    def test_adjacent_template_literals_fold(self):
        ast = parse('int main(){ asm("MOV P0, 1\\n" "ADD P0, 2"); return 0; }')
        assert _first_asm(ast).lines == ['MOV P0, 1', 'ADD P0, 2']

    def test_block_form_has_no_operands(self):
        ast = parse('int main(){ asm {\n MOV R0, 7\n }\n return 0; }')
        block = _first_asm(ast)
        assert block.operands == []
        assert any('R0' in line and '7' in line for line in block.lines)

    def test_bad_constraint_rejected(self):
        with pytest.raises(CompileError) as exc:
            parse('int main(){ int r; asm("NOP" : "=m"(r)); return 0; }')
        assert 'constraint' in str(exc.value)

    def test_ternary_colon_not_taken_as_operand_list(self):
        ast = parse('int main(){ int c; int x = c ? asm "MOV P0, 1" : 4; '
                    'return x; }')
        assert ast.functions[0].body  # parsed without error


# --- runtime --------------------------------------------------------------

class TestRuntime:
    def test_block_form_regression(self):
        assert run('int main(){ asm {\n MOV P0, 7\n }\n return 7; }') == 7

    def test_inputs_and_output_local(self):
        assert run('int main(){ int a = 5; int b = 9; int r; '
                   'asm("MOV {0}, {1}\\nADD {0}, {2}" '
                   ': "=r"(r) : "r"(a), "r"(b)); return r; }') == 14

    def test_single_colon_list(self):
        assert run('int main(){ int a = 4; int r; '
                   'asm("MOV {0}, {1}\\nADD {0}, {0}" : "=r"(r), "r"(a)); '
                   'return r; }') == 8

    def test_read_write_operand(self):
        assert run('int main(){ int acc = 10; asm("ADD {0}, {0}" : "+r"(acc)); '
                   'return acc; }') == 20

    def test_immediate_constants(self):
        assert run('enum { K = 30 }; struct S { int a; int b; }; '
                   'int main(){ int r; '
                   'asm("MOV {0}, {1}\\nADD {0}, {2}" '
                   ': "=r"(r) : "i"(K + 10), "i"(sizeof(struct S))); '
                   'return r; }') == 44

    def test_output_to_global(self):
        assert run('int g; int main(){ asm("MOV {0}, 321" : "=r"(g)); '
                   'return g; }') == 321

    def test_output_to_array_element(self):
        assert run('int arr[4]; int main(){ int i = 2; '
                   'asm("MOV {0}, 77" : "=r"(arr[i])); '
                   'return arr[2] + arr[1]; }') == 77

    def test_outputs_to_struct_members(self):
        assert run('struct P { int x; int y; }; int main(){ struct P p; '
                   'asm("MOV {0}, 50\\nMOV {1}, 60" : "=r"(p.y), "=r"(p.x)); '
                   'return p.x * 2 + p.y; }') == 170

    def test_output_through_pointer(self):
        assert run('int main(){ int v = 0; int *q = &v; '
                   'asm("MOV {0}, 9" : "=r"(*q)); return v; }') == 9

    def test_inputs_with_calls_do_not_clobber_each_other(self):
        assert run('int sq(int x){ return x*x; } int main(){ int a = 3; int r; '
                   'asm("MOV {0}, {1}\\nADD {0}, {2}" '
                   ': "=r"(r) : "r"(sq(a)+1), "r"(sq(4))); return r; }') == 26

    def test_six_register_operands(self):
        assert run('int main(){ int a=1; int b=2; int c=3; int d=4; int e=5; '
                   'int r; asm("MOV {0}, {1}\\nADD {0}, {2}\\nADD {0}, {3}\\n'
                   'ADD {0}, {4}\\nADD {0}, {5}" '
                   ': "=r"(r) : "r"(a), "r"(b), "r"(c), "r"(d), "r"(e)); '
                   'return r; }') == 15

    def test_expression_form_keeps_p0(self):
        assert run('int main(){ int z; '
                   'int x = asm("MOV P0, {1}\\nMOV {0}, 5" : "=r"(z) : "i"(12)); '
                   'return x * 10 + z; }') == 125

    def test_named_substitution_alongside_numbered(self):
        assert run('int main(){ int x = 33; int r; '
                   'asm("MOV {0}, {x}" : "=r"(r)); return r; }') == 33

    def test_inside_loop(self):
        assert run('int main(){ int s = 0; int i; '
                   'for (i = 1; i <= 4; i++) { '
                   'asm("ADD {0}, {1}" : "+r"(s) : "r"(i)); } '
                   'return s; }') == 10


# --- codegen diagnostics --------------------------------------------------

class TestDiagnostics:
    def test_out_of_range_placeholder(self):
        with pytest.raises(CodeGenError) as exc:
            generate('int main(){ int r; asm("MOV {0}, {3}" : "=r"(r)); '
                     'return r; }')
        assert '{3}' in str(exc.value)

    def test_non_constant_immediate(self):
        with pytest.raises(CodeGenError) as exc:
            generate('int main(){ int a = 1; asm("MOV P0, {0}" : "i"(a)); '
                     'return 0; }')
        assert 'constant' in str(exc.value)

    def test_output_must_be_lvalue(self):
        with pytest.raises(CodeGenError) as exc:
            generate('int main(){ int a = 1; asm("MOV {0}, 1" : "=r"(a + 1)); '
                     'return 0; }')
        assert 'lvalue' in str(exc.value)

    def test_const_output_rejected(self):
        with pytest.raises(CompileError):
            generate('const int K = 5; int main(){ '
                     'asm("MOV {0}, 1" : "=r"(K)); return K; }')

    def test_too_many_register_operands(self):
        args = ', '.join(f'"r"(a)' for _ in range(8))
        with pytest.raises(CodeGenError) as exc:
            generate('int main(){ int a = 1; asm("NOP" : ' + args + '); '
                     'return 0; }')
        assert 'register operands' in str(exc.value)
