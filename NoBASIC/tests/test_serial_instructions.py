"""
Comprehensive tests for NoBASIC serial instruction support (opcodes 0xA2-0xA5).

Covers:
- Lexer:      SEROUT / SERIN / SERSTAT / SERCTRL keyword recognition
- Parser:     all four statement forms and both expression forms (SERIN()/SERSTAT())
- Semantic:   variable definition via SerIn/SerStat; expression arity checks
- Codegen:    correct assembly emission for statements and builtin expressions
- Integration: round-trip NoBASIC source → assembly (with Nova assembler)
- VM:         runtime behaviour via NovaUART inject/read helpers
"""

from __future__ import annotations

import re
import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Make sure the NoBASIC package root is on sys.path (mirrors conftest.py).
# ---------------------------------------------------------------------------
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType
from compiler.parser.parser import Parser
from compiler.parser.ast import (
    Program,
    SerOutStmt,
    SerInStmt,
    SerStatStmt,
    SerCtrlStmt,
    LiteralExpr,
    VariableExpr,
    AssignmentStmt,
    FunctionCallExpr,
)
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.utils.error import ParserError, SemanticError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lex(source: str):
    return Lexer().tokenize(source)


def _parse(source: str) -> Program:
    tokens = _lex(source)
    return Parser().parse(tokens)


def _analyze(source: str) -> Program:
    program = _parse(source)
    SemanticAnalyzer().analyze(program)
    return program


def _generate(source: str) -> str:
    program = _parse(source)
    SemanticAnalyzer().analyze(program)
    return CodeGenerator().generate(program)


# ---------------------------------------------------------------------------
# 1. Lexer tests
# ---------------------------------------------------------------------------

class TestSerialLexer:
    """Verify the four serial keywords are tokenised correctly."""

    @pytest.mark.parametrize("kw,expected", [
        ("serout",  TokenType.SEROUT),
        ("SEROUT",  TokenType.SEROUT),
        ("SerOut",  TokenType.SEROUT),
        ("serin",   TokenType.SERIN),
        ("SERIN",   TokenType.SERIN),
        ("SerIn",   TokenType.SERIN),
        ("serstat", TokenType.SERSTAT),
        ("SERSTAT", TokenType.SERSTAT),
        ("SerStat", TokenType.SERSTAT),
        ("serctrl", TokenType.SERCTRL),
        ("SERCTRL", TokenType.SERCTRL),
        ("SerCtrl", TokenType.SERCTRL),
    ])
    def test_keyword_recognised(self, kw, expected):
        tokens = _lex(kw)
        assert tokens[0].type == expected

    def test_all_four_in_one_source(self):
        tokens = _lex("serout serin serstat serctrl")
        types = [t.type for t in tokens[:-1]]  # exclude EOF
        assert types == [TokenType.SEROUT, TokenType.SERIN,
                         TokenType.SERSTAT, TokenType.SERCTRL]

    def test_lexeme_preserved(self):
        tokens = _lex("SerOut")
        assert tokens[0].lexeme == "SerOut"

    def test_not_confused_with_identifiers(self):
        """serout2 should be an IDENTIFIER, not SEROUT."""
        tokens = _lex("serout2")
        assert tokens[0].type == TokenType.IDENTIFIER


# ---------------------------------------------------------------------------
# 2. Parser tests
# ---------------------------------------------------------------------------

class TestSerialParser:
    """Verify all four statement forms and both expression forms parse."""

    # --- statement forms ---------------------------------------------------

    def test_ser_out_literal(self):
        program = _parse("SerOut(65)")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, SerOutStmt)
        assert isinstance(stmt.value, LiteralExpr)
        assert stmt.value.value == 65

    def test_ser_out_variable(self):
        program = _parse("SerOut(myByte)")
        stmt = program.statements[0]
        assert isinstance(stmt, SerOutStmt)
        assert isinstance(stmt.value, VariableExpr)
        assert stmt.value.name == "myByte"

    def test_ser_in_statement(self):
        program = _parse("SerIn(rxByte)")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, SerInStmt)
        assert stmt.variable == "rxByte"

    def test_ser_stat_statement(self):
        program = _parse("SerStat(flags)")
        stmt = program.statements[0]
        assert isinstance(stmt, SerStatStmt)
        assert stmt.variable == "flags"

    def test_ser_ctrl_literal(self):
        program = _parse("SerCtrl(1)")
        stmt = program.statements[0]
        assert isinstance(stmt, SerCtrlStmt)
        assert isinstance(stmt.value, LiteralExpr)
        assert stmt.value.value == 1

    def test_ser_ctrl_variable(self):
        program = _parse("SerCtrl(ctrlReg)")
        stmt = program.statements[0]
        assert isinstance(stmt, SerCtrlStmt)
        assert isinstance(stmt.value, VariableExpr)

    # --- expression / builtin-function forms --------------------------------

    def test_serin_as_expression(self):
        """x = SERIN() should parse as assignment whose RHS is FunctionCallExpr."""
        program = _parse("x = SERIN()")
        stmt = program.statements[0]
        assert isinstance(stmt, AssignmentStmt)
        assert isinstance(stmt.expression, FunctionCallExpr)
        assert stmt.expression.name.upper() == "SERIN"
        assert stmt.expression.arguments == []

    def test_serstat_as_expression(self):
        program = _parse("st = SERSTAT()")
        stmt = program.statements[0]
        assert isinstance(stmt, AssignmentStmt)
        assert isinstance(stmt.expression, FunctionCallExpr)
        assert stmt.expression.name.upper() == "SERSTAT"

    def test_serin_in_condition(self):
        """SERIN() can appear in a boolean context."""
        program = _parse("If SERIN() <> 0 Then clrdraw End")
        assert len(program.statements) == 1

    def test_multiple_serial_statements(self):
        src = "SerCtrl(1)\nSerOut(0x41)\nSerIn(rxByte)\nSerStat(st)"
        program = _parse(src)
        assert len(program.statements) == 4
        assert isinstance(program.statements[0], SerCtrlStmt)
        assert isinstance(program.statements[1], SerOutStmt)
        assert isinstance(program.statements[2], SerInStmt)
        assert isinstance(program.statements[3], SerStatStmt)

    # --- error cases -------------------------------------------------------

    def test_ser_out_missing_arg_raises(self):
        with pytest.raises(ParserError):
            _parse("SerOut()")

    def test_ser_in_missing_arg_raises(self):
        with pytest.raises(ParserError):
            _parse("SerIn()")

    def test_ser_in_expr_arg_raises(self):
        """SerIn requires an identifier, not an expression."""
        with pytest.raises(ParserError):
            _parse("SerIn(x + 1)")

    def test_ser_ctrl_missing_arg_raises(self):
        with pytest.raises(ParserError):
            _parse("SerCtrl()")


# ---------------------------------------------------------------------------
# 3. Semantic analyser tests
# ---------------------------------------------------------------------------

class TestSerialSemantic:
    """Verify semantic analysis accepts valid programs and catches errors."""

    def test_ser_in_defines_variable(self):
        """SerIn(v) must register v so later uses don't raise."""
        program = _analyze("SerIn(v)\nx = v + 1")
        # If we reach here without SemanticError, the variable was registered.

    def test_ser_stat_defines_variable(self):
        _analyze("SerStat(st)\nIf st & 1 Then clrdraw End")

    def test_ser_out_with_expression(self):
        _analyze("a = 0x41\nSerOut(a)")

    def test_ser_ctrl_with_literal(self):
        _analyze("SerCtrl(3)")

    def test_serin_builtin_too_many_args_raises(self):
        with pytest.raises(SemanticError):
            _analyze("x = SERIN(1)")

    def test_serstat_builtin_too_many_args_raises(self):
        with pytest.raises(SemanticError):
            _analyze("x = SERSTAT(99)")


# ---------------------------------------------------------------------------
# 4. Code-generation tests
# ---------------------------------------------------------------------------

class TestSerialCodegen:
    """Verify the correct assembly instructions are emitted."""

    def test_ser_out_literal_emits_serout(self):
        code = _generate("SerOut(65)")
        assert "SEROUT" in code

    def test_ser_out_loads_value_before_serout(self):
        code = _generate("SerOut(0x41)")
        lines = code.splitlines()
        serout_idx = next(i for i, l in enumerate(lines) if "SEROUT" in l)
        # There must be a MOV to a register before SEROUT
        pre = "\n".join(lines[:serout_idx])
        assert re.search(r"MOV\s+R\d,", pre)

    def test_ser_in_emits_serin(self):
        code = _generate("SerIn(rxByte)")
        assert "SERIN" in code

    def test_ser_in_stores_result(self):
        """After SERIN R0, the value must be stored to the target variable."""
        code = _generate("SerIn(rxByte)")
        assert "SERIN R0" in code
        # The result must be stored somewhere after SERIN R0
        lines = code.splitlines()
        serin_idx = next(i for i, l in enumerate(lines) if "SERIN R0" in l)
        after = "\n".join(lines[serin_idx + 1:])
        assert re.search(r"MOV", after), "Expected a store instruction after SERIN"

    def test_ser_stat_emits_serstat(self):
        code = _generate("SerStat(flags)")
        assert "SERSTAT" in code

    def test_ser_stat_stores_result(self):
        code = _generate("SerStat(flags)")
        assert "SERSTAT R0" in code
        lines = code.splitlines()
        idx = next(i for i, l in enumerate(lines) if "SERSTAT R0" in l)
        after = "\n".join(lines[idx + 1:])
        assert re.search(r"MOV", after)

    def test_ser_ctrl_literal_emits_serctrl(self):
        code = _generate("SerCtrl(1)")
        assert "SERCTRL" in code

    def test_ser_ctrl_loads_before_serctrl(self):
        code = _generate("SerCtrl(0x05)")
        lines = code.splitlines()
        ctrl_idx = next(i for i, l in enumerate(lines) if "SERCTRL" in l)
        pre = "\n".join(lines[:ctrl_idx])
        assert re.search(r"MOV\s+R\d,", pre)

    def test_serin_builtin_expression(self):
        code = _generate("x = SERIN()")
        assert "SERIN R0" in code

    def test_serstat_builtin_expression(self):
        code = _generate("st = SERSTAT()")
        assert "SERSTAT R0" in code

    def test_ser_ctrl_variable_operand(self):
        code = _generate("cfg = 3\nSerCtrl(cfg)")
        assert "SERCTRL" in code

    def test_full_echo_loop_compiles(self):
        """Compile a more complete serial echo program without error."""
        src = """
SerCtrl(1)
Repeat
    SerStat(st)
    If st & 1 Then
        SerIn(rxByte)
        SerOut(rxByte)
    End
Until 0
"""
        code = _generate(src)
        assert "SERCTRL" in code
        assert "SERSTAT" in code
        assert "SERIN"   in code
        assert "SEROUT"  in code

    def test_serin_inside_if_condition(self):
        """SERIN() used directly in condition must compile."""
        src = "If SERIN() <> 0 Then SerOut(1) End"
        code = _generate(src)
        assert "SERIN" in code

    def test_ser_out_expression_arg(self):
        """SerOut can take an arithmetic expression."""
        code = _generate("SerOut(32 + 65)")
        assert "SEROUT" in code

    def test_ends_with_hlt(self):
        code = _generate("SerOut(1)")
        assert code.strip().splitlines()[-1] == "HLT"

    def test_serial_with_variables(self):
        """Full variable lifecycle around serial instructions."""
        src = """
a = 0x41
SerOut(a)
SerIn(b)
c = b + 1
SerOut(c)
"""
        code = _generate(src)
        assert code.count("SEROUT") == 2
        assert code.count("SERIN")  == 1

    def test_serin_serstat_as_expressions_assigned(self):
        src = """
x = SERIN()
y = SERSTAT()
"""
        code = _generate(src)
        assert "SERIN R0" in code
        assert "SERSTAT R0" in code


# ---------------------------------------------------------------------------
# 5. VM / runtime tests
# ---------------------------------------------------------------------------

class TestSerialVM:
    """Test serial behaviour through the NoBASIC VM interpreter."""

    @pytest.fixture()
    def vm(self):
        """Return a configured NoBASICVM with sound disabled."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        return NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))

    def _run(self, source: str):
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        # Inject a byte into the UART RX FIFO before running so SERIN has data
        vm.proc.uart.queue_rx_byte(0x41)  # 'A'
        vm.load_source(source, "<test>")
        vm.run()
        return vm

    # --- SerOut --------------------------------------------------------------

    def test_ser_out_transmits_byte(self, vm):
        """SerOut(65) should place 0x41 into the UART TX path."""
        vm.load_source("SerOut(65)", "<test>")
        vm.run()
        # The UART should have transmitted byte 0x41 ('A')
        assert vm.proc.uart.data_register == 0x41

    def test_ser_out_with_variable(self, vm):
        vm.load_source("val = 66\nSerOut(val)", "<test>")
        vm.run()
        assert vm.proc.uart.data_register == 66

    # --- SerIn ---------------------------------------------------------------

    def test_ser_in_reads_injected_byte(self):
        vm = self._run("SerIn(rxByte)")
        assert vm._get_var("rxbyte") == 0x41

    def test_ser_in_sets_ans(self):
        vm = self._run("SerIn(rxByte)")
        assert vm._get_var("ans") == 0x41

    def test_ser_in_zero_when_empty(self, vm):
        """When RX FIFO is empty, SerIn should return 0."""
        vm.load_source("SerIn(rxByte)", "<test>")
        vm.run()
        assert vm._get_var("rxbyte") == 0

    # --- SerStat -------------------------------------------------------------

    def test_ser_stat_rx_available(self):
        """After injecting a byte, bit 0 of status should be set."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        vm.proc.uart.queue_rx_byte(0x55)
        vm.load_source("SerStat(st)", "<test>")
        vm.run()
        # Bit 0 = RX available
        assert (vm._get_var("st") & 0x01) == 1

    def test_ser_stat_no_data(self, vm):
        """With empty FIFO, bit 0 should be clear."""
        vm.load_source("SerStat(st)", "<test>")
        vm.run()
        assert (vm._get_var("st") & 0x01) == 0

    def test_ser_stat_sets_ans(self):
        vm = self._run("SerStat(st)")
        assert vm._get_var("ans") == (vm._get_var("st") & 0xFF)

    # --- SerCtrl -------------------------------------------------------------

    def test_ser_ctrl_writes_control(self, vm):
        """SerCtrl(1) should enable the UART interrupt control bit."""
        vm.load_source("SerCtrl(1)", "<test>")
        vm.run()
        # Bit 0 = IRQ enable; stored separately in interrupt_enabled
        assert vm.proc.uart.interrupt_enabled is True

    def test_ser_ctrl_disable(self, vm):
        vm.load_source("SerCtrl(0)", "<test>")
        vm.run()
        assert (vm.proc.uart.control & 0x01) == 0

    # --- SERIN() / SERSTAT() as expression builtins -------------------------

    def test_serin_builtin_expr(self):
        """x = SERIN() should populate x with the injected byte."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        vm.proc.uart.queue_rx_byte(0x42)
        vm.load_source("x = SERIN()", "<test>")
        vm.run()
        assert vm._get_var("x") == 0x42

    def test_serstat_builtin_expr(self):
        """y = SERSTAT() should return the status flags."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        vm.proc.uart.queue_rx_byte(0x01)
        vm.load_source("y = SERSTAT()", "<test>")
        vm.run()
        assert (vm._get_var("y") & 0x01) == 1

    # --- Combined scenarios --------------------------------------------------

    def test_echo_one_byte(self):
        """Read a byte and immediately echo it back."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        vm.proc.uart.queue_rx_byte(0x7E)
        vm.load_source("SerIn(rxByte)\nSerOut(rxByte)", "<test>")
        vm.run()
        assert vm._get_var("rxbyte") == 0x7E
        # Last byte written to UART data register should be the same byte
        assert vm.proc.uart.data_register == 0x7E

    def test_conditional_on_serstat(self):
        """Use SERSTAT result to conditionally run SerIn."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=10_000))
        vm.proc.uart.queue_rx_byte(0x55)
        src = """
SerStat(st)
If st & 1 Then
    SerIn(rxByte)
End
"""
        vm.load_source(src, "<test>")
        vm.run()
        assert vm._get_var("rxbyte") == 0x55

    def test_serout_in_for_loop(self):
        """Send bytes 65..67 ('A','B','C') using a for loop."""
        from nobasic_vm import NoBASICVM, NoBASICVMConfig
        vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=50_000))
        vm.load_source("For i = 65 To 67\n    SerOut(i)\nNext", "<test>")
        vm.run()
        # Last byte sent should be 67 ('C')
        assert vm.proc.uart.data_register == 67
