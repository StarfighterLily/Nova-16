"""
Regression tests for NoBASIC list (L1, L2, ...) code generation.

Covers a register-allocation bug in generate_list_access / generate_list_store:
the index value could be silently clobbered before being copied into P2 when
the index expression's result happened to already reside in register P1 (the
same register the descriptor address is loaded into just before the call to
_nb_list_elem_addr). Under register pressure this produced a wrong element
address (or accidentally used the descriptor address as an index) instead of
raising an error, so it needs an explicit regression test rather than relying
on it merely raising register-exhaustion.
"""

import sys
from pathlib import Path


from compiler.codegen.generator import CodeGenerator
from compiler.parser.ast import ListAccessExpr, VariableExpr
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer


def parse_and_generate(code: str) -> tuple:
    lexer = Lexer()
    parser = Parser()
    tokens = lexer.tokenize(code)
    ast = parser.parse(tokens)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    generator = CodeGenerator()
    asm = generator.generate(ast)
    return asm, generator


def _make_pressured_generator() -> CodeGenerator:
    """Build a generator where the list index's variable lives in P2 and every
    other scratch register (R0-R9, P0) is already busy, forcing the index
    expression's temporary to land in P1 - the same register
    generate_list_access/store use to hold the list descriptor address."""
    gen = CodeGenerator()
    gen.current_output = gen.output
    gen.program_counter = 0
    gen.live_at_point = {}

    gen.var_reg['I'] = 'P2'
    gen.register_usage['P2'] = True
    for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'P0']:
        gen.register_usage[reg] = True
    return gen


def _mov_index_line_index(lines, mov_line):
    return next(i for i, line in enumerate(lines) if line.strip() == mov_line)


class TestListIndexRegisterSafety:
    """The index value must be copied into P2 before P1 is repurposed for the
    descriptor address, no matter which register the index computation used."""

    def test_list_access_does_not_clobber_index_in_p1(self):
        gen = _make_pressured_generator()
        desc_addr = gen._get_or_create_list_descriptor('L1')
        gen.generate_list_access(ListAccessExpr('L1', VariableExpr('I')), 'R0')

        lines = gen.current_output
        # The index's value starts in P1 (copied from I's home register P2).
        assert lines[0].strip() == "MOV P1, P2"

        move_to_p2 = _mov_index_line_index(lines, "MOV P2, P1")
        move_desc_into_p1 = _mov_index_line_index(lines, f"MOV P1, 0x{desc_addr:04X}")

        # P2 must be loaded with the real index (from P1) before P1 is
        # overwritten with the descriptor address, or the call receives the
        # descriptor address as its index instead of the intended value.
        assert move_to_p2 < move_desc_into_p1

    def test_list_store_does_not_clobber_index_in_p1(self):
        gen = _make_pressured_generator()
        desc_addr = gen._get_or_create_list_descriptor('L1')
        gen.generate_list_store(ListAccessExpr('L1', VariableExpr('I')), 'R1')

        lines = gen.current_output
        move_to_p2 = _mov_index_line_index(lines, "MOV P2, P1")
        move_desc_into_p1 = _mov_index_line_index(lines, f"MOV P1, 0x{desc_addr:04X}")
        assert move_to_p2 < move_desc_into_p1

    def test_list_access_index_already_in_p2_is_unaffected(self):
        """Common/fast path: index lands directly in P2, no extra MOV needed."""
        gen = CodeGenerator()
        gen.current_output = gen.output
        gen.program_counter = 0
        gen.live_at_point = {}

        desc_addr = gen._get_or_create_list_descriptor('L1')
        gen.generate_list_access(ListAccessExpr('L1', VariableExpr('I')), 'R0')

        lines = gen.current_output
        assert not any(line.strip() == "MOV P2, P2" for line in lines)
        assert any(line.strip() == f"MOV P1, 0x{desc_addr:04X}" for line in lines)


class TestListEndToEndCodegen:
    """Sanity check that ordinary list access/store still compiles cleanly
    through the full pipeline after the reordering fix."""

    def test_variable_indexed_list_access_and_store(self):
        code = """
        For i = 1 To 5
            L1(i) = i * 2
        Next
        For i = 1 To 5
            Disp L1(i)
        Next
        """
        asm, generator = parse_and_generate(code)
        assert "_nb_list_elem_addr" in asm
        assert "CALL _nb_list_elem_addr" in asm


class TestListLogicalLength:
    """Regression tests for the logical-length concept in the list runtime.

    The descriptor grew a 3rd word (+4: length) alongside base (+0) and
    capacity (+2). Capacity is a growth-allocator implementation detail (it
    rounds up, e.g. to 8, on first write) and must never leak into SUM, MEAN,
    FILL, SORTA, SORTD, REVERSE or DIM - those must only ever see `length`,
    the count of elements actually written via indexed assignment or SEQ.
    """

    def test_descriptor_is_six_bytes_with_length_word(self):
        gen = CodeGenerator()
        before = gen._reserve_data_memory(0, "probe")
        desc_addr = gen._get_or_create_list_descriptor('L1')
        after = gen._reserve_data_memory(0, "probe2")
        assert after - before == 6
        assert desc_addr == before

    def test_runtime_init_zeroes_all_three_words(self):
        code = "L1(1) = 5"
        asm, generator = parse_and_generate(code)
        desc_addr = generator.list_descriptors['L1']
        # base, capacity, and length must all be zeroed at start-up.
        assert asm.count(f"MOV P0, 0x{desc_addr:04X}") >= 1
        zero_writes = asm.count("MOV [P0], P1")
        assert zero_writes >= 3

    def test_indexed_store_extends_length_but_never_shrinks_it(self):
        gen = CodeGenerator()
        gen.current_output = gen.output
        gen.program_counter = 0
        gen.live_at_point = {}
        desc_addr = gen._get_or_create_list_descriptor('L1')
        gen.generate_list_store(ListAccessExpr('L1', VariableExpr('I')), 'R0')

        lines = [line.strip() for line in gen.current_output]
        length_addr_line = f"MOV P3, 0x{desc_addr + 4:04X}"
        assert length_addr_line in lines
        # Extension must be conditional (compare-then-store), not unconditional.
        idx = lines.index(length_addr_line)
        following = lines[idx:idx + 5]
        assert "MOV P4, [P3]" in following
        assert "CMP P2, P4" in following
        assert any(op.startswith("JLE") for op in following)
        assert "MOV [P3], P2" in following

    def test_bulk_builtins_read_length_not_capacity(self):
        """SUM/MEAN/FILL/SORTA/SORTD/REVERSE/DIM share a preamble that must
        read the descriptor's length word (offset +4), not the raw capacity
        word (offset +2), or padding left over from growth leaks into results.

        (The growth helper _nb_list_elem_addr legitimately reads capacity via
        the same 2-INC pattern internally, so this checks the specific
        preamble anchored on "MOV P5, [P6]" rather than the whole program.)"""
        for call in ["Sum(L1)", "Mean(L1)", "Dim(L1)", "SortA(L1)", "SortD(L1)", "Reverse(L1)"]:
            code = f"Fill(L1, 0)\nX = {call}"
            asm, _ = parse_and_generate(code)
            anchor = "MOV P5, [P6]"
            idx = asm.index(anchor)
            preamble = asm[idx:idx + len(anchor) + 200]
            assert preamble.startswith(
                "MOV P5, [P6]\nMOV P0, P6\nINC P0\nINC P0\nINC P0\nINC P0\nMOV P4, [P0]"
            ), (call, preamble)

    def test_seq_grows_list_through_shared_helper_and_sets_exact_length(self):
        code = "Seq(L1, N, 1, 5)"
        asm, generator = parse_and_generate(code)
        desc_addr = generator.list_descriptors['L1']
        assert "CALL _nb_list_elem_addr" in asm
        # Length is set to the exact element count produced, not merely extended.
        assert f"MOV P0, 0x{desc_addr + 4:04X}" in asm
        assert "MOV [P0], P1" in asm

    def test_seq_handles_descending_step_termination(self):
        """A negative step must be checked against its own termination
        (current < end), not silently fall through the ascending check only
        (the pre-existing SEQ had no descending-step bound at all)."""
        code = "Seq(L1, N, 10, 2, Stp)"
        asm, _ = parse_and_generate(code)
        assert "JLT" in asm
        assert "JGT" in asm
